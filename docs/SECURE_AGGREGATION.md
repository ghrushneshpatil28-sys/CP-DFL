# Secure aggregation implementation and validation

The secure option runs Flower **1.40.0** `SecAggPlusWorkflow` and `secaggplus_mod`, with three separately spawned hospital processes and a versioned cryptographic PRG adapter. This replaces the previous unsupported option. It is an implemented local research protocol, not an independently audited production service.

## Run it

In Admin → Federated learning → Configure experiment, choose FedAvg or FedProx and enable **secure aggregation**. The separate training worker must be running (`START.cmd` starts it). Or, from the repository root:

```powershell
.\backend\venv\Scripts\python.exe -m ml.train --algorithm fedavg --secure-aggregation --rounds 1 --image-size 64 --batch-size 8 --optimizer sgd --threads 2 --output ml/outputs/experiments/secagg-verification
.\backend\venv\Scripts\python.exe -m backend.import_experiment ml/outputs/experiments/secagg-verification
```

Use a fresh output directory for every run. Add `--dp` for experimental example-level Opacus DP-SGD. Centralized training rejects secure aggregation because it has no hospital aggregation step. Plaintext experiments remain available as explicitly configured baselines; they do not silently substitute for failed secure rounds.

## Protocol boundary

The coordinator sends the same global GroupNorm ResNet18 to all three clients. Local training and optional DP accounting happen inside each hospital process. Client callbacks return model arrays to Flower's modifier **inside that process**. The modifier quantizes, masks, and clears the arrays before any IPC response is serialized. The coordinator receives public keys, encrypted key shares, masked integer vectors and reconstruction shares, never an individual unmasked local model. Private keys, model state and client accountant state are not returned through the transport.

The adapter executes all four upstream workflow stages: setup, share keys, collect masked vectors, and unmask. Flower uses elliptic-curve key agreement, authenticated encryption of shares, Shamir secret sharing, private masks and pairwise masks. The application does not replace this protocol with plain averaging or independently invented masking.

The local transport implements the workflow's Grid `send_and_receive` interface using private multiprocessing pipes and Flower protobuf messages. It avoids a Ray requirement on this Windows/Python environment. It is **not** a Flower SuperLink/SuperNode network deployment. Child processes are closed even after failed rounds. No dependency files are edited.

## Cryptographic PRG adapter

Inspection of the pinned Flower source found its default `pseudo_rand_gen` folds its input into a 32-bit NumPy RandomState seed. That implementation is **not used here**. The application installs the same explicit replacement on client and server: HKDF-SHA256 derives a 256-bit key from the entire secret seed, with a PULSAR protocol/version/array-index/shape domain, then `cryptography` ChaCha20 expands the mask stream. Uniform little-endian uint32 entries are represented as int64 for modular arithmetic. The fixed modulus is 2^32; other moduli fail. New protocol keys and private seeds are generated every round using Flower's cryptographic primitives. Public experiment seeds cannot select masks.

All peers must use this adapter; it is a versioned variant of Flower SecAgg+, not wire-compatible with an unmodified mask generator. The adapter pins/checks the tested Flower version and uses pinned `cryptography`. Tests cover seeds that collide under the original 32-bit fold, deterministic expansion, full-seed dependence, array-domain separation and fresh masked uploads across rounds. These tests support implementation correctness; they are not an independent cryptographic proof or audit.

## Threshold and dropout policy

| Situation | Behavior |
| --- | --- |
| Registered clients | Exactly Hospital A, B and C |
| Key establishment | All three must complete setup and share-keys |
| Reconstruction threshold | Two shares out of three |
| Minimum masked contributors | Two |
| One dropout before masked upload, after key exchange | Aggregate the two uploaded models; reconstruct dropped pairwise masks |
| One dropout after masked upload, before unmask reply | Recover the aggregate including all three uploads |
| Dropout during setup/share-keys | Abort; no model commit |
| Fewer than two contributors or reconstruction responders | Abort; no model commit |
| Malformed/replayed response or invalid encrypted share | Reject and abort; no plaintext fallback |

