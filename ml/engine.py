"""Shared ResNet18 training/evaluation engine used by CLI and background worker."""
import copy
import json
import random
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset

from ml.checkpoints import DEFAULT_PREPROCESS, preprocessing, save_checkpoint, file_sha256, load_checkpoint
from ml.dataset import ROOT, load_manifest
from ml.config import TrainingConfig
from ml.federated import aggregate, communication_bytes, partition_clients, proximal_loss
from ml.metrics import classification_metrics
from ml.models import build_resnet18
from ml.models.resnet18 import use_group_norm
from ml.privacy import PRIVACY_RNG, private_optimizer_step, privatize


class ManifestDataset(Dataset):
    def __init__(self, rows, classes, config):
        self.rows, self.classes, self.transform = rows, classes, preprocessing(config)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(ROOT / row["path"]) as image:
            tensor = self.transform(ImageOps.exif_transpose(image).convert("RGB"))
        return tensor, self.classes.index(row["label"])


def seed_everything(seed, threads=4):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True, warn_only=True)


def loader(rows, classes, preprocess, batch_size, shuffle=False, seed=42):
    return DataLoader(ManifestDataset(rows, classes, preprocess), batch_size=batch_size, shuffle=shuffle,
                      num_workers=0, generator=torch.Generator().manual_seed(seed))


def evaluate(model, data, classes):
    model.eval()
    labels, probabilities, losses = [], [], []
    start = time.perf_counter()
    with torch.no_grad():
        for x, y in data:
            logits = model(x)
            losses.append((float(torch.nn.functional.cross_entropy(logits, y)), len(y)))
            labels.extend(y.tolist())
            probabilities.extend(torch.softmax(logits, 1).tolist())
    if not labels:
        raise ValueError("Cannot evaluate an empty split")
    result = classification_metrics(labels, probabilities, classes)
    result["loss"] = sum(loss * n for loss, n in losses) / len(labels)
    result["inference_ms_per_image"] = (time.perf_counter() - start) * 1000 / len(labels)
    return result


def train_local(model, data, config, global_parameters=None, accountant_state=None, total_epochs=1):
    model.train()
    optimizer_type = torch.optim.Adam if config.get("optimizer", "adam") == "adam" else torch.optim.SGD
    optimizer = optimizer_type(model.parameters(), lr=config["learning_rate"])
    privacy = config.get("dp", {})
    engine = None
    if privacy.get("enabled"):
        model, optimizer, data, engine = privatize(model, optimizer, data, privacy, accountant_state, total_epochs)
    samples, loss_total, steps = 0, 0., 0
    for _ in range(config["local_epochs"]):
        for x, y in data:
            if engine:
                x.requires_grad_(True)
            if len(y) == 0:
                # Poisson batches may be empty. Opacus supports them; avoid undefined mean CE.
                optimizer.zero_grad()
                logits = model(x)
                loss = logits.sum()
            else:
                optimizer.zero_grad()
                loss = torch.nn.functional.cross_entropy(model(x), y)
            if global_parameters is not None and config["algorithm"] == "fedprox" and not engine:
                loss = loss + proximal_loss(model, global_parameters, config["mu"])
            loss.backward()
            if engine and global_parameters is not None and config["algorithm"] == "fedprox":
                private_optimizer_step(optimizer, model, global_parameters, config["mu"])
            else:
                optimizer.step()
            samples += len(y)
            loss_total += float(loss.detach()) * len(y)
            steps += 1
    result = {"loss": loss_total / max(samples, 1), "steps": steps, "sample_count_processed": samples}
    if engine:
        # Raw local loss is a separate, unaccounted disclosure. Do not release it.
        result["loss"] = None
        result["privacy"] = {"epsilon": engine.get_epsilon(privacy["delta"]), "delta": privacy["delta"],
            "noise_multiplier": optimizer.noise_multiplier, "max_grad_norm": privacy["max_grad_norm"],
            "sample_rate": data.sample_rate, "steps_this_round": steps,
            "cumulative_steps": sum(item[2] for item in engine.accountant.history),
            "scope": "example-level", "accountant": "RDP", "secure_rng": False}
        result["privacy"]["randomness"] = PRIVACY_RNG
        accountant_state = copy.deepcopy(engine.accountant.state_dict())
        model.remove_hooks()
        model = model._module
    return model, result, accountant_state


