"""
Replay renderer for Cricket Ball Tracker
Handles rendering of replay frames with overlays
"""
import cv2
import numpy as np
from typing import Optional, Deque, List
from ..models.ball_detection import Trajectory
from ..models.delivery import ImpactEvent
from ..calibration.pitch_calibrator import PitchCalibrator


class ReplayRenderer:
    """Renderer for replay frames with trajectory and decision overlays."""

    def __init__(self, calibrator: Optional[PitchCalibrator] = None):
        """
        Initialize the replay renderer.

        Args:
            calibrator: Pitch calibrator for drawing calibrated elements
        """
        self.calibrator = calibrator

    def render_frame(self, frame: np.ndarray, trajectory: Optional[Trajectory] = None,
                     current_frame_idx: int = 0, total_frames: int = 0) -> np.ndarray:
        """
        Render a replay frame with overlays.

        Args:
            frame: Original frame to render
            trajectory: Trajectory data to overlay
            current_frame_idx: Current frame index in the replay
            total_frames: Total number of frames in the replay

        Returns:
            Rendered frame with overlays
        """
        # Make a copy of the frame to avoid modifying the original
        overlay = frame.copy()

        # Draw trajectory if available
        if trajectory and trajectory.detections:
            # Draw trajectory path up to the current frame index
            detections_to_draw = trajectory.detections[:current_frame_idx+1]
            if len(detections_to_draw) > 1:
                points = [(int(d.x), int(d.y)) for d in detections_to_draw if 0 <= d.x < frame.shape[1] and 0 <= d.y < frame.shape[0]]
                if len(points) > 1:
                    for i in range(len(points) - 1):
                        cv2.line(overlay, points[i], points[i+1], (255, 0, 0), 2)

            # Draw current ball position if available
            if current_frame_idx < len(trajectory.detections):
                current_detection = trajectory.detections[current_frame_idx]
                if 0 <= current_detection.x < frame.shape[1] and 0 <= current_detection.y < frame.shape[0]:
                    cv2.circle(overlay, (int(current_detection.x), int(current_detection.y)), 8, (0, 255, 0), -1)
                    cv2.putText(overlay, f"Ball", (int(current_detection.x) + 10, int(current_detection.y) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Draw bounce point if available and it's within the frame range
            if trajectory.bounce_point:
                cv2.circle(overlay, (int(trajectory.bounce_point.x), int(trajectory.bounce_point.y)), 10, (0, 255, 255), 2)
                cv2.putText(overlay, "Bounce", (int(trajectory.bounce_point.x) + 10, int(trajectory.bounce_point.y) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Draw impact points if available
            if trajectory.impact_points:
                for impact in trajectory.impact_points:
                    color_map = {
                        "bat": (255, 0, 0),      # Blue
                        "pad": (0, 255, 0),      # Green
                        "ground": (0, 255, 255), # Yellow
                        "stumps": (0, 0, 255),   # Red
                        "wall": (255, 0, 255),   # Magenta
                        "unknown": (128, 128, 128)  # Gray
                    }

                    color = color_map.get(impact.impact_type, (128, 128, 128))  # Default to gray
                    pos = impact.position_px

                    # Draw different shapes based on impact type
                    if impact.impact_type == "stumps":
                        # Draw a rectangle for stumps hit
                        cv2.rectangle(overlay, (pos[0]-8, pos[1]-8), (pos[0]+8, pos[1]+8), color, 2)
                    elif impact.impact_type == "bat":
                        # Draw a circle for bat hit
                        cv2.circle(overlay, pos, 8, color, 2)
                    elif impact.impact_type == "pad":
                        # Draw a triangle for pad hit
                        pts = np.array([[pos[0], pos[1]-8], [pos[0]-7, pos[1]+5], [pos[0]+7, pos[1]+5]], np.int32)
                        cv2.polylines(overlay, [pts], True, color, 2)
                    else:
                        # Default to circle for other impacts
                        cv2.circle(overlay, pos, 6, color, 2)

                    cv2.putText(overlay, impact.impact_type, (pos[0] + 10, pos[1] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            # Draw LBW projected path if available in trajectory
            if hasattr(trajectory, 'projected_path') and trajectory.projected_path and len(trajectory.projected_path) >= 2:
                path = trajectory.projected_path
                for i in range(len(path) - 1):
                    cv2.line(overlay, path[i], path[i+1], (255, 165, 0), 2)  # Orange line for projected path
                    # Add arrowheads to indicate direction
                    if i % 5 == 0:  # Add arrowheads every 5 segments to avoid clutter
                        mid_point = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                        next_point = path[i+1]
                        cv2.arrowedLine(overlay, mid_point, next_point, (255, 165, 0), 1, tipLength=0.2)

            # Draw caught behind visual evidence if available
            if hasattr(trajectory, 'caught_behind_decision') and trajectory.caught_behind_decision:
                caught_behind = trajectory.caught_behind_decision
                if caught_behind.result == "OUT":
                    # Draw a red circle around the bat impact if caught behind is OUT
                    for impact in trajectory.impact_points:
                        if impact.impact_type == "bat":
                            cv2.circle(overlay, impact.position_px, 15, (0, 0, 255), 3)  # Red circle for bat hit
                            cv2.putText(overlay, "EDGE!", (impact.position_px[0] + 20, impact.position_px[1] - 20),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    # Draw a dashed line from bat to wall if ball hits wall
                    wall_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "wall"]
                    if wall_impacts:
                        bat_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "bat"]
                        if bat_impacts:
                            bat_pos = bat_impacts[0].position_px
                            wall_pos = wall_impacts[0].position_px
                            # Draw a dashed line from bat to wall to indicate direct hit
                            self._draw_dashed_line(overlay, bat_pos, wall_pos, (0, 165, 255), 2)  # Orange for caught behind

        # Draw calibrated elements (stumps, wide lines) if calibrator is available
        if self.calibrator and hasattr(self.calibrator, 'config'):
            try:
                # Note: We'll need to access config from somewhere - for now we'll skip this
                # as it depends on the specific implementation of the calibrator
                pass
            except:
                pass  # Skip if calibrator not ready

        # Draw frame counter
        cv2.putText(overlay, f"Frame: {current_frame_idx+1}/{total_frames}", (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Draw decision status text if available
        self._draw_decision_status(overlay, trajectory)

        # Blend overlay with original frame
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        return frame

    def _draw_dashed_line(self, img, pt1, pt2, color, thickness=1, gap=10):
        """Draw a dashed line from pt1 to pt2."""
        dist = ((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)**0.5
        dash_count = int(dist / gap)

        for i in range(dash_count):
            start = (
                int(pt1[0] + (pt2[0] - pt1[0]) * i / dash_count),
                int(pt1[1] + (pt2[1] - pt1[1]) * i / dash_count)
            )
            end = (
                int(pt1[0] + (pt2[0] - pt1[0]) * (i + 0.5) / dash_count),
                int(pt1[1] + (pt2[1] - pt1[1]) * (i + 0.5) / dash_count)
            )
            cv2.line(img, start, end, color, thickness)

    def _draw_decision_status(self, frame, trajectory: Optional[Trajectory]):
        """Draw decision status information on the frame."""
        decision_texts = []

        if trajectory:
            # Check for LBW decision
            if hasattr(trajectory, 'lbw_decision') and trajectory.lbw_decision:
                lbw = trajectory.lbw_decision
                decision_texts.append(f"LBW: {lbw.result} ({lbw.confidence:.2f})")

            # Check for Wide decision
            if hasattr(trajectory, 'wide_decision') and trajectory.wide_decision:
                wide = trajectory.wide_decision
                if wide.result == "WIDE":
                    decision_texts.append(f"WIDE: {wide.side}")

            # Check for Caught Behind decision
            if hasattr(trajectory, 'caught_behind_decision') and trajectory.caught_behind_decision:
                cb = trajectory.caught_behind_decision
                decision_texts.append(f"CAUGHT: {cb.result} ({cb.confidence:.2f})")

        # Display decision texts on the frame
        for i, text in enumerate(decision_texts):
            cv2.putText(frame, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)