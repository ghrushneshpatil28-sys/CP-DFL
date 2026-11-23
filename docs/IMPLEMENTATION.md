# Upgrade evidence — 20 October 2026

The existing `frontend`, `backend` and `ml` directories were extended in place. Original unsafe/stale source and README were preserved as non-executable text under `docs/legacy`. The repository had no Git metadata, authentication or persistent application database at inspection. This document records implemented behavior and remaining limits; it is not a clinical or privacy certification.

**Latest model update — 16 November 2026:** the selected ResNet18 now measures **92.79% test accuracy (103/111)** after pretrained 224-pixel fine-tuning. The November section below records the run, selection policy, dashboard evidence and final regression results. Earlier sections retain their historical measured results.

## Stage 1 — inspect and repair

**Files:** `upgrade-checklist.md`, `.gitignore`, `docs/source-inventory.json`, `docs/checkpoint-audit.json`; repaired `backend/main.py`, legacy backend pipeline/schema entry points, `ml/inference/image_predictor.py`, training/evaluation entry points and dataset utilities. Historical sources are archived as `.txt`, outside active imports. `frontend/vite.config.js` imports Node's `process` explicitly.

**Findings:** single unauthenticated React prediction form; public FastAPI heatmaps; unrestricted upload writes; clinical/synthetic score fusion and image heuristics; alternate classifier fallback and training; stale D: paths; unrelated class labels in the old CSV; raw ResNet18 checkpoint lacking class/preprocessing provenance; unverified performance/privacy claims in historical metadata. No auth/database existed. `docs/checkpoint-audit.json` records actual parameter-head shapes and checkpoint metadata, including the incompatible legacy artifacts.

**Executed:** repository/file/import searches with PowerShell/rg; checkpoint inspection using `torch.load(..., weights_only=True)`; `python -m pytest backend -q`; `npm.cmd run build`; `npm.cmd run lint`; dependency/version inspections and `python -m pip check`.

**Baseline:** backend collection failed (`requests` missing in a legacy live-server script); frontend built but lint failed (`process` undefined). The old live-server scripts were archived and replaced by real isolated tests. All active image classifier creation now goes through `ml/models/resnet18.py`. Old checkpoints remain on disk but are never fallback candidates. The unsafe public prediction endpoint was deliberately retired.

## Stage 2 — dataset, checkpoints, centralized training

**Files:** `ml/models/{__init__,resnet18}.py`, `ml/dataset.py`, `ml/checkpoints.py`, `ml/metrics.py`, `ml/engine.py`, `ml/train.py`, `ml/evaluate.py`, `ml/approve.py`, `ml/data/manifest.json`, `dataset_audit_report.json`, `ml/saved_models/approved.pt` and its metadata; CLI artifacts under `ml/outputs/experiments/centralized-verification`.

**Verified audit:** 1,565 image files; 838 unique file-byte hashes; 727 unique decoded images. 727 duplicate-byte groups reflect pool/train copies. Decoded hashing additionally proves that all 111 original test images have identical pixels in training despite different bytes. No corrupt images or conflicting duplicate labels were found. No patient/study metadata exists. New manifests reserve original test groups and remove duplicates from active splits: 506 train, 110 validation, 111 test. Original source images were not deleted. Same seed and source reproduce the manifest byte for byte. Byte/pixel/patient/study/group overlap checks run before training; input hashes are revalidated.

**Executed:** `python -m ml.dataset`; `python -m ml.train --algorithm centralized --rounds 2 --image-size 64 --batch-size 16 --output ml/outputs/experiments/centralized-verification`; `python -m ml.approve ml/outputs/experiments/centralized-verification/best.pt`. Architecture, output shapes, exact metadata mapping, strict key/head loading, preprocessing and Grad-CAM are covered by tests. Legacy checkpoints are explicitly rejected.

**Measured centralized verification:** test accuracy 0.7567568, balanced accuracy 0.7451732, macro F1 0.7334770, 111 test images. These are real outputs of a short, from-scratch 64-pixel run. They are not a final research benchmark. Full per-class sensitivity/specificity, confusion matrix, ROC-AUC, losses and timing are in `results.json`. The test split was read after validation-selected checkpoint saving.

