# DFL CP — LungIQ: Lung Cancer Detection Project

Detailed project documentation, implementation inventory, model information, setup instructions, and current limitations.

**Documentation reviewed:** 19 October 2026. This README describes the source code and artifacts present in this checkout. Saved experiment results are identified separately from current runtime behavior; no overall completion percentage is invented because the project has no agreed milestone or acceptance checklist.

> This is a research and educational prototype. Its model outputs, clinical scores, and heatmaps are not validated medical diagnoses. In particular, the current image test split overlaps the training split, and the clinical model uses synthetic data.

## Contents

1. [Project overview](#1-project-overview)
2. [What has been implemented](#2-what-has-been-implemented)
3. [Technology stack](#3-technology-stack)
4. [Architecture and request lifecycle](#4-architecture-and-request-lifecycle)
5. [Project structure and file responsibilities](#5-project-structure-and-file-responsibilities)
6. [Models used and available experiments](#6-models-used-and-available-experiments)
7. [Dataset inventory and data quality](#7-dataset-inventory-and-data-quality)
8. [Image processing and inference](#8-image-processing-and-inference)
9. [Clinical features and tabular inference](#9-clinical-features-and-tabular-inference)
10. [Combining image and clinical results](#10-combining-image-and-clinical-results)
11. [Grad-CAM explainability](#11-grad-cam-explainability)
12. [Recorded performance and interpretation](#12-recorded-performance-and-interpretation)
13. [Frontend behavior](#13-frontend-behavior)
14. [API reference](#14-api-reference)
15. [Installation and local setup](#15-installation-and-local-setup)
16. [Running and using the application](#16-running-and-using-the-application)
17. [Configuration](#17-configuration)
18. [Training and evaluation scripts](#18-training-and-evaluation-scripts)
19. [Saved artifacts and generated files](#19-saved-artifacts-and-generated-files)
20. [Verification and tests](#20-verification-and-tests)
21. [Known issues and unfinished work](#21-known-issues-and-unfinished-work)
22. [Suggested implementation order](#22-suggested-implementation-order)
23. [Troubleshooting](#23-troubleshooting)
24. [Project ownership, provenance, and license](#24-project-ownership-provenance-and-license)

## 1. Project overview

The workspace is named **DFL CP**. The web interface calls the application **LungIQ**, and the backend identifies itself as **Lung Cancer Early Detection API**, version **2.0.0**. No authoritative expansion of “DFL CP” is defined in the inspected application files.

The project combines two inputs:

- An optional uploaded chest scan image, processed by a deep learning classifier.
- Structured patient information: age, gender, smoking history, family history, symptoms, and oral intake habits.

It returns a predicted image class, a confidence value, probabilities for all classes, an explanation, and an optional Grad-CAM overlay. Users can submit clinical information without an image, although that path cannot establish a cancer subtype from imaging evidence.

The four saved image classes, in the current class mapping order, are:

| Index | Class |
| --- | --- |
| 0 | Adenocarcinoma |
| 1 | Large Cell Carcinoma |
| 2 | No Cancer |
| 3 | Squamous Cell Carcinoma |

“No Cancer” is a dataset/model label, not a guarantee about a patient's health. The application accepts raster images described as CT or X-ray scans; separate evidence of reliable X-ray subtype classification is not present.

## 2. What has been implemented

The source contains the main pieces of a local full-stack prototype: a browser form, API, image inference, clinical inference, fusion logic, saved weights, explainability code, and experiment artifacts. Training and deployment readiness are incomplete.

| Area | Work present | Status and practical scope |
| --- | --- | --- |
| Patient form | Demographics, smoking details, family history | Implemented in React |
| Symptom input | Add/remove named symptoms with severity | Implemented |
| Habit input | Add/remove oral intake items with frequency | Implemented |
| Image upload | Optional file selection, local preview, removal | Implemented |
| Result display | Subtype, confidence, class probabilities, explanation | Implemented |
| Explainability display | Renders a returned Grad-CAM data URI | Implemented; overlay generation can return null |
| Backend | FastAPI application and multipart prediction endpoint | Implemented |
| Validation | JSON/Pydantic request parsing and basic image decoding/color checks | Partial; clinical ranges and upload controls are limited |
| Image classification | ResNet18 loader, preprocessing, softmax probabilities | Implemented; checkpoint compatibility needs care when retraining |
| Alternate image model | MobileNetV2 fallback loader and saved checkpoints | Present |
| Clinical model | Saved classifier/scaler, 12-feature extraction, heuristic fallback | Implemented as a synthetic-data demonstration |
| Fusion | Image/clinical weights, aggregate cancer decision, subtype selection | Implemented; not clinically validated |
| Dataset tooling | Audit, cleaning, splitting, inspection, manifest generation | Present; several scripts have obsolete paths/imports |
| Training | ResNet18, MobileNetV2, generic cross-validation, final training | Scripts present; not a consistent reproducible pipeline yet |
| Evaluation | Classification reports, confusion matrices, plots | Historical artifacts present |
| Word project report | Generation script and an existing `.docx` artifact | Present; separate from the prediction API |
| Test scripts | Two manual HTTP scripts | Present; incomplete and partly outdated |
| Persistence | Local model files, upload directory, output folders | Implemented through the filesystem |
| Database/accounts/history | No implementation found | Unimplemented |
| Production hosting/CI/containers | No application deployment or CI configuration found | Unimplemented |

The project therefore has substantial prototype implementation, but evidence does not support calling it production-ready, clinically validated, or a fully reproducible ML system.

## 3. Technology stack

### Frontend

Versions below are declarations in `frontend/package.json`, unless indicated otherwise.

| Technology | Version / format | Role |
| --- | --- | --- |
| React | `^19.2.0` | Component rendering and state |
| React DOM | `^19.2.0` | Browser root rendering |
| JavaScript | ES modules and JSX | Application language; no TypeScript application code |
| Vite | `^7.3.1` | Development server, API proxy, production bundle |
| Vite React plugin | `^5.1.1` | React build integration |
| CSS | Custom stylesheet | Dark theme, cards, form layout, responsive behavior |
| ESLint | `^9.39.1` | Static linting; React Hooks and Refresh plugins |
| `lucide-react` | `^0.575.0` | Declared dependency; current `App.jsx` uses inline SVG icons |
| Browser Fetch API | Native | Sends multipart requests; Axios is not used |
| Inter / Outfit | Google Fonts references | Interface typography, with local fallback fonts |

`package-lock.json` is present. The installed Vite 7.3.1 package declares Node support as `^20.19.0 || >=22.12.0`; the older README's generic “Node 18+” instruction does not match this dependency.

### Backend and machine learning

`backend/requirements.txt` declares these packages without version pins:

| Package | Role |
| --- | --- |
| `fastapi` | REST API and generated OpenAPI documentation |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response models; code uses the v2 `model_dump()` API |
| `python-multipart` | Multipart form and file parsing |
| `httpx` | HTTP client and FastAPI TestClient support |
| `pytest` | Test runner dependency; existing scripts are mostly manual smoke checks |
| `Pillow` | Image decoding, color statistics, resizing, and JPEG output |
| `torch` | Neural network loading, inference, gradients, and training |
| `torchvision` | ResNet18/MobileNetV2 architectures and image transforms |
| `timm` | Model creation in experimental training/evaluation scripts |
| `joblib` | Serialized clinical model/scaler loading |
| `scikit-learn` | Clinical models, scaling, data splits, and classification metrics |
| `numpy` | Feature vectors, probabilities, and image operations |
| `opencv-python` | Used in auxiliary image/Grad-CAM tooling |

Additional dependencies are referenced outside the main requirements: `pandas`, `matplotlib`, `seaborn`, `albumentations`, `python-docx`, and `requests`. Which ones are needed depends on the script being run. They are not all installed in the bundled backend environment.

### Observed backend environment

This is a local inventory from `backend/venv`, not a supported-version policy or a reproducible lockfile:

| Component | Observed version |
| --- | --- |
| Python | 3.14.0 |
| FastAPI / Uvicorn | 0.133.1 / 0.41.0 |
| Pydantic | 2.12.5 |
| PyTorch / torchvision | 2.12.0+cpu / 0.27.0+cpu |
| timm | 1.0.27 |
| scikit-learn / joblib | 1.8.0 / 1.5.3 |
| NumPy / Pillow | 2.4.2 / 12.1.1 |
| httpx / python-multipart | 0.28.1 / 0.0.22 |
| OpenCV | 4.13.0.92 |
| pytest | 9.0.2 |

Both `.venv/` and `backend/venv/` exist. Their configuration records original creation paths from other locations. Creating a fresh environment avoids depending on copied environment paths.

### Storage and external services

- Storage is local: `.pth` weights, `.pkl` artifacts, JSON metadata, CSV files, uploads, reports, and plots.
- No SQL/NoSQL database, ORM, user authentication, or patient record service is integrated.
- No cloud inference API, LLM, chatbot model, or API key is required by the application code.
- Model initialization for training can download pretrained weights. Normal inference uses saved local checkpoints.
- Google Fonts is the external resource referenced by the frontend HTML.

## 4. Architecture and request lifecycle

```mermaid
flowchart TD
    UI[React browser form] -->|multipart: data JSON and optional image| API[FastAPI /api/predict]
    API --> REQ[Pydantic clinical request]
    API --> UP[Save image with UUID filename]
    UP --> VAL[Pillow decode and color check]
    VAL --> MOD[Heuristic CT or X-ray label]
    MOD --> IMG[ResNet18 first, MobileNetV2 fallback]
    IMG --> CAM[Optional Grad-CAM overlay]
    REQ --> TAB[12 clinical features]
    TAB --> CL[Saved classifier and scaler, or heuristic]
    IMG --> FUSE[Fusion and aggregate cancer decision]
    CL --> FUSE
    CAM --> FUSE
    FUSE --> RESPONSE[Six-field PredictionResponse]
    RESPONSE --> UI
```

1. React holds form values in `useState` and builds a JSON object.
2. It appends the JSON to multipart field `data`, with optional file field `image`.
3. Vite proxies `/api` requests to the backend during development.
4. FastAPI parses and validates clinical input using `PredictionRequest`.
5. When a file is included, it is written to `backend/uploads/` under a UUID filename.
6. The image pipeline decodes it, applies a basic color heuristic, assigns a heuristic modality label, and attempts neural inference.
7. The clinical predictor loads its saved model/scaler on first use, extracts 12 features, and produces a binary malignancy signal. If artifacts cannot load, a weighted heuristic is used.
8. The combined predictor fuses available signals and produces a class distribution and explanation.
9. `ml_service.py` maps the internal result to the six public response fields.
10. React renders the result and heatmap if one is available.

The image predictor is initialized when the backend's image pipeline module is imported. Both model services use process-local singleton instances; there is no separate model-serving process or inference queue.

## 5. Project structure and file responsibilities

```text
DFL-CP/
|-- README.md                         # This detailed project reference
|-- 123redme.md                        # Older project overview
|-- Project_Details_Report.docx        # Existing Word project report
|-- dataset_audit.py                   # Image integrity/duplicate audit utility
|-- dataset_audit_report.json          # Existing audit output; empty class inventory
|-- error_log.txt                      # Historical model-loading traceback
|-- .agent/                           # Local agent guidance and development utilities
|-- .venv/                            # Existing root Python environment
|-- backend/
|   |-- main.py                       # FastAPI routes, CORS, uploads, static mount
|   |-- schemas.py                    # PredictionRequest and PredictionResponse
|   |-- image_pipeline.py             # Image checks, modality heuristic, inference bridge
|   |-- ml_service.py                 # Clinical/image orchestration and response mapping
|   |-- requirements.txt              # Unpinned main Python dependencies
|   |-- test_api.py                   # Manual asynchronous HTTP smoke script
|   |-- api_test.py                   # Older manual HTTP integration script
|   |-- generate_report.py            # Word project-report generator
|   |-- test_valid.jpg                # Existing smoke-test image
|   |-- test_img.jpg                  # Additional local test image
|   |-- DataSet/
|   |   |-- pool/<class>/             # Current image pool
|   |   |-- train/<class>/            # Current training folders
|   |   `-- test/<class>/             # Current test folders; overlap training
|   |-- uploads/                      # Saved accepted uploads
|   `-- venv/                         # Existing backend Python environment
|-- frontend/
|   |-- package.json                  # Frontend dependencies and scripts
|   |-- package-lock.json             # npm dependency lockfile
|   |-- vite.config.js                # React plugin and /api development proxy
|   |-- eslint.config.js              # JavaScript/React lint configuration
|   |-- index.html                    # Root HTML, title, Google Fonts references
|   |-- README.md                     # Original frontend scaffold documentation
|   `-- src/
|       |-- main.jsx                  # React root and StrictMode
|       |-- App.jsx                   # Form, submission, and result components
|       `-- index.css                 # Theme and responsive styles
`-- ml/
    |-- __init__.py
    |-- README.md                     # Older ML overview; some claims are stale
    |-- inference/
    |   |-- image_predictor.py        # Checkpoint loaders, softmax, runtime Grad-CAM
    |   |-- tabular_predictor.py      # Clinical feature encoding and inference
    |   `-- combined_predictor.py     # Weighted fusion and internal explanations
    |-- training/
    |   |-- train_image.py            # Dynamic-class ResNet18 trainer
    |   |-- train_image_4class.py     # Legacy MobileNetV2 trainer
    |   |-- train_tabular.py          # Synthetic CSV + RF/LR model comparison
    |   |-- train_cv.py               # Generic timm stratified cross-validation
    |   |-- train_final.py            # timm ResNet18 trainer; evaluates on train data
    |   |-- evaluate.py               # Legacy MobileNetV2 evaluation
    |   |-- evaluate_advanced.py      # Generic timm metrics/plots
    |   |-- prepare_dataset.py        # Legacy manifest preparation
    |   |-- inspect_dataset.py        # Legacy split/class inspection
    |   `-- run_gpu_training.ps1      # Changes torch installation, then trains
    |-- utils/
    |   |-- config.py                 # Current paths and shared hyperparameters
    |   |-- clean_dataset.py          # Rename/deduplicate utility
    |   |-- merge_pool.py             # Merge split folders into a pool
    |   |-- split_data.py             # Copy pool into train/test partitions
    |   `-- gradcam_v2.py             # Auxiliary timm Grad-CAM utility
    |-- saved_models/                 # Checkpoints, scaler, class mapping, metadata
    |-- data/processed/               # Historical manifest, class report, synthetic CSV
    `-- outputs/
        |-- reports/                  # Saved evaluation/training reports
        |-- plots/                    # Saved training curves
        `-- heatmaps/                 # Static heatmap mount directory
```

`__pycache__` folders and installed dependency directories are omitted from this tree.

## 6. Models used and available experiments

### Primary image model: ResNet18

- Framework: PyTorch, using a torchvision architecture at runtime.
- Primary artifact: `ml/saved_models/resnet18_model.pth`.
- Input: RGB tensor resized to `224 x 224` with ImageNet normalization.
- Runtime classifier head: `Linear(512, number_of_classes)`.
- Output: softmax probabilities for the four current classes.
- Device: CUDA if `torch.cuda.is_available()`, otherwise CPU.
- Runtime Grad-CAM target: `model.layer4[-1]`.
- Saved metadata describes ImageNet initialization and reports best accuracy `0.8501` and F1 `0.8714`. These are recorded metadata values, not independently reproduced held-out results.

There are two different ResNet18 training paths. `train_image.py` builds a multi-layer head, whereas `train_final.py` uses a timm ResNet18 and saves a raw state dictionary. The runtime loader constructs a plain linear head. These differences matter: the loader uses `strict=False`, so some incompatible checkpoints may leave classifier parameters uninitialized from the saved weights while still appearing loaded. See the training and limitations sections.

### Alternate image model: MobileNetV2

- Fallback artifact: `ml/saved_models/image_model_best.pth`.
- Additional artifact: `ml/saved_models/image_model_mobilenetv2_improved.pth`.
- Used only if the ResNet18 path does not load successfully.
- Loader reconstructs a custom head from checkpoint tensor shapes: dropout `0.3`, linear layer, BatchNorm, ReLU, dropout `0.2`, final linear layer.
- Runtime Grad-CAM target: `model.features[-1]`.
- The improved checkpoint is not selected automatically by its own filename; inference explicitly checks `image_model_best.pth`.

This is a fallback arrangement, not an ensemble of two image models.

### Clinical model: Logistic Regression artifact; Random Forest comparison in training

- Artifact: `ml/saved_models/tabular_model.pkl`, accompanied by `scaler.pkl`.
- Current `tabular_metadata.json` identifies the saved model as **LogisticRegression** with recorded accuracy **0.90**.
- `train_tabular.py` compares Logistic Regression against Random Forest and saves whichever has higher synthetic test accuracy; ties favor Random Forest.
- Both operate on a `StandardScaler` transformation of the same 12 clinical features.
- The prediction is binary: `No / Benign` versus `Malignant`.
- The data is synthetic and generated from rules; its accuracy does not establish performance on real patients.

Some existing docstrings say runtime always uses rule-based clinical scoring in `ml_service.py`. The current implementation instead calls `TabularPredictor`, which uses the saved model when it loads and falls back to rules when it cannot load.

### Experimental model support

`train_cv.py` uses `timm.create_model` with a configurable model name and defaults to `resnet50`. Advanced evaluation and auxiliary Grad-CAM tooling also accept a model name. The Grad-CAM utility includes target-layer branches for ResNet, DenseNet, and EfficientNet families.

This demonstrates code support for additional experiments. It does **not** prove those models were trained successfully: no corresponding ResNet50, DenseNet, or EfficientNet result/checkpoint was found in the inspected model artifacts.

### Fusion is an algorithm, not a separately trained model

The combined predictor uses fixed weights and decision rules. There is no learned multimodal network or separate fusion checkpoint.

## 7. Dataset inventory and data quality

### Current files in this checkout

Counts below were taken directly from `backend/DataSet/` on the documentation review date.

| Class | Train | Test | Pool |
| --- | ---: | ---: | ---: |
| Adenocarcinoma | 217 | 33 | 217 |
| Large Cell Carcinoma | 187 | 29 | 187 |
| No Cancer | 66 | 10 | 66 |
| Squamous Cell Carcinoma | 257 | 39 | 257 |
| **Total** | **727** | **111** | **727** |

There is **no `backend/DataSet/valid/` directory** in the current checkout, even though the shared configuration and several trainers expect it.

The columns count file copies, not independent observations. A fresh read-only SHA-256 comparison across these folders found:

| Check | Result |
| --- | ---: |
| Unique file-content hashes across train/test/pool | 727 |
| Hashes shared between train and test | 111 |
| Hashes shared between train and pool | 727 |
| Duplicate hash groups within train | 0 |
| Duplicate hash groups within test | 0 |
| Duplicate hash groups within pool | 0 |

Every current test image is an exact byte-for-byte duplicate of an image in training. Pool and train contain the same unique image contents. This test folder cannot provide an independent estimate of generalization.

Byte-level hashing does not identify different slices from the same patient, recompressed copies, or augmented variants. Patient-level separation would still need verification after removing exact duplicates.

### Historical split report

`ml/data/processed/class_distribution.txt` describes an older split:

| Class | Historical train | Historical valid | Historical test |
| --- | ---: | ---: | ---: |
| No Cancer | 148 | 13 | 54 |
| Adenocarcinoma | 195 | 23 | 120 |
| Large Cell Carcinoma | 115 | 21 | 51 |
| Squamous Cell Carcinoma | 155 | 15 | 90 |
| **Total** | **613** | **72** | **315** |

These values do not describe the current folders. The improvement report additionally describes merging 613 training and 72 validation samples into a 685-image pool and splitting that pool 80/20.

### Provenance and audit gaps

- No authoritative dataset download URL, patient identifiers, dataset version, or dataset license is recorded in the inspected active configuration.
- `dataset_manifest.csv` contains absolute paths from an older machine and labels from a previous three-class dataset, including `Benign Nodule`. It is not the current four-class inventory.
- Existing `dataset_audit_report.json` has an empty `class_distribution` and zero counters. It is not evidence that the current dataset is clean.
- `dataset_audit.py` points to an obsolete `D:` directory; missing split folders are skipped, which can produce a misleading empty report.
- Class counts are imbalanced: the current `No Cancer` training class has 66 files, while Squamous Cell Carcinoma has 257.

## 8. Image processing and inference

### Input handling

The backend uses Pillow to open and fully decode the uploaded file. An undecodable file produces HTTP 400. The UI uses `accept="image/*"` and describes scan uploads; the backend's practical decoding support depends on Pillow rather than a strict file-extension allowlist.

There is no DICOM reader, CT-volume loader, Hounsfield-unit processing, lung segmentation, or series-level inference. An uploaded scan is treated as a single raster image.

### Basic color validation

`_validate_grayscale_medical()` computes the mean of each RGB channel. It rejects the image when:

```text
max(mean_red, mean_green, mean_blue)
  - min(mean_red, mean_green, mean_blue) > 40
```

This is a simple color check. It cannot establish that an image is a medical scan, a chest image, or correctly oriented. Grayscale nonmedical images can pass.

### Modality heuristic

After grayscale conversion, the pipeline measures the proportion of pixels with intensities below 20:

```text
dark_pixel_ratio > 0.40  -> CT_SCAN
otherwise               -> X_RAY
```

This label is an internal heuristic. It is not a learned modality classifier, does not select a different neural model, and is not included as a separate field in the public six-field response.

### Neural preprocessing

1. Convert to RGB.
2. Resize directly to `224 x 224`.
3. Convert to a tensor.
4. Normalize with mean `[0.485, 0.456, 0.406]` and standard deviation `[0.229, 0.224, 0.225]`.
5. Add a batch dimension and move to the selected device.
6. Run the model in evaluation mode and apply softmax.

Class names normally come from `class_mapping.json`; supported checkpoint metadata can also supply names. Fallback class lists and known label handling remain in the code, so the system is not completely free of hardcoded labels.

### Image failure path

If the image model is unavailable or inference fails, `image_pipeline.py` calculates a legacy heuristic tumor score from edges and brightness. However, the active `ml_service.py` only passes `image_analysis['ml_result']` into fusion. Therefore, the heuristic image score is **not** used in the final public prediction; that path effectively relies on clinical input instead.

## 9. Clinical features and tabular inference

| Position | Feature | Encoding / derivation |
| --- | --- | --- |
| 1 | `age` | Integer age |
| 2 | `gender_enc` | Female = 0, Male = 1, Other = 2 |
| 3 | `smoking_status_enc` | Never = 0, Former = 1, Current = 2 |
| 4 | `cigarettes_per_day` | Integer |
| 5 | `years_smoking` | Integer |
| 6 | `family_history` | Boolean converted to 0/1 |
| 7 | `symptom_count` | Number of symptom dictionary entries |
| 8 | `has_severe_symptom` | Any severity equals `Severe`, case insensitive |
| 9 | `has_cough` | Any symptom name contains `cough` |
| 10 | `has_weight_loss` | Any symptom name contains `weight` |
| 11 | `daily_tobacco` | Daily item containing tobacco, betel, or nicotine |
| 12 | `daily_alcohol` | Daily item containing alcohol |

Unknown gender strings default to the Male encoding; unknown smoking strings default to Never. Symptom and habit dictionaries are accepted as arbitrary string keys/values by the schema. The UI's full symptom severity and intake detail is reduced to the features above.

The saved model predicts a malignancy signal using `predict_proba(...)[1]`. Explanations show globally important Random Forest features or the largest absolute Logistic Regression coefficients. These are not individualized causal explanations; coefficient output also omits the coefficient sign.

### Heuristic clinical fallback

When model/scaler loading fails, the fallback signal is:

```text
0.15 * min(age / 80, 1)
+ 0.30 * (smoking_status_enc / 2)
+ 0.12 * family_history
+ 0.20 * min(symptom_count / 6, 1)
+ 0.10 * has_severe_symptom
+ 0.08 * has_weight_loss
+ 0.05 * daily_tobacco
```

The implementation caps the total at `0.99`. Cigarette count, smoking duration, gender, cough, and alcohol are extracted but do not contribute to this fallback formula. If an already-loaded model raises during prediction, it returns a failure result rather than retrying with the heuristic.

### Synthetic training data

`train_tabular.py` can generate 800 synthetic records. The generated labels come from a hand-authored risk equation plus Gaussian noise. It then compares:

- Random Forest: 100 trees, maximum depth 8, minimum split size 5, balanced class weights, random seed 42.
- Logistic Regression: maximum 500 iterations, balanced class weights, random seed 42.

The script uses a stratified 80/20 train/test split. It currently fits the scaler **before** splitting, which leaks preprocessing information into evaluation. This should be corrected alongside replacing demo records with appropriately sourced real data.

## 10. Combining image and clinical results

Default weights in `ml/inference/combined_predictor.py` are:

```text
IMAGE_WEIGHT   = 0.70
TABULAR_WEIGHT = 0.30
```

When both predictors succeed:

```text
image_cancer = sum(image probabilities for all cancer subtypes)
image_safe   = sum(image probabilities for safe classes)
clinical_cancer = clinical malignancy signal

fused_cancer = 0.70 * image_cancer + 0.30 * clinical_cancer
fused_safe   = 0.70 * image_safe   + 0.30 * (1 - clinical_cancer)
```

The code includes a rule: if aggregate image cancer probability exceeds aggregate image safe probability, but fusion reverses that comparison, it restores the image aggregate probabilities. This is a coded decision preference, not evidence that false negatives are prevented.

Fused cancer probability is distributed between cancer subtypes **in proportion to the image model's cancer subtype probabilities**. It is not divided equally when an image result is available. Safe-class probability is distributed proportionally too.

Available-input behavior:

| Available successful results | Behavior |
| --- | --- |
| Image + clinical | Weighted aggregate fusion and proportional subtype redistribution |
| Image only | Uses image class probabilities |
| Clinical only | Divides the binary clinical cancer signal equally among cancer subtypes |
| Neither | Uses a default cancer signal of `0.30`, then the clinical-only distribution logic |

The final decision first compares **total cancer probability** with **total safe probability**, then selects the largest class within the winning group. Consequently, `predicted_subtype` need not be the globally largest individual probability. The returned `confidence` is the selected individual class probability, not the aggregate cancer probability.

Probabilities are normalized and rounded to four decimal places, so displayed totals can differ slightly from 1. Clinical-only output cannot distinguish the three cancer subtypes; equal subtype scores can result in selection by mapping order.

The internal fusion result contains risk score, risk level, modality, precautions, and other legacy fields. `PredictionResponse` exposes only the six fields documented below.

## 11. Grad-CAM explainability

The runtime predictor:

1. Registers activation and gradient hooks on the target feature block.
2. Backpropagates the image model's selected class score.
3. Averages gradients spatially to obtain channel weights.
4. Combines the feature maps, applies ReLU, and normalizes the activation map.
5. Resizes it to the original image dimensions.
6. Applies a jet-like colormap and blends it over the original image with heatmap alpha `0.45`.
7. Encodes the overlay as JPEG, quality 85, and returns `data:image/jpeg;base64,...`.

The main runtime path returns this image inline; it does not need to write a heatmap file. The backend nevertheless mounts `ml/outputs/heatmaps/` at `/static/heatmaps` for existing/auxiliary files.

Heatmap generation can fail independently of classification, returning `gradcam_image: null`. The code's Grad-CAM accumulator is created on CPU, which can cause a device mismatch on CUDA. The overlay explains the image model's chosen class, which can differ from the final fused class. A heatmap is not a tumor segmentation mask or proof of tumor location.

## 12. Recorded performance and interpretation

These are values saved in the project, not results of a fresh benchmark during README preparation.

| Artifact | Model/context | Recorded result | Interpretation |
| --- | --- | --- | --- |
| `saved_models/model_metadata.json` | ResNet18 | Best accuracy 85.01%; best F1 0.8714 | Metadata calls these validation values; current `train_final.py` evaluates on its own training directory |
| `outputs/reports/classification_report.txt` | Earlier four-class image run | Accuracy about 79%; macro F1 about 0.81; support 72 | Historical report; trainer writes this from the validation loader |
| `outputs/reports/classification_report_4class.txt` | Historical four-class baseline | Test accuracy 65.40%; macro F1 0.6887; support 315 | Historical test set, different from current folders |
| `outputs/reports/improvement_report.txt` | Improved MobileNetV2 | Test accuracy 73.65%; test macro F1 0.7529; validation macro F1 0.8110 | Historical experiment; report names MobileNetV2 as its best model |
| `saved_models/tabular_metadata.json` | Logistic Regression | Accuracy 90% | Synthetic-record result; not patient validation |

### Historical improved MobileNetV2 per-class results

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| No Cancer | 0.9815 | 0.9815 | 0.9815 | 54 |
| Adenocarcinoma | 0.7273 | 0.7333 | 0.7303 | 120 |
| Large Cell Carcinoma | 0.5610 | 0.9020 | 0.6917 | 51 |
| Squamous Cell Carcinoma | 0.7759 | 0.5000 | 0.6081 | 90 |

The improvement report describes weighted loss, label smoothing, augmentation changes, BatchNorm, more backbone fine-tuning, cosine scheduling, gradient clipping, and macro-F1-based selection. The exact improved trainer is not present as a corresponding standalone script, so those report statements should not be assumed to describe every current trainer.

The stored metrics cannot be combined into one “project accuracy”: models, data splits, evaluation procedures, and artifact dates are not consistently tied together. No held-out fusion benchmark, calibration analysis, external validation, or patient-level evaluation was found.

## 13. Frontend behavior

All main UI behavior is in `frontend/src/App.jsx`:

- Patient age input with browser limits 1–120; Male/Female/Other gender selection.
- Family-history toggle.
- Never/Former/Current smoking selection; conditional cigarette/day and smoking-years inputs.
- Add/remove symptom tags, with Mild/Moderate/Severe severity.
- Add/remove habit tags, with Occasional/Frequent/Daily frequency.
- Image selection, thumbnail preview, filename display, and removal.
- Analyze button, loading spinner, empty state, server error display.
- Subtype result, percentage confidence, model label, class probabilities, explanation, and optional overlay.

Available symptom names are Chronic Cough, Coughing Up Blood, Shortness of Breath, Chest Pain, Chronic Chest Pain, Hoarseness, Unexplained Weight Loss, Bone Pain, Headache, and Fatigue.

Habit choices are Tobacco, Betel Nut, Alcohol, Hot Beverages, Chewing Gum (Nicotine), and Frequent Spices. Presence in the form does not mean each choice is independently represented in the clinical model.

Styling uses CSS custom properties, blue/cyan accents, dark cards, and a two-column layout that becomes one column below 900px. Result coloring is based on the predicted class name. State remains in browser memory; there is no login, saved analysis history, application router, report download flow, or patient dashboard.

## 14. API reference

Default development backend: `http://127.0.0.1:8000`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | API identity, listed routes, image-model status |
| GET | `/api/health` | Basic health and image-model loaded flag |
| POST | `/api/predict` | Clinical input with optional image |
| GET | `/static/heatmaps/<filename>` | Serve an existing file from the heatmap directory |
| GET | `/docs` | FastAPI Swagger UI |
| GET | `/redoc` | FastAPI ReDoc documentation |
| GET | `/openapi.json` | Generated API schema |

### Request

`POST /api/predict` accepts **multipart/form-data**, not a raw JSON request body.

| Multipart field | Type | Required | Description |
| --- | --- | --- | --- |
| `data` | String containing JSON | Yes | `PredictionRequest` object |
| `image` | Uploaded file | No | A Pillow-readable scan image |

Fields inside `data`:

| Field | Type | Required / default |
| --- | --- | --- |
| `age` | Integer | Required |
| `gender` | String | Required; intended Male/Female/Other |
| `smoking_history` | String | Required; intended Never/Former/Current |
| `cigarettes_per_day` | Optional integer | Default `0` |
| `years_smoking` | Optional integer | Default `0` |
| `family_history` | Boolean | Required |
| `symptoms` | Dictionary of string to string | Required; `{}` is accepted |
| `daily_mouth_intake` | Dictionary of string to string | Required; `{}` is accepted |
| `has_imaging` | Boolean | Default `false`; set true by backend after a valid upload |

Example JSON inside the multipart `data` field:

```json
{
  "age": 60,
  "gender": "Male",
  "smoking_history": "Former",
  "cigarettes_per_day": 10,
  "years_smoking": 20,
  "family_history": false,
  "symptoms": {"Chronic Cough": "Moderate"},
  "daily_mouth_intake": {},
  "has_imaging": false
}
```

`has_imaging: true` alone does not supply an image or activate image inference.

### Request example in Python

Run this from the project root while the backend is running:

```python
import json
import httpx

payload = {
    "age": 60,
    "gender": "Male",
    "smoking_history": "Former",
    "cigarettes_per_day": 10,
    "years_smoking": 20,
    "family_history": False,
    "symptoms": {"Chronic Cough": "Moderate"},
    "daily_mouth_intake": {},
}

with open("backend/test_valid.jpg", "rb") as scan:
    response = httpx.post(
        "http://127.0.0.1:8000/api/predict",
        data={"data": json.dumps(payload)},
        files={"image": ("scan.jpg", scan, "image/jpeg")},
        timeout=120.0,
    )
response.raise_for_status()
print(response.json())
```

For a clinical-only request, omit the file open and `files` argument. The local `test_valid.jpg` is a smoke fixture, not a validation dataset or clinical example.

### Response

Exactly these six public fields are defined:

| Field | Type | Meaning |
| --- | --- | --- |
| `predicted_subtype` | String | Selected fused class |
| `confidence` | Float | Selected class probability on a 0–1 scale |
| `probabilities` | Dictionary of floats | Fused distribution for all classes |
| `gradcam_image` | String or null | JPEG data URI when available |
| `fusion_explanation` | String | Joined explanation lines |
| `model` | String | Currently hardcoded to `ResNet18` by `ml_service.py` |

The `model` field does not reliably identify a fallback or clinical-only execution. The internal image predictor records its actual architecture, but the public mapping currently discards that detail.

### Errors and health

- Missing required multipart `data`: FastAPI normally returns HTTP 422.
- Malformed JSON or invalid/missing request-object fields: HTTP 400 from the route's parsing block.
- Undecodable image or rejected color heuristic: HTTP 400; the invalid saved upload is removed.
- Other inference/load failures can degrade to fallback paths instead of failing the request.

`/api/health` returns status `ok`, `ml_model_loaded`, and version `2.0.0`. It checks the image loader flag only; it does not validate weight completeness, tabular readiness, heatmap generation, dataset integrity, or model quality.

## 15. Installation and local setup

### Prerequisites

- Python with compatible PyTorch, torchvision, NumPy, and scikit-learn packages. The inspected environment uses Python 3.14.0; a supported Python-version range is not declared by the project.
- Node matching the installed Vite engine requirement: `^20.19.0 || >=22.12.0`.
- npm.
- The model files in `ml/saved_models/` for normal neural inference.
- Dataset images only if you intend to repair/run training or evaluation.

The following commands assume PowerShell and this checkout at `F:\DFL-CP`. Adjust that root path if the project is moved. A repository clone URL is not supplied because none is configured in this workspace.

### Backend environment

To create a separate clean environment without overwriting either existing environment:

```powershell
Set-Location F:\DFL-CP
python -m venv .venv-local
.\.venv-local\Scripts\python.exe -m pip install --upgrade pip
.\.venv-local\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

Using the environment's Python executable directly avoids requiring PowerShell activation. The requirements are unpinned, so a new installation may differ from the observed environment snapshot.

Optional packages for auxiliary scripts:

```powershell
.\.venv-local\Scripts\python.exe -m pip install pandas matplotlib seaborn albumentations python-docx requests
```

These packages alone do not fix the legacy path, configuration, and checkpoint issues described below.

### Frontend dependencies

```powershell
Set-Location F:\DFL-CP\frontend
npm ci
```

Use the existing npm lockfile for dependency installation. If PowerShell blocks the `npm.ps1` wrapper, invoke `npm.cmd ci` and `npm.cmd run dev` instead.

## 16. Running and using the application

### Terminal 1: backend

With the clean environment created above:

```powershell
Set-Location F:\DFL-CP\backend
..\.venv-local\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

If the bundled backend environment works on your machine, the equivalent command is:

```powershell
Set-Location F:\DFL-CP\backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start from `backend/` because backend modules use imports such as `from schemas import ...`. For development, `--reload` can be added, at the cost of reinitializing the model after reloads.

### Terminal 2: frontend

```powershell
Set-Location F:\DFL-CP\frontend
npm run dev
```

| Service | Default URL |
| --- | --- |
| Browser interface | `http://localhost:5173` |
| Backend | `http://127.0.0.1:8000` |
| API docs | `http://127.0.0.1:8000/docs` |
| Health | `http://127.0.0.1:8000/api/health` |

Use the exact frontend URL printed by Vite. If it selects another port, the backend's explicit CORS allowlist may need adjustment for direct cross-origin access.

### Demo workflow

1. Start both processes and check the health endpoint.
2. Open LungIQ and enter patient information.
3. Add optional symptoms and habits.
4. Optionally select a raster scan image.
5. Click **Analyze Risk**.
6. Inspect class probabilities, explanation, and heatmap if generated.

Accepted uploads remain in `backend/uploads/`. There is no automated expiry or user-facing delete/history feature.

### Frontend build commands

```powershell
Set-Location F:\DFL-CP\frontend
npm run lint
npm run build
npm run preview
```

`build` produces `frontend/dist/`. The configured `/api` proxy is under Vite's development `server` options; a deployed bundle or preview setup needs API routing configured separately. The FastAPI app does not currently serve the React production bundle.

## 17. Configuration

### Shared ML configuration

`ml/utils/config.py` derives active paths relative to the source location:

| Setting | Current value / destination |
| --- | --- |
| Dataset root | `backend/DataSet` |
| Train / valid / test | Corresponding folders under dataset root |
| Image checkpoint | `ml/saved_models/resnet18_model.pth` |
| Clinical model | `ml/saved_models/tabular_model.pkl` |
| Scaler | `ml/saved_models/scaler.pkl` |
| Class map | `ml/saved_models/class_mapping.json` |
| Image metadata | `ml/saved_models/model_metadata.json` |
| Image size | 224 |
| Batch size | 16 |
| Main training epochs | 10 |
| Head learning rate | `1e-3` |
| Fine-tuning learning rate | `5e-5` |
| Early-stopping patience | 3 |
| Random seed | 42 |

`LABEL_ENCODER_PATH` is declared, but no `label_encoder.pkl` is currently present and the active inference code does not require it. Some trainers have their own hyperparameters and absolute paths, so editing this shared configuration does not update every script.

### Frontend API proxy

`frontend/vite.config.js` reads `API_PROXY_TARGET` from the Vite process environment, defaulting to `http://127.0.0.1:8000`:

```powershell
Set-Location F:\DFL-CP\frontend
$env:API_PROXY_TARGET = 'http://127.0.0.1:8001'
npm run dev
```

Start the backend on the matching port if changing this setting. The code does not explicitly load a `.env` file; the example sets the process environment directly.

### Backend CORS allowlist

`backend/main.py` currently allows:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:3000`

Credentials are enabled; methods and headers are allowed with `*`. No authentication layer accompanies this CORS configuration.

## 18. Training and evaluation scripts

The commands in this section describe the entry points. They are **not all ready to run successfully** in the current checkout. Back up saved checkpoints and repair the listed issues before retraining because scripts overwrite shared artifact paths.

### ResNet18 dynamic-class trainer

```powershell
Set-Location F:\DFL-CP
.\.venv-local\Scripts\python.exe .\ml\training\train_image.py
```

Intended behavior:

- Discover class directories in the training split.
- Initialize ImageNet-pretrained ResNet18 and freeze the backbone.
- Replace the head with dropout, linear 512, BatchNorm, ReLU, dropout, and final class layer.
- Train the head for up to 10 epochs, then fine-tune `layer4` for up to 5 more epochs.
- Use cross-entropy, Adam, ReduceLROnPlateau, and early stopping.
- Apply resizing to 248, random crop to 224, horizontal flip, rotation, and color jitter during training; validation uses deterministic resizing/normalization.
- Write checkpoint, class mapping, metadata, validation classification report, and training curve.

Current blockers: the validation folder is missing, and the multi-layer saved head differs from the runtime loader's plain linear head. Any replacement must also preserve class-index consistency.

### Clinical trainer

```powershell
Set-Location F:\DFL-CP
.\.venv-local\Scripts\python.exe .\ml\training\train_tabular.py
```

Intended behavior: create/reuse the synthetic CSV, compare Random Forest and Logistic Regression, and save the winner, scaler, metadata, and an optional Random Forest importance plot.

Current blocker: it imports `CLASS_NAMES` from `config.py`, but that symbol does not exist there. It also needs `pandas`; plotting needs `matplotlib`. After fixing imports, split before fitting the scaler.

### Legacy MobileNetV2 trainer

`train_image_4class.py` trains a pretrained MobileNetV2 head, followed by fine-tuning of the final two backbone blocks. It uses shared hyperparameters, cross-entropy, Adam, and ReduceLROnPlateau.

Current blockers: missing `CLASS_NAMES` and `FOLDER_TO_LABEL` configuration symbols, no validation folder, and a destination conflict. Despite its docstring naming `image_model_best.pth`, it saves to shared `IMAGE_MODEL_PATH`, currently the ResNet18 filename. Do not use it to overwrite the primary artifact without correcting the architecture/path contract.

### Final ResNet18 trainer

`train_final.py` uses timm ResNet18, 224px input, batch size 16, 15 epochs, learning rate `1e-3`, weighted cross-entropy, AdamW, OneCycleLR, and CUDA mixed precision when available.

Important current behavior:

- Its root is hardcoded to an old `D:` path.
- `TEST_DIR = TRAIN_DIR`, so reported validation accuracy/F1 is measured on training images.
- It writes `resnet18_model.pth` and `model_metadata.json` but does not update `class_mapping.json`.
- OneCycleLR is configured with batch-level step counts but stepped once per epoch.
- Its metadata mentions “Focal/Weighted Loss”, but the actual criterion is weighted cross-entropy.

### Cross-validation and advanced evaluation

| Script | Intended capability | Current caveat |
| --- | --- | --- |
| `train_cv.py` | Stratified K-fold training with configurable timm model; defaults to ResNet50, 5 folds, 15 epochs, batch 32, 224px, LR `1e-3`, patience 4 | Old absolute root; optional dependencies; scheduler stepping needs review |
| `evaluate_advanced.py` | Evaluate timm checkpoint; accuracy, precision/recall/F1, confusion matrix, ROC-related evaluation | Old absolute root; match architecture, label order, checkpoint, and data split |
| `evaluate.py` | Legacy MobileNetV2 evaluation and reports | Missing configuration symbols and architecture mismatch with current primary checkpoint |
| `ml/utils/gradcam_v2.py` | Offline Grad-CAM for a chosen model/checkpoint/image | Old absolute root and `from evaluate_advanced import ...` import-path issue |

The generic CLI entry points include:

```text
train_cv.py:
  --model_name --img_size --batch_size --epochs --folds --lr --patience --single_fold

evaluate_advanced.py:
  --model_name --checkpoint --img_size --batch_size

gradcam_v2.py:
  --model_name --checkpoint --image_path --img_size
```

### Dataset utilities

| Script | Function | Issue to resolve before use |
| --- | --- | --- |
| `dataset_audit.py` | SHA-based duplicate checks, image integrity checks, JSON report | Obsolete absolute dataset path; skips missing directories |
| `clean_dataset.py` | Standardize class names and remove duplicate files | Obsolete path; mutates/deletes dataset files |
| `merge_pool.py` | Merge split contents into pool | Obsolete path; can remove original split directories |
| `split_data.py` | Copy an 85/15 split within each class from pool | Obsolete path; deletes/recreates train/test directories; does not produce validation |
| `prepare_dataset.py` | Build legacy split manifest | Missing config symbols; previous three-class assumptions |
| `inspect_dataset.py` | Inspect classes/splits and write summary | Missing `CLASS_NAMES` / `FOLDER_TO_LABEL` |

Do not run the entire utility collection as an ordered pipeline without first repairing and reviewing it. `split_data.py` recursively deletes the configured training/test destinations before copying. Current duplicate findings describe the present folders; the exact sequence of operations that produced them is not recorded.

### GPU helper

`run_gpu_training.ps1` uninstalls torch/torchvision/torchaudio, installs packages from a CUDA 11.8 wheel index, checks CUDA, and invokes `train_final.py`. It changes the active Python environment. Its “40-Epoch” message does not match `train_final.py`, which sets 15 epochs. The README setup does not require running this helper.

## 19. Saved artifacts and generated files

### Model artifacts currently present

| File under `ml/saved_models/` | Size in bytes | Purpose |
| --- | ---: | --- |
| `resnet18_model.pth` | 44,793,675 | Primary image checkpoint |
| `image_model_best.pth` | 11,786,476 | Alternate MobileNetV2 checkpoint |
| `image_model_mobilenetv2_improved.pth` | 11,786,476 | Improved MobileNetV2 artifact |
| `tabular_model.pkl` | 959 | Clinical classifier |
| `scaler.pkl` | 871 | Clinical feature scaler |
| `class_mapping.json` | 514 | Class names and index mappings |
| `model_metadata.json` | 473 | Recorded image architecture and metrics |
| `tabular_metadata.json` | 519 | Clinical feature schema, model type, demo metrics |

The class map's raw folder keys use older long dataset names and `normal`, while current directories use display names. Ordered class names are what active fusion relies on; raw mappings should be regenerated consistently with future checkpoints.

### Processed data and experiment outputs

- `ml/data/processed/sample_demo_tabular.csv`: synthetic clinical records.
- `ml/data/processed/dataset_manifest.csv`: historical path/class/split manifest.
- `ml/data/processed/class_distribution.txt`: historical four-class split counts.
- `ml/outputs/reports/classification_report.txt`: older validation report and confusion matrix.
- `ml/outputs/reports/classification_report_4class.txt`: baseline historical test report.
- `ml/outputs/reports/improvement_report.txt`: improved MobileNetV2 report.
- `ml/outputs/plots/training_curve.png`: saved training curve.
- `ml/outputs/plots/training_curve_4class.png`: saved four-class training curve.
- `ml/outputs/plots/curve_mobilenetv2_improved.png`: saved improved-model curve.
- `backend/uploads/`: accepted uploaded images; filenames use UUIDs.
- `ml/outputs/heatmaps/`: auxiliary/static heatmap storage; runtime overlay normally returns inline.

`backend/generate_report.py` uses `python-docx` to generate a project report. It is a development/reporting script, not an API endpoint for exporting a patient's prediction. Existing report text and older READMEs should be checked against this source-based inventory before reuse.

## 20. Verification and tests

### Existing scripts

`backend/test_api.py` sends an asynchronous request using httpx. It requires a running backend and opens `test_valid.jpg` relative to its working directory. Run it from `backend/` if using the existing script. Its 10-second timeout can be too short during slow first inference.

`backend/api_test.py` uses `requests`, which is absent from the main requirements and inspected backend environment. It also prints legacy response keys such as `cancer_type`, `class_probabilities`, and `heatmap_url`; those are no longer public API fields.

These scripts mainly print responses rather than asserting correctness. There is no established comprehensive automated suite for model contracts, class mapping, fusion branches, image rejection, or dataset leakage.

### Documentation review checks

- Inspected frontend declarations, source, backend routes/schemas, inference, training, utilities, model metadata, and saved reports.
- Counted the current dataset files directly.
- Compared SHA-256 hashes across train/test/pool without modifying images.
- Inspected package versions using the existing backend environment.
- The in-process TestClient smoke attempt initialized the image model but then stalled and was stopped; it is not counted as a passing HTTP integration check.
- A second direct-function check loaded the primary **ResNet18 on CPU** and returned `{"status":"ok","ml_model_loaded":true,"version":"2.0.0"}` from `health()`. The subsequent clinical prediction did not finish during the review and the process was stopped before image prediction/Grad-CAM checks. Clinical inference, heatmap generation, and end-to-end HTTP behavior are therefore not marked as verified here.
- Checked this README's contents links and balanced code fences; no missing section anchors or unfinished placeholder markers were found.

No retraining or fresh accuracy benchmark was performed for this README. This documentation task does not change application behavior or fix the known implementation issues.

## 21. Known issues and unfinished work

### Data and evaluation

1. **Current test leakage:** all 111 test files also occur in training; 727 unique image contents exist across the three folders.
2. **Training-set evaluation:** `train_final.py` evaluates on its training directory. Its metadata field names can be mistaken for held-out validation.
3. **Missing validation split:** active configuration expects `valid/`, but that directory is absent.
4. **Stale manifests/reports:** historical paths, labels, counts, and scores do not consistently match current artifacts.
5. **Synthetic clinical model:** no evidence of real-patient clinical training or validation; scaler fitting also precedes splitting.
6. **Missing provenance:** dataset origin, permissions, patient grouping, and licensing are not established in current project metadata.

### Model and inference contracts

7. **Training/loading head mismatch:** dynamic ResNet18 training and runtime construct different classifier heads; non-strict loading can conceal missing weights.
8. **Class mapping consistency:** some training paths update weights without updating mappings, and MobileNetV2 may carry a different class order from the shared map.
9. **Architecture reporting:** public `model` always says `ResNet18`, including fallback/clinical-only cases.
10. **Fallback transparency:** health does not report tabular readiness; the image heuristic score does not reach final fusion, and some missing-model paths still return a normal-looking prediction.
11. **Clinical-only subtype ties:** the binary clinical signal is spread equally among subtypes, which can select a subtype by index rather than evidence.
12. **Heatmap robustness:** CUDA device handling and hook compatibility need verification; an explanation can claim a heatmap was generated even when the overlay is null.
13. **Global mutable model/hooks:** concurrent requests share an image model and temporary Grad-CAM hooks without an explicit synchronization mechanism.

### Training/tooling

14. Several legacy scripts import configuration symbols removed from `config.py`.
15. Dataset and advanced ML utilities contain old absolute `D:` paths.
16. Auxiliary packages are missing from main requirements; Python packages are unpinned.
17. Model destinations conflict across trainers; metadata and saved checkpoints lack a consistent run identifier or artifact manifest.
18. OneCycleLR stepping in final/CV training does not match its configured batch schedule.
19. The GPU helper changes installed packages and contains outdated status text.

### Application and operational work

20. Request schemas lack strict numeric bounds/enums, and optional numeric nulls can reach integer conversion code.
21. Image validation is a basic heuristic; no content-type/size policy, chest verification, or DICOM workflow is implemented.
22. Accepted uploads remain on disk without retention management; static heatmap access has no user authorization.
23. No authentication, patient database, consent/retention workflow, persistent analysis history, or audit trail is implemented.
24. No complete production API routing, React hosting, HTTPS configuration, container setup, or CI pipeline is provided.
25. Inference and Grad-CAM run synchronously inside an async route; no queue, capacity limit, latency benchmark, or load validation is provided.

These items explain the difference between “code exists” and “feature is validated and ready for deployment.”

## 22. Suggested implementation order

1. Establish dataset provenance and construct independent patient-aware train/validation/test splits, removing exact and related-image leakage.
2. Standardize checkpoint architecture, classifier head, class order, metadata, filenames, and strict loading checks.
3. Repair configuration imports and hardcoded paths; add the missing training dependencies and a reproducible environment definition.
4. Retrain on training data, select on validation data, and evaluate once on an untouched test set. Save the split manifest and run identity with every checkpoint.
5. Replace synthetic clinical data with an appropriately governed dataset, or explicitly present that path as a demo. Fit preprocessing on training data only.
6. Validate fusion against image-only and clinical-only baselines; handle unavailable models and unsupported subtype inference explicitly.
7. Verify Grad-CAM on supported devices and concurrent requests; report actual model/fallback status in responses.
8. Add meaningful automated contract, fusion, validation, and leakage tests; update the existing HTTP scripts.
9. Complete upload controls, retention, access control, and deployment routing before shared hosting.

## 23. Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `No module named schemas` / `ml_service` | Starting the backend from an incompatible working directory | Use the documented `backend/` directory and `uvicorn main:app` command |
| Frontend cannot reach `/api/predict` | Backend stopped, wrong port, or proxy target mismatch | Check backend health, Vite output, and `API_PROXY_TARGET` |
| CORS error | Direct request from an unlisted frontend origin | Update the allowlist for the actual origin |
| `ml_model_loaded` is false | Missing checkpoint or load/import failure | Read startup logs and confirm compatible weights/packages |
| Loaded flag is true but results look unreliable | Non-strict loading, class-order mismatch, poor training, or domain mismatch | Validate complete parameter loading and label order; use an independent dataset |
| HTTP 400 for clinical data | Malformed JSON or missing required fields | Send every required field; use `{}` for empty symptoms/habits |
| HTTP 400 for an image | Decode failure or RGB mean-difference heuristic rejected it | Use a supported raster scan; inspect the actual error detail |
| Prediction returns without a heatmap | Grad-CAM failure, unavailable image result, or device/hook issue | Inspect logs; verify CPU/CUDA behavior and target layer |
| Training imports `CLASS_NAMES` and fails | Legacy script expects removed config names | Reconcile the script with current dynamic class metadata |
| Dataset utility sees no data | Obsolete absolute path | Fix path configuration before running the utility |
| `train_image.py` cannot find validation data | `valid/` does not exist | Create a properly independent validation partition first |
| Historical `api_test.py` prints `None` values | It reads old public response keys | Use `predicted_subtype`, `probabilities`, `gradcam_image`, and `fusion_explanation` |
| GPU helper fails or removes working torch packages | Environment/wheel compatibility or legacy CUDA assumptions | Inspect it before use; it is optional and mutates the active environment |
| Built frontend receives API 404s | Development proxy is absent from production hosting | Configure a reverse proxy or a deployment-specific API base/routing strategy |

`error_log.txt` contains an older MobileNetV2 head-shape traceback from another project location. It is historical evidence, not proof of the current process state.

## 24. Project ownership, provenance, and license

The older project README describes an academic EDI project. No verified author list, repository remote URL, release history, or standalone license file was found in this checkout. The application package is named `frontend` at version `0.0.0`; that is separate from the backend API's `2.0.0` version.

Add an explicit project license, dataset attribution/terms, model provenance, and maintainer information before distributing the project. Third-party library licenses do not automatically define licensing or redistribution rights for project code, datasets, or saved model weights.

The most direct references for this README are the implementation in `frontend/src/`, `backend/`, `ml/inference/`, `ml/training/`, `ml/utils/config.py`, and the saved metadata/reports. Older documentation is retained for historical context and may disagree with current behavior.
