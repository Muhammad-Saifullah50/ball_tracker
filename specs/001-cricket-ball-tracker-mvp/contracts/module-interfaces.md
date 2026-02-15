# Module Interface Contracts: Cricket Ball Tracker MVP

**Date**: 2026-02-15
**Branch**: `001-cricket-ball-tracker-mvp`

These contracts define the interfaces between modules. Dependencies flow inward:
`UI → Services → Core → Models`

---

## 1. Detection Module (`src/detection/`)

### BallDetector

```python
class BallDetector:
    """Detects ball position using TrackNet model."""

    def __init__(self, model_path: str, device: str = "cpu") -> None: ...

    def detect(self, frame_triplet: tuple[ndarray, ndarray, ndarray]) -> BallDetection | None:
        """
        Detect ball in a set of 3 consecutive frames.

        Args:
            frame_triplet: Three consecutive BGR frames (oldest, middle, newest)

        Returns:
            BallDetection with position and confidence, or None if not detected.

        Raises:
            DetectionError: If model inference fails.
        """

    def warmup(self) -> None:
        """Run a dummy inference to initialize the model."""
```

### StumpDetector

```python
class StumpDetector:
    """Detects stump positions using YOLOv8."""

    def __init__(self, model_path: str, device: str = "cpu") -> None: ...

    def detect_stumps(self, frame: ndarray) -> StumpPosition | None:
        """
        Detect stumps in a single frame.

        Args:
            frame: BGR frame from camera.

        Returns:
            StumpPosition with off/middle/leg stump coordinates, or None.
        """

    def detect_batsman(self, frame: ndarray) -> BatsmanDetection | None:
        """
        Detect batsman and classify handedness.

        Args:
            frame: BGR frame from camera.

        Returns:
            BatsmanDetection with bounding box and handedness, or None.
        """
```

---

## 2. Tracking Module (`src/tracking/`)

### BallTracker

```python
class BallTracker:
    """Tracks ball trajectory using Kalman filter."""

    def __init__(self, fps: float = 30.0) -> None: ...

    def update(self, detection: BallDetection | None) -> None:
        """
        Update tracker with new detection (or None for predict-only).

        Args:
            detection: Ball detection from current frame, or None if not detected.
        """

    def get_trajectory(self) -> Trajectory:
        """Return the current trajectory with all detections and computed metrics."""

    def detect_bounce(self) -> BallDetection | None:
        """Return bounce point if detected in current trajectory."""

    def detect_impact(self, threshold: float = 50.0) -> ImpactEvent | None:
        """
        Check if an impact event occurred in the latest update.

        Args:
            threshold: Minimum velocity change magnitude for impact detection.

        Returns:
            ImpactEvent if impact detected, None otherwise.
        """

    def get_predicted_position(self) -> tuple[float, float]:
        """Return Kalman-predicted position for next frame."""

    def reset(self) -> None:
        """Reset tracker for a new delivery."""
```

### DeliverySegmenter

```python
class DeliverySegmenter:
    """Auto-detects delivery start/end from ball motion."""

    def __init__(self, min_frames: int = 10, idle_frames: int = 15) -> None: ...

    def update(self, detection: BallDetection | None) -> str:
        """
        Update segmenter with new detection.

        Returns:
            State: "idle", "tracking", "complete"
        """

    def is_delivery_active(self) -> bool:
        """Return True if currently tracking a delivery."""

    def get_delivery_frames(self) -> tuple[int, int]:
        """Return (start_frame, end_frame) of current/last delivery."""
```

---

## 3. Calibration Module (`src/calibration/`)

### PitchCalibrator

```python
class PitchCalibrator:
    """Manages pitch calibration and coordinate mapping."""

    def __init__(self, pitch_config: PitchConfig, stump_position: StumpPosition) -> None: ...

    def pixels_to_meters(self, pixel_distance: float) -> float:
        """Convert pixel distance to real-world meters."""

    def meters_to_pixels(self, meter_distance: float) -> float:
        """Convert real-world meters to pixel distance."""

    def speed_kmh(self, pixel_velocity: float, fps: float) -> float:
        """Convert pixel velocity (px/frame) to km/h."""

    def get_wide_lines(self, wide_config: WideConfig) -> tuple[Line, Line]:
        """Calculate pixel coordinates for wide corridor lines."""

    def is_in_stump_zone(
        self, position_px: tuple[int, int], tolerance: float = 1.0
    ) -> bool:
        """Check if a position falls within the stump zone (with tolerance)."""

    def get_stump_zone_polygon(self, tolerance: float = 1.0) -> list[tuple[int, int]]:
        """Return polygon vertices for the stump zone (for overlay drawing)."""
```