**Limits:** validation is provisional. The absence of patient IDs prevents patient-independent claims, and exact hashing cannot exclude related scans or near duplicates. Legacy models may have trained on the old test images; their reported scores are not reused. Cross-entropy is an explicit baseline; class counts and balanced metrics expose imbalance without unjustified synthetic resampling. Longer 224-pixel, external, modality-specific and patient-independent evaluation remains research work.

## Stage 3 — persistence and two-role authorization

**Files:** `backend/database.py`, `models.py`, `security.py`, `api_schemas.py`, `bootstrap.py`, `main.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_research.py`, pinned requirements, `.env.example`, tests.

**Implemented:** SQLAlchemy tables for users, doctor profiles, hashed sessions, login attempts, patients, clinical history snapshots, visits, images, analyses, reports, three federated clients, experiments, round/privacy metrics and audit logs. Database check constraints permit Admin/Doctor only. Admin cannot access patient/image/report endpoints. Doctor queries enforce patient ownership. Scrypt passwords, CSRF tokens, origin checks, eight-hour opaque sessions, logout revocation, account status checks, session revocation on password/status changes and login throttling are active. Password whitespace is preserved. SQL constraints and schema validation reject unsupported roles/fields. Admin audit views redact patient resource identifiers.

**Executed:** dependency installation; `python -m alembic -c backend/alembic.ini upgrade head`; isolated fresh-database migration verification (16 tables including Alembic tracking); TestClient integration tests. SQLite persistence is tested. PostgreSQL URL/driver support is provided but an actual PostgreSQL instance was unavailable and is not reported as tested.

**Limits:** run one training worker and the documented API deployment. This is not an audited healthcare deployment. Application-level storage encryption, centralized identity, operational backups/retention and production infrastructure controls require deployment-specific implementation. No default production account is embedded in source; use local first-run enrollment or interactive bootstrap. Operator-requested accounts were subsequently created as described below.

## Stage 4 — protected images, analysis, reports

**Files:** `backend/storage.py`, `reports.py`, patient/image/analysis/report routes in `main.py`; `ml/inference/image_predictor.py`, `ml/gradcam.py`; `tests/test_api.py`; `docs/screens/report-*`.

**Implemented:** ownership-checked uploads with size/pixel limits and MIME/extension/content verification; PNG re-encoding removes uploaded metadata; opaque private storage references; authenticated originals/heatmaps; strict checkpoint inference; per-class probabilities; ResNet18 layer4 Grad-CAM; persisted model version/digest/preprocessing/time; doctor observations/recommendations; immutable PDF snapshots and authorized downloads. Failed inference returns 503 and saves no prediction. Images and clinical observations do not feed a fabricated risk score.

**Verified:** real checkpoint inference in the browser workflow; API invalid content/format/oversize/ownership tests; finite class probabilities; Grad-CAM rendering and hook cleanup; analysis/history persistence; PDF text/authorization checks. A synthetic test-only report with a long review was rendered with PyMuPDF into two pages and visually inspected: no clipping, overlap or lost follow-up text. `docs/screens/report-qa.pdf` uses explicitly untrained test-fixture weights and synthetic identity solely for layout testing, never application inference.

**Limits:** PNG/JPEG only, no DICOM. Upload validation is not modality certification. Grad-CAM is not validated tumor localization. The selected application checkpoint is a structurally validated research model, not clinically approved.

## Stage 5 — federated simulation and comparison

**Files:** `ml/federated.py`, `ml/engine.py`, `backend/worker.py`, `backend/import_experiment.py`, experiment/round/client/comparison routes, `tests/test_worker.py`, CLI artifacts and SQL records.

**Implemented:** three named hospital partitions, reproducible patient/content-grouped Dirichlet non-IID training allocations, identical global ResNet18 initialization, actual local optimizer steps, weighted Flower FedAvg strategy aggregation and FedProx regularization. No image/record content appears in parameter payloads. All three updates are required; malformed keys/shapes/dtypes, nonfinite tensors and dropout are rejected. Per-round counts, class distribution, loss, validation metrics, duration and tensor communication volume are persisted. Best checkpoints use validation macro F1; final test evaluation uses the same manifest as centralized runs. Background worker failures are explicit SQL states; interrupted jobs require explicit recovery, never silent DP accountant reset.

