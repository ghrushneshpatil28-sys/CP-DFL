# Distributed Lung Cancer Diagnosis Using Privacy-Preserving Federated Learning

For the full project explanation, technology/database rationale, model details, measured results, API reference and completion status, see [DFL FINAL-CP — Complete Project README](<DFL FINAL-CP README.md>).

**PULSAR** upgrades the existing React, FastAPI and PyTorch repository into a research application with exactly two roles: **Admin** and **Doctor**. Patients are doctor-owned database records, never accounts. ResNet18 is the only active image classifier.

This is research decision support, **not a confirmed medical diagnosis**. Secure aggregation is implemented using **Flower SecAgg+ with process-isolated local hospitals**, under the documented semi-honest, non-colluding threat model. This is not protection against a shared-host administrator or an independently audited production deployment. Opacus DP-SGD is experimental and its accountant applies only to the documented update mechanism, not to the entire application or to patients.

## Start locally (PowerShell, repository root)

Validated environment: Windows, Python 3.14, PyTorch 2.12 CPU / torchvision 0.27, Node.js with React 19 and Vite 7. The installed `backend/venv` works. If creating a fresh environment:

```powershell
python -m venv backend/venv
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd frontend
npm.cmd ci
cd ..
```

For CPU-specific wheels, install the matching `torch` and `torchvision` versions from the [official PyTorch wheel index](https://download.pytorch.org/whl/cpu). No training script uninstalls or replaces your environment. `requirements-privacy.txt` contains Flower and Opacus; both are needed for federated/DP runs. The development requirements include all runtime and report QA dependencies.

After installing dependencies, double-click `START.cmd` or run:

```powershell
.\backend\venv\Scripts\python.exe -m backend.dev --detach
.\backend\venv\Scripts\python.exe -m backend.dev --status
```

The launcher applies database migrations, starts the API, training worker and React, and prints the ready URL: [PULSAR](http://127.0.0.1:7351). The frontend uses port 7351; the launcher selects an available API port and configures the frontend proxy automatically. Startup fails clearly if frontend port 7351 is occupied. Logs are under `backend/storage/logs`; stop it with `python -m backend.dev --stop` using the same virtual environment.

On an empty database the local launcher enables one-time browser Admin creation. Enrollment requires a loopback request and is locked after the first Admin is created. It is disabled by default outside this launcher. There are **no hardcoded default credentials**. Operator-provisioned accounts persist in the database. Sign in as Admin to manage Doctor accounts. Test accounts exist only in isolated test databases.

For manual operation, first initialize the database and create an Admin interactively (password at least 12 characters):

```powershell
.\backend\venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\backend\venv\Scripts\python.exe -m backend.bootstrap --email admin@example.org --name "Research Admin"
```

Then run these in three terminals, all starting from the repository root:

```powershell
# Terminal 1 — API
.\backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2 — persistent training queue (one worker)
.\backend\venv\Scripts\python.exe -m backend.worker
# Terminal 3 — React
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open [PULSAR](http://127.0.0.1:7351) and [API documentation](http://127.0.0.1:8000/docs). The manual Vite setup proxies `/api` to port 8000. Keep the frontend and API on the documented origins. `API_PROXY_TARGET` changes the development proxy target.

SQLite is the tested persistent local database. SQLAlchemy/Alembic also accept PostgreSQL through `DATABASE_URL`; install `backend/requirements-postgres.txt` for that driver. PostgreSQL deployment has **not** been tested here. `.env.example` documents environment variables; it is not loaded automatically. Set them in the process environment. Hosted deployments require HTTPS, `COOKIE_SECURE=true`, a restricted `CORS_ORIGINS`, private storage/database volumes, backups, and deployment-specific access policies. Stored files are protected by APIs but are not encrypted at rest by this application.

## Dataset and model readiness

The old audit scanned a missing D: drive and falsely reported empty/clean data. The old manifest also referenced missing D: images and incompatible labels. The replacement audit verifies both file SHA-256 and decoded RGB pixel SHA-256.

Actual audit: **1,565 files / 838 unique file hashes / 727 unique decoded images**. All **111 original test images** have pixel-identical training copies. Those copies differ at the file-byte level. No patient/study IDs were found. The repaired, non-destructive manifest contains **506 training, 110 validation, 111 test** images with no exact byte/pixel overlap across splits. Original test groups remain reserved for testing; duplicate copies are removed from the manifest, not deleted from disk.

```powershell
.\backend\venv\Scripts\python.exe -m ml.dataset
# Optional metadata CSV: source-relative path,patient_id,study_id
.\backend\venv\Scripts\python.exe -m ml.dataset --metadata patient_metadata.csv --seed 42 --ratios 0.70 0.15 0.15
```

Patient/study identities and content duplicates are transitively grouped. Missing IDs make validation **provisional**, not patient-independent. Exact duplicate controls cannot establish absence of related scans, augmented variants or near duplicates without source metadata. Existing legacy models may have seen the old test images; they cannot substantiate held-out performance and are excluded from inference. Retrained models start from a new initialization by default.

The verified dataset labels, in checkpoint index order, are Adenocarcinoma, Large Cell Carcinoma, No Cancer, Squamous Cell Carcinoma. Labels describe this dataset; they do not establish suitability for arbitrary X-rays, CT modalities or unseen populations.

`ml/models/resnet18.py` is the canonical factory. Every new checkpoint embeds its class mapping, preprocessing, normalization variant, version, seed/configuration and manifest digest. Loading is strict. The API returns 503 and saves no analysis when checkpoint validation/inference fails. There is no untrained-model, alternate-architecture, heuristic or synthetic clinical-risk fallback.

The selected `ml/saved_models/approved.pt` is now **centralized-transfer-224-20261116**: pretrained ResNet18 fine-tuned at **224×224** for 20 epochs, with epoch **15** selected by validation macro F1. Its measured test accuracy is **92.79% (103/111)**, balanced accuracy **93.96%**, macro F1 **92.44%**. This is a centralized model; its score does not replace historical federated/secure results. The original 75.68% checkpoint is preserved for rollback. The test split was used in earlier experiments and has no patient IDs, so this remains provisional research evidence. “Approved” means selected for this application, not clinically approved. See [current evaluation](docs/approved-model-test.json) and [upgrade evidence](docs/accuracy-improvement-result-20261116.json).

## Training, comparison and inference selection

The Overview screen reports the **selected inference model's actual test evaluation**, including sample count, balanced accuracy and macro F1. `/api/model/evaluation` requires an authenticated Admin or Doctor. Its evidence file (`approved.evaluation.json`) is bound to the checkpoint SHA-256, and reported accuracy/F1 are checked against the saved confusion matrix. Missing or mismatched evidence is shown as unavailable; a target accuracy never overrides a measured score. `ml.approve` publishes this evidence from a completed experiment's `results.json` when selecting its checkpoint.

Use a fresh output directory for every run. The engine refuses to overwrite experiment evidence. Defaults use 224-pixel images; historical short verification runs use 64 pixels, while the selected November transfer-learning model uses 224 pixels.

```powershell
.\backend\venv\Scripts\python.exe -m ml.train --algorithm centralized --rounds 10 --image-size 224 --batch-size 16 --output ml/outputs/experiments/centralized-224
.\backend\venv\Scripts\python.exe -m ml.train --algorithm fedavg --rounds 10 --local-epochs 1 --image-size 224 --alpha 0.5 --output ml/outputs/experiments/fedavg-224
.\backend\venv\Scripts\python.exe -m ml.train --algorithm fedprox --mu 0.01 --rounds 10 --image-size 224 --output ml/outputs/experiments/fedprox-224
.\backend\venv\Scripts\python.exe -m ml.train --algorithm fedavg --secure-aggregation --rounds 10 --image-size 224 --output ml/outputs/experiments/fedavg-secagg-224
.\backend\venv\Scripts\python.exe -m ml.train --algorithm fedavg --dp --noise-multiplier 1.1 --delta 0.00001 --max-grad-norm 1 --rounds 10 --output ml/outputs/experiments/fedavg-dp-224
# Alternatively calibrate noise with --target-epsilon 5; read actual accountant output.
.\backend\venv\Scripts\python.exe -m ml.evaluate --checkpoint ml/outputs/experiments/centralized-224/best.pt --output ml/outputs/experiments/centralized-224/test-repeat.json
.\backend\venv\Scripts\python.exe -m backend.import_experiment ml/outputs/experiments/centralized-224
.\backend\venv\Scripts\python.exe -m ml.approve ml/outputs/experiments/centralized-224/best.pt
```

The Admin experiment form queues real jobs in SQL. The separate worker records every completed round, failure and final test result. It stays separate from FastAPI so training does not block API requests. `--once` handles one queued job. After a worker crash, confirm no worker remains before using `python -m backend.worker --recover-interrupted`; interrupted jobs are marked failed, never silently resumed with reset privacy accounting.

Centralized training supports Adam/SGD, configurable learning rate/epochs/batches, deterministic initialization and loaders, validation loss/metrics, early stopping and best-checkpoint saving. Cross-entropy is the baseline; class distributions and balanced metrics are reported rather than introducing unjustified resampling. The held-out test is accessed after validation selects the checkpoint. Do not repeatedly tune on test results.

The three local hospitals use fixed, seeded Dirichlet label-imbalanced partitions of **training groups only**. FedProx adds μ/2 times the squared distance from global parameters. The plaintext baseline uses Flower's weighted FedAvg strategy, can expose local updates, and counts logical tensor bytes. With `--secure-aggregation`, local GroupNorm ResNet18 training happens in separate hospital processes, and Flower SecAgg+ reconstructs only the weighted aggregate. Secure communication metrics count serialized protocol messages in both directions, excluding OS pipe framing. Both modes are local simulations sharing a host/filesystem, not three independently administered hospital deployments.

Each run writes `config.json`, `rounds.jsonl`, `best.pt`, and `results.json`; DP runs also save private accountant state. Do not publish raw artifacts containing sensitive metadata. SQL imports validate provenance and reject inconsistent or superseded DP artifacts. Charts use only persisted measured results; comparison cohorts match manifest digest and image size, with configuration/training-budget differences visible.

## Privacy scope

- **Secure aggregation: Implemented / local.** Flower's four-stage SecAgg+ workflow/client modifier runs across three hospital processes. All three must establish keys; two masked contributors and two reconstruction shares are required, tolerating one later dropout. Malformed/replayed messages and insufficient participants abort without plaintext fallback. A versioned HKDF/ChaCha20 PRG adapter replaces the pinned dependency's 32-bit mask seed fold. Raw local losses/classes are withheld. See [protocol, tests, quantization and threat model](docs/SECURE_AGGREGATION.md). No malicious coordinator, client collusion, host-compromise, model-poisoning or independently audited production guarantee is claimed. Existing plaintext runs are not retroactively protected.
- **DP-SGD: Experimental.** [Opacus](https://opacus.ai/api/privacy_engine.html) handles per-sample gradients, clipping, Gaussian noise, Poisson sampling and RDP accounting. ResNet18 replaces BatchNorm with GroupNorm and uses mathematically equivalent non-inplace residual additions for hook compatibility. See [Opacus layer compatibility](https://opacus.ai/tutorials/guide_to_module_validator).
- Privacy noise and Poisson draws use independent entropy-seeded generators, never the public experiment seed. They still use research PRNGs (`secure_mode=False`), not a tested CSPRNG deployment. No production privacy guarantee is asserted.
- Each client's accountant persists across rounds and reports actual ε, δ, sample rate, noise, clip norm and cumulative steps. The guarantee model is **example-level updates conditional on fixed partitions and public sample counts**, not patient-level or client-level privacy. Partition construction and held-out evaluation are outside that budget. Budgets across separate experiments are not composed automatically; repeated releases require a separate composition policy.
- Raw DP local losses and class distributions are withheld because their disclosure is not accounted for. DP FedProx adds the deterministic proximal gradient after Opacus clips/noises the data gradient and before the underlying SGD/Adam step. This preserves the optimizer's proximal-loss semantics without adding an unclipped data-dependent gradient. Noisy training can reduce accuracy. Do not compare BatchNorm and GroupNorm runs as an isolated privacy-noise effect.
- Validation discovered earlier development runs with raw loss disclosures and public-seed-controlled sampling/noise. Those artifacts are retained for audit, rejected for future privacy imports, and any imported affected run is explicitly invalidated. Use the final `fedavg-dp-entropy` run for mechanism verification.

## Workflows and authorization

Admin: doctor creation/profile updates/activation, aggregate counts, experiments, comparison, privacy ledger, redacted audit log and system readiness. Admin is denied identifiable patient records, scans, heatmaps and report downloads.

Doctor: search/filter/sort/page through owned patients; register/edit demographics, symptoms and histories; manage visits/follow-ups; upload/re-encode protected PNG/JPEG images; run strict ResNet18 inference plus layer4 Grad-CAM; save review notes/recommendations; generate and retrieve immutable PDF snapshots. Patient tabs cover overview, history, images, analyses, timeline and reports.

Passwords use salted scrypt. Eight-hour opaque sessions are stored only as hashes, revoked on logout, password reset and doctor status changes. Mutations require a CSRF token and accepted browser origin. Login attempts are throttled. Patient/image/analysis/report authorization is checked in SQL-backed API handlers, including direct identifier access. File names are random references, storage is not mounted publicly, and uploads are limited to 10 MiB / 16 megapixels with MIME/extension/decoder consistency checks. DICOM is not supported.

API prefixes are `/api/auth`, `/api/admin`, `/api/patients`, `/api/images`, `/api/analyses` and `/api/reports`. The legacy unauthenticated `/api/predict` endpoint has been retired because it combined synthetic tabular scores and heuristic fallbacks. Archived text sources and old README are under `docs/legacy`; they are not runtime modules.

## Validation

```powershell
New-Item -ItemType Directory -Force .test-tmp | Out-Null
.\backend\venv\Scripts\python.exe -m pytest --basetemp=.test-tmp/validation -q
cd frontend
npm.cmd run build
npm.cmd run lint
npm.cmd run test:e2e
npm.cmd audit
```

Playwright starts isolated API/Vite servers and uses installed Edge. Change `channel: 'msedge'` in its configuration or install Chromium for another environment. No production patient/account data is used. Windows sandboxing can block asyncio's internal loopback socket pair; run local TestClient/browser checks where loopback is permitted. Use a fresh pytest temporary directory if the sandbox prevents cleanup.

See [stage evidence, acceptance and limitations](docs/IMPLEMENTATION.md), [secure aggregation scope](docs/SECURE_AGGREGATION.md), [verified dataset audit](dataset_audit_report.json), [checkpoint audit](docs/checkpoint-audit.json), and [screenshots](docs/screens). No clinical, patient-independent or independently audited production privacy validation is claimed.
