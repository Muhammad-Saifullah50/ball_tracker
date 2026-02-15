"""
Wide Engine for Cricket Ball Tracker
Evaluates if deliveries are wide based on ball position at batting crease
"""
from ..calibration.pitch_calibrator import PitchCalibrator
from ..models.calibration import WideConfig
from ..models.ball_detection import Trajectory
from ..models.decisions import WideDecision


class WideEngine:
    """Evaluates wide deliveries. Auto-triggered after each delivery."""

    def __init__(self, calibrator: PitchCalibrator, wide_config: WideConfig) -> None:
        """
        Initialize the Wide Engine.

        Args:
            calibrator: PitchCalibrator for coordinate mapping
            wide_config: WideConfig with off-side and leg-side distances
        """
        self.calibrator = calibrator
        self.wide_config = wide_config

    def evaluate(self, trajectory: Trajectory) -> WideDecision:
        """
        Evaluate if delivery was a wide.

        Args:
            trajectory: Full delivery trajectory.

        Returns:
            WideDecision with result and ball position at batting crease.
        """
        # Get the ball position at the end of the trajectory (when it reaches the batting crease area)
        if not trajectory.detections:
            # If no detections, return a default "not wide" decision with low confidence
            return WideDecision(
                delivery_id=trajectory.delivery_id,
                ball_position_at_crease_px=(0, 0),
                off_line_distance_px=0.0,
                leg_line_distance_px=0.0,
                result="NOT_WIDE",
                side=None,
                confidence=0.0
            )

        # Get the last detection which represents where the ball ended up
        # This would typically be where the ball was last detected in the trajectory
        # For wide detection, we're interested in where the ball crossed the batting crease
        last_detection = trajectory.detections[-1]
        ball_x, ball_y = last_detection.x, last_detection.y
        ball_position = (int(ball_x), int(ball_y))

        # Get the positions of the wide lines using the calibrator
        try:
            wide_lines = self.calibrator.get_wide_lines(self.wide_config)
            off_line, leg_line = wide_lines

            # For wide detection, we only care about the x-coordinate at the batting crease line
            # Get x-coordinates of the wide lines at the batting crease (y position)
            # In the calibrator's get_wide_lines method, the lines are defined as [[x1, y1], [x2, y2]]
            # For vertical lines, both points have same x-coordinate
            off_line_x = off_line[0][0]  # x-coordinate of off-side wide line
            leg_line_x = leg_line[0][0]   # x-coordinate of leg-side wide line

            # Calculate distances from ball position to each wide line
            off_line_distance = abs(ball_x - off_line_x)
            leg_line_distance = abs(ball_x - leg_line_x)

            # Determine if the delivery is wide
            is_wide = False
            wide_side = None

            # If ball is outside the off-side wide line (to the left for right-handed batsman)
            if ball_x < off_line_x:
                is_wide = True
                wide_side = "off"
            # If ball is outside the leg-side wide line (to the right for right-handed batsman)
            elif ball_x > leg_line_x:
                is_wide = True
                wide_side = "leg"

            # Calculate confidence based on the trajectory characteristics
            # More detections = higher confidence in the trajectory
            confidence = min(1.0, len(trajectory.detections) / 10.0)  # Base confidence on trajectory length
            confidence = max(0.3, confidence)  # Minimum confidence threshold

            if is_wide:
                result = "WIDE"
            else:
                result = "NOT_WIDE"
                wide_side = None

            return WideDecision(
                delivery_id=trajectory.delivery_id,
                ball_position_at_crease_px=ball_position,
                off_line_distance_px=off_line_distance,
                leg_line_distance_px=leg_line_distance,
                result=result,
                side=wide_side,
                confidence=confidence
            )
        except Exception as e:
            # If there's an error calculating wide lines, return a conservative "not wide"
            # decision with low confidence
            return WideDecision(
                delivery_id=trajectory.delivery_id,
                ball_position_at_crease_px=ball_position,
                off_line_distance_px=0.0,
                leg_line_distance_px=0.0,
                result="NOT_WIDE",
                side=None,
                confidence=0.1
            )