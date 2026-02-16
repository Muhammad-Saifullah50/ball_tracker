"""
Replay renderer for Cricket Ball Tracker
Handles rendering of replay frames with overlays
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
        # Convert frame from numpy array to PIL Image
        if frame.dtype == np.uint8:
            if len(frame.shape) == 3:  # Color image
                if frame.shape[2] == 3:  # BGR
                    overlay = Image.fromarray(frame[:, :, ::-1])  # Convert BGR to RGB
                else:  # RGB
                    overlay = Image.fromarray(frame)
            else:  # Grayscale
                overlay = Image.fromarray(frame)
        else:
            # Convert to uint8 first
            frame_uint8 = (frame * 255).astype(np.uint8)
            overlay = Image.fromarray(frame_uint8)

        # Create drawing context
        draw = ImageDraw.Draw(overlay, "RGBA")

        # Draw trajectory if available
        if trajectory and trajectory.detections:
            # Draw trajectory path up to the current frame index
            detections_to_draw = trajectory.detections[:current_frame_idx+1]
            if len(detections_to_draw) > 1:
                points = [(int(d.x), int(d.y)) for d in detections_to_draw if 0 <= d.x < frame.shape[1] and 0 <= d.y < frame.shape[0]]
                if len(points) > 1:
                    # Draw line between consecutive points
                    for i in range(len(points) - 1):
                        draw.line([points[i], points[i+1]], fill=(255, 0, 0, 255), width=2)

            # Draw current ball position if available
            if current_frame_idx < len(trajectory.detections):
                current_detection = trajectory.detections[current_frame_idx]
                if 0 <= current_detection.x < frame.shape[1] and 0 <= current_detection.y < frame.shape[0]:
                    # Draw green circle for current ball position
                    center = (int(current_detection.x), int(current_detection.y))
                    bbox = [center[0] - 8, center[1] - 8, center[0] + 8, center[1] + 8]
                    draw.ellipse(bbox, fill=(0, 255, 0, 255), outline=(0, 255, 0, 255), width=1)
                    # Add text label
                    self._draw_text(draw, "Ball", (int(current_detection.x) + 10, int(current_detection.y) - 10), (0, 255, 0, 255))

            # Draw bounce point if available and it's within the frame range
            if trajectory.bounce_point:
                center = (int(trajectory.bounce_point.x), int(trajectory.bounce_point.y))
                bbox = [center[0] - 10, center[1] - 10, center[0] + 10, center[1] + 10]
                draw.ellipse(bbox, outline=(0, 255, 255, 255), width=2)
                self._draw_text(draw, "Bounce", (int(trajectory.bounce_point.x) + 10, int(trajectory.bounce_point.y) - 10), (0, 255, 255, 255))

            # Draw impact points if available
            if trajectory.impact_points:
                for impact in trajectory.impact_points:
                    color_map = {
                        "bat": (255, 0, 0, 255),      # Blue
                        "pad": (0, 255, 0, 255),      # Green
                        "ground": (0, 255, 255, 255), # Yellow
                        "stumps": (0, 0, 255, 255),   # Red
                        "wall": (255, 0, 255, 255),   # Magenta
                        "unknown": (128, 128, 128, 255)  # Gray
                    }

                    color = color_map.get(impact.impact_type, (128, 128, 128, 255))  # Default to gray
                    pos = impact.position_px

                    # Draw different shapes based on impact type
                    if impact.impact_type == "stumps":
                        # Draw a rectangle for stumps hit
                        bbox = [pos[0]-8, pos[1]-8, pos[0]+8, pos[1]+8]
                        draw.rectangle(bbox, outline=color, width=2)
                    elif impact.impact_type == "bat":
                        # Draw a circle for bat hit
                        bbox = [pos[0]-8, pos[1]-8, pos[0]+8, pos[1]+8]
                        draw.ellipse(bbox, outline=color, width=2)
                    elif impact.impact_type == "pad":
                        # Draw a triangle for pad hit
                        points = [(pos[0], pos[1]-8), (pos[0]-7, pos[1]+5), (pos[0]+7, pos[1]+5)]
                        draw.polygon(points, outline=color, width=2)
                    else:
                        # Default to circle for other impacts
                        bbox = [pos[0]-6, pos[1]-6, pos[0]+6, pos[1]+6]
                        draw.ellipse(bbox, outline=color, width=2)

                    self._draw_text(draw, impact.impact_type, (pos[0] + 10, pos[1] - 10), color)

            # Draw LBW projected path if available in trajectory
            if hasattr(trajectory, 'projected_path') and trajectory.projected_path and len(trajectory.projected_path) >= 2:
                path = trajectory.projected_path
                for i in range(len(path) - 1):
                    draw.line([path[i], path[i+1]], fill=(255, 165, 0, 255), width=2)  # Orange line for projected path
                    # Add arrowheads to indicate direction
                    if i % 5 == 0:  # Add arrowheads every 5 segments to avoid clutter
                        mid_point = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                        next_point = path[i+1]
                        # Draw simple arrow by drawing a line from mid_point to next_point with different styling
                        draw.line([mid_point, next_point], fill=(255, 165, 0, 255), width=3)

            # Draw caught behind visual evidence if available
            if hasattr(trajectory, 'caught_behind_decision') and trajectory.caught_behind_decision:
                caught_behind = trajectory.caught_behind_decision
                if caught_behind.result == "OUT":
                    # Draw a red circle around the bat impact if caught behind is OUT
                    for impact in trajectory.impact_points:
                        if impact.impact_type == "bat":
                            bbox = [impact.position_px[0]-15, impact.position_px[1]-15,
                                   impact.position_px[0]+15, impact.position_px[1]+15]
                            draw.ellipse(bbox, outline=(0, 0, 255, 255), width=3)  # Red circle for bat hit
                            self._draw_text(draw, "EDGE!", (impact.position_px[0] + 20, impact.position_px[1] - 20), (0, 0, 255, 255))

                    # Draw a dashed line from bat to wall if ball hits wall
                    wall_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "wall"]
                    if wall_impacts:
                        bat_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "bat"]
                        if bat_impacts:
                            bat_pos = bat_impacts[0].position_px
                            wall_pos = wall_impacts[0].position_px
                            # Draw a dashed line from bat to wall to indicate direct hit
                            self._draw_dashed_line(draw, bat_pos, wall_pos, (0, 165, 255, 255), 2)  # Orange for caught behind

        # Draw calibrated elements (stumps, wide lines) if calibrator is available
        if self.calibrator and hasattr(self.calibrator, 'config'):
            try:
                # Note: We'll need to access config from somewhere - for now we'll skip this
                # as it depends on the specific implementation of the calibrator
                pass
            except:
                pass  # Skip if calibrator not ready

        # Draw frame counter
        self._draw_text(draw, f"Frame: {current_frame_idx+1}/{total_frames}", (10, frame.shape[0] - 20), (255, 255, 255, 255), font_size=16)

        # Draw decision status text if available
        self._draw_decision_status(draw, trajectory)

        # Convert back to numpy array
        frame_with_overlays = np.array(overlay)

        # Convert back to BGR (since original frame was BGR)
        frame_with_overlays = frame_with_overlays[:, :, ::-1]  # RGB to BGR

        return frame_with_overlays

    def _draw_dashed_line(self, draw, pt1, pt2, color, thickness=1, gap=10):
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
            draw.line([start, end], fill=color, width=thickness)

    def _draw_text(self, draw, text, position, color, font_size=12):
        """Draw text using PIL."""
        try:
            # Try to use a default font
            font = ImageFont.load_default()
            # For more control, we could load a specific font file if needed
        except:
            # If default font fails, just use PIL's default text drawing
            font = None

        # Draw text at the specified position
        if font:
            draw.text(position, text, fill=color, font=font)
        else:
            draw.text(position, text, fill=color)

    def _draw_decision_status(self, draw, trajectory: Optional[Trajectory]):
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
            self._draw_text(draw, text, (10, 20 + i * 22), (0, 0, 255, 255), font_size=16)