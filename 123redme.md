# 🫁 Lung Cancer Detection System

An AI-powered lung cancer detection web application that uses deep learning (ResNet18) to analyze medical images (CT scans & X-rays) and clinical data to detect and classify lung cancer subtypes.

---

## 🚀 Features

- 🔬 **AI Image Analysis** — ResNet18 deep learning model trained on 727+ medical images
- 📊 **Clinical Risk Assessment** — Tabular ML model using patient history and symptoms
- 🗺️ **Grad-CAM Heatmaps** — Visual explainability showing which regions influenced the AI decision
- 🏥 **4 Cancer Classes** — Adenocarcinoma, Large Cell Carcinoma, Squamous Cell Carcinoma, No Cancer
- ⚡ **FastAPI Backend** — High-performance REST API
- ⚛️ **React Frontend** — Modern, responsive UI built with Vite

---

## 🗂️ Project Structure

```
lung_cancer_detection/
├── backend/                  # FastAPI backend
│   ├── main.py               # API entry point
│   ├── image_pipeline.py     # Medical image analysis pipeline
│   ├── ml_service.py         # ML orchestration service
│   ├── schemas.py            # Pydantic data models
│   ├── DataSet/              # Training dataset (train/test)
│   │   ├── train/            # 727 training images (4 classes)
│   │   └── test/             # 111 test images
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── components/       # UI components
│   │   └── App.jsx           # Main application
│   └── package.json
└── ml/                       # Machine learning pipeline
    ├── inference/
    │   ├── image_predictor.py    # ResNet18 inference
    │   ├── tabular_predictor.py  # Clinical data inference
    │   └── combined_predictor.py # Fusion of image + tabular
    ├── training/
    │   ├── train_image.py        # ResNet18 training script
    │   └── train_tabular.py      # Tabular model training
    ├── saved_models/
    │   ├── resnet18_model.pth    # Trained ResNet18 (85% accuracy)
    │   ├── tabular_model.pkl     # Trained LogisticRegression
    │   ├── scaler.pkl            # Feature scaler
    │   └── class_mapping.json   # Class index mapping
    └── utils/
        └── config.py             # Central configuration
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd lung_cancer_detection
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

---

## ▶️ Running the Application

### Start Backend (Terminal 1)
```bash
cd backend
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

- **Frontend:** http://localhost:7351
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

---

## 🤖 ML Models

| Model | Architecture | Accuracy | Purpose |
|-------|-------------|----------|---------|
| Image Model | ResNet18 (torchvision) | ~85% val | CT/X-ray classification |
| Tabular Model | LogisticRegression (sklearn) | — | Clinical risk scoring |
| Combined | Weighted fusion (70% image + 30% tabular) | — | Final prediction |

### Cancer Classes
| Class | Description |
|-------|-------------|
| `Adenocarcinoma` | Most common type, found in outer lung tissue |
| `Squamous Cell Carcinoma` | Found in central airways |
| `Large Cell Carcinoma` | Can appear in any part of the lung |
| `No Cancer` | No malignant patterns detected |

---

## 🔁 Retraining Models

If you want to retrain the models on new data:

```bash
# Train image model (ResNet18)
python ml/training/train_image.py

# Train tabular model
python ml/training/train_tabular.py
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Run cancer detection (multipart form) |
| `GET`  | `/api/health` | Health check |
| `GET`  | `/docs` | Swagger API documentation |

### Example Request
```bash
curl -X POST http://127.0.0.1:8000/api/predict \
  -F "data={\"age\":65,\"gender\":\"Male\",\"smoking_history\":\"Current\"}" \
  -F "image=@/path/to/scan.png"
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, CSS |
| Backend | FastAPI, Python 3.10+ |
| Deep Learning | PyTorch, torchvision |
| Classical ML | scikit-learn, joblib |
| Image Processing | Pillow, numpy |
| API Client | httpx, axios |

---

## ⚠️ Disclaimer

> This tool is intended for **research and educational purposes only**. It is **not** a certified medical device and should **not** replace professional medical diagnosis. Always consult a qualified medical professional for clinical decisions.

---

## 📄 License

This project is developed as part of an academic EDI (Entrepreneurship Development & Innovation) project.

---

*Built with ❤️ for early lung cancer detection research.*
