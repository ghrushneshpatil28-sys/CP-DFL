# Existing project upgrade — 2026-10-20

Baseline: React 19/Vite 7 `frontend/src/main.jsx` -> `App.jsx`, single public prediction form. FastAPI `backend/main.py`, no authentication/database, public heatmaps and heuristic fallback. Python 3.14/PyTorch 2.12 CPU, no CUDA. No AGENTS.md found.

Baseline checks: frontend build passes; lint fails (`process` undefined). Backend pytest fails collection (`requests` missing in legacy live-server script). Old dataset audit scans missing D: path. Old CSV references missing D: images and different labels.

Dataset: 1,565 files, 838 unique byte hashes, 727 duplicate groups in pool/train; direct train/test and decoded-pixel overlap require separate verification. No patient/study metadata. Legacy four-class ResNet18 has no embedded class/preprocessing provenance. Legacy alternate-model artifacts are preserved but excluded from approved inference.

## Stages (mark only after verification)
- [x] 1. Repair paths, remove active alternate classifiers and heuristic results.
- [x] 2. SHA-256/pixel audit, grouped reproducible manifests, strict checkpoints, centralized training/evaluation.
- [x] 3. SQLAlchemy persistence/migrations, sessions, Admin/Doctor authorization and patients.
- [x] 4. Protected uploads, inference, Grad-CAM, analysis history and PDF reports.
- [x] 5. Three-hospital FedAvg/FedProx, grouped non-IID partitions, background jobs, real metrics.
- [ ] 6. Test DP-SGD/accounting; explicitly disable secure aggregation unless protocol verified.
- [x] 7. Original responsive React workspaces connected to APIs.
- [x] 8. Automated tests, visual report checks, reproducible setup and acceptance documentation.

Stage 6 remains partial: Opacus gradients/clipping/noise/accounting and independent privacy RNG tests pass. Secure aggregation is Not Implemented; production CSPRNG and end-to-end privacy guarantees are unverified. No patient-independent/clinical validation is claimed.

Stage evidence and remaining limitations: `docs/IMPLEMENTATION.md`.
