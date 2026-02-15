"""
Pitch calibrator for Cricket Ball Tracker
Handles pixel-to-real-world conversion and coordinate mapping
"""
from typing import Tuple, Union
import math

from ..models.calibration import PitchConfig, StumpPosition, WideConfig
from ..models.session_config import SessionConfig


class PitchCalibrator:
    """Manages pitch calibration and coordinate mapping."""

    def __init__(self, pitch_config: PitchConfig, stump_position: StumpPosition) -> None:
        self.pitch_config = pitch_config
        self.stump_position = stump_position

    def pixels_to_meters(self, pixel_distance: float) -> float:
        """Convert pixel distance to real-world meters."""
        return pixel_distance / self.pitch_config.pixels_per_meter

    def meters_to_pixels(self, meter_distance: float) -> float:
        """Convert real-world meters to pixel distance."""
        return meter_distance * self.pitch_config.pixels_per_meter

    def speed_kmh(self, pixel_velocity: float, fps: float) -> float:
        """
        Convert pixel velocity (px/frame) to km/h.

        Args:
            pixel_velocity: Velocity in pixels per frame
            fps: Frames per second of the video
        """
        # Convert pixels per frame to pixels per second
        pixels_per_second = pixel_velocity * fps
        # Convert pixels to meters
        meters_per_second = self.pixels_to_meters(pixels_per_second)
        # Convert m/s to km/h
        return meters_per_second * 3.6

    def get_wide_lines(self, wide_config: WideConfig) -> Tuple[Tuple[Tuple[int, int], Tuple[int, int]], Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Calculate pixel coordinates for wide corridor lines.

        Returns:
            Tuple of (off_side_line, leg_side_line) where each line is ((x1, y1), (x2, y2))
        """
        # For this MVP, we'll assume the wide lines are vertical lines
        # based on the position of the stumps and the wide distance in pixels
        off_stump_x, _ = self.stump_position.off_stump_px
        leg_stump_x, _ = self.stump_position.leg_stump_px

        # Convert wide distances from meters to pixels
        off_side_px = self.meters_to_pixels(wide_config.off_side_distance_m)
        leg_side_px = self.meters_to_pixels(wide_config.leg_side_distance_m)

        # Calculate wide line positions
        off_line_x = off_stump_x - int(off_side_px)
        leg_line_x = leg_stump_x + int(leg_side_px)

        # Return vertical lines from top to bottom of the frame
        # We'll use the batting crease y-coordinate as the starting point
        batting_crease_y = self.pitch_config.batting_crease_px[1]

        # For now, just use frame boundaries (this would be adjusted based on actual frame size)
        off_line = ((off_line_x, batting_crease_y), (off_line_x, batting_crease_y + 100))
        leg_line = ((leg_line_x, batting_crease_y), (leg_line_x, batting_crease_y + 100))

        return (off_line, leg_line)

    def is_in_stump_zone(self, position_px: Tuple[int, int], tolerance: float = 1.0) -> bool:
        """
        Check if a position falls within the stump zone (with tolerance).

        Args:
            position_px: Pixel coordinates of the position to check
            tolerance: Multiplier for the stump zone width (for lenient settings)
        """
        pos_x, pos_y = position_px

        # Get the x-coordinates of the stumps
        off_stump_x, off_stump_y = self.stump_position.off_stump_px
        middle_stump_x, _ = self.stump_position.middle_stump_px
        leg_stump_x, _ = self.stump_position.leg_stump_px

        # Calculate the effective stump zone, accounting for tolerance
        effective_width = self.stump_position.stump_width_px * tolerance

        # The effective zone is between off_stump_x and leg_stump_x
        # with tolerance applied to the boundaries
        left_boundary = min(off_stump_x, middle_stump_x, leg_stump_x) - (effective_width - self.stump_position.stump_width_px) // 2
        right_boundary = max(off_stump_x, middle_stump_x, leg_stump_x) + (effective_width - self.stump_position.stump_width_px) // 2

        # Check if the position is within the stump zone boundaries
        return left_boundary <= pos_x <= right_boundary

    def get_stump_zone_polygon(self, tolerance: float = 1.0) -> list[Tuple[int, int]]:
        """
        Return polygon vertices for the stump zone (for overlay drawing).

        Args:
            tolerance: Multiplier for the stump zone width (for lenient settings)
        """
        # Get the x-coordinates of the stumps
        off_stump_x, off_stump_y = self.stump_position.off_stump_px
        leg_stump_x, leg_stump_y = self.stump_position.leg_stump_px

        # Calculate the effective stump zone, accounting for tolerance
        effective_width = self.stump_position.stump_width_px * tolerance

        # Calculate the center of the stumps to determine orientation
        center_x = (off_stump_x + leg_stump_x) // 2

        # Define the polygon points for the stump zone
        # This creates a rectangle around the stumps
        left_boundary = center_x - int(effective_width // 2)
        right_boundary = center_x + int(effective_width // 2)

        # Use the stumps' y-coordinate as the top of the zone, and add some height
        top_y = min(off_stump_y, leg_stump_y) - 10  # Add some space above stumps
        bottom_y = max(off_stump_y, leg_stump_y) + 30  # Add space below stumps

        # Create the polygon as a rectangle
        polygon = [
            (left_boundary, top_y),
            (right_boundary, top_y),
            (right_boundary, bottom_y),
            (left_boundary, bottom_y)
        ]

        return polygon

    def distance_between_points(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """
        Calculate Euclidean distance between two points in pixels.

        Args:
            p1: First point as (x, y)
            p2: Second point as (x, y)

        Returns:
            Distance in pixels
        """
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx * dx + dy * dy)

    def is_ball_wide(self, ball_position: Tuple[int, int], wide_config: WideConfig, is_batting_end: bool = True) -> Tuple[bool, str]:
        """
        Determine if a ball position at the crease is wide.

        Args:
            ball_position: Ball position at the crease (x, y)
            wide_config: Wide configuration
            is_batting_end: Whether this is at the batting crease (vs bowling crease)

        Returns:
            Tuple of (is_wide, side) where side is 'off', 'leg', or None if not wide
        """
        ball_x, ball_y = ball_position

        # Get the x-coordinates of the stumps
        off_stump_x, _ = self.stump_position.off_stump_px
        leg_stump_x, _ = self.stump_position.leg_stump_px

        # Convert wide distances from meters to pixels
        off_side_px = self.meters_to_pixels(wide_config.off_side_distance_m)
        leg_side_px = self.meters_to_pixels(wide_config.leg_side_distance_m)

        # Calculate wide line positions
        off_line_x = off_stump_x - int(off_side_px)
        leg_line_x = leg_stump_x + int(leg_side_px)

        # Check if the ball is outside the wide lines
        if ball_x < off_line_x:
            return (True, 'off')
        elif ball_x > leg_line_x:
            return (True, 'leg')
        else:
            return (False, None)