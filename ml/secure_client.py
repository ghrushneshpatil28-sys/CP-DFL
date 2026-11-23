"""Local hospital training callback. Invoked only inside a SecAgg+ child."""
import copy
import json
import secrets
from dataclasses import dataclass, field


@dataclass
class HospitalTask:
    rows: list
    classes: list
    preprocessing: dict
    config: dict
    accountant: dict | None = field(default=None, init=False)
    noise_multiplier: float | None = field(default=None, init=False)

    def __call__(self, message, context):
        import numpy as np
        import torch
        from flwr.app import Message
        from flwr.common import FitRes, Code, Status, ndarrays_to_parameters, parameters_to_ndarrays
        from flwr.compat.common.recorddict_compat import recorddict_to_fitins, fitres_to_recorddict
        from ml.engine import loader, train_local, seed_everything
        from ml.models import build_resnet18
        from ml.models.resnet18 import use_group_norm
        from ml.secure_aggregation import CLIP, SecureAggregationError

        instruction = recorddict_to_fitins(message.content, keep_input=True)
        round_number = instruction.config["round"]
        seed_everything(self.config["seed"] + round_number, self.config["threads"])
        model = use_group_norm(build_resnet18(len(self.classes)))
        reference = model.state_dict()
        arrays = parameters_to_ndarrays(instruction.parameters)
        if len(arrays) != len(reference):
            raise SecureAggregationError("Global model contract mismatch")
        model.load_state_dict({k: torch.from_numpy(a.copy()).to(v.dtype) for (k, v), a in zip(reference.items(), arrays, strict=True)}, strict=True)
        global_parameters = [p.detach().clone() for p in model.parameters()]
        config = copy.deepcopy(self.config)
        if self.noise_multiplier is not None:
            config["dp"]["noise_multiplier"] = self.noise_multiplier
        data = loader(self.rows, self.classes, self.preprocessing, min(config["batch_size"], len(self.rows)), True, config["seed"] + round_number)
        model, metrics, self.accountant = train_local(model, data, config,
            global_parameters if config["algorithm"] == "fedprox" else None,
            self.accountant, config["rounds"] * config["local_epochs"])
        if metrics.get("privacy"):
            self.noise_multiplier = metrics["privacy"]["noise_multiplier"]
        updated = [v.detach().cpu().numpy().copy() for v in model.state_dict().values()]
        if any(not np.isfinite(a).all() or np.max(np.abs(a)) > CLIP for a in updated):
            # Flower clips during quantization. Reject saturation so it cannot
            # silently change the training result.
            raise SecureAggregationError("Local model exceeds secure quantization bounds")
        released = {"steps": metrics["steps"]}
        if metrics.get("privacy"):
            released["privacy"] = json.dumps(metrics["privacy"])
        # Raw losses/classes/accountants never cross this boundary. The outer
        # Flower modifier masks arrays and erases these ArrayRecords before IPC.
        result = FitRes(Status(Code.OK, "OK"), ndarrays_to_parameters(updated), len(self.rows), released)
        np.random.seed(secrets.randbits(32))
        return Message(fitres_to_recorddict(result, keep_input=False), reply_to=message)
