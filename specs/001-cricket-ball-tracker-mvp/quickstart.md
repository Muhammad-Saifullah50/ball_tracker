# Quickstart: Cricket Ball Tracker MVP

**Branch**: `001-cricket-ball-tracker-mvp`

## Prerequisites

- Python 3.11+
- USB webcam or smartphone camera connected to laptop
- Standard laptop/desktop (2020 or newer, no GPU required)

## Setup

```bash
# Clone and checkout feature branch
git clone <repo-url>
cd ball_tracker
git checkout 001-cricket-ball-tracker-mvp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Verify camera is detected
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'No camera'); cap.release()"
```

## Dependencies (requirements.txt)

```
# Core
opencv-python>=4.8.0
numpy>=1.24.0

# ML Models
torch>=2.0.0
ultralytics>=8.0.0    # YOLOv8
onnxruntime>=1.16.0    # CPU-optimized inference

# Tracking
filterpy>=1.4.5

# UI
streamlit>=1.33.0
streamlit-drawable-canvas>=0.9.3

# Testing
pytest>=7.0.0
pytest-cov>=4.0.0

# Code Quality
ruff>=0.1.0
mypy>=1.0.0
```

## Running the Application

```bash
# Start the Streamlit app
streamlit run src/ui/app.py

# The app opens at http://localhost:8501
```

## First-Time Setup Flow

1. **Camera check**: App auto-detects connected camera
2. **Pitch calibration**: Enter pitch length (meters or feet)
3. **Stump detection**: System detects stumps via YOLOv8; adjust if needed
4. **Wide corridor**: Enter off-side and leg-side wide distances
5. **Wall boundary**: Draw the catch zone polygon on the camera frame
6. **Batsman handedness**: Select left or right (or let auto-detection handle it)
7. **Save config**: Configuration persists for next session

## Running Tests

```bash
# Run all tests
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test suites
pytest tests/unit/ -v                    # Unit tests
pytest tests/integration/ -v             # Integration tests
pytest tests/unit/test_decision_engine/  # Decision engine only (100% coverage required)

# Linting
ruff check src/ tests/
mypy src/
```

## Project Structure

```
ball_tracker/
├── src/
│   ├── detection/          # TrackNet ball detection
│   ├── tracking/           # Kalman filter trajectory tracking
│   ├── calibration/        # Pitch setup, stump detection
│   ├── decision_engine/    # LBW, wide, caught behind
│   ├── replay/             # Replay buffer and playback
│   ├── config/             # Configuration loading/saving
│   └── ui/                 # Streamlit pages
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/           # Test data (frames, trajectories)
├── config/                 # Persisted configuration files
├── models/                 # Pre-trained ML model weights
└── specs/                  # Feature specifications
```

## Key Commands

| Action | Command |
|--------|---------|
| Start app | `streamlit run src/ui/app.py` |
| Run tests | `pytest tests/ -v` |
| Lint | `ruff check src/ tests/` |
| Type check | `mypy src/` |
| Coverage report | `pytest --cov=src --cov-report=html` |
