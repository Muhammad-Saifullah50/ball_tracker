"""
Caught Behind Decision Engine for Cricket Ball Tracker
Automatically checks for caught-behind wall rule: if ball edges bat and hits wall directly without bouncing, declare OUT.
"""
from typing import Optional, List
from ..models.decisions import CaughtBehindDecision
from ..models.delivery import ImpactEvent
from ..models.ball_detection import Trajectory
from ..calibration.pitch_calibrator import PitchCalibrator
from ..models.session_config import SessionConfig


class CaughtBehindEngine:
    """Caught Behind Decision Engine - checks for caught-behind wall rule."""

    def __init__(self, calibrator: PitchCalibrator, edge_sensitivity: float = 0.7):
        """
        Initialize the Caught Behind Engine.

        Args:
            calibrator: Pitch calibrator for boundary detection
            edge_sensitivity: Sensitivity threshold for edge detection (0.0-1.0)
        """
        self.calibrator = calibrator
        self.edge_sensitivity = edge_sensitivity

    def evaluate(self, trajectory: Trajectory, config: SessionConfig) -> CaughtBehindDecision:
        """
        Evaluate caught behind decision based on trajectory and configuration.

        Args:
            trajectory: Ball trajectory to analyze
            config: Session configuration with wall boundary and rules

        Returns:
            CaughtBehindDecision with result and confidence
        """
        # Check for edge (bat contact)
        has_edge = self._has_edge(trajectory)

        # Check for wall hit
        hits_wall = self._hits_wall(trajectory, config)

        # Check if there's no bounce between edge and wall hit
        no_bounce_between = self._no_bounce_between_edge_and_wall(trajectory)

        # Determine if caught behind should be called
        is_out = has_edge and hits_wall and no_bounce_between

        # Calculate confidence based on the strength of evidence
        confidence = self._calculate_confidence(has_edge, hits_wall, no_bounce_between, trajectory)

        # Determine reasoning
        if is_out:
            reason = "Ball hit bat and hit wall directly without bouncing"
        else:
            reasons = []
            if not has_edge:
                reasons.append("Ball did not hit bat")
            if not hits_wall:
                reasons.append("Ball did not hit wall")
            if not no_bounce_between:
                reasons.append("Ball bounced between bat and wall")

            reason = f"Caught behind not satisfied: {', '.join(reasons)}"

        return CaughtBehindDecision(
            result="OUT" if is_out else "NOT OUT",
            reason=reason,
            confidence=confidence,
            has_edge=has_edge,
            hits_wall=hits_wall,
            no_bounce_between=no_bounce_between
        )

    def _has_edge(self, trajectory: Trajectory) -> bool:
        """
        Check if the ball has hit the bat (edge detection).

        Args:
            trajectory: Ball trajectory to analyze

        Returns:
            True if bat contact detected, False otherwise
        """
        if not trajectory.impact_points:
            return False

        # Check if any impact is a bat hit
        for impact in trajectory.impact_points:
            if impact.impact_type == "bat":
                return True

        # For unknown impacts with high velocity change, consider as potential edge
        for impact in trajectory.impact_points:
            if impact.impact_type == "unknown" and impact.velocity_change > 40.0:  # High velocity change suggests edge
                return True

        return False

    def _hits_wall(self, trajectory: Trajectory, config: SessionConfig) -> bool:
        """
        Check if the ball has hit the wall.

        Args:
            trajectory: Ball trajectory to analyze
            config: Session configuration with wall boundary

        Returns:
            True if wall hit detected, False otherwise
        """
        if not config.wall_boundary or not trajectory.impact_points:
            return False

        # Check if any impact is in the wall boundary
        for impact in trajectory.impact_points:
            if impact.impact_type == "wall":
                return True

        # Check if any detection point is within wall boundary
        for detection in trajectory.detections:
            if self._is_in_wall_boundary(detection, config.wall_boundary):
                return True

        return False

    def _is_in_wall_boundary(self, detection, wall_boundary) -> bool:
        """
        Check if a detection is within the wall boundary using point-in-polygon algorithm.

        Args:
            detection: BallDetection object
            wall_boundary: WallBoundary object containing the polygon

        Returns:
            True if detection is inside the boundary polygon, False otherwise
        """
        if not wall_boundary or len(wall_boundary.polygon_points) < 3:
            return False

        x, y = int(detection.x), int(detection.y)
        polygon = wall_boundary.polygon_points

        # Implement point-in-polygon test using ray casting algorithm
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _no_bounce_between_edge_and_wall(self, trajectory: Trajectory) -> bool:
        """
        Check if there's no bounce between the edge (bat hit) and wall hit.

        Args:
            trajectory: Ball trajectory to analyze

        Returns:
            True if no bounce between edge and wall, False otherwise
        """
        if not trajectory.impact_points or not trajectory.bounce_point:
            return True  # If no bounce point exists, assume no bounce between edge and wall

        # Find the frames for edge and wall hits
        edge_frame = None
        wall_frame = None

        for impact in trajectory.impact_points:
            if impact.impact_type == "bat":
                edge_frame = impact.frame_number
            elif impact.impact_type == "wall":
                wall_frame = impact.frame_number

        if edge_frame is None or wall_frame is None:
            return True  # Can't determine without both edge and wall hits

        # Check if bounce occurred between edge and wall frames
        bounce_frame = trajectory.bounce_point.frame_number if trajectory.bounce_point and trajectory.bounce_point.frame_number else float('inf')

        # Return True if bounce happened outside the edge-wall interval
        if edge_frame <= wall_frame:
            return not (edge_frame < bounce_frame < wall_frame)
        else:
            return not (wall_frame < bounce_frame < edge_frame)

    def _calculate_confidence(self, has_edge: bool, hits_wall: bool, no_bounce_between: bool, trajectory: Trajectory) -> float:
        """
        Calculate confidence in the caught behind decision.

        Args:
            has_edge: Whether bat contact was detected
            hits_wall: Whether wall was hit
            no_bounce_between: Whether there was no bounce between edge and wall
            trajectory: Ball trajectory for additional metrics

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0

        # Base confidence for each condition
        if has_edge:
            confidence += 0.3
        if hits_wall:
            confidence += 0.3
        if no_bounce_between:
            confidence += 0.3

        # Additional confidence based on trajectory metrics
        if trajectory.deviation_px and trajectory.deviation_px < 50:  # Low deviation suggests straight path
            confidence += 0.1

        return min(1.0, confidence)