Recovery applies within the current round. Subsequent rounds require all three clients to establish new keys; permanent client loss requires a new experiment. The coordinator enforces message routing, request correlation, round identity, masked vector count/shape/dtype/range and public sample counts. NumPy decoding disallows pickle. Inconsistent data fail explicitly. These checks do not make the protocol Byzantine robust or prevent model poisoning.

## Threat model and release scope

The supported model is a **semi-honest coordinator with no colluding clients**, following the prescribed cohort/model/protocol. At least two contributing clients are required. A coordinator that controls client processes, colludes with clients, sends inconsistent global models, manipulates cohorts, reads process memory or reads shared-host files is outside this scope. Three processes are not equivalent to three independently administered hospitals. No protection against a host administrator or compromised client is asserted.

Public sample counts, selected/participating client IDs, global model, timing, protocol message lengths and held-out validation/test results remain visible. Raw client training losses and class distributions are withheld in secure mode, including when DP is disabled. Class-label names and partition construction remain outside the privacy guarantee. Aggregates can still leak information about small cohorts or across releases. Secure aggregation is **not differential privacy** and has no epsilon/delta budget.

The supported model architecture remains ResNet18, using GroupNorm and non-inplace residual operations. GroupNorm avoids sending BatchNorm integer counters through an incompatible floating weighted quantizer. This normalization variant is stored in checkpoints and must be considered when comparing experiments. Secure FedAvg and FedProx use the same canonical factory and strict inference loader.

## Quantization and measurement

Parameters use a clipping bound of 8, quantization range 2^22, modulus 2^32 and the actual maximum public client sample count as `max_weight`. The client rejects nonfinite parameters and parameters exceeding the bound, avoiding silent saturation. Flower's fixed-point weighted reconstruction approximates floating-point FedAvg. Tests compare unequal-weight known vectors within 3e-5; this is not bitwise equality or a universal accuracy guarantee. Counts must be positive integers below 2^22. An invalid reconstructed model is rejected before checkpoint/metric commit.

Each successful round persists the protocol version, threshold, actual contributors, stage responder lists, quantization parameters, duration, and byte counts of serialized Flower messages in both directions. OS pipe framing and network overhead are excluded. Plaintext baselines count logical tensor bytes; the UI exposes the scope so these are not mistaken for identical measurements. No raw protocol secrets or masked payloads are persisted as audit evidence.

With DP enabled, each hospital composes its Opacus accountant across rounds inside its persistent process. Only accountant metrics are released; raw accountant state stays local and no server `accountants.pt` is written for secure runs. Crashes fail the experiment rather than silently restarting accounting. Existing experimental DP limits (example-level, research PRNG, fixed partitions, public counts, evaluation outside the budget, no automatic composition across experiments) still apply.

## Verification

```powershell
.\backend\venv\Scripts\python.exe -m pytest tests/test_secure_aggregation.py tests/test_worker.py tests/test_api.py -q --basetemp=.test-tmp/secagg-check
cd frontend
npm.cmd run build
npm.cmd run lint
npx.cmd playwright test
```

Protocol tests use known vectors solely for mathematical verification. Worker tests train actual ResNet18 models on a small subset of the repository's real dataset, including secure FedAvg and secure FedProx with composed DP accounting. No test fixture is used for production prediction or presented as a clinical benchmark. The final test counts and full-data verification run are recorded in `IMPLEMENTATION.md` and `verification-summary.json` after execution.

References: [Flower secure aggregation example](https://flower.ai/docs/examples/flower-secure-aggregation.html), [Flower protocol overview](https://flower.ai/docs/framework/main/en/explanation-ref-secure-aggregation-protocols.html), [cryptography ChaCha20](https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/#cryptography.hazmat.primitives.ciphers.algorithms.ChaCha20), [cryptography HKDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf).