**Executed:** two full-data rounds each for `fedavg-verification`, `fedprox-verification`, and then `fedavg-flower`, `fedprox-flower` using the final Flower aggregation path; SQL imports through `python -m backend.import_experiment <directory>`. A separate isolated worker test completes a real FedProx round for all three clients and verifies round/result/checkpoint persistence.

**Measured short-run results:** FedAvg test macro F1 0.3894412, FedProx 0.3965242, centralized 0.7334770. Each uses 64-pixel inputs and the same 111-image test boundary. Each federated two-round run represents 537,033,792 logical parameter bytes; framework/network overhead is excluded. The clients contain 198 / 233 / 75 training images. The UI makes configuration/training budgets visible and does not imply federated superiority.

**Limits:** this is a local, in-process Flower-strategy simulation, not separate hospital deployments or Ray-based distributed execution. Raw data shares a machine/filesystem; the coordinator can see updates. No network throughput, communication secrecy or fault-tolerant deployment claim is made.

## Stage 6 — privacy (initial upgrade; secure aggregation added below)

**Files:** `ml/privacy.py`, DP normalization/activation variant in `ml/models/resnet18.py`, training integration in `ml/engine.py`, privacy schema/routes/ledger, `backend/invalidate_experiment.py`, privacy and malformed/dropout tests.

**DP-SGD implemented and tested:** Opacus per-sample gradients, clipping, Gaussian noise, Poisson sampling, actual RDP accounting, target epsilon/noise configuration and persistent per-client composition across rounds. BatchNorm becomes GroupNorm while retaining ResNet18 blocks/head; inplace activations/residual addition are removed for hook correctness. The public experiment seed is separated from privacy noise and Poisson RNG entropy. Actual sample rate, clip norm, noise multiplier, epsilon/delta and cumulative steps are stored. Raw local losses and private class distributions are withheld in DP runs.

Validation found two substantive flaws in intermediate development: direct raw-loss disclosure, and deterministic public-seed-controlled noise/sampling. The old artifacts are retained for audit, excluded from the importer and not accepted as privacy-valid releases. The previously imported `fedavg-dp-flower` run is marked **invalidated** with its reason; its privacy metrics are excluded from the active ledger. A replacement full-data `fedavg-dp-entropy` run uses independent entropy-seeded generators. Separate tests verify accountant composition, per-sample gradient tensors and that resetting the public seed cannot reproduce private optimizer output.

**Guarantee boundary:** experimental example-level model-update accounting conditional on fixed client partitions/public sample counts. Not patient-level/client-level. Private partition selection, held-out metrics and cross-experiment composition are outside that budget. `secure_mode=False` uses research PRNGs; a production CSPRNG configuration and end-to-end formal release policy are not verified. No fully privacy-preserving application claim is made.

**Initial secure aggregation status was Not Implemented.** The later implementation and executed protocol checks are recorded in the 21 October section below. Historical plaintext experiments remain plaintext.

## Stage 7 — original React workspaces

**Files:** `frontend/src/App.jsx`, `index.css`, `api.js`, `useResource.js`, `frontend/index.html`, `public/pulsar.svg`, Vite/package/ESLint configuration, Playwright configuration and `e2e/workflows.spec.js`.

**Implemented:** original PULSAR identity with violet/cyan/coral/lime bento grids, typography, model probability and experiment charts, asymmetric panels, iconography, responsive navigation, reduced-motion transitions, keyboard focus states, labelled native forms and focus-trapped doctor modal. Admin screens cover overview, doctors, federated clients/experiments/details, comparison, privacy, audit and server settings. Doctor screens cover overview, paginated directory, registration/edit, patient tabs, upload/inference/Grad-CAM, analysis history, reports, visits/follow-ups and profile. All displayed counts/metrics/records come from APIs; empty states are used when evidence is absent. Sessions stay in HttpOnly cookies; no authentication token is stored in localStorage.

**Executed:** `npm.cmd run build`, `npm.cmd run lint`, `npm.cmd audit fix`, icon package repair, `npx.cmd playwright test`. Build and lint passed. Compatible dependency updates resolved npm's initially reported 13 advisories; final audit is checked separately. Browser tests exposed and fixed required-label naming and hash-route construction. Visual QA fixed an offscreen-sidebar resize transition and white-on-white patient action. Synthetic account/patient screenshots are isolated browser test data; experiment charts use actual imported training artifacts.

