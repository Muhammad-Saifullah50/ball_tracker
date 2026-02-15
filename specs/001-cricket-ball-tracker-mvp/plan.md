# Implementation Plan: Cricket Ball Tracker MVP

**Branch**: `001-cricket-ball-tracker-mvp` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-cricket-ball-tracker-mvp/spec.md`

## Summary

Build a computer vision application for home cricket that detects and tracks ball trajectories (TrackNet), detects stumps and batsman handedness (YOLOv8), and adjudicates decisions (LBW, wide, caught-behind wall rule) with visual evidence. Streamlit-based UI with pitch calibration, real-time tracking, instant replay, and configurable rules engine. All processing runs locally on consumer hardware with a single straight-on camera behind the bowler.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: OpenCV 4.8+, PyTorch 2.0+, Ultralytics (YOLOv8), ONNX Runtime, filterpy, Streamlit 1.33+, streamlit-drawable-canvas
**Storage**: JSON files for configuration persistence (no database)
**Testing**: pytest with pytest-cov; ruff for linting; mypy for type checking
**Target Platform**: Linux/macOS/Windows desktop with USB webcam
**Project Type**: Single Python project with Streamlit UI
**Performance Goals**: Ball detection <33ms/frame (30fps), replay available <3 seconds, display at 10-15fps
**Constraints**: <2GB memory, CPU-only inference (no GPU required), offline-first, single camera
**Scale/Scope**: Single user, single camera, 1 session at a time, rolling buffer of 2 deliveries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Accuracy-First | PASS | TrackNet chosen for 95%+ accuracy; confidence scores on all decisions; false positive preference over false negative |
| II. Fairness & Transparency | PASS | Every decision includes visual overlay + confidence; manual override on handedness; rules agreed before match |
| III. Real-Time Performance | PASS | TrackNet ONNX ~25ms CPU, Kalman <0.1ms; processing at 30fps, display at 10-15fps; replay <3s |
| IV. Simplicity & Accessibility | PASS | Streamlit UI; single camera; setup <5 minutes; no technical knowledge required |
| V. Modularity | PASS | 7 independent modules (detection, tracking, calibration, decision_engine, replay, config, ui) with clear interface contracts |
| VI. Offline-First | PASS | All processing local; no cloud/network dependencies; JSON file persistence |
| VII. Configurable Rules Engine | PASS | Stump tolerance, LBW strictness, wide distances, edge sensitivity, confidence threshold all configurable |
| VIII. Graceful Degradation | PASS | Camera failure → warning; incomplete trajectory → low confidence; lighting change → degraded not wrong |
| TDD (Non-Negotiable) | PASS | Red-green-refactor for every feature; 80% min coverage, 100% for decision engine; test fixtures version-controlled |
| Coding Standards | PASS | PEP 8 via ruff, type hints, max 30-line functions, max 300-line files, snake_case, docstrings |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-cricket-ball-tracker-mvp/
├── plan.md              # This file
├── research.md          # Phase 0: Technology research
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Developer setup guide
├── contracts/           # Phase 1: Module interface contracts
│   └── module-interfaces.md
└── tasks.md             # Phase 2: Actionable tasks (via /sp.tasks)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── models/                    # Data classes and types
│   ├── __init__.py
│   ├── ball_detection.py      # BallDetection, Trajectory
│   ├── calibration.py         # PitchConfig, StumpPosition, WideConfig, WallBoundary
│   ├── decisions.py           # LBWDecision, WideDecision, CaughtBehindDecision
│   ├── delivery.py            # Delivery, ImpactEvent
│   └── session_config.py      # SessionConfig, BatsmanDetection
├── detection/                 # ML model inference
│   ├── __init__.py
│   ├── ball_detector.py       # TrackNet-based ball detection
│   └── stump_detector.py      # YOLOv8-based stump + batsman detection
├── tracking/                  # Trajectory tracking
│   ├── __init__.py
│   ├── ball_tracker.py        # Kalman filter tracker
│   └── delivery_segmenter.py  # Auto delivery start/end detection
├── calibration/               # Pitch setup and coordinate mapping
│   ├── __init__.py
│   └── pitch_calibrator.py    # Pixel-to-real-world conversion, stump zones
├── decision_engine/           # Cricket rules evaluation
│   ├── __init__.py
│   ├── lbw_engine.py          # LBW evaluation (on-demand)
│   ├── wide_engine.py         # Wide evaluation (auto)
│   └── caught_behind_engine.py # Wall rule evaluation (auto)
├── replay/                    # Replay buffer and rendering
│   ├── __init__.py
│   ├── replay_buffer.py       # Thread-safe rolling buffer
│   └── replay_renderer.py     # Video rendering with overlays
├── config/                    # Configuration management
│   ├── __init__.py
│   └── config_manager.py      # JSON load/save
└── ui/                        # Streamlit application
    ├── app.py                 # Main entry point
    ├── pages/
    │   ├── 1_Setup.py         # Pitch calibration, stump detection, boundary drawing
    │   ├── 2_Live_Tracking.py # Real-time tracking with overlays
    │   ├── 3_Replay.py        # Replay playback and analysis
    │   └── 4_Rules.py         # Rules engine configuration
    └── components/
        ├── __init__.py
        ├── video_display.py   # Frame display with overlays
        └── overlay_renderer.py # OpenCV overlay drawing utilities

tests/
├── unit/
│   ├── test_models/
│   ├── test_detection/
│   ├── test_tracking/
│   ├── test_calibration/
│   ├── test_decision_engine/  # 100% coverage required
│   ├── test_replay/
│   └── test_config/
├── integration/
│   ├── test_detection_tracking.py  # Detection-to-tracking handoff
│   ├── test_decision_pipeline.py   # Full delivery → decision flow
│   └── test_config_persistence.py  # Save/load config round-trip
└── fixtures/
    ├── frames/                # Sample video frames
    ├── trajectories/          # Known ball trajectory data
    └── configs/               # Test configuration files

config/                        # Persisted user configuration (gitignored)
├── pitch_config.json
├── rules_config.json
├── wall_boundary.json
└── camera_config.json

models/                        # Pre-trained ML model weights (gitignored)
├── tracknet_cricket.onnx      # TrackNet model (ONNX format)
└── yolov8n_stumps.pt          # Fine-tuned YOLOv8 nano
```

