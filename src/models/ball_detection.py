"""
Ball detection and trajectory models for Cricket Ball Tracker
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np


@dataclass
class BallDetection:
    """Per-frame ball detection from TrackNet."""
    frame_number: int  # Sequential frame index within delivery
    x: float          # Horizontal pixel position
    y: float          # Vertical pixel position
    confidence: float  # TrackNet heatmap peak confidence (0.0 to 1.0)
    timestamp_ms: float  # Frame timestamp in milliseconds
    visibility: str = "visible"  # "visible", "occluded", or "absent"

    def to_tuple(self) -> Tuple[float, float]:
        """Return (x, y) position as tuple."""
        return (self.x, self.y)


@dataclass
class Trajectory:
    """Ordered sequence of BallDetections forming a delivery path."""
    delivery_id: str                    # Unique identifier for the delivery
    detections: List[BallDetection]     # Ordered ball positions
    speed_kmh: Optional[float] = None   # Calculated ball speed
    bounce_point: Optional[BallDetection] = None  # Detection where ball pitches
    impact_points: List['ImpactEvent'] = None     # All detected impacts
    deviation_px: Optional[float] = None          # Max lateral deviation from straight line
    is_complete: bool = False           # Full trajectory captured (no gaps)
    kalman_state: Optional[dict] = None  # Final Kalman filter state vector
    caught_behind_decision: Optional['CaughtBehindDecision'] = None  # Caught behind decision for visualization
    lbw_decision: Optional['LBWDecision'] = None  # LBW decision for visualization
    wide_decision: Optional['WideDecision'] = None  # Wide decision for visualization

    def __post_init__(self):
        if self.impact_points is None:
            self.impact_points = []

    @property
    def start_position(self) -> Optional[Tuple[float, float]]:
        """Return the starting position of the trajectory."""
        if self.detections:
            first_detection = self.detections[0]
            return (first_detection.x, first_detection.y)
        return None

    @property
    def end_position(self) -> Optional[Tuple[float, float]]:
        """Return the ending position of the trajectory."""
        if self.detections:
            last_detection = self.detections[-1]
            return (last_detection.x, last_detection.y)
        return None

    @property
    def length(self) -> int:
        """Return the number of detections in the trajectory."""
        return len(self.detections)