---

## 4. Decision Engine Module (`src/decision_engine/`)

### LBWEngine

```python
class LBWEngine:
    """Evaluates LBW appeals. On-demand only (user triggers)."""

    def __init__(
        self,
        calibrator: PitchCalibrator,
        stump_tolerance: float = 1.0,
        strictness: str = "standard",
    ) -> None: ...

    def evaluate(
        self,
        trajectory: Trajectory,
        pad_impact: ImpactEvent,
        handedness: str,
    ) -> LBWDecision:
        """
        Evaluate an LBW appeal.

        Args:
            trajectory: Full delivery trajectory.
            pad_impact: The pad contact impact event.
            handedness: "right" or "left".

        Returns:
            LBWDecision with result, reason, confidence, and projected path.

        Raises:
            InsufficientDataError: If trajectory is too short for reliable projection.
        """
```

### WideEngine

```python
class WideEngine:
    """Evaluates wide deliveries. Auto-triggered after each delivery."""

    def __init__(self, calibrator: PitchCalibrator, wide_config: WideConfig) -> None: ...

    def evaluate(self, trajectory: Trajectory) -> WideDecision:
        """
        Evaluate if delivery was a wide.

        Args:
            trajectory: Full delivery trajectory.

        Returns:
            WideDecision with result and ball position at batting crease.
        """
```

### CaughtBehindEngine

```python
class CaughtBehindEngine:
    """Evaluates caught-behind wall rule. Auto-triggered after each delivery."""

    def __init__(self, wall_boundary: WallBoundary, edge_sensitivity: float = 0.7) -> None: ...

    def evaluate(self, trajectory: Trajectory) -> CaughtBehindDecision:
        """
        Evaluate caught-behind wall rule.

        Args:
            trajectory: Full delivery trajectory including post-edge path.

        Returns:
            CaughtBehindDecision with edge detection, bounce analysis, and result.
        """
```

---

## 5. Replay Module (`src/replay/`)

### ReplayBuffer

```python
class ReplayBuffer:
    """Thread-safe rolling buffer for recent deliveries."""

    def __init__(self, max_deliveries: int = 2) -> None: ...

    def add_frame(self, frame: ndarray, detection: BallDetection | None) -> None:
        """Add a frame to the current delivery buffer."""

    def end_delivery(self, delivery: Delivery) -> None:
        """Finalize current delivery and add to rolling buffer."""

    def get_delivery(self, index: int = -1) -> Delivery | None:
        """Get a delivery from the buffer (-1 = most recent)."""

    def get_replay_frames(
        self, delivery_index: int = -1, speed: float = 1.0
    ) -> list[ndarray]:
        """Get frames with overlays for replay at given speed."""
```

### ReplayRenderer

```python
class ReplayRenderer:
    """Renders replay video with overlays and decision graphics."""

    def render_to_video(
        self,
        delivery: Delivery,
        speed: float = 0.5,
        output_path: str = "replay.mp4",
    ) -> str:
        """
        Render a delivery to a video file with overlays.

        Returns:
            Path to the rendered video file.
        """

    def render_frame(
        self, frame: ndarray, trajectory: Trajectory, decisions: dict
    ) -> ndarray:
        """Render overlays on a single frame for display."""
```

---

## 6. Config Module (`src/config/`)

### ConfigManager

```python
class ConfigManager:
    """Loads and saves configuration from/to JSON files."""

    def __init__(self, config_dir: str = "config") -> None: ...

    def load_session_config(self) -> SessionConfig:
        """Load all config files into a SessionConfig."""

    def save_session_config(self, config: SessionConfig) -> None:
        """Save SessionConfig to individual JSON files."""

    def load_defaults(self) -> SessionConfig:
        """Return default configuration."""

    def config_exists(self) -> bool:
        """Check if a saved configuration exists."""
```

---

## 7. UI Module (`src/ui/`)

No formal API contracts — Streamlit pages call into services directly. Key patterns:

- `@st.cache_resource` for model and camera initialization
- `st.session_state` for runtime state
- `ConfigManager` for persistence
- Background thread for CV pipeline; `@st.fragment` for display updates
