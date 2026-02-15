# Research: Cricket Ball Tracker MVP

**Date**: 2026-02-15
**Branch**: `001-cricket-ball-tracker-mvp`

## 1. TrackNet — Ball Detection Model

### Decision: Use TrackNet v2 architecture with custom training for cricket balls

**Rationale**: TrackNet is purpose-built for tracking small, fast-moving balls in sports video. It uses 3 consecutive frames as input, producing a heatmap of likely ball position. This temporal context handles motion blur far better than single-frame detectors like YOLO.

**Architecture**:
- Input: 3 consecutive RGB frames (640x360 recommended resolution)
- Output: Gaussian heatmap centered on ball position
- Backbone: VGG16-based encoder-decoder (U-Net style)
- TrackNet v2 adds a second output head for visibility classification (visible/occluded/absent)

**Performance**:
- GPU inference: ~5-10ms per 3-frame set
- CPU inference: ~30-80ms per 3-frame set (PyTorch, depends on CPU generation)
- **CPU-only concern**: May exceed 33ms budget on older CPUs. Mitigation: use ONNX Runtime for optimized CPU inference (~20-40ms), or accept processing every 2nd frame set.

**Dependencies**: PyTorch, OpenCV, NumPy, ONNX Runtime (for CPU optimization)

**Training**: Requires annotated cricket ball frames (ball position labeled per frame). Minimum ~5,000 annotated frames for fine-tuning. Can start from badminton/tennis pre-trained weights and fine-tune.

**Alternatives considered**:
- YOLOv8 for ball detection: Faster but single-frame, struggles with motion blur (80-90% accuracy vs 95%+ for TrackNet)
- Color-based HSV detection: Simplest but unreliable with varying backgrounds and ball colors

**Limitations**:
- Requires training data — no off-the-shelf cricket ball model exists
- CPU inference is borderline for 30fps; ONNX optimization critical
- Input resolution must match training resolution

---

## 2. YOLOv8 — Stump & Player Detection

### Decision: Use YOLOv8 Nano for stump detection and batsman position

**Rationale**: YOLOv8n is the smallest model, optimized for speed on CPU. Pre-trained on COCO (includes "person" class). Needs fine-tuning for stumps (not in COCO).

**Model sizes (CPU inference, 640x480)**:
| Model | Params | CPU Inference | Accuracy |
|-------|--------|---------------|----------|
| YOLOv8n | 3.2M | ~40-80ms | Good |
| YOLOv8s | 11.2M | ~80-150ms | Better |
| YOLOv8m | 25.9M | ~150-300ms | Best |

**Decision**: YOLOv8n — best speed/accuracy tradeoff for CPU. ONNX export further reduces to ~25-50ms.

**Stump detection strategy**:
- Fine-tune YOLOv8n on cricket stump images (stumps are visually distinctive — 3 vertical poles with bails)
- Minimum ~500 annotated stump images for fine-tuning
- During setup/calibration only (not per-frame during play) — can afford slower inference

**Batsman handedness strategy**:
- Detect "person" bounding box (pre-trained COCO class)
- Determine handedness from bat position relative to body center in the bounding box
- Heuristic: if bat is on left side of body center → right-handed; if on right → left-handed
- Manual override always available as fallback

**Combined inference budget (TrackNet + YOLO per frame)**:
- TrackNet: ~25ms (ONNX, CPU)
- YOLO: Not needed per-frame during play — only during calibration
- During play: only TrackNet runs per-frame; YOLO runs periodically or on-demand
- **Budget met**: <33ms for per-frame ball detection

**Dependencies**: ultralytics, PyTorch, ONNX Runtime

**Alternatives considered**:
- Detectron2: More accurate but significantly slower on CPU
- MediaPipe Pose: Good for body pose but overkill for just bat position detection

---

## 3. Kalman Filter — Trajectory Tracking

### Decision: Use filterpy KalmanFilter with constant-acceleration model

**Rationale**: filterpy is a pure-Python Kalman filter library that is lightweight, well-documented, and has no heavy dependencies. OpenCV's KalmanFilter is also viable but filterpy has a better API for custom state vectors.

**State vector design for cricket ball**:
```
State: [x, y, vx, vy, ax, ay]  (6D)
- x, y: ball position in pixels
- vx, vy: velocity in pixels/frame
- ax, ay: acceleration in pixels/frame^2 (captures gravity + spin effects)
```

**Measurement vector**: [x, y] from TrackNet detection

**Key operations**:
- **Predict**: Extrapolate position when ball is occluded (behind batsman). Run predict-only without update.
- **Update**: Correct state when TrackNet provides a detection.
- **Bounce detection**: Monitor vertical velocity sign change — when vy flips from positive to negative (ball moving down then up), a bounce occurred. The frame where sign changes is the bounce point.
- **Impact detection**: Monitor acceleration magnitude. A sudden spike in acceleration (|delta_v| > threshold) indicates an impact event. The ball position at that frame is the impact point.
- **Speed calculation**: Convert pixel velocity to real-world speed using calibrated pitch length. `speed_kmh = pixel_velocity * (pitch_length_m / pitch_length_px) * fps * 3.6`

