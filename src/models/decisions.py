"""
Decision models for Cricket Ball Tracker
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class LBWDecision:
    """Result of an on-demand LBW review."""
    delivery_id: str                    # Reference to delivery
    pitching_zone: str                  # "in_line", "outside_off", "outside_leg"
    impact_zone: str                    # "in_line", "outside_off"
    projected_hitting_stumps: bool      # Would ball have hit stumps?
    projected_path: List[Tuple[int, int]]  # Pixel path from impact to stumps
    stump_zone_hit: Optional[str]       # "off", "middle", "leg" or None
    handedness: str                     # "right" or "left"
    result: str                         # "OUT" or "NOT_OUT"
    reason: str                         # Human-readable explanation
    confidence: float                   # Decision confidence score (0.0 to 1.0)

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.result not in ["OUT", "NOT_OUT"]:
            raise ValueError("LBW result must be 'OUT' or 'NOT_OUT'")


@dataclass
class WideDecision:
    """Auto-evaluated wide result after each delivery."""
    delivery_id: str                    # Reference to delivery
    ball_position_at_crease_px: Tuple[int, int]  # Ball position when crossing batting crease
    off_line_distance_px: float         # Pixel distance from off-side wide line
    leg_line_distance_px: float         # Pixel distance from leg-side wide line
    result: str                         # "WIDE" or "NOT_WIDE"
    side: Optional[str]                 # "off" or "leg" (if wide)
    confidence: float                   # Decision confidence score (0.0 to 1.0)

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.result not in ["WIDE", "NOT_WIDE"]:
            raise ValueError("Wide result must be 'WIDE' or 'NOT_WIDE'")


@dataclass
class CaughtBehindDecision:
    """Auto-evaluated caught-behind (wall rule) result."""
    delivery_id: str                    # Reference to delivery
    edge_detected: bool                 # Was bat contact detected before wall hit?
    edge_point_px: Optional[Tuple[int, int]]  # Where edge occurred
    ground_bounce_before_wall: bool     # Did ball bounce before hitting wall?
    wall_hit_in_boundary: bool          # Did ball hit within drawn boundary?
    result: str                         # "OUT" or "NOT_OUT"
    reason: str                         # Human-readable explanation
    confidence: float                   # Decision confidence score (0.0 to 1.0)

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.result not in ["OUT", "NOT_OUT"]:
            raise ValueError("Caught behind result must be 'OUT' or 'NOT_OUT'")