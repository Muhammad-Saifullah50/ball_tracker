"""
Session configuration models for Cricket Ball Tracker
"""
from dataclasses import dataclass
from typing import Tuple, Optional
from .calibration import PitchConfig, StumpPosition, WideConfig, WallBoundary


@dataclass
class BatsmanDetection:
    """Detected batsman position and handedness."""
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    handedness: str                          # "right" or "left"
    handedness_confidence: float = 1.0       # Auto-detection confidence (0.0 to 1.0)
    is_manual_override: bool = False         # User manually set handedness

    def __post_init__(self):
        if not 0.0 <= self.handedness_confidence <= 1.0:
            raise ValueError("Handedness confidence must be between 0.0 and 1.0")
        if self.handedness not in ["right", "left"]:
            raise ValueError("Handedness must be 'right' or 'left'")


@dataclass
class SessionConfig:
    """All configuration for a session, persisted as JSON."""
    pitch_config: PitchConfig              # Pitch dimensions
    batting_stumps: StumpPosition          # Batting end stump positions
    wide_config: WideConfig                # Wide corridor distances
    wall_boundary: WallBoundary            # Catch zone polygon
    batsman_handedness: str                # "right" or "left"

    # Rules configuration
    stump_width_tolerance: float = 1.0     # Multiplier for LBW stump zone (0.5 to 3.0)
    lbw_strictness: str = "standard"       # "strict", "standard", "lenient"
    edge_sensitivity: float = 0.7          # Threshold for edge detection (0.0 to 1.0)
    confidence_threshold: float = 0.5      # Minimum confidence for OUT (0.0 to 1.0)

    # Camera configuration
    camera_index: int = 0                  # OpenCV camera device index
    resolution: Tuple[int, int] = (640, 480)  # Camera resolution (width, height)

    def __post_init__(self):
        if not 0.5 <= self.stump_width_tolerance <= 3.0:
            raise ValueError("Stump width tolerance must be between 0.5 and 3.0")
        if self.lbw_strictness not in ["strict", "standard", "lenient"]:
            raise ValueError("LBW strictness must be 'strict', 'standard', or 'lenient'")
        if not 0.0 <= self.edge_sensitivity <= 1.0:
            raise ValueError("Edge sensitivity must be between 0.0 and 1.0")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        if self.batsman_handedness not in ["right", "left"]:
            raise ValueError("Batsman handedness must be 'right' or 'left'")
        if self.camera_index < 0:
            raise ValueError("Camera index must be non-negative")
        if self.resolution[0] <= 0 or self.resolution[1] <= 0:
            raise ValueError("Camera resolution must have positive dimensions")