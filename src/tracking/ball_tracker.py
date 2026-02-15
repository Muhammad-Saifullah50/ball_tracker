"""
Ball tracker for Cricket Ball Tracker
Uses Kalman filter for trajectory tracking
"""
import numpy as np
from typing import Optional, List, Tuple
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

from ..models.ball_detection import BallDetection, Trajectory
from ..models.delivery import ImpactEvent


class BallTracker:
    """Tracks ball trajectory using Kalman filter."""

    def __init__(self, fps: float = 30.0) -> None:
        """
        Initialize the BallTracker.

        Args:
            fps: Frames per second of the video
        """
        self.fps = fps
        self.dt = 1.0 / fps  # Time step

        # Initialize Kalman filter
        # State: [x, y, vx, vy, ax, ay] - position, velocity, acceleration
        self.kf = KalmanFilter(dim_x=6, dim_z=2)

        # State transition matrix (for constant acceleration model)
        self.kf.F = np.array([
            [1, 0, self.dt, 0, 0.5 * self.dt**2, 0],           # x = x + vx*dt + 0.5*ax*dt^2
            [0, 1, 0, self.dt, 0, 0.5 * self.dt**2],           # y = y + vy*dt + 0.5*ay*dt^2
            [0, 0, 1, 0, self.dt, 0],                          # vx = vx + ax*dt
            [0, 0, 0, 1, 0, self.dt],                          # vy = vy + ay*dt
            [0, 0, 0, 0, 1, 0],                                # ax = ax (constant acceleration)
            [0, 0, 0, 0, 0, 1]                                 # ay = ay (constant acceleration)
        ])

        # Measurement function (we only measure position)
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0],  # Measure x
            [0, 1, 0, 0, 0, 0]   # Measure y
        ])

        # Measurement noise covariance
        self.kf.R = np.array([
            [5, 0],   # Measurement noise for x
            [0, 5]    # Measurement noise for y
        ])

        # Initial state covariance
        self.kf.P = np.array([
            [10, 0, 0, 0, 0, 0],
            [0, 10, 0, 0, 0, 0],
            [0, 0, 10, 0, 0, 0],
            [0, 0, 0, 10, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])

        # Process noise (will be set adaptively)
        self.kf.Q = Q_discrete_white_noise(dim=2, dt=self.dt, var=1.0, block_size=3)

        # Initialize state
        self.kf.x = np.array([0, 0, 0, 0, 0, 0], dtype=float)

        # Track trajectory
        self.trajectory_detections: List[BallDetection] = []
        self.speed_kmh: Optional[float] = None
        self.bounce_point: Optional[BallDetection] = None
        self.impact_events: List[ImpactEvent] = []
        self.deviation_px: float = 0.0
        self.is_complete: bool = False
        self.bounce_detected: bool = False
        self.last_vertical_velocity: float = 0.0

        # For impact detection
        self.velocity_history: List[np.ndarray] = []
        self.max_history_length = 5

    def update(self, detection: Optional[BallDetection]) -> None:
        """
        Update tracker with new detection (or None for predict-only).

        Args:
            detection: Ball detection from current frame, or None if not detected.
        """
        if detection is not None:
            # Measurement is [x, y]
            z = np.array([detection.x, detection.y])

            # Perform Kalman update
            self.kf.update(z)

            # Add to trajectory
            self.trajectory_detections.append(detection)

            # Check for bounce
            if not self.bounce_detected:
                current_vy = self.kf.x[3]  # current vertical velocity
                # Check if vertical velocity changed sign (indicating bounce)
                if self.last_vertical_velocity > 0 and current_vy < 0:
                    # This indicates bounce (ball was going down then up)
                    self.bounce_point = detection
                    self.bounce_detected = True
                self.last_vertical_velocity = current_vy

            # Store velocity for impact detection
            current_velocity = np.array([self.kf.x[2], self.kf.x[3]])  # [vx, vy]
            self.velocity_history.append(current_velocity)
            if len(self.velocity_history) > self.max_history_length:
                self.velocity_history.pop(0)
        else:
            # No detection - just predict
            pass

        # Always perform prediction for next state
        self.kf.predict()

    def get_trajectory(self, pixels_per_meter: float = None) -> Trajectory:
        """Return the current trajectory with all detections and computed metrics."""
        # Calculate derived metrics if we have enough data
        speed = self.speed_kmh
        if len(self.trajectory_detections) > 1 and speed is None:
            # Calculate speed from first and last detection if not already calculated
            start_det = self.trajectory_detections[0]
            end_det = self.trajectory_detections[-1]

            # Calculate distance between first and last points
            dx = end_det.x - start_det.x
            dy = end_det.y - start_det.y
            distance_pixels = np.sqrt(dx**2 + dy**2)

            # Calculate time between first and last detection
            if len(self.trajectory_detections) > 1:
                dt_frames = len(self.trajectory_detections) - 1
                dt_seconds = dt_frames / self.fps

                # Calculate speed if we have time
                if dt_seconds > 0:
                    # Calculate speed in pixels per second
                    pixels_per_second = distance_pixels / dt_seconds

                    # Convert to km/h if calibration data is provided
                    if pixels_per_meter is not None and pixels_per_meter > 0:
                        # Convert pixels per second to meters per second, then to km/h
                        meters_per_second = pixels_per_second / pixels_per_meter
                        speed = meters_per_second * 3.6  # Convert m/s to km/h
                    else:
                        # For now, just store pixels per second as the speed value
                        # since we don't have proper calibration
                        speed = pixels_per_second

        # Calculate trajectory deviation (how much the ball deviated from a straight line)
        if len(self.trajectory_detections) >= 3:
            # Calculate total deviation from straight line path
            if self.trajectory_detections[0] and self.trajectory_detections[-1]:
                start_x, start_y = self.trajectory_detections[0].x, self.trajectory_detections[0].y
                end_x, end_y = self.trajectory_detections[-1].x, self.trajectory_detections[-1].y

                # Calculate deviation for each point from the straight line
                total_deviation = 0
                for i in range(1, len(self.trajectory_detections) - 1):  # Skip first and last
                    point = self.trajectory_detections[i]
                    # Calculate distance from point to line (simplified)
                    # This is a perpendicular distance calculation
                    px, py = point.x, point.y

                    # Calculate distance from point to line formed by start and end points
                    # Distance from point (px,py) to line passing through (x1,y1) and (x2,y2)
                    line_dist = abs((end_y - start_y) * px - (end_x - start_x) * py + end_x * start_y - end_y * start_x)
                    line_dist /= np.sqrt((end_y - start_y)**2 + (end_x - start_x)**2)

                    total_deviation += line_dist

                self.deviation_px = total_deviation / max(1, len(self.trajectory_detections) - 2)

        return Trajectory(
            delivery_id="current",  # Will be set when delivery is completed
            detections=self.trajectory_detections,
            speed_kmh=speed,
            bounce_point=self.bounce_point,
            impact_points=self.impact_events,
            deviation_px=self.deviation_px,
            is_complete=self.is_complete,
            kalman_state=self.kf.x.tolist()
        )

    def detect_bounce(self) -> Optional[BallDetection]:
        """Return bounce point if detected in current trajectory."""
        return self.bounce_point

    def detect_impact(self, threshold: float = 50.0, calibrator=None, config=None) -> Optional[ImpactEvent]:
        """
        Check if an impact event occurred in the latest update.

        Args:
            threshold: Minimum velocity change magnitude for impact detection.
            calibrator: PitchCalibrator for position-based impact classification
            config: SessionConfig for boundary information

        Returns:
            ImpactEvent if impact detected, None otherwise.
        """
        if len(self.velocity_history) < 2:
            return None

        # Calculate velocity change
        recent_velocity = self.velocity_history[-1]
        previous_velocity = self.velocity_history[-2]

        velocity_change = np.linalg.norm(recent_velocity - previous_velocity)

        if velocity_change > threshold:
            # Impact detected
            if self.trajectory_detections:
                latest_detection = self.trajectory_detections[-1]

                # Determine impact type based on position relative to calibrated elements
                impact_type = "unknown"

                if calibrator and config:
                    # Check if impact is at stumps
                    off_stump = config.batting_stumps.off_stump_px
                    middle_stump = config.batting_stumps.middle_stump_px
                    leg_stump = config.batting_stumps.leg_stump_px

                    # Calculate distances to each stump
                    d_off = np.sqrt((latest_detection.x - off_stump[0])**2 + (latest_detection.y - off_stump[1])**2)
                    d_middle = np.sqrt((latest_detection.x - middle_stump[0])**2 + (latest_detection.y - middle_stump[1])**2)
                    d_leg = np.sqrt((latest_detection.x - leg_stump[0])**2 + (latest_detection.y - leg_stump[1])**2)

                    # If close to any stump, consider as stump hit
                    STUMP_THRESHOLD = config.batting_stumps.stump_width_px if hasattr(config.batting_stumps, 'stump_width_px') else 30
                    if min(d_off, d_middle, d_leg) <= STUMP_THRESHOLD:
                        impact_type = "stumps"
                    # Check if it's close to the pad area (relative to stumps and expected pad position)
                    elif calibrator.is_in_stump_zone((int(latest_detection.x), int(latest_detection.y)), tolerance=1.5):
                        # Additional check: if it's in line with stumps and not too far from crease
                        impact_type = "pad"
                    # Check if it's likely ground contact (based on y position)
                    elif latest_detection.y > max(off_stump[1], middle_stump[1], leg_stump[1]):
                        impact_type = "ground"
                    # Check if it's in wall boundary
                    elif config.wall_boundary and self._is_in_boundary(latest_detection, config.wall_boundary):
                        impact_type = "wall"

                # If no calibrator/config provided, use basic heuristics
                else:
                    # If y coordinate is at the bottom of the frame, more likely ground
                    # If x coordinate is in center range, could be stumps/pad
                    impact_type = "unknown"

                # Check if impact is in wall boundary
                is_in_boundary = False
                if config and config.wall_boundary:
                    is_in_boundary = self._is_in_boundary(latest_detection, config.wall_boundary)

                # Create ImpactEvent
                impact = ImpactEvent(
                    impact_type=impact_type,
                    position_px=(int(latest_detection.x), int(latest_detection.y)),
                    frame_number=latest_detection.frame_number,
                    confidence=min(1.0, velocity_change / 100.0),  # Normalize confidence
                    velocity_change=velocity_change,
                    is_in_boundary=is_in_boundary
                )

                self.impact_events.append(impact)
                return impact

        return None

    def _is_in_boundary(self, detection, wall_boundary) -> bool:
        """
        Check if a detection is within the wall boundary.

        Args:
            detection: BallDetection object
            wall_boundary: WallBoundary object containing the polygon

        Returns:
            True if the detection is inside the boundary polygon, False otherwise
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

    def get_predicted_position(self) -> Tuple[float, float]:
        """Return Kalman-predicted position for next frame."""
        return (float(self.kf.x[0]), float(self.kf.x[1]))

    def reset(self) -> None:
        """Reset tracker for a new delivery."""
        # Reset Kalman filter state
        self.kf.x = np.array([0, 0, 0, 0, 0, 0], dtype=float)
        self.kf.P = np.array([
            [10, 0, 0, 0, 0, 0],
            [0, 10, 0, 0, 0, 0],
            [0, 0, 10, 0, 0, 0],
            [0, 0, 0, 10, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])

        # Reset tracking data
        self.trajectory_detections = []
        self.speed_kmh = None
        self.bounce_point = None
        self.impact_events = []
        self.deviation_px = 0.0
        self.is_complete = False
        self.bounce_detected = False
        self.last_vertical_velocity = 0.0
        self.velocity_history = []