**Swing/deviation detection**: Compare actual trajectory against straight-line fit from release to bounce. Lateral deviation indicates swing.

**Computational cost**: Negligible — filterpy Kalman filter predict+update is <0.1ms per frame. Not a performance concern.

**Dependencies**: filterpy, numpy

**Alternatives considered**:
- OpenCV KalmanFilter: Works but C++ API wrapped in Python is less ergonomic
- scipy optimization: Too heavy for real-time tracking
- Custom implementation: Unnecessary when filterpy exists

---

## 4. Streamlit — UI Architecture

### Decision: Multi-page Streamlit app with background CV thread

**Rationale**: Streamlit is chosen for rapid MVP development and non-technical user accessibility. Key architectural decisions to work within Streamlit's constraints:

**Camera capture**: Use `cv2.VideoCapture` directly (local camera). Avoids browser round-trip overhead of streamlit-webrtc. Camera is physically connected to the machine running the app.

**Processing architecture**:
- Background thread: Runs CV pipeline (TrackNet + Kalman filter) at camera's native framerate (~30fps)
- Streamlit main thread: Polls for display frames at 10-15fps via `@st.fragment(run_every=0.066)`
- This decouples processing speed from display speed

**Display limitation**: `st.image()` achieves ~10-15fps display (due to base64 encoding + WebSocket transfer). This is acceptable for monitoring — processing still runs at full speed internally.

**Calibration UX (two-phase approach)**:
1. Capture a static frame from camera
2. Use `streamlit-drawable-canvas` with `drawing_mode="polygon"` for wall boundary drawing
3. Canvas outputs Fabric.js JSON with polygon coordinates
4. Save coordinates to JSON config file
5. Switch to live mode with overlays

**App structure**: Multi-page Streamlit app:
- `pages/1_Setup.py` — Pitch calibration, stump detection, wall boundary drawing, rules config
- `pages/2_Live_Tracking.py` — Live video feed with overlays, auto-decisions (wide, caught behind)
- `pages/3_Replay.py` — Replay playback with slow-mo, frame-stepping, decision graphics
- `pages/4_Rules.py` — Rules engine configuration

**State management**:
- `st.session_state` for runtime state (current frame, tracking data)
- JSON files for persistent config (pitch, rules, wall boundary)
- `@st.cache_resource` for ML models and camera object (survives re-runs)

**Replay approach**: Hybrid — `st.video()` for smooth pre-rendered replay, slider + `st.image()` for frame-by-frame analysis mode

**Dependencies**: streamlit, streamlit-drawable-canvas

**Limitations acknowledged**:
- No true 30fps display via Streamlit (10-15fps display, 30fps processing)
- Canvas cannot overlay on live video (calibration is on frozen frame)
- Page refresh loses session state (mitigated by file persistence)

**Alternatives considered**:
- PyQt: Better performance but harder to use for non-technical users
- Gradio: Similar limitations to Streamlit
- FastAPI + custom JS: Full control but much higher development effort

---

## 5. Configuration Persistence

### Decision: JSON files for config, separate files per concern

**Rationale**: JSON round-trips perfectly with Python dicts, is human-readable, and requires no extra dependencies.

**File structure**:
```
config/
├── pitch_config.json    # Pitch length, stump positions, crease positions
├── rules_config.json    # LBW strictness, wide distances, confidence thresholds
├── wall_boundary.json   # Wall boundary polygon coordinates
└── camera_config.json   # Camera index, resolution
```

**Alternatives considered**:
- YAML: Better for hand-editing but adds pyyaml dependency
- SQLite: Overkill for simple key-value config
- Pickle: Not human-readable, security concerns

---

## 6. LBW Trajectory Prediction

### Decision: Physics-based extrapolation using Kalman filter state

**Rationale**: After pad impact, extrapolate the ball's trajectory using the pre-impact velocity and acceleration from the Kalman filter. Apply gravity correction for the vertical component.

**Method**:
1. At impact point, capture Kalman state: position (x, y), velocity (vx, vy), acceleration (ax, ay)
2. Project forward frame-by-frame: `x_next = x + vx + 0.5*ax`, `y_next = y + vy + 0.5*ay + 0.5*g`
3. Continue until the projected y-position reaches the stump line (batting crease x-coordinate)
4. Check if the projected ball position at stump line falls within the stump zone (off-stump to leg-stump width, with configurable tolerance)
5. Confidence score based on: trajectory length before impact, number of detections, consistency of acceleration model

**Stump zone geometry**:
- Standard stumps: 22.86cm width (off to leg), 71.1cm height
- Configurable tolerance multiplier (e.g., 1.0x = strict, 1.5x = lenient for beginners)
- Stump position from YOLOv8 detection during calibration

**Alternatives considered**:
- ML-based trajectory prediction: More accurate but requires training data of ball trajectories with ground truth outcomes
- Simple linear projection: Too inaccurate — ignores gravity, swing, and bounce behavior
