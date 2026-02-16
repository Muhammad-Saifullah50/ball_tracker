"""
Calibration models for Cricket Ball Tracker
"""
from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class PitchConfig:
    """Represents the physical pitch dimensions entered during calibration."""
    pitch_length: float  # Distance between bowling and batting crease in meters
    unit: str = "meters"  # "meters" or "feet"
    bowling_crease_px: Tuple[int, int] = (0, 0)  # Pixel coordinates of bowling crease center
    batting_crease_px: Tuple[int, int] = (0, 0)  # Pixel coordinates of batting crease center
    pixels_per_meter: float = 0.0  # Calculated: pixel distance / real distance

    def __post_init__(self):
        if self.unit == "feet":
            # Convert feet to meters for internal calculations
            self.pitch_length = self.pitch_length * 0.3048
            self.unit = "meters"


@dataclass
class StumpPosition:
    """Detected or manually marked stump coordinates."""
    off_stump_px: Tuple[int, int]      # Pixel position of off-stump (top)
    middle_stump_px: Tuple[int, int]   # Pixel position of middle-stump (top)
    leg_stump_px: Tuple[int, int]      # Pixel position of leg-stump (top)
    stump_width_px: int                # Pixel distance off-stump to leg-stump
    stump_height_px: int               # Pixel height of stumps
    confidence: float = 1.0            # Detection confidence (1.0 if manually set)
    end: str = "batting"               # "batting" or "bowling"


@dataclass
class WideConfig:
    """Configurable wide corridor distances."""
    off_side_distance_m: float         # Wide distance from off-stump (meters)
    leg_side_distance_m: float         # Wide distance from leg-stump (meters)
    off_line_px: Tuple[Tuple[int, int], Tuple[int, int]] = None  # Calculated pixel line for off-side wide
    leg_line_px: Tuple[Tuple[int, int], Tuple[int, int]] = None  # Calculated pixel line for leg-side wide

    def __post_init__(self):
        if self.off_line_px is None:
            self.off_line_px = ((0, 0), (0, 0))
        if self.leg_line_px is None:
            self.leg_line_px = ((0, 0), (0, 0))


@dataclass
class WallBoundary:
    """User-drawn polygon defining the catch zone behind the wicket."""
    polygon_points: List[Tuple[int, int]]  # Ordered vertices of the boundary polygon
    is_valid: bool = True                  # All points within camera frame

    def __post_init__(self):
        if len(self.polygon_points) < 3:
            raise ValueError("Wall boundary polygon must have at least 3 points")