## Stage 8 — validation and remaining acceptance

Backend regression, browser workflow, final build/lint/audit outcomes are recorded below after their final run. Core tests exercise API authorization and persistence, strict model contracts, pixel duplicate detection/reproducibility/group isolation, actual three-client training/worker persistence, Opacus gradients/composition/randomness, report generation and failure paths. Browser tests exercise the complete patient-to-PDF workflow, doctor account creation/deactivation, measured experiment screens, role guards, native form constraints, responsive layouts and loading/error/retry behavior. Screenshots are under `docs/screens`.

The initial pre-existing `.agent/scripts/checklist.py` run passed four checks and failed static UX/SEO checks. Original reports remain in `docs/legacy-checklist.log`, `ux-audit.log`, `seo-audit.log`. Follow-up repairs scoped these heuristics to application sources, counted actual navigation items, and explicitly configured the user-requested violet palette. The final rerun passed all six checks; see `docs/checks-after-fixes.log`. Browser/API checks remain the evidence for actual behavior.

### Acceptance status

- Existing repository upgraded; exactly Admin/Doctor; persistent doctor-owned records; secured account management, image analysis and reports: implemented and integration-tested.
- ResNet18-only active classifier; strict retrained research checkpoint; Grad-CAM; leakage-repaired manifests; centralized/FedAvg/FedProx actual runs; real dashboards: implemented and tested.
- DP-SGD/accounting: implemented and tested within the experimental update-mechanism scope above; no production/full-application guarantee.
- Secure aggregation: implemented for local process-isolated Flower SecAgg+ under the documented semi-honest, non-colluding threat model; production/collusion/malicious-host guarantees are not established. Clinical/patient-independent validation remains blocked by absent identity/source metadata and external evaluation resources.
- PostgreSQL deployment, production CSPRNG, real multi-host hospitals and production operational controls: not validated in this local environment.

### Initial upgrade command results (superseded by follow-up checks below)

| Command / check actually executed | Final result |
| --- | --- |
| `python -u -m pytest -q --basetemp=.test-tmp/run7 --tb=short` | **15 passed**, 3 warnings, 23.42 s |
| `npx.cmd playwright test` | **4 passed**, 27.2 s; isolated API/Vite/Edge, real dataset image |
| `npm.cmd run build` | **Passed**, 2,355 modules, 6.89 s |
| `npm.cmd run lint` | **Passed** |
| `npm.cmd audit --json` | **0 reported vulnerabilities**, saved in `docs/npm-audit-final.json` |
| `python -m pip check` | **No broken requirements found** |
| Fresh Alembic `upgrade head` | **Passed**, 16 tables including version tracking |
| Repeated full dataset audit to a separate manifest | **Exact manifest digest match**, no split overlap |
| Strict `python -m ml.evaluate --checkpoint ml/saved_models/approved.pt --output docs/approved-model-test.json` | **Passed**, matches stored central test metrics |
| Active-code search for alternate architectures and old heuristic pipelines | **No remaining active alternate image classifier or heuristic prediction path**; archived `.txt` and legacy binaries excluded |
| Direct legacy training alias `python ml/training/train_image.py --help` and module compilation | **Passed**, routes to canonical ResNet18 trainer |
| Synthetic PDF render and visual review | **Passed**, two pages, original + Grad-CAM, long review and follow-up legible |
| Legacy heuristic checklist | **4 passed / 2 failed**; scoped false/conflicting UX/SEO findings detailed above |

The three backend warnings are a Starlette TestClient/httpx deprecation notice and two PyTorch full-backward-hook notices in Opacus tests. Actual per-sample-gradient/accountant assertions pass. Opacus also warns that secure RNG is disabled during CLI runs; this is a material experimental limitation, reflected in UI/artifacts/documentation.

