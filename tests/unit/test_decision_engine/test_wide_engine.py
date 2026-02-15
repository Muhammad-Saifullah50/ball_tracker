"""
Unit tests for Wide Engine in Cricket Ball Tracker
"""
import pytest
from src.decision_engine.wide_engine import WideEngine
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.calibration import PitchConfig, StumpPosition, WideConfig
from src.models.ball_detection import Trajectory, BallDetection
from src.models.decisions import WideDecision


class TestWideCorridorBoundaryCheck:
    """Test for wide corridor boundary check (T059)"""

    def test_wide_corridor_boundary_check(self):
        """Test that Wide engine checks if ball crosses batting crease outside wide lines."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        wide_config = WideConfig(
            off_side_distance_m=0.83,
            leg_side_distance_m=0.83
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = WideEngine(calibrator=calibrator, wide_config=wide_config)

        # Create a trajectory that ends outside the off-side wide line
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 80, 100, 0.9, 0),   # Ball starts from bowler's end
                BallDetection(1, 85, 120, 0.9, 100),
                BallDetection(2, 90, 140, 0.9, 200),
                BallDetection(3, 95, 160, 0.9, 300),
                BallDetection(4, 70, 180, 0.8, 400),  # Ball ends up outside off-side wide
            ]
        )

        result = engine.evaluate(trajectory)

        # Verify that the result is a WideDecision object
        assert isinstance(result, WideDecision)
        # Since the ball ended up outside the off-side wide line (70 < 100 which is off_stump), it should be wide
        assert result.result == "WIDE"
        assert result.side == "off"


class TestBallPositionAtBattingCrease:
    """Test for ball position at batting crease (T060)"""

    def test_ball_position_at_batting_crease(self):
        """Test that Wide engine evaluates ball position at the batting crease."""
        pitch_config = PitchConfig(pitch_length=20.12)
        stump_position = StumpPosition(
            off_stump_px=(100, 200),
            middle_stump_px=(150, 200),
            leg_stump_px=(200, 200),
            stump_width_px=100,
            stump_height_px=70
        )
        wide_config = WideConfig(
            off_side_distance_m=0.83,
            leg_side_distance_m=0.83
        )
        calibrator = PitchCalibrator(pitch_config, stump_position)

        engine = WideEngine(calibrator=calibrator, wide_config=wide_config)

        # Create a trajectory that ends within the wide lines (not wide)
        trajectory = Trajectory(
            delivery_id="test_delivery",
            detections=[
                BallDetection(0, 120, 100, 0.9, 0),   # Ball starts from bowler's end
                BallDetection(1, 125, 120, 0.9, 100),
                BallDetection(2, 130, 140, 0.9, 200),
                BallDetection(3, 135, 160, 0.9, 300),
                BallDetection(4, 140, 180, 0.8, 400),  # Ball ends up within wide lines (between 100 and 200)
            ]
        )

        result = engine.evaluate(trajectory)

        # Verify that the result is a WideDecision object
        assert isinstance(result, WideDecision)
        # Since the ball ended up within the wide lines, it should not be wide
        assert result.result == "NOT_WIDE"
        assert result.side is None  # No side for not wide
        assert result.ball_position_at_crease_px == (140, 180)  # Last detection position