def run_experiment(config, output_dir, on_round=None):
    config = TrainingConfig.model_validate(config).model_dump()
    secure = config.get("secure_aggregation", False)
    if secure:
        from ml.secure_aggregation import require_runtime
        require_runtime()
    seed_everything(config["seed"], config.get("threads", 4))
    manifest_path = Path(config["manifest"])
    manifest = load_manifest(manifest_path)
    classes = manifest["classes"]
    if classes != sorted({r["label"] for r in manifest["rows"]}):
        raise ValueError("Manifest class mapping inconsistent")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Experiment output directory is not empty; use a new experiment ID to preserve prior evidence")
    preprocess = {**DEFAULT_PREPROCESS, "image_size": config["image_size"]}
    private = config.get("dp", {}).get("enabled", False)
    model = build_resnet18(len(classes), config.get("pretrained", False))
    if private or secure:
        model = use_group_norm(model)
    meta = {"architecture": "ResNet18", "classes": classes, "class_to_idx": {c: i for i, c in enumerate(classes)},
            "preprocessing": preprocess, "normalization": "groupnorm" if private or secure else "batchnorm",
            "manifest_sha256": file_sha256(manifest_path), "validation_scope": manifest["validation_scope"],
            "version": output.name, "algorithm": config["algorithm"], "research_only": True,
            "training_config": config, "privacy_randomness": PRIVACY_RNG if private else None}
    splits = {s: [r for r in manifest["rows"] if r["split"] == s] for s in ["train", "val", "test"]}
    validation = loader(splits["val"], classes, preprocess, config["batch_size"])
    clients = {"Centralized": splits["train"]} if config["algorithm"] == "centralized" else partition_clients(manifest["rows"], config["seed"], config["alpha"])
    distributions = {name: {"sample_count": len(rows), "classes": {} if private or secure else dict(Counter(r["label"] for r in rows)),
                           "class_distribution_withheld": private or secure} for name, rows in clients.items()}
    (output / "config.json").write_text(json.dumps({"config": config, "clients": distributions, "metadata": meta}, indent=2), encoding="utf-8")
    rounds, best, stale, accountants, local_metrics_noise = [], -1., 0, {}, {}
    started = time.perf_counter()
    with ExitStack() as stack:
        federation = None
        if secure:
            from ml.secure_aggregation import SecureFederation
            from ml.secure_client import HospitalTask
            tasks = {i: HospitalTask(rows, classes, preprocess, config) for i, rows in enumerate(clients.values(), 1)}
            federation = stack.enter_context(SecureFederation(tasks, [v.cpu().numpy() for v in model.state_dict().values()],
                {i: len(rows) for i, rows in enumerate(clients.values(), 1)}))
        for round_number in range(1, config["rounds"] + 1):
            round_start = time.perf_counter()
            updates, local_metrics, secure_evidence = [], {}, None
            if federation:
                reference = model.state_dict()
                arrays, released, secure_evidence = federation.aggregate([v.cpu().numpy() for v in reference.values()], round_number)
                model.load_state_dict({k: torch.from_numpy(a).to(v.dtype) for (k, v), a in zip(reference.items(), arrays, strict=True)}, strict=True)
                local_metrics = {name: released.get(i, {"loss": None, "status": "dropped"}) for i, name in enumerate(clients, 1)}
            else:
                global_params = [p.detach().clone() for p in model.parameters()]
                for name, rows in clients.items():
                    local = copy.deepcopy(model)
                    data = loader(rows, classes, preprocess, min(config["batch_size"], len(rows)), True, config["seed"] + round_number)
                    local_config = copy.deepcopy(config)
                    if name in accountants and private:
                        local_config["dp"]["noise_multiplier"] = local_metrics_noise[name]
                    local, metrics, accountant = train_local(local, data, local_config,
                        global_params if config["algorithm"] == "fedprox" else None,
                        accountants.get(name), config["rounds"] * config["local_epochs"])
                    accountants[name] = accountant
                    if private:
                        local_metrics_noise[name] = metrics["privacy"]["noise_multiplier"]
                    updates.append((len(rows), {k: v.detach().clone() for k, v in local.state_dict().items()}))
                    local_metrics[name] = metrics
                    del local
                model.load_state_dict(updates[0][1] if config["algorithm"] == "centralized" else aggregate(updates), strict=True)
            val = evaluate(model, validation, classes)
            row = {"round": round_number, "clients": local_metrics, "distributions": distributions,
                   "local_loss": None if private or secure else sum(len(clients[n]) * m["loss"] for n, m in local_metrics.items()) / sum(map(len, clients.values())),
                   "validation": val, "duration_seconds": time.perf_counter() - round_start,
                   "secure_aggregation": secure_evidence,
                   "communication_bytes": (secure_evidence["bytes_sent"] + secure_evidence["bytes_received"]) if secure else
                       (0 if config["algorithm"] == "centralized" else 2 * len(clients) * communication_bytes(model.state_dict())),
                   "communication_scope": "serialized Flower protocol messages (both directions)" if secure else "logical model tensor payload"}
            rounds.append(row)
            if private and not secure:
                torch.save(accountants, output / "accountants.pt")
            if val["macro_f1"] > best:
                best, stale = val["macro_f1"], 0
                save_checkpoint(output / "best.pt", model, {**meta, "best_round": round_number})
            else:
                stale += 1
            with (output / "rounds.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(row) + "\n")
            if on_round:
                on_round(row)
            print(f"Round {round_number}: val_accuracy={val['accuracy']:.4f}, macro_f1={val['macro_f1']:.4f}", flush=True)
            if stale >= config["patience"]:
                break
    # The held-out test is accessed once, after validation-based checkpoint selection.
    best_model, _, _ = load_checkpoint(output / "best.pt")
    test = evaluate(best_model, loader(splits["test"], classes, preprocess, config["batch_size"]), classes)
    result = {"algorithm": config["algorithm"], "test": test, "training_seconds": time.perf_counter() - started,
              "communication_bytes": sum(r["communication_bytes"] for r in rounds), "rounds_completed": len(rounds),
              "checkpoint": str((output / "best.pt").resolve()), "manifest_sha256": meta["manifest_sha256"],
              "checkpoint_sha256": file_sha256(output / "best.pt"),
              "validation_scope": manifest["validation_scope"], "classes": classes, "image_size": config["image_size"],
              "clients": distributions, "privacy": {n: r.get("privacy") for n, r in rounds[-1]["clients"].items()},
              "privacy_randomness": PRIVACY_RNG if private else None,
              "secure_aggregation": rounds[-1]["secure_aggregation"] if secure else {"status": "disabled"},
              "communication_scope": rounds[-1]["communication_scope"],
              "aggregation_framework": "Flower SecAgg+ workflow / process-isolated clients" if secure else
                  ("Flower FedAvg strategy (local in-process simulation)" if config["algorithm"] != "centralized" else None)}
    (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