The final independent-entropy DP run completed two rounds with actual client sample counts 198 / 233 / 75. RDP accountant outputs at δ=1e-5: Hospital A ε=2.1252798095 (50 cumulative steps, sample rate .04), Hospital B ε=1.9208895974 (60 steps, 1/30 sample rate), Hospital C ε=3.4966946552 (20 steps, sample rate .1). Noise multiplier 1.1, max gradient norm 1.0. Its measured test macro F1 is 0.125 and accuracy 0.3243243; no performance benefit is implied. Six round/client privacy entries are persisted. These are separate client mechanisms, not a composed cross-experiment/patient-level budget.

The main database contains real completed training records. It initially had no users; the six operator-requested accounts below now persist. Patient/account/report fixtures used for tests live only under `.test-tmp`, and screenshots clearly use test identities. The old unsafe imported DP run remains visibly invalidated, with its reason, rather than being silently deleted.

## Follow-up startup and workflow repairs

**Files created:** `backend/dev.py`, `START.cmd`, `start.ps1`, `backend/migrations/versions/0002_setup_state.py`, `ml/config.py`, `tests/test_setup.py`, `tests/test_training_config.py`, `tests/e2e_setup_server.py`, `frontend/e2e/first-run.spec.js`, `.ux-audit.json`, `docs/checks-after-fixes.log`.

**Files modified:** `backend/{main,models,security,bootstrap,api_schemas}.py`, `backend/requirements-dev.txt`, `ml/{engine,train,privacy}.py`, `tests/test_privacy.py`, `frontend/src/{App.jsx,index.css,api.js,useResource.js}`, `frontend/index.html`, `frontend/playwright.config.js`, `frontend/e2e/workflows.spec.js`, `.agent/scripts/checklist.py`, `.agent/skills/{frontend-design,seo-fundamentals,testing-patterns}/scripts` audit/test utilities, `README.md`, `.env.example`, `docs/verification-summary.json`, this document.

**Implemented:** one-command local startup with migrations, readiness checks, correct Vite proxy, supervised API/worker/frontend and persistent logs; opt-in loopback-only first-Admin browser setup with transactional one-time lock; conflict-safe hospital seeding. Fixed offscreen desktop logout, stale image/analysis pairing, PDF generation omitting current review edits, patient pagination on sorting, dialog focus resets, stale polling responses and unclear network failures. Unified CLI/API training validation and corrected DP FedProx to add the deterministic proximal gradient after private gradient processing and before SGD/Adam. Optimizer tests cover both SGD and Adam.

**Commands actually executed and final outcomes:**

| Command | Result |
| --- | --- |
| `python -m backend.dev --detach`, `python -m backend.dev --status` | API, worker and frontend ready at local URLs |
| `python -u -m pytest -q --basetemp=.test-tmp/error-fixes2 --tb=short` | **28 passed**, no warnings, 42.57 s |
| `npx.cmd playwright test` | **5 passed**, 36.1 s, including first-run Admin enrollment and complete doctor-to-PDF flow |
| `npm.cmd run build` / `npm.cmd run lint` | **Both passed**, build 6.91 s |
| `python -m pip check` | **No broken requirements found** |
| `.agent/scripts/checklist.py` with the project Python | **6 passed / 0 failed / 0 skipped**; actual pytest execution included |
| Local account provisioning and independent login/logout per account | **1 Admin + 5 active Doctors**, all six roles/logins verified |

The six accounts were explicitly requested by the operator, created through the local authenticated APIs, and stored with salted password hashes. Credentials were provided directly in chat and are not embedded in source, documentation, or a shared credential file. Refresh the frontend after initial provisioning to exit any cached first-run setup screen. Existing account sessions and records persist across restarts.

**Remaining blockers at that follow-up:** clinical validation, unavailable patient metadata, experimental DP scope and untested production/PostgreSQL deployment. Secure aggregation was subsequently implemented as recorded below.

## Secure aggregation upgrade — 21 October 2026

**Created:** `ml/secure_aggregation.py`, `ml/secure_client.py`, `tests/test_secure_aggregation.py`, `docs/SECURE_AGGREGATION.md`; actual artifacts under `ml/outputs/experiments/secagg-verification`.

**Modified:** `ml/{config,engine,train,privacy,federated}.py`, `backend/{main,import_experiment}.py`, `backend/requirements-privacy.txt`, `frontend/src/App.jsx`, `tests/{test_api,test_worker,e2e_server}.py`, `frontend/e2e/workflows.spec.js`, `README.md`, `ml/README.md`, this document and verification summary.

