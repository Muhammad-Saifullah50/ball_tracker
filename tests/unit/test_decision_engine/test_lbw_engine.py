"""
Unit tests for LBW Engine in Cricket Ball Tracker
"""
import pytest
from src.decision_engine.lbw_engine import LBWEngine, InsufficientDataError
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.calibration import PitchConfig, StumpPosition
from src.models.ball_detection import Trajectory, BallDetection
from src.models.delivery import ImpactEvent
from src.models.decisions import LBWDecision


class TestLBWPitchingPointAnalysis:
    """Test for LBW pitching point analysis (T047)"""

    def test_lbw_pitching_point_analysis(self):
        """Test that LBW engine can analyze where the ball pitched."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = LBWEngine(calibrator=calibrator)

        # Create a mock trajectory with multiple points to make it realistic
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 120, 100, 0.9, 0),
                BallDetection(1, 125, 120, 0.9, 100),
                BallDetection(2, 130, 140, 0.9, 200),
                BallDetection(3, 135, 160, 0.9, 300),
            ],
            bounce_point=BallDetection(2, 130, 140, 0.8, 200)
        )

        # Create a mock impact event
        impact = ImpactEvent(
            impact_type="pad",
            position_px=(138, 170),
            frame_number=3,
            confidence=0.8,
            velocity_change=50.0
        )

        result = engine.evaluate(trajectory, impact, "right")

        # Verify that the result is an LBWDecision object
        assert isinstance(result, LBWDecision)
        # Verify that the pitching zone is one of the expected values
        assert result.pitching_zone in ["in_line", "outside_off", "outside_leg"]


class TestLBWImpactPointAnalysis:
    """Test for LBW impact point analysis (T048)"""

    def test_lbw_impact_point_analysis(self):
        """Test that LBW engine can analyze where the ball hit the pad."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = LBWEngine(calibrator=calibrator)

        # Create a mock trajectory
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 120, 100, 0.9, 0),
                BallDetection(1, 125, 120, 0.9, 100),
                BallDetection(2, 130, 140, 0.9, 200),
                BallDetection(3, 135, 160, 0.9, 300),
            ],
            bounce_point=BallDetection(2, 130, 140, 0.8, 200)
        )
        impact = ImpactEvent(
            impact_type="pad",
            position_px=(138, 170),
            frame_number=3,
            confidence=0.8,
            velocity_change=50.0
        )

        result = engine.evaluate(trajectory, impact, "right")

        # Verify that the impact zone is calculated properly
        assert isinstance(result, LBWDecision)
        assert result.impact_zone in ["in_line", "outside_off"]


class TestLBWTrajectoryProjection:
    """Test for trajectory projection to stumps (T049)"""

    def test_trajectory_projection_to_stumps(self):
        """Test that LBW engine can project trajectory to check if it would hit stumps."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = LBWEngine(calibrator=calibrator)

        # Create a mock trajectory
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 120, 100, 0.9, 0),
                BallDetection(1, 125, 120, 0.9, 100),
                BallDetection(2, 130, 140, 0.9, 200),
                BallDetection(3, 135, 160, 0.9, 300),
            ],
            bounce_point=BallDetection(2, 130, 140, 0.8, 200)
        )
        impact = ImpactEvent(
            impact_type="pad",
            position_px=(138, 170),
            frame_number=3,
            confidence=0.8,
            velocity_change=50.0
        )

        result = engine.evaluate(trajectory, impact, "right")

        # Verify that the projected path exists and is the right format
        assert isinstance(result, LBWDecision)
        assert hasattr(result, 'projected_path')
        assert isinstance(result.projected_path, list)
        assert len(result.projected_path) >= 2  # Should have at least start and end points


class TestLBWDecisionOutput:
    """Test for LBW decision output with confidence score (T050)"""

    def test_lbw_decision_output_with_confidence(self):
        """Test that LBW engine outputs decision with confidence score."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = LBWEngine(calibrator=calibrator)

        # Create a mock trajectory
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 120, 100, 0.9, 0),
                BallDetection(1, 125, 120, 0.9, 100),
                BallDetection(2, 130, 140, 0.9, 200),
                BallDetection(3, 135, 160, 0.9, 300),
            ],
            bounce_point=BallDetection(2, 130, 140, 0.8, 200)
        )
        impact = ImpactEvent(
            impact_type="pad",
            position_px=(138, 170),
            frame_number=3,
            confidence=0.8,
            velocity_change=50.0
        )

        result = engine.evaluate(trajectory, impact, "right")

        # Verify that result is an LBWDecision object with confidence score
        assert isinstance(result, LBWDecision)
        assert hasattr(result, 'confidence')
        assert 0.0 <= result.confidence <= 1.0
        assert result.result in ["OUT", "NOT_OUT"]
        assert isinstance(result.reason, str)
        assert isinstance(result.handedness, str)

    def test_lbw_short_trajectory_raises_error(self):
        """Test that short trajectories raise InsufficientDataError."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = LBWEngine(calibrator=calibrator)

        # Create a very short trajectory
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[BallDetection(0, 120, 180, 0.9, 0)]
        )
        impact = ImpactEvent(
            impact_type="pad",
            position_px=(130, 190),
            frame_number=0,
            confidence=0.8,
            velocity_change=50.0
        )

        with pytest.raises(InsufficientDataError):
            engine.evaluate(trajectory, impact, "right")