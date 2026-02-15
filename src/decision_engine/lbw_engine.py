"""
LBW Engine for Cricket Ball Tracker
Evaluates LBW appeals based on where ball pitched, hit pad, and projected trajectory
"""
from typing import Tuple
import math
import numpy as np

from ..calibration.pitch_calibrator import PitchCalibrator
from ..models.ball_detection import Trajectory, BallDetection
from ..models.delivery import ImpactEvent
from ..models.decisions import LBWDecision


class InsufficientDataError(Exception):
    """Raised when there's insufficient data to make a reliable LBW decision."""
    pass


class LBWEngine:
    """Evaluates LBW appeals. On-demand only (user triggers)."""

    def __init__(
        self,
        calibrator: PitchCalibrator,
        stump_tolerance: float = 1.0,
        strictness: str = "standard",
    ) -> None:
        """
        Initialize the LBW Engine.

        Args:
            calibrator: PitchCalibrator for coordinate mapping
            stump_tolerance: Multiplier for LBW stump zone (0.5 to 3.0)
            strictness: "strict", "standard", "lenient" - affects decision criteria
        """
        self.calibrator = calibrator
        self.stump_tolerance = stump_tolerance
        self.strictness = strictness

        # Set parameters based on strictness level
        if strictness == "strict":
            self.pitch_threshold = 0.2  # Must pitch very close to stumps
            self.impact_threshold = 0.2  # Must impact very close to stumps
            self.projection_error_threshold = 0.1  # Very strict projection
        elif strictness == "lenient":
            self.pitch_threshold = 0.8  # More lenient with pitching position
            self.impact_threshold = 0.8  # More lenient with impact position
            self.projection_error_threshold = 0.3  # More lenient projection
        else:  # standard
            self.pitch_threshold = 0.5
            self.impact_threshold = 0.5
            self.projection_error_threshold = 0.2

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
        if len(trajectory.detections) < 3:
            raise InsufficientDataError("Trajectory too short for reliable LBW decision")

        # Step 1: Determine where the ball pitched
        pitching_zone, pitch_confidence = self._analyze_pitching_zone(trajectory, handedness)

        # Step 2: Determine where the ball hit the pad
        impact_zone, impact_confidence = self._analyze_impact_zone(pad_impact, handedness)

        # Step 3: Project trajectory from pad impact to stumps
        projected_path, projected_hitting_stumps, projection_confidence = \
            self._project_trajectory_to_stumps(trajectory, pad_impact, handedness)

        # Step 4: Make decision based on all factors
        result, reason, confidence = self._make_lbw_decision(
            pitching_zone, impact_zone, projected_hitting_stumps,
            pitch_confidence, impact_confidence, projection_confidence
        )

        # Determine which stump was hit (if any)
        stump_zone_hit = self._determine_stump_hit(pad_impact.position_px, handedness) if projected_hitting_stumps else None

        # Create and return the decision
        return LBWDecision(
            delivery_id=trajectory.delivery_id,
            pitching_zone=pitching_zone,
            impact_zone=impact_zone,
            projected_hitting_stumps=projected_hitting_stumps,
            projected_path=projected_path,
            stump_zone_hit=stump_zone_hit,
            handedness=handedness,
            result=result,
            reason=reason,
            confidence=confidence
        )

    def _analyze_pitching_zone(self, trajectory: Trajectory, handedness: str) -> Tuple[str, float]:
        """
        Analyze where the ball pitched relative to stumps.
        In a real implementation, this would find the bounce point and analyze it.
        """
        # For MVP, we'll use the first part of the trajectory to estimate pitch location
        if not trajectory.detections:
            return "outside_leg", 0.0

        # Estimate bounce point by looking for change in vertical trajectory
        bounce_point = trajectory.bounce_point
        if bounce_point:
            pos = bounce_point
        else:
            # Use a middle point in the trajectory if bounce point isn't available
            mid_idx = len(trajectory.detections) // 2
            if mid_idx < len(trajectory.detections):
                pos = trajectory.detections[mid_idx]
            else:
                pos = trajectory.detections[0]

        # Determine if the pitch was in line with stumps using the calibrator
        in_stump_zone = self.calibrator.is_in_stump_zone(
            (int(pos.x), int(pos.y)),
            tolerance=self.stump_tolerance
        )

        if in_stump_zone:
            # Check if it's on the off side or leg side relative to batsman
            off_stump_x = self.calibrator.stump_position.off_stump_px[0]
            leg_stump_x = self.calibrator.stump_position.leg_stump_px[0]

            if (handedness == "right" and pos.x < off_stump_x) or \
               (handedness == "left" and pos.x > leg_stump_x):
                # Pitched outside off stump
                return "outside_off", 0.3
            else:
                # Pitched in line
                return "in_line", 0.9
        else:
            # Check if it's outside leg stump
            off_stump_x = self.calibrator.stump_position.off_stump_px[0]
            leg_stump_x = self.calibrator.stump_position.leg_stump_px[0]

            if (handedness == "right" and pos.x > leg_stump_x) or \
               (handedness == "left" and pos.x < off_stump_x):
                return "outside_leg", 0.1  # Very low confidence if outside leg
            else:
                return "outside_off", 0.3

    def _analyze_impact_zone(self, pad_impact: ImpactEvent, handedness: str) -> Tuple[str, float]:
        """
        Analyze where the ball hit the pad relative to stumps.
        """
        pos = pad_impact.position_px

        # Determine if the impact was in line with stumps using the calibrator
        in_stump_zone = self.calibrator.is_in_stump_zone(
            pos,
            tolerance=self.stump_tolerance
        )

        if in_stump_zone:
            # Impact was in line
            return "in_line", min(1.0, pad_impact.confidence)
        else:
            # Check if it's outside off stump
            off_stump_x = self.calibrator.stump_position.off_stump_px[0]
            leg_stump_x = self.calibrator.stump_position.leg_stump_px[0]

            if (handedness == "right" and pos[0] < off_stump_x) or \
               (handedness == "left" and pos[0] > leg_stump_x):
                # Hit outside off stump
                return "outside_off", min(0.3, pad_impact.confidence)
            else:
                # Hit outside leg stump (not out in this case per cricket rules)
                return "outside_off", 0.1  # Low confidence if outside leg

    def _project_trajectory_to_stumps(self, trajectory: Trajectory, pad_impact: ImpactEvent, handedness: str) -> Tuple[list, bool, float]:
        """
        Project the ball's trajectory from pad impact to the stumps.
        """
        # Get the point of impact with the pad
        impact_x, impact_y = pad_impact.position_px

        # Get impact frame number to know what part of trajectory to use for projection
        impact_frame = pad_impact.frame_number

        # Find the detection closest to the impact frame to get the direction
        impact_detection = next((d for d in trajectory.detections if d.frame_number == impact_frame),
                                trajectory.detections[-1] if trajectory.detections else None)

        if not impact_detection:
            # If no matching detection, use the last detection in trajectory
            impact_detection = trajectory.detections[-1]

        # Find another detection before the impact to determine the direction
        prev_detection = None
        for det in reversed(trajectory.detections):
            if det.frame_number < impact_frame:
                prev_detection = det
                break

        if not prev_detection:
            # If no previous detection, use the second to last if available
            if len(trajectory.detections) > 1:
                prev_detection = trajectory.detections[-2]
            else:
                # Fallback: assume direction towards stumps
                prev_detection = impact_detection
                # For this case, we'll just estimate the direction towards stumps
                batting_crease_x = self.calibrator.pitch_config.batting_crease_px[0] if self.calibrator.pitch_config.batting_crease_px != (0, 0) else impact_x - 50

        # Calculate the direction vector from previous detection to impact
        dx = impact_detection.x - prev_detection.x
        dy = impact_detection.y - prev_detection.y

        # For projection, we want to continue the trajectory in the same direction
        # toward the batting crease (where stumps are)
        batting_crease_x = self.calibrator.pitch_config.batting_crease_px[0]
        if batting_crease_x == 0:  # Default value, estimate the crease position
            # Estimate batting crease as near the stumps
            avg_stump_x = (self.calibrator.stump_position.off_stump_px[0] +
                          self.calibrator.stump_position.leg_stump_px[0]) / 2
            batting_crease_x = avg_stump_x

        # Calculate how far to project - from impact to batting crease line
        dist_to_project = batting_crease_x - impact_x

        # Calculate projection factor based on direction
        if dx != 0:
            projection_factor = dist_to_project / dx
        else:
            # If dx is 0, the ball is moving vertically - this shouldn't happen
            # Just project a set distance in y direction
            projection_factor = 1.0
            dy = -10  # Move up (towards stumps)

        # Project the path to the batting crease line
        projected_x = batting_crease_x
        projected_y = impact_y + dy * projection_factor

        # Create projected path as a list of points (we'll just use start and end for MVP)
        projected_path = [(int(impact_x), int(impact_y)), (int(projected_x), int(projected_y))]

        # Check if the projected path hits the stumps
        # Get the horizontal range of stumps
        off_stump_x, off_stump_y = self.calibrator.stump_position.off_stump_px
        leg_stump_x, leg_stump_y = self.calibrator.stump_position.leg_stump_px
        middle_stump_x = self.calibrator.stump_position.middle_stump_px[0]

        # The stumps form a horizontal line at roughly the batting crease y coordinate
        stumps_y = (off_stump_y + leg_stump_y + self.calibrator.stump_position.middle_stump_px[1]) / 3

        # Calculate effective stump width with tolerance
        stump_width = abs(leg_stump_x - off_stump_x)
        effective_width = stump_width * self.stump_tolerance

        # Calculate center of stumps
        stumps_center_x = (off_stump_x + leg_stump_x) / 2

        # Determine if projected point hits stumps
        projected_hits_stumps = False
        confidence = 0.5  # Base confidence

        # Check if projected point is within stump zone width
        if abs(projected_x - stumps_center_x) <= effective_width / 2:
            # Also check if projected Y is at appropriate height for stumps
            # (in a full implementation, we'd check if the ball would pass through the stumps)
            if abs(projected_y - stumps_y) <= self.calibrator.stump_position.stump_height_px / 2:
                projected_hits_stumps = True
                confidence = 0.8  # High confidence if it looks like it hits stumps

        # Adjust confidence based on quality of input data
        if len(trajectory.detections) < 5:
            # Less confidence with shorter trajectory
            confidence *= 0.6

        return projected_path, projected_hits_stumps, confidence

    def _make_lbw_decision(self, pitching_zone: str, impact_zone: str, projected_hitting_stumps: bool,
                          pitch_confidence: float, impact_confidence: float, projection_confidence: float) -> Tuple[str, str, float]:
        """
        Make the final LBW decision based on all analysis.
        """
        # LBW conditions in cricket:
        # 1. Ball must pitch in line with stumps OR outside off stump (not outside leg)
        # 2. Impact must be in line with stumps (not outside off stump)
        # 3. Ball would have hit the stumps
        # 4. Ball does not hit the bat first

        # Check if pitching conditions are met
        if pitching_zone == "outside_leg":
            return "NOT_OUT", "Ball pitched outside leg stump", 0.9

        # Check if impact conditions are met
        if impact_zone == "outside_off":
            return "NOT_OUT", "Ball hit pad outside off stump", 0.8

        # Check if projection suggests ball would hit stumps
        if not projected_hitting_stumps:
            return "NOT_OUT", "Ball would not have hit stumps", 0.7

        # All conditions met for LBW
        return "OUT", "Ball pitched in line, hit pad in line, and would have hit stumps", 0.9

    def _determine_stump_hit(self, impact_position: Tuple[int, int], handedness: str) -> str:
        """
        Determine which stump the projected ball would hit.
        """
        # Get stump positions
        off_stump_x, off_stump_y = self.calibrator.stump_position.off_stump_px
        middle_stump_x, middle_stump_y = self.calibrator.stump_position.middle_stump_px
        leg_stump_x, leg_stump_y = self.calibrator.stump_position.leg_stump_px

        # Calculate distance to each stump
        d_off = math.sqrt((impact_position[0] - off_stump_x) ** 2 + (impact_position[1] - off_stump_y) ** 2)
        d_middle = math.sqrt((impact_position[0] - middle_stump_x) ** 2 + (impact_position[1] - middle_stump_y) ** 2)
        d_leg = math.sqrt((impact_position[0] - leg_stump_x) ** 2 + (impact_position[1] - leg_stump_y) ** 2)

        # Return the closest stump
        min_dist = min(d_off, d_middle, d_leg)
        if min_dist == d_off:
            return "off"
        elif min_dist == d_middle:
            return "middle"
        else:
            return "leg"