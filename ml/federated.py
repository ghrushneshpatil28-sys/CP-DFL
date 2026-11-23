"""Three-client local simulation. Raw samples stay in each client loader.

The plaintext baseline sees model updates. The secure path lives separately in
ml.secure_aggregation and does not call this plaintext aggregation function.
"""
from collections import Counter, defaultdict
import numpy as np
import torch

HOSPITALS = ["Hospital A", "Hospital B", "Hospital C"]


def partition_clients(rows, seed=42, alpha=.5):
    if alpha <= 0:
        raise ValueError("Dirichlet alpha must be positive")
    rng = np.random.default_rng(seed)
    groups = defaultdict(list)
    for row in rows:
        if row["split"] == "train":
            groups[row.get("patient_id") or row["group_id"]].append(row)
    if len(groups) < 3:
        raise ValueError("Three clients require at least three independent training groups")
    clients = {name: [] for name in HOSPITALS}
    preferences = {label: rng.dirichlet([alpha] * 3) for label in sorted({r["label"] for r in rows})}
    items = sorted(groups.items())
    rng.shuffle(items)
    for index, (_, group) in enumerate(items):
        label = Counter(r["label"] for r in group).most_common(1)[0][0]
        # Ensure all clients participate without splitting patient groups.
        client = index if index < 3 else int(rng.choice(3, p=preferences[label]))
        clients[HOSPITALS[client]].extend(group)
    return clients


def aggregate(updates):
    if len(updates) != 3:
        raise ValueError("All three clients required; no dropout protocol is implemented")
    reference = updates[0][1]
    for count, state in updates:
        if not isinstance(count, int) or count <= 0 or state.keys() != reference.keys():
            raise ValueError("Malformed client update")
        for key, value in state.items():
            if value.shape != reference[key].shape or value.dtype != reference[key].dtype or not torch.isfinite(value).all():
                raise ValueError(f"Invalid update tensor: {key}")
    # Use Flower's tested sample-weighted strategy for floating model tensors.
    # Validation above rejects malformed payloads before entering the strategy.
    from flwr.common import Code, FitRes, Status, ndarrays_to_parameters, parameters_to_ndarrays
    from flwr.server.strategy import FedAvg
    floating_keys = [key for key, value in reference.items() if value.is_floating_point()]
    if not floating_keys:
        raise ValueError("Update contains no floating parameters")
    responses = [(None, FitRes(Status(Code.OK, "OK"),
        ndarrays_to_parameters([state[key].cpu().numpy() for key in floating_keys]), count, {})) for count, state in updates]
    strategy = FedAvg(min_fit_clients=3, min_available_clients=3, accept_failures=False,
                      fit_metrics_aggregation_fn=lambda metrics: {}, inplace=False)
    parameters, _ = strategy.aggregate_fit(1, responses, [])
    if parameters is None:
        raise ValueError("Flower rejected aggregate")
    floating = dict(zip(floating_keys, parameters_to_ndarrays(parameters)))
    result = {}
    for key, value in reference.items():
        if value.is_floating_point():
            result[key] = torch.from_numpy(floating[key]).to(dtype=value.dtype)
        else:
            result[key] = torch.stack([state[key] for _, state in updates]).max(0).values
    return result


def proximal_loss(model, global_parameters, mu):
    if mu < 0:
        raise ValueError("FedProx mu cannot be negative")
    return .5 * mu * sum((param - original).pow(2).sum() for param, original in zip(model.parameters(), global_parameters))


def communication_bytes(state):
    return sum(t.numel() * t.element_size() for t in state.values())
