"""
Delivery models for Cricket Ball Tracker
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
from .ball_detection import BallDetection, Trajectory


@dataclass
class ImpactEvent:
    """A detected impact during a delivery."""
    impact_type: str           # "bat", "pad", "ground", "stumps", "wall"
    position_px: Tuple[int, int]  # Pixel location of impact
    frame_number: int          # Frame where impact detected
    confidence: float          # Impact detection confidence (0.0 to 1.0)
    velocity_change: float     # Magnitude of velocity change at impact
    is_in_boundary: bool = False  # Impact within wall boundary (if wall)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class Delivery:
    """Complete record of one ball bowled."""
    delivery_id: str                         # Unique identifier
    timestamp_start: float                   # Start time (ball enters frame)
    timestamp_end: float                     # End time (ball at rest or exits frame)
    trajectory: Trajectory                   # Full ball trajectory
    impact_events: List[ImpactEvent]         # All impacts during delivery
    frames: List[np.ndarray] = None          # Raw frames for replay (JPEG compressed)
    wide_decision: Optional[object] = None   # Auto-evaluated wide result
    caught_behind_decision: Optional[object] = None  # Auto-evaluated caught behind
    lbw_decision: Optional[object] = None    # LBW review result (if appealed)

    def __post_init__(self):
        if self.frames is None:
            self.frames = []
        if self.impact_events is None:
            self.impact_events = []

    @property
    def duration(self) -> float:
        """Return the duration of the delivery in seconds."""
        return self.timestamp_end - self.timestamp_start

    @property
    def has_impacts(self) -> bool:
        """Check if the delivery had any impacts."""
        return len(self.impact_events) > 0

    @property
    def impact_positions(self) -> List[Tuple[int, int]]:
        """Return all impact positions."""
        return [impact.position_px for impact in self.impact_events]