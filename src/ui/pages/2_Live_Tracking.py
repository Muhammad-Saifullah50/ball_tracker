"""
Live Tracking page for Cricket Ball Tracker
Displays real-time ball tracking with overlays
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import time
from typing import Optional
import threading
from collections import deque

# Add the project root directory to the Python path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.detection.ball_detector import BallDetector
from src.tracking.ball_tracker import BallTracker
from src.tracking.delivery_segmenter import DeliverySegmenter
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.ball_detection import BallDetection
from src.models.session_config import SessionConfig
from src.decision_engine.lbw_engine import LBWEngine
from src.decision_engine.wide_engine import WideEngine
from src.decision_engine.caught_behind_engine import CaughtBehindEngine
from src.models.decisions import LBWDecision, WideDecision, CaughtBehindDecision
from src.replay.replay_buffer import ReplayBuffer


class LiveTrackingApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[SessionConfig] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_tracking = False
        self.tracker_thread = None

        # Initialize components
        self.ball_detector = BallDetector()
        self.ball_tracker = BallTracker(fps=30.0)
        self.delivery_segmenter = DeliverySegmenter()
        self.pitch_calibrator = None
        self.lbw_engine = None  # Will be initialized when needed
        self.wide_engine = None  # Will be initialized when needed
        self.caught_behind_engine = None  # Will be initialized when needed
        self.replay_buffer = ReplayBuffer()  # Initialize replay buffer

        # Tracking states
        self.current_frame = None
        self.current_detection = None
        self.current_trajectory = None
        self.current_frame_number = 0
        self.current_lbw_decision = None
        self.current_wide_decision = None
        self.current_caught_behind_decision = None

    def load_config(self):
        """Load session configuration."""
        if 'session_config' in st.session_state:
            self.config = st.session_state.session_config
        else:
            try:
                self.config = self.config_manager.load_session_config()
                st.session_state.session_config = self.config
            except:
                st.error("No configuration found. Please complete setup first.")
                return False
        return True

    def initialize_camera(self):
        """Initialize camera with current config."""
        if not self.config:
            return False

        try:
            # Release existing camera if it exists
            if self.cap:
                self.cap.release()

            self.cap = cv2.VideoCapture(self.config.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])

            if not self.cap.isOpened():
                st.error(f"Cannot open camera at index {self.config.camera_index}")
                return False

            return True
        except Exception as e:
            st.error(f"Error initializing camera: {str(e)}")
            return False

    def draw_overlays(self, frame, detection, trajectory, calibrator):
        """Draw tracking overlays on frame."""
        overlay = frame.copy()

        # Draw detection point if available
        if detection:
            cv2.circle(overlay, (int(detection.x), int(detection.y)), 8, (0, 255, 0), -1)
            cv2.putText(overlay, f"Ball: {detection.confidence:.2f}",
                       (int(detection.x) + 10, int(detection.y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Draw trajectory if available
        if trajectory and len(trajectory.detections) > 1:
            points = [(int(d.x), int(d.y)) for d in trajectory.detections]
            if len(points) > 1:
                for i in range(len(points) - 1):
                    cv2.line(overlay, points[i], points[i+1], (255, 0, 0), 2)

        # Draw bounce point if detected
        if trajectory and trajectory.bounce_point:
            bp = trajectory.bounce_point
            cv2.circle(overlay, (int(bp.x), int(bp.y)), 10, (0, 255, 255), 2)
            cv2.putText(overlay, "Bounce", (int(bp.x) + 10, int(bp.y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Draw impact points if detected
        if trajectory and trajectory.impact_points:
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

        # Draw calibrated elements (stumps, wide lines)
        if calibrator:
            # Draw stumps
            off_stump = self.config.batting_stumps.off_stump_px
            middle_stump = self.config.batting_stumps.middle_stump_px
            leg_stump = self.config.batting_stumps.leg_stump_px

            cv2.circle(overlay, off_stump, 5, (0, 0, 255), -1)
            cv2.circle(overlay, middle_stump, 5, (0, 0, 255), -1)
            cv2.circle(overlay, leg_stump, 5, (0, 0, 255), -1)
            cv2.putText(overlay, "Off", (off_stump[0] + 10, off_stump[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.putText(overlay, "Mid", (middle_stump[0] + 10, middle_stump[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.putText(overlay, "Leg", (leg_stump[0] + 10, leg_stump[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # Draw wide lines
            try:
                wide_lines = calibrator.get_wide_lines(self.config.wide_config)
                off_line, leg_line = wide_lines

                cv2.line(overlay, off_line[0], off_line[1], (255, 255, 0), 2)
                cv2.line(overlay, leg_line[0], leg_line[1], (255, 255, 0), 2)
            except:
                pass  # Skip if calibrator not ready

        # Draw LBW projected path if available in trajectory
        if trajectory and hasattr(trajectory, 'projected_path') and trajectory.projected_path and len(trajectory.projected_path) >= 2:
            path = trajectory.projected_path
            for i in range(len(path) - 1):
                cv2.line(overlay, path[i], path[i+1], (255, 165, 0), 2)  # Orange line for projected path
                # Add arrowheads to indicate direction
                if i % 5 == 0:  # Add arrowheads every 5 segments to avoid clutter
                    mid_point = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                    next_point = path[i+1]
                    cv2.arrowedLine(overlay, mid_point, next_point, (255, 165, 0), 1, tipLength=0.2)

        # Draw caught behind visual evidence if available
        if trajectory and trajectory.caught_behind_decision:
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

        # Draw decision status text (LBW, Wide, Caught Behind) on the frame
        decision_texts = []
        if self.current_lbw_decision and self.current_lbw_decision.result == "OUT":
            decision_texts.append(f"LBW: {self.current_lbw_decision.result}")
        if self.current_wide_decision and self.current_wide_decision.result == "WIDE":
            decision_texts.append(f"WIDE: {self.current_wide_decision.side}")
        if self.current_caught_behind_decision and self.current_caught_behind_decision.result == "OUT":
            decision_texts.append(f"CAUGHT: {self.current_caught_behind_decision.result}")

        # Display decision texts on the frame
        for i, text in enumerate(decision_texts):
            cv2.putText(overlay, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Blend overlay with original frame
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        return frame

    def _draw_dashed_line(self, img, pt1, pt2, color, thickness=1, gap=10):
        """Draw a dashed line from pt1 to pt2."""
        import math
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

    def tracking_loop(self):
        """Main tracking loop running in separate thread."""
        while self.is_tracking and self.cap and self.cap.isOpened():
            success, frame = self.cap.read()

            if not success:
                time.sleep(0.03)  # ~30fps
                continue

            self.current_frame = frame.copy()
            self.current_frame_number += 1

            # Add current frame to replay buffer
            self.replay_buffer.add_frame(frame.copy())

            # Create a BallDetection from the frame (using placeholder logic for now)
            # In real implementation, we'd use the actual detector
            if self.current_frame is not None:
                # For MVP, just use the placeholder detector
                # Create a fake frame triplet for the detector
                frame_triplet = (self.current_frame, self.current_frame, self.current_frame)

                try:
                    detection = self.ball_detector.detect(frame_triplet)
                    self.current_detection = detection
                except:
                    # If detection fails, continue with no detection
                    self.current_detection = None

            # Update tracker
            self.ball_tracker.update(self.current_detection)

            # Detect impacts using the calibrator and config if available
            if self.pitch_calibrator and self.config:
                self.ball_tracker.detect_impact(threshold=30.0, calibrator=self.pitch_calibrator, config=self.config)
            else:
                self.ball_tracker.detect_impact(threshold=30.0)  # Fallback without classification

            # Update segmenter
            state = self.delivery_segmenter.update(self.current_detection)

            # Check if delivery just completed and evaluate wide and caught behind decisions if needed
            if state == "complete":
                # Get current trajectory to save with the delivery in the replay buffer
                pixels_per_meter = self.config.pitch_config.pixels_per_meter if self.config else None
                trajectory = self.ball_tracker.get_trajectory(pixels_per_meter=pixels_per_meter)

                # Associate decisions with the trajectory
                if self.current_lbw_decision:
                    trajectory.lbw_decision = self.current_lbw_decision
                if self.current_wide_decision:
                    trajectory.wide_decision = self.current_wide_decision
                if self.current_caught_behind_decision:
                    trajectory.caught_behind_decision = self.current_caught_behind_decision

                # Store the trajectory in the replay buffer
                self.replay_buffer.set_current_trajectory(trajectory)

                # Save the delivery in the replay buffer
                self.replay_buffer.save_current_delivery()

                # Auto-evaluate wide after delivery completion
                self.evaluate_wide_auto()
                # Auto-evaluate caught behind after delivery completion
                self.evaluate_caught_behind_auto()

            # Get current trajectory
            pixels_per_meter = self.config.pitch_config.pixels_per_meter if self.config else None
            self.current_trajectory = self.ball_tracker.get_trajectory(pixels_per_meter=pixels_per_meter)

            # Add the caught behind decision to the trajectory for visualization if available
            if self.current_caught_behind_decision and self.current_trajectory:
                self.current_trajectory.caught_behind_decision = self.current_caught_behind_decision

            time.sleep(0.03)  # ~30fps

    def start_tracking(self):
        """Start the tracking process."""
        if not self.is_tracking:
            self.is_tracking = True
            self.tracker_thread = threading.Thread(target=self.tracking_loop)
            self.tracker_thread.start()

    def stop_tracking(self):
        """Stop the tracking process."""
        self.is_tracking = False
        if self.tracker_thread:
            self.tracker_thread.join(timeout=1)  # Wait up to 1 second for thread to finish

        if self.cap:
            self.cap.release()

    def run(self):
        """Run the live tracking page."""
        st.title("🏏 Cricket Ball Tracker - Live Tracking")
        st.markdown("### Real-time ball tracking with decision support")

        if not self.load_config():
            st.stop()

        if not self.initialize_camera():
            st.stop()

        # Initialize pitch calibrator
        if self.config:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )

        # Control buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Start Tracking", type="primary"):
                self.start_tracking()

        with col2:
            if st.button("Stop Tracking", type="secondary"):
                self.stop_tracking()

        with col3:
            if st.button("LBW Appeal", type="secondary"):
                if self.current_trajectory and self.current_trajectory.impact_points:
                    # Find pad impact events in the trajectory
                    pad_impacts = [impact for impact in self.current_trajectory.impact_points if impact.impact_type == "pad"]
                    if pad_impacts:
                        latest_pad_impact = pad_impacts[-1]  # Use the most recent pad impact
                        self.evaluate_lbw(latest_pad_impact)
                    else:
                        st.warning("No pad impact detected for LBW appeal.")
                else:
                    st.warning("No trajectory or pad impact available for LBW appeal.")

        # Status info
        tracking_status = "🟢 Active" if self.is_tracking else "🔴 Stopped"
        st.sidebar.markdown(f"**Tracking Status:** {tracking_status}")

        if self.config:
            st.sidebar.markdown(f"**Camera:** {self.config.camera_index}")
            st.sidebar.markdown(f"**Resolution:** {self.config.resolution}")
            st.sidebar.markdown(f"**Batsman:** {self.config.batsman_handedness}")

        # Create video display area
        video_placeholder = st.empty()

        # Create info panels
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Ball Detection")
            detection_status = st.empty()

        with col2:
            st.markdown("### Tracking Info")
            tracking_info = st.empty()

        with col3:
            st.markdown("### Delivery Status")
            delivery_status = st.empty()

        # Main tracking loop for UI updates
        while self.is_tracking:
            if self.current_frame is not None:
                # Draw overlays on current frame
                display_frame = self.current_frame.copy()

                if self.pitch_calibrator:
                    display_frame = self.draw_overlays(
                        display_frame,
                        self.current_detection,
                        self.current_trajectory,
                        self.pitch_calibrator
                    )

                # Convert BGR to RGB for display
                display_frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

                # Display the frame
                video_placeholder.image(
                    display_frame_rgb,
                    caption="Live Tracking",
                    channels="RGB",
                    use_column_width=True
                )

                # Update status panels
                if self.current_detection:
                    detection_status.info(f"🟢 Detected - Confidence: {self.current_detection.confidence:.2f}")
                else:
                    detection_status.warning("🟡 No ball detected")

                if self.current_trajectory:
                    tracking_info.info(f"""
                    **Trajectory:**
                    - Points: {len(self.current_trajectory.detections)}
                    - Speed: {self.current_trajectory.speed_kmh or 'N/A'} px/s
                    - Bounce: {'Yes' if self.current_trajectory.bounce_point else 'No'}
                    """)

                delivery_state = self.delivery_segmenter.update(self.current_detection)
                delivery_status.info(f"State: {delivery_state}")

                # Auto-evaluate wide and caught behind decisions when delivery is completed
                if delivery_state == "complete" and self.current_trajectory:
                    self.evaluate_wide_auto()
                    self.evaluate_caught_behind_auto()

                    # Also save the trajectory with decisions to replay buffer
                    if self.current_lbw_decision:
                        self.current_trajectory.lbw_decision = self.current_lbw_decision
                    if self.current_wide_decision:
                        self.current_trajectory.wide_decision = self.current_wide_decision
                    if self.current_caught_behind_decision:
                        self.current_trajectory.caught_behind_decision = self.current_caught_behind_decision

            time.sleep(0.1)  # Update UI at ~10fps for better responsiveness

        # When tracking stops, show final status
        if not self.is_tracking:
            st.info("Tracking stopped. Start again to continue.")

    def evaluate_lbw(self, pad_impact):
        """Evaluate LBW decision based on pad impact."""
        if not self.current_trajectory:
            st.error("No trajectory available for LBW evaluation.")
            return

        if not self.config:
            st.error("No configuration loaded for LBW evaluation.")
            return

        # Initialize LBW engine if not already created
        if not self.pitch_calibrator:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )

        if not self.lbw_engine:
            self.lbw_engine = LBWEngine(
                calibrator=self.pitch_calibrator,
                stump_tolerance=self.config.stump_width_tolerance,
                strictness=self.config.lbw_strictness
            )
        else:
            # Update the engine with current configuration
            self.lbw_engine.stump_tolerance = self.config.stump_width_tolerance
            self.lbw_engine.strictness = self.config.lbw_strictness

        try:
            # Evaluate LBW decision
            lbw_decision = self.lbw_engine.evaluate(
                self.current_trajectory,
                pad_impact,
                self.config.batsman_handedness
            )

            # Store the decision
            self.current_lbw_decision = lbw_decision

            # Display the decision in Streamlit
            if lbw_decision.result == "OUT":
                st.success(f"LBW Decision: OUT - {lbw_decision.reason}")
            else:
                st.info(f"LBW Decision: NOT OUT - {lbw_decision.reason}")

            st.write(f"Confidence: {lbw_decision.confidence:.2f}")
            st.write(f"Pitching Zone: {lbw_decision.pitching_zone}")
            st.write(f"Impact Zone: {lbw_decision.impact_zone}")
            st.write(f"Would Hit Stumps: {lbw_decision.projected_hitting_stumps}")

            # Update the trajectory with the projected path
            # This will be used by the draw_overlays function to show the projection
            self.current_trajectory.projected_path = lbw_decision.projected_path

        except Exception as e:
            st.error(f"Error evaluating LBW: {str(e)}")

    def evaluate_wide_auto(self):
        """Auto-evaluate wide decision after delivery completion."""
        if not self.current_trajectory:
            return

        if not self.config:
            return

        # Initialize Wide engine if not already created
        if not self.pitch_calibrator:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )

        if not self.wide_engine:
            self.wide_engine = WideEngine(
                calibrator=self.pitch_calibrator,
                wide_config=self.config.wide_config
            )
        else:
            # Update the engine with current configuration
            self.wide_engine.wide_config = self.config.wide_config

        try:
            # Evaluate wide decision
            wide_decision = self.wide_engine.evaluate(self.current_trajectory)

            # Store the decision
            self.current_wide_decision = wide_decision

            # Display the wide decision
            if wide_decision.result == "WIDE":
                st.warning(f"WIDE DECISION: {wide_decision.side.upper()} wide - {wide_decision.ball_position_at_crease_px}")
            else:
                # Optionally display NOT WIDE decisions too, or just log them
                pass

        except Exception as e:
            # Could log to a debug area if needed
            pass

    def evaluate_caught_behind_auto(self):
        """Auto-evaluate caught behind decision after delivery completion."""
        if not self.current_trajectory:
            return

        if not self.config:
            return

        # Initialize Caught Behind engine if not already created
        if not self.pitch_calibrator:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )

        if not self.caught_behind_engine:
            self.caught_behind_engine = CaughtBehindEngine(
                calibrator=self.pitch_calibrator,
                edge_sensitivity=self.config.edge_sensitivity
            )
        else:
            # Update the engine with current configuration
            self.caught_behind_engine.edge_sensitivity = self.config.edge_sensitivity

        try:
            # Evaluate caught behind decision
            caught_behind_decision = self.caught_behind_engine.evaluate(self.current_trajectory, self.config)

            # Store the decision
            self.current_caught_behind_decision = caught_behind_decision

            # Display the caught behind decision
            if caught_behind_decision.result == "OUT":
                st.error(f"CAUGHT BEHIND DECISION: OUT - {caught_behind_decision.reason}")
                st.write(f"Confidence: {caught_behind_decision.confidence:.2f}")
            else:
                # Optionally display NOT OUT decisions too, or just log them
                pass

        except Exception as e:
            # Could log to a debug area if needed
            pass


def main():
    app = LiveTrackingApp()
    app.run()


if __name__ == "__main__":
    main()