**Structure Decision**: Single project layout. All source in `src/` with modular packages matching the 7 independent modules from the constitution. Tests mirror source structure. Config and model weights are gitignored runtime artifacts.

## Architecture Decisions

### 1. Processing Pipeline Architecture

**Decision**: Background thread for CV processing, Streamlit main thread for display.

```
Camera (30fps) → Background Thread → Frame Buffer → Streamlit Display (10-15fps)
                      │
                      ├── TrackNet (ball detection)
                      ├── Kalman Filter (tracking)
                      ├── Delivery Segmenter (start/end)
                      ├── Impact Detector
                      └── Auto-decisions (wide, caught behind)
```

**Rationale**: Streamlit's re-run execution model cannot sustain 30fps display. Decoupling processing from display ensures full detection accuracy while accepting lower display refresh rate.

### 2. Model Inference Strategy

**Decision**: ONNX Runtime for TrackNet (CPU-optimized), Ultralytics for YOLOv8.

- TrackNet: Convert PyTorch model to ONNX; use ONNX Runtime for ~25ms CPU inference
- YOLOv8: Use Ultralytics' built-in inference (includes ONNX export option)
- YOLOv8 runs only during calibration (not per-frame during play)
- Combined per-frame cost during play: ~25ms (TrackNet only) + <0.1ms (Kalman) = well under 33ms budget

### 3. Calibration Approach

**Decision**: Two-phase calibration UX.

1. **Static phase**: Capture a frame, use streamlit-drawable-canvas for wall boundary polygon drawing, manually confirm stump positions detected by YOLOv8
2. **Live phase**: Switch to live video with calibration overlays (stump boxes, wide lines, wall boundary) for verification

### 4. Replay Architecture

**Decision**: Hybrid replay — pre-rendered video for smooth playback, frame-by-frame via slider for analysis.

- Store last 2 deliveries as JPEG-compressed frames (~5-10MB per delivery)
- `st.video()` for smooth slow-motion playback
- Slider + `st.image()` for frame-stepping with overlays
- Memory budget: ~20MB for replay buffer (well within 2GB limit)

### 5. Decision Trigger Model

**Decision**: Wide and caught-behind auto-evaluated; LBW on-demand.

- After each delivery completes (segmenter detects end):
  - WideEngine.evaluate() runs automatically
  - CaughtBehindEngine.evaluate() runs automatically
  - Results displayed immediately on UI
- LBW: User presses "Appeal" button → LBWEngine.evaluate() runs → result displayed
- All decisions include confidence score and visual overlay

## Complexity Tracking

> No constitution violations detected. No complexity justifications needed.

## Post-Design Constitution Re-Check

| Principle | Post-Design Status | Notes |
|-----------|-------------------|-------|
| I. Accuracy-First | PASS | TrackNet ONNX, Kalman filter, confidence on all outputs |
| II. Fairness & Transparency | PASS | Visual overlays on every decision, manual handedness override |
| III. Real-Time Performance | PASS | 25ms detection + <0.1ms tracking = ~25ms/frame; replay buffer in-memory |
| IV. Simplicity & Accessibility | PASS | Multi-page Streamlit, guided setup flow, sensible defaults |
| V. Modularity | PASS | 7 modules with typed interfaces; dependency flow: UI → Services → Core → Models |
| VI. Offline-First | PASS | JSON files, local models, no network calls |
| VII. Configurable Rules Engine | PASS | All parameters in SessionConfig, saved to JSON |
| VIII. Graceful Degradation | PASS | DetectionError handling, incomplete trajectory warnings |

**Gate result**: PASS — design complies with all constitution principles.