**Implemented:** upstream Flower 1.40 SecAgg+ workflow/client modifier across separate hospital processes; encrypted key-share exchange; masked weighted updates; two-of-three reconstruction after key establishment; protocol/message/shape/count validation and explicit abort without plaintext fallback. The pinned upstream's folded 32-bit NumPy mask generator is replaced on both sides by a versioned HKDF-SHA256/ChaCha20 adapter using `cryptography`. No installed library files were modified. All three clients must complete key establishment; one later dropout is recoverable, including after masked upload. A minimum of two contributing clients is required. Full threat model, quantization, custom PRG compatibility and deployment limits are documented in `SECURE_AGGREGATION.md`.

**Integration:** Admin can enable secure aggregation for FedAvg/FedProx through the form or CLI. ResNet18 uses GroupNorm; strict checkpoint metadata records that normalization and secure training configuration. Per-round protocol evidence and serialized-message byte counts persist in SQL/artifacts and appear on the privacy page and experiment detail. Secure runs withhold raw local losses/classes. Optional DP accountants remain within each persistent hospital process and compose across rounds. Old plaintext runs remain labelled plaintext. Browser checks found and repaired numeric step/minimum constraints that previously blocked default experiment form submission.

**Executed checks:**

| Command/check | Observed result |
| --- | --- |
| `python -m pytest -q --basetemp=.test-tmp/secagg-integration --tb=short` | **41 passed**, 234.43 s, no warnings |
| Additional `test_tampered_encrypted_key_share_rejected` after adding authenticated-share tamper coverage | **1 passed**, 4.48 s; 42 distinct backend tests passed across these runs |
| Protocol checks within the backend suite | Unequal-weight reconstruction, masked-only coordinator boundary, fresh masks, full-seed/domain separation, one dropout before/after upload, insufficient participants at every stage, malformed vectors and replay rejection |
| Worker integration checks | Actual secure FedAvg; actual secure FedProx + DP across two rounds; checkpoint/SQL persistence; six composed accountant entries |
| `npx.cmd playwright test` after form repair | **6 passed**, about one minute; includes actual secure experiment queueing |
| Targeted Admin browser rerun after importing the real secure experiment | **1 passed**; populated ledger and four-stage responder evidence verified |
| `npm.cmd run build` / `npm.cmd run lint` | **Passed**, final build 11.14 s |
| `python -m pip check` | **No broken requirements found** |
| Full-data `ml.train --algorithm fedavg --secure-aggregation --rounds 1 --image-size 64 --batch-size 8 --optimizer sgd --threads 2` | Completed all four stages with all three hospitals; actual checkpoint/test metrics saved |
| `backend.import_experiment ml/outputs/experiments/secagg-verification` | Imported actual secure round into the main database |
| Authenticated live `/api/admin/federated/privacy` through port 7351 | Status **Implemented / local**, one persisted secure round, contributors `[1,2,3]`, four stages |

The full-data verification used 198 / 233 / 75 client training images and 111 held-out test images. It took 42.098 s including final evaluation and recorded **402,499,977 serialized protocol bytes** (134,182,062 sent / 268,317,915 received). Test accuracy was 0.3603604 and macro F1 0.1455784. This one-round, 64-pixel SGD/GroupNorm run verifies execution, not predictive quality, clinical validity or superiority. The selected application inference checkpoint was not replaced by this verification model.

**Limits:** semi-honest coordinator, no colluding clients; shared-host/process-memory compromise, malicious server/cohort manipulation, model poisoning, independent cryptographic audit, authenticated multi-host hospital deployment and production operational controls are outside the verified scope. Secure aggregation does not establish DP or conceal aggregate outputs, public sample counts, timing or held-out metrics. Existing DP and patient-independent/clinical validation limitations still apply.


## Accuracy upgrade — 16 November 2026

**Actual result:** the new selected classifier, `centralized-transfer-224-20261116`, achieves **92.79% test accuracy (103/111)**, balanced accuracy **93.96%**, macro precision **91.31%**, macro recall **93.96%**, macro F1 **92.44%**, ROC-AUC **0.9902**. The previous model measured 75.68% (84/111); its checkpoint and original evaluation remain available for rollback/history. The target was exceeded by actual evaluation, not a display floor or changed test labels.

