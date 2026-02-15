"""
Delivery segmenter for Cricket Ball Tracker
Auto-detects delivery start/end from ball motion
"""
from typing import Tuple, Optional
from ..models.ball_detection import BallDetection


class DeliverySegmenter:
    """Auto-detects delivery start/end from ball motion."""

    def __init__(self, min_frames: int = 10, idle_frames: int = 15) -> None:
        """
        Initialize the DeliverySegmenter.

        Args:
            min_frames: Minimum frames to consider a valid delivery
            idle_frames: Number of frames with no detection to consider delivery complete
        """
        self.min_frames = min_frames
        self.idle_frames = idle_frames

        # State tracking
        self.current_state = "idle"  # "idle", "tracking", "complete"
        self.consecutive_idle_frames = 0
        self.delivery_start_frame = -1
        self.delivery_end_frame = -1
        self.is_tracking = False

    def update(self, detection: Optional[BallDetection]) -> str:
        """
        Update segmenter with new detection.

        Returns:
            State: "idle", "tracking", "complete"
        """
        if detection is not None:
            # Detection found
            if self.current_state == "idle":
                # Start of delivery
                self.current_state = "tracking"
                self.delivery_start_frame = detection.frame_number
                self.consecutive_idle_frames = 0
                self.is_tracking = True
            elif self.current_state == "tracking":
                # Continue tracking
                self.consecutive_idle_frames = 0
            elif self.current_state == "complete":
                # Delivery completed, wait for next delivery
                self.current_state = "idle"
                self.consecutive_idle_frames = 0
                self.is_tracking = False
        else:
            # No detection
            if self.current_state == "tracking":
                self.consecutive_idle_frames += 1
                # Check if we've exceeded the idle threshold
                if self.consecutive_idle_frames >= self.idle_frames:
                    # Delivery completed
                    self.current_state = "complete"
                    # For now, we'll just set the end frame to current frame + idle frames
                    # In a real implementation, we'd track this more precisely
                    self.is_tracking = False
            elif self.current_state == "idle":
                # Stay in idle state
                pass
            elif self.current_state == "complete":
                # Stay in complete state until next delivery
                pass

        return self.current_state

    def is_delivery_active(self) -> bool:
        """Return True if currently tracking a delivery."""
        return self.is_tracking

    def get_delivery_frames(self) -> Tuple[int, int]:
        """Return (start_frame, end_frame) of current/last delivery."""
        return (self.delivery_start_frame, self.delivery_end_frame)