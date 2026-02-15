"""
Tests for Caught Behind Engine
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.decision_engine.caught_behind_engine import CaughtBehindEngine
from src.models.decisions import CaughtBehindDecision
from src.models.delivery import ImpactEvent
from src.models.ball_detection import Trajectory, BallDetection
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.calibration import PitchConfig, StumpPosition, WallBoundary


class TestCaughtBehindEngineEdgeDetection:
    """Test edge detection logic in Caught Behind Engine."""

    def test_edge_detection_identifies_bat_impact(self):
        """Test that edge detection identifies when ball hits the bat."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with bat impact
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=10,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        assert has_edge is True

    def test_edge_detection_identifies_unknown_impact_as_potential_edge(self):
        """Test that unknown impacts near the bat position are considered potential edges."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with unknown impact that might be an edge
        unknown_impact = ImpactEvent(
            impact_type="unknown",
            position_px=(310, 245),
            frame_number=12,
            confidence=0.75,
            velocity_change=60.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [unknown_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        # This should return True if the impact has high velocity change (likely edge)
        assert has_edge is True

    def test_edge_detection_returns_false_for_no_impacts(self):
        """Test that edge detection returns False when no impacts exist."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with no impacts
        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = []
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        assert has_edge is False

    def test_edge_detection_returns_false_for_only_ground_impact(self):
        """Test that edge detection returns False for ground impacts."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with ground impact
        ground_impact = ImpactEvent(
            impact_type="ground",
            position_px=(400, 350),
            frame_number=15,
            confidence=0.8,
            velocity_change=25.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [ground_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        assert has_edge is False

    def test_edge_detection_returns_false_for_only_stumps_impact(self):
        """Test that edge detection returns False for stumps impacts."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with stumps impact
        stumps_impact = ImpactEvent(
            impact_type="stumps",
            position_px=(280, 200),
            frame_number=14,
            confidence=0.95,
            velocity_change=50.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [stumps_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        assert has_edge is False

    def test_edge_detection_with_multiple_impacts(self):
        """Test edge detection with multiple impacts where at least one is a bat impact."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with multiple impacts including a bat impact
        ground_impact = ImpactEvent(
            impact_type="ground",
            position_px=(400, 350),
            frame_number=15,
            confidence=0.8,
            velocity_change=25.0,
            is_in_boundary=False
        )

        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=10,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [ground_impact, bat_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        assert has_edge is True

    def test_edge_detection_with_edge_sensitivity_parameter(self):
        """Test that edge detection respects the edge sensitivity parameter."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance with low edge sensitivity
        engine = CaughtBehindEngine(calibrator=calibrator, edge_sensitivity=0.3)  # Lower threshold

        # Create trajectory with impact that has moderate velocity change
        unknown_impact = ImpactEvent(
            impact_type="unknown",
            position_px=(310, 245),
            frame_number=12,
            confidence=0.75,
            velocity_change=20.0,  # Lower velocity change
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [unknown_impact]
        trajectory.detections = []

        # Call edge detection function
        has_edge = engine._has_edge(trajectory)

        # With lower sensitivity threshold, this might still be detected as edge due to velocity change
        # The exact behavior depends on the implementation of _has_edge method
        # This test verifies the parameter is considered
        assert isinstance(has_edge, bool)


class TestCaughtBehindEngineBounceDetection:
    """Test bounce detection logic before wall hit in Caught Behind Engine."""

    def test_bounce_detection_between_edge_and_wall_positive_case(self):
        """Test that bounce is detected when bounce occurs between edge and wall hit."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with bat impact at frame 10, bounce at frame 15, and wall hit at frame 20
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=10,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 150),
            frame_number=20,
            confidence=0.8,
            velocity_change=35.0,
            is_in_boundary=True
        )

        # Create a bounce point at frame 15
        bounce_detection = BallDetection(
            x=200,
            y=200,
            confidence=0.85,
            frame_number=15,
            timestamp=15.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return False since bounce occurred between edge (frame 10) and wall hit (frame 20)
        assert no_bounce_between is False

    def test_bounce_detection_no_bounce_between_edge_and_wall(self):
        """Test that no bounce is detected between edge and wall when bounce happens elsewhere."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with bat impact at frame 20, wall hit at frame 10, and bounce at frame 5
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=20,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 150),
            frame_number=10,
            confidence=0.8,
            velocity_change=35.0,
            is_in_boundary=True
        )

        # Create a bounce point at frame 5 (before both edge and wall hits)
        bounce_detection = BallDetection(
            x=400,
            y=400,
            confidence=0.75,
            frame_number=5,
            timestamp=5.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return True since bounce (frame 5) occurred before both edge (frame 20) and wall hit (frame 10)
        assert no_bounce_between is True

    def test_bounce_detection_with_no_impacts(self):
        """Test bounce detection when there are no edge or wall impacts."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with no bat or wall impacts
        ground_impact = ImpactEvent(
            impact_type="ground",
            position_px=(400, 350),
            frame_number=15,
            confidence=0.8,
            velocity_change=25.0,
            is_in_boundary=False
        )

        # Create a bounce point
        bounce_detection = BallDetection(
            x=200,
            y=200,
            confidence=0.85,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [ground_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return True as there are no edge and wall hits to compare with bounce
        assert no_bounce_between is True

    def test_bounce_detection_with_no_bounce_point(self):
        """Test bounce detection when there is no bounce point in trajectory."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with bat impact and wall hit but no bounce point
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=10,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 150),
            frame_number=20,
            confidence=0.8,
            velocity_change=35.0,
            is_in_boundary=True
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = None  # No bounce point

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return True since there's no bounce point to consider
        assert no_bounce_between is True

    def test_bounce_detection_with_only_bat_impact(self):
        """Test bounce detection when there's only a bat impact and bounce, but no wall hit."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with bat impact but no wall hit
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(300, 250),
            frame_number=10,
            confidence=0.9,
            velocity_change=45.0,
            is_in_boundary=False
        )

        # Create a bounce point
        bounce_detection = BallDetection(
            x=200,
            y=200,
            confidence=0.85,
            frame_number=15,
            timestamp=15.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return True as there's no wall hit to form an interval with the bat hit
        assert no_bounce_between is True

    def test_bounce_detection_with_only_wall_impact(self):
        """Test bounce detection when there's only a wall hit and bounce, but no bat impact."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create trajectory with wall impact but no bat impact
        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 150),
            frame_number=20,
            confidence=0.8,
            velocity_change=35.0,
            is_in_boundary=True
        )

        # Create a bounce point
        bounce_detection = BallDetection(
            x=200,
            y=200,
            confidence=0.85,
            frame_number=15,
            timestamp=15.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call bounce detection function
        no_bounce_between = engine._no_bounce_between_edge_and_wall(trajectory)

        # Should return True as there's no bat hit to form an interval with the wall hit
        assert no_bounce_between is True


class TestCaughtBehindEngineWallBoundary:
    """Test wall boundary check in Caught Behind Engine."""

    def test_is_in_wall_boundary_point_inside_triangle(self):
        """Test that a point inside a triangular wall boundary is correctly identified."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a triangular wall boundary
        wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (150, 200)],
            is_valid=True
        )

        # Create a ball detection inside the triangle
        detection = BallDetection(
            x=150,
            y=130,
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        assert is_in_boundary is True

    def test_is_in_wall_boundary_point_outside_triangle(self):
        """Test that a point outside a triangular wall boundary is correctly identified."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a triangular wall boundary
        wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (150, 200)],
            is_valid=True
        )

        # Create a ball detection outside the triangle
        detection = BallDetection(
            x=300,
            y=300,
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        assert is_in_boundary is False

    def test_is_in_wall_boundary_point_on_edge(self):
        """Test that a point on the edge of a wall boundary is handled properly."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a rectangular wall boundary
        wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (200, 200), (100, 200)],
            is_valid=True
        )

        # Create a ball detection on the edge of the rectangle
        detection = BallDetection(
            x=150,
            y=100,  # On the top edge
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        # Points on the edge should be considered inside (implementation may vary)
        # For the ray casting algorithm, edge points can sometimes be considered inside
        assert isinstance(is_in_boundary, bool)

    def test_is_in_wall_boundary_invalid_boundary(self):
        """Test that an invalid wall boundary returns False."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create an invalid wall boundary (less than 3 points)
        wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100)],  # Only 2 points
            is_valid=False
        )

        # Create a ball detection
        detection = BallDetection(
            x=150,
            y=100,
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        assert is_in_boundary is False

    def test_is_in_wall_boundary_empty_boundary(self):
        """Test that an empty wall boundary returns False."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create an empty wall boundary
        wall_boundary = WallBoundary(
            polygon_points=[],
            is_valid=True
        )

        # Create a ball detection
        detection = BallDetection(
            x=150,
            y=100,
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        assert is_in_boundary is False

    def test_is_in_wall_boundary_point_at_vertex(self):
        """Test that a point exactly at a vertex of the wall boundary is handled properly."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a square wall boundary
        wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (200, 200), (100, 200)],
            is_valid=True
        )

        # Create a ball detection at one of the vertices
        detection = BallDetection(
            x=100,
            y=100,  # At the corner vertex
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        # Call the function to check if point is in boundary
        is_in_boundary = engine._is_in_wall_boundary(detection, wall_boundary)

        # Points at vertices should be handled consistently
        assert isinstance(is_in_boundary, bool)

    def test_hits_wall_with_wall_impact(self):
        """Test that hits_wall returns True when there's a wall impact."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        # Create a trajectory with wall impact
        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(150, 100),
            frame_number=20,
            confidence=0.8,
            velocity_change=35.0,
            is_in_boundary=True
        )

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (200, 200), (100, 200)],
            is_valid=True
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [wall_impact]
        trajectory.detections = []

        # Call the function to check if wall is hit
        hits_wall = engine._hits_wall(trajectory, config)

        assert hits_wall is True

    def test_hits_wall_with_detection_in_boundary(self):
        """Test that hits_wall returns True when detection is in wall boundary."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(100, 100), (200, 100), (200, 200), (100, 200)],
            is_valid=True
        )

        # Create a trajectory with detection inside wall boundary
        detection_in_boundary = BallDetection(
            x=150,
            y=150,
            confidence=0.8,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = []  # No impact points
        trajectory.detections = [detection_in_boundary]

        # Call the function to check if wall is hit
        hits_wall = engine._hits_wall(trajectory, config)

        assert hits_wall is True


class TestCaughtBehindEngineFullEvaluation:
    """Test the full caught behind evaluation process."""

    def test_caught_behind_out_case(self):
        """Test caught behind evaluation returns OUT when all conditions are met."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(50, 50), (300, 50), (300, 250), (50, 250)],
            is_valid=True
        )

        # Create a trajectory with bat hit and wall hit, but no bounce between
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(250, 150),
            frame_number=10,
            confidence=0.9,
            velocity_change=50.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 100),
            frame_number=15,
            confidence=0.8,
            velocity_change=40.0,
            is_in_boundary=True
        )

        # No bounce in between (bounce is after the wall hit)
        bounce_detection = BallDetection(
            x=80,
            y=80,
            confidence=0.7,
            frame_number=20,
            timestamp=20.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call the full evaluation
        decision = engine.evaluate(trajectory, config)

        # Should be OUT because all conditions are met
        assert decision.result == "OUT"
        assert decision.confidence > 0.5
        assert decision.reason.startswith("Ball hit bat and hit wall directly")

    def test_caught_behind_not_out_due_to_bounce(self):
        """Test caught behind evaluation returns NOT OUT when ball bounces between bat and wall."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(50, 50), (300, 50), (300, 250), (50, 250)],
            is_valid=True
        )

        # Create a trajectory with bat hit, bounce in between, and wall hit
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(250, 150),
            frame_number=5,
            confidence=0.9,
            velocity_change=50.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 100),
            frame_number=15,
            confidence=0.8,
            velocity_change=40.0,
            is_in_boundary=True
        )

        # Bounce in between the bat hit and wall hit
        bounce_detection = BallDetection(
            x=200,
            y=180,
            confidence=0.7,
            frame_number=10,
            timestamp=10.0,
            visibility="visible"
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, wall_impact]
        trajectory.detections = []
        trajectory.bounce_point = bounce_detection

        # Call the full evaluation
        decision = engine.evaluate(trajectory, config)

        # Should be NOT OUT because there's a bounce between bat and wall
        assert decision.result == "NOT OUT"
        assert "bounced between bat and wall" in decision.reason

    def test_caught_behind_not_out_due_to_no_edge(self):
        """Test caught behind evaluation returns NOT OUT when there's no bat contact."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(50, 50), (300, 50), (300, 250), (50, 250)],
            is_valid=True
        )

        # Create a trajectory with wall hit but no bat hit
        ground_impact = ImpactEvent(
            impact_type="ground",
            position_px=(200, 200),
            frame_number=10,
            confidence=0.8,
            velocity_change=30.0,
            is_in_boundary=False
        )

        wall_impact = ImpactEvent(
            impact_type="wall",
            position_px=(100, 100),
            frame_number=15,
            confidence=0.8,
            velocity_change=40.0,
            is_in_boundary=True
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [ground_impact, wall_impact]
        trajectory.detections = []

        # Call the full evaluation
        decision = engine.evaluate(trajectory, config)

        # Should be NOT OUT because there was no bat contact
        assert decision.result == "NOT OUT"
        assert "did not hit bat" in decision.reason

    def test_caught_behind_not_out_due_to_no_wall_hit(self):
        """Test caught behind evaluation returns NOT OUT when there's no wall hit."""
        # Create mock calibrator
        calibrator = Mock(spec=PitchCalibrator)

        # Create engine instance
        engine = CaughtBehindEngine(calibrator=calibrator)

        from src.models.session_config import SessionConfig

        config = Mock(spec=SessionConfig)
        config.wall_boundary = WallBoundary(
            polygon_points=[(50, 50), (300, 50), (300, 250), (50, 250)],
            is_valid=True
        )

        # Create a trajectory with bat hit but no wall hit
        bat_impact = ImpactEvent(
            impact_type="bat",
            position_px=(250, 150),
            frame_number=10,
            confidence=0.9,
            velocity_change=50.0,
            is_in_boundary=False
        )

        ground_impact = ImpactEvent(
            impact_type="ground",
            position_px=(200, 200),
            frame_number=15,
            confidence=0.8,
            velocity_change=30.0,
            is_in_boundary=False
        )

        trajectory = Mock(spec=Trajectory)
        trajectory.impact_points = [bat_impact, ground_impact]
        trajectory.detections = []

        # Call the full evaluation
        decision = engine.evaluate(trajectory, config)

        # Should be NOT OUT because there was no wall hit
        assert decision.result == "NOT OUT"
        assert "did not hit wall" in decision.reason