**Training executed:** `python -u -m ml.train --algorithm centralized --pretrained --rounds 20 --local-epochs 1 --image-size 224 --batch-size 8 --optimizer adam --learning-rate 0.0001 --patience 6 --seed 42 --threads 4 --output ml/outputs/experiments/centralized-transfer-224-20261116`, using the existing virtual environment and workspace TORCH_HOME. Official torchvision ResNet18 weights were downloaded and hash checked. The original manifest remains unchanged: 506 training, 110 validation, 111 test images. All 20 epochs completed; epoch 15 had the highest validation macro F1 (0.9688468; validation accuracy 97.27%). Only that checkpoint was evaluated on test at the end of this run. Actual training/evaluation duration was 2,523.402 seconds, including elapsed runtime interruptions; this is not a hardware-independent speed claim.

**Files created:** `ml/evaluation_evidence.py`, `tests/test_evaluation_evidence.py`, `ml/saved_models/approved.evaluation.json`, `docs/accuracy-improvement-plan-20261116.json`, `docs/accuracy-improvement-result-20261116.json`, `docs/model-rollback-20261116.json`, `docs/approved-model-test-20261020.json`; actual experiment config/round/checkpoint/results artifacts in the new experiment directory.

**Files modified:** `ml/approve.py` (atomic checkpoint selection and hash-bound evaluation publishing), `ml/engine.py` (checkpoint digest in future result records), `backend/main.py` (authenticated selected-model evaluation endpoint), `frontend/src/App.jsx`, `frontend/src/index.css`, both browser spec files, `.gitignore` (workspace pretrained cache), selected checkpoint/metadata, README files, current evaluation and verification summary.

**Implemented UI/API:** both roles' Overview screens show actual selected-model accuracy, balanced accuracy, macro F1, test count, model version, normalization, training algorithm and privacy configuration. `/api/model/evaluation` requires authentication and returns unavailable instead of a percentage if evidence is missing, malformed or belongs to another checkpoint. Accuracy/precision/recall/F1 are checked against the saved confusion matrix. Tests explicitly reject fabricated accuracy and demonstrate that a lower score is not clamped to a target. This reader uses standard-library hashing and does not initialize PyTorch just to display a metric.

**Final checks actually executed:**

| Check | Outcome |
| --- | --- |
| API, model, evidence, configuration and setup regression run | **31 passed**, 90.93 seconds |
| Final API/evidence rerun after removing cold PyTorch imports | **14 passed**, 63.48 seconds; overlapping tests, not 14 additional cases |
| Browser suite with selected 224-pixel model | **7 passed**, about 1.4 minutes |
| Browser model-performance check | Display matches authenticated evidence and confusion-matrix arithmetic |
| Doctor browser workflow | Actual new-model inference, Grad-CAM, review persistence and PDF download passed |
| Authenticated live app through port 7351 | Correct new model version, 224px and **103/111** returned |
| Frontend production build and lint | Passed |
| Original manifest verification | All 727 file hashes verified; split counts unchanged |
| Selected-model digest | Matches the published evaluation digest |

Two intermediate browser failures were investigated rather than ignored: first-run route cleanup left an evaluation request in flight; then the fresh server's read-only endpoint unnecessarily initialized PyTorch and exceeded the expected loading window. The reader was made lightweight and test cleanup now waits for the resource/requests. The final full browser rerun passed all seven tests.

**Selection and deployment commands executed:** `python -m ml.approve .../best.pt --evaluation .../results.json`, `python -m backend.import_experiment ...`, and `python -m backend.dev --detach`. Selection is local research model configuration, not clinical approval. The Admin experiment ledger contains the new measured centralized run. Historical federated/DP/secure verification metrics remain unchanged.

**Limits:** this is a centralized BatchNorm ResNet18 run with no DP-SGD or secure aggregation. Its score must not be presented as a federated/privacy-enabled score. The test split was used in earlier project experiments; it is not a fresh external benchmark. Patient identifiers remain unavailable. No patient-independent, clinical, calibrated individual-risk or production privacy claim follows from exceeding 85% on these 111 images. No attempt was made to keep tuning on this run's final test score.
