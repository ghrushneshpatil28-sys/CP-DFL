"""Privacy capabilities and Opacus DP-SGD integration."""
import importlib.util
import secrets
import torch

PRIVACY_RNG = "independent-entropy-seeded-prng"


def capabilities():
    return {"differential_privacy": {"status": "experimental" if importlib.util.find_spec("opacus") else "dependency_missing",
             "scope": "example-level per-client DP-SGD; not patient-level or client-level",
             "limitations": "Research RNG; accountant covers DP-SGD updates conditional on fixed client partitions and public sample counts. Partition construction and held-out evaluation are outside this budget. Raw local losses and class distributions are withheld. Not an audited deployment guarantee."},
            "secure_aggregation": secure_capability()}


def secure_capability():
    from ml.secure_aggregation import PROTOCOL, require_runtime
    try:
        require_runtime()
    except (ImportError, ValueError) as error:
        return {"status": "dependency_missing", "enabled": False, "reason": str(error)}
    return {"status": "Implemented / local", "enabled": True, "protocol": PROTOCOL,
        "reason": "Flower's four-stage SecAgg+ workflow and client modifier run across three separate hospital processes. Only masked vectors cross the coordinator boundary; each secure round records its protocol evidence.",
        "minimum_clients": 3, "minimum_contributors": 2, "reconstruction_threshold": 2,
        "dropout": "One client may drop after key exchange, including after upload. Dropout during key establishment or fewer than two survivors aborts without committing a model.",
        "scope": "Semi-honest coordinator with no colluding clients. Public sample counts, selected cohort, model and validation results remain visible.",
        "limitations": "Local processes share a host and filesystem; host administrators can inspect them. No malicious-server, client-collusion, model-poisoning, multi-host deployment or independent cryptographic audit guarantee. Aggregate output can still reveal information; DP is a separate option."}


def privatize(model, optimizer, loader, config, accountant_state=None, epochs=1):
    from opacus import PrivacyEngine
    from opacus.validators import ModuleValidator
    ModuleValidator.validate(model, strict=True)
    engine = PrivacyEngine(accountant="rdp", secure_mode=False)
    if accountant_state:
        engine.accountant.load_state_dict(accountant_state)
    # The public reproducibility seed must never determine privacy noise or Poisson draws.
    # This remains an experimental PRNG, not Opacus secure_mode/CSPRNG.
    loader.generator = torch.Generator().manual_seed(secrets.randbits(63))
    kwargs = {"module": model, "optimizer": optimizer, "data_loader": loader,
              "max_grad_norm": config["max_grad_norm"],
              "noise_generator": torch.Generator().manual_seed(secrets.randbits(63))}
    if config.get("target_epsilon") and accountant_state is None:
        model, optimizer, loader = engine.make_private_with_epsilon(**kwargs,
            target_epsilon=config["target_epsilon"], target_delta=config["delta"], epochs=epochs)
    else:
        model, optimizer, loader = engine.make_private(**kwargs, noise_multiplier=config["noise_multiplier"])
    return model, optimizer, loader, engine


def private_optimizer_step(optimizer, model, global_parameters, mu):
    """Add the FedProx gradient after Opacus clipping/noise, before Adam/SGD.

    The deterministic term depends only on current/global model parameters.
    It is post-processing of the accounted private gradient. Applying a weight
    shrinkage AFTER Adam is a different algorithm and is not FedProx.
    """
    if optimizer.pre_step():
        with torch.no_grad():
            for param, original in zip(model.parameters(), global_parameters):
                if param.grad is not None:
                    param.grad.add_(param - original, alpha=mu)
        optimizer.original_optimizer.step()
