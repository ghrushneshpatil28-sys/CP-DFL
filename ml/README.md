# ResNet18 research pipeline

Use the canonical commands and privacy limitations in [the root README](../README.md).

- `python -m ml.dataset`: non-destructive SHA-256/pixel audit and grouped manifests.
- `python -m ml.train`: centralized, FedAvg and FedProx using one ResNet18 factory.
- `python -m ml.evaluate`: strict held-out evaluation, never random-weight fallback.
- `python -m ml.approve`: provenance-check and select a research inference checkpoint.

Historical metadata/checkpoints are retained but not used for inference. No patient-independent or clinical validation has been established. Optional Flower SecAgg+ runs across three local hospital processes (`--secure-aggregation`); see `docs/SECURE_AGGREGATION.md` for the cryptographic PRG adapter, thresholds, tests and threat model. Opacus DP-SGD remains experimental.
