"""
Live Tracking page for Cricket Ball Tracker
Displays real-time ball tracking with overlays
"""
import streamlit as st
import numpy as np
from PIL import Image
import time
from typing import Optional
import threading
from collections import deque
import sys
from pathlib import Path

# Add the project root directory to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

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

# Import streamlit-webrtc components
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import av


class BallTrackingProcessor(VideoProcessorBase):
    def __init__(self, detector, tracker, segmenter, config):
        self.ball_detector = detector
        self.ball_tracker = tracker
        self.delivery_segmenter = segmenter
        self.config = config
        self.current_frame = None
        self.current_detection = None
        self.current_trajectory = None

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # Convert av.VideoFrame to numpy array
        img = frame.to_ndarray(format="bgr24")

        # Store the frame for access by the UI
        self.current_frame = img.copy()

        # Perform ball detection
        try:
            # Create a triplet of frames for the detector (using same frame for now)
            frame_triplet = (img, img, img)
            detection = self.ball_detector.detect(frame_triplet)
            self.current_detection = detection
        except:
            # If detection fails, continue with no detection
            self.current_detection = None

        # Update tracker
        self.ball_tracker.update(self.current_detection)

        # Detect impacts if config is available
        if self.config:
            from src.calibration.pitch_calibrator import PitchCalibrator
            calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )
            self.ball_tracker.detect_impact(threshold=30.0, calibrator=calibrator, config=self.config)
        else:
            self.ball_tracker.detect_impact(threshold=30.0)  # Fallback without classification

        # Update segmenter
        self.delivery_segmenter.update(self.current_detection)

        # Get trajectory
        pixels_per_meter = self.config.pitch_config.pixels_per_meter if self.config else None
        self.current_trajectory = self.ball_tracker.get_trajectory(pixels_per_meter=pixels_per_meter)

        # Return the original frame (we can also return a processed frame with overlays if needed)
        # Returning the original frame for display in the UI
        return img


class LiveTrackingApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[SessionConfig] = None
        self.is_tracking = False
        self.tracker_thread = None  # Initialize to None to prevent AttributeError
        self.webrtc_ctx = None  # We'll store the WebRTC context here

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

        # For WebRTC compatibility, we don't initialize OpenCV camera
        # Instead, we'll use streamlit-webrtc component in the UI
        return True

    def draw_overlays(self, frame, detection, trajectory, calibrator):
        """Draw tracking overlays on frame using PIL for mobile compatibility."""
        from PIL import Image, ImageDraw, ImageFont
        import math

        # Convert numpy array to PIL Image if it's not already
        if not isinstance(frame, Image.Image):
            # Make sure frame is in correct format
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            pil_image = Image.fromarray(frame)
        else:
            pil_image = frame.copy()

        draw = ImageDraw.Draw(pil_image, "RGBA")

        # Draw detection point if available
        if detection:
            x, y = int(detection.x), int(detection.y)
            # Draw circle: (left, top, right, bottom)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=(0, 255, 0), outline=(0, 255, 0), width=2)
            # Text: (x, y) position
            draw.text((x + 10, y - 15), f"Ball: {detection.confidence:.2f}", fill=(0, 255, 0))

        # Draw trajectory if available
        if trajectory and len(trajectory.detections) > 1:
            points = [(int(d.x), int(d.y)) for d in trajectory.detections]
            if len(points) > 1:
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill=(255, 0, 0), width=2)

        # Draw bounce point if detected
        if trajectory and trajectory.bounce_point:
            bp = trajectory.bounce_point
            x, y = int(bp.x), int(bp.y)
            draw.ellipse([x-10, y-10, x+10, y+10], outline=(0, 255, 255), width=2)
            draw.text((x + 10, y - 15), "Bounce", fill=(0, 255, 255))

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
                pos = (int(impact.position_px[0]), int(impact.position_px[1]))

                # Draw different shapes based on impact type
                if impact.impact_type == "stumps":
                    # Draw a rectangle for stumps hit
                    draw.rectangle([pos[0]-8, pos[1]-8, pos[0]+8, pos[1]+8], outline=color, width=2)
                elif impact.impact_type == "bat":
                    # Draw a circle for bat hit
                    draw.ellipse([pos[0]-8, pos[1]-8, pos[0]+8, pos[1]+8], outline=color, width=2)
                elif impact.impact_type == "pad":
                    # Draw a triangle for pad hit
                    points = [(pos[0], pos[1]-8), (pos[0]-7, pos[1]+5), (pos[0]+7, pos[1]+5)]
                    draw.polygon(points, outline=color, width=2)
                else:
                    # Default to circle for other impacts
                    draw.ellipse([pos[0]-6, pos[1]-6, pos[0]+6, pos[1]+6], outline=color, width=2)

                draw.text((pos[0] + 10, pos[1] - 15), impact.impact_type, fill=color)

        # Draw calibrated elements (stumps, wide lines)
        if calibrator and self.config:
            # Draw stumps
            off_stump = self.config.batting_stumps.off_stump_px
            middle_stump = self.config.batting_stumps.middle_stump_px
            leg_stump = self.config.batting_stumps.leg_stump_px

            # Draw stumps as circles
            draw.ellipse([off_stump[0]-5, off_stump[1]-5, off_stump[0]+5, off_stump[1]+5],
                        fill=(0, 0, 255), outline=(0, 0, 255), width=2)
            draw.ellipse([middle_stump[0]-5, middle_stump[1]-5, middle_stump[0]+5, middle_stump[1]+5],
                        fill=(0, 0, 255), outline=(0, 0, 255), width=2)
            draw.ellipse([leg_stump[0]-5, leg_stump[1]-5, leg_stump[0]+5, leg_stump[1]+5],
                        fill=(0, 0, 255), outline=(0, 0, 255), width=2)

            draw.text((off_stump[0] + 10, off_stump[1] - 10), "Off", fill=(0, 0, 255))
            draw.text((middle_stump[0] + 10, middle_stump[1] - 10), "Mid", fill=(0, 0, 255))
            draw.text((leg_stump[0] + 10, leg_stump[1] - 10), "Leg", fill=(0, 0, 255))

            # Draw wide lines
            try:
                wide_lines = calibrator.get_wide_lines(self.config.wide_config)
                off_line, leg_line = wide_lines

                draw.line([off_line[0], off_line[1]], fill=(255, 255, 0), width=2)
                draw.line([leg_line[0], leg_line[1]], fill=(255, 255, 0), width=2)
            except:
                pass  # Skip if calibrator not ready

        # Draw LBW projected path if available in trajectory
        if trajectory and hasattr(trajectory, 'projected_path') and trajectory.projected_path and len(trajectory.projected_path) >= 2:
            path = trajectory.projected_path
            for i in range(len(path) - 1):
                draw.line([path[i], path[i+1]], fill=(255, 165, 0), width=2)  # Orange line for projected path
                # Add arrowheads to indicate direction
                if i % 5 == 0:  # Add arrowheads every 5 segments to avoid clutter
                    mid_point = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                    next_point = path[i+1]
                    # Draw a small line to indicate direction
                    draw.line([mid_point, next_point], fill=(255, 165, 0), width=2)

        # Draw caught behind visual evidence if available
        if trajectory and trajectory.caught_behind_decision:
            caught_behind = trajectory.caught_behind_decision
            if caught_behind.result == "OUT":
                # Draw a red circle around the bat impact if caught behind is OUT
                for impact in trajectory.impact_points:
                    if impact.impact_type == "bat":
                        pos = impact.position_px
                        draw.ellipse([pos[0]-15, pos[1]-15, pos[0]+15, pos[1]+15], outline=(0, 0, 255), width=3)  # Red circle for bat hit
                        draw.text((pos[0] + 20, pos[1] - 25), "EDGE!", fill=(0, 0, 255))

                # Draw a dashed line from bat to wall if ball hits wall
                wall_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "wall"]
                if wall_impacts:
                    bat_impacts = [imp for imp in trajectory.impact_points if imp.impact_type == "bat"]
                    if bat_impacts:
                        bat_pos = bat_impacts[0].position_px
                        wall_pos = wall_impacts[0].position_px
                        # Draw a dashed line from bat to wall to indicate direct hit
                        self._draw_dashed_line_pil(draw, bat_pos, wall_pos, (0, 165, 255), 2)  # Orange for caught behind

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
            draw.text((10, 30 + i * 30), text, fill=(0, 0, 255))

        # Convert back to numpy array for display
        return np.array(pil_image)

    def _draw_dashed_line_pil(self, draw, pt1, pt2, color, thickness=1, gap=10):
        """Draw a dashed line from pt1 to pt2 using PIL."""
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
            draw.line([start, end], fill=color, width=thickness)

    def tracking_loop(self):
        """Main tracking loop running in separate thread."""
        # In mobile mode, this function is not used directly as we handle frames via Streamlit UI
        # This is kept for potential advanced implementations that might use background processing
        # For now, frame processing happens in the main UI loop
        pass

    def start_tracking(self):
        """Start the tracking process."""
        self.is_tracking = True
        # In WebRTC mode, we don't need a background thread
        # The tracking happens in the WebRTC video processor
        # Only initialize thread if needed for other processes
        pass

    def stop_tracking(self):
        """Stop the tracking process."""
        self.is_tracking = False
        # Safely handle thread if it exists
        if hasattr(self, 'tracker_thread') and self.tracker_thread:
            try:
                if self.tracker_thread.is_alive():
                    self.tracker_thread.join(timeout=1)  # Wait up to 1 second for thread to finish
            except AttributeError:
                # Thread might not have started or been properly initialized
                pass
        # Reset thread reference
        self.tracker_thread = None

    def run(self):
        """Run the live tracking page."""
        st.title("🏏 Cricket Ball Tracker - Live Tracking")
        st.markdown("### Real-time ball tracking with decision support")

        if not self.load_config():
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
            if st.button("Start Tracking", type="primary", key="start_tracking_mobile"):
                self.start_tracking()

        with col2:
            if st.button("Stop Tracking", type="secondary", key="stop_tracking_mobile"):
                self.stop_tracking()

        with col3:
            if st.button("LBW Appeal", type="secondary", key="lbw_appeal_mobile"):
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
            st.sidebar.markdown(f"**Camera:** Mobile Camera")
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

        # WebRTC camera input for real-time tracking
        if self.is_tracking:
            st.subheader("Camera Input")
            st.info("Point your camera at the cricket game to start tracking")

            # Troubleshooting info for camera issues
            with st.expander(" troubleshoot camera issues"):
                st.markdown("""
                ### Troubleshooting Camera Issues:

                1. **Browser Permissions:**
                   - Check if camera access is blocked (look for camera icon in address bar)
                   - Click on the icon and select "Always allow" for camera
                   - Refresh the page after granting permissions

                2. **Browser Compatibility:**
                   - Use Chrome, Firefox, or Safari (Edge sometimes has issues)
                   - Make sure your browser is up-to-date
                   - Ensure you are using a secure connection (https://)

                3. **Mobile Users:**
                   - Use Chrome (Android) or Safari (iOS)
                   - Tap on the gray box and click the "Start" button inside the video player
                   - Using rear camera ("environment" facing mode)

                4. **WebRTC Connection:**
                   - If you see a gray box with a start button, click it to begin streaming
                   - This is required for security reasons (user must explicitly allow camera access)

                5. **Network:**
                   - If camera doesn't work, you may be behind a restrictive firewall
                   - Try using a different network if possible
                """)

            st.info("💡 Make sure to allow camera permissions when prompted. On mobile, use Chrome or Safari for best results.")
            # Use streamlit-webrtc for continuous camera access with WebRTC
            # Updated to SENDRECV mode to properly get camera feed from browser
            try:
                self.webrtc_ctx = webrtc_streamer(
                    key="ball-tracking",
                    mode=WebRtcMode.SENDRECV,  # Changed from RECVONLY to SENDRECV - browser sends video to Python
                    rtc_configuration=RTCConfiguration({
                        "iceServers": [
                            {"urls": ["stun:stun.l.google.com:19302"]},
                            {"urls": ["stun:stun.cloudflare.com:3478"]},
                            {"urls": ["stun:stun.stunprotocol.org:3478"]},  # Additional STUN server
                            {"urls": ["stun:stun.freeswitch.org:3478"]}      # Backup STUN server
                        ],
                        "iceCandidatePoolSize": 10
                    }),
                    video_processor_factory=lambda: BallTrackingProcessor(
                        self.ball_detector,
                        self.ball_tracker,
                        self.delivery_segmenter,
                        self.config
                    ),
                    media_stream_constraints={
                        "video": {
                            "facingMode": "environment" if self.config and self.config.camera_index == 1 else "user",  # Use rear camera on mobile (index 1), front on desktop
                            "width": {"ideal": 1280},
                            "height": {"ideal": 720},
                            # Add frame rate constraint for smooth video
                            "frameRate": {"ideal": 30}
                        },
                        "audio": False  # Not needed for ball tracking
                    },
                    async_processing=True,
                    video_html_attrs={
                        "style": {"width": "100%", "maxWidth": "600px", "height": "auto", "objectFit": "cover"},
                        "controls": False,
                        "autoPlay": True,
                        "playsInline": True,
                        "muted": True
                    }
                    # Removed desired_playing_state to let user explicitly start the stream
                )

                if self.webrtc_ctx:
                    # Check if the stream is active with better error handling
                    if hasattr(self.webrtc_ctx, 'state') and self.webrtc_ctx.state:
                        if hasattr(self.webrtc_ctx.state, 'playing') and self.webrtc_ctx.state.playing:
                            st.success("✅ Camera connected! Ball tracking is active.")
                            # Additional message for gray box issue
                            st.info("💡 If you see a gray box instead of video, click/tap on it to activate the camera feed.")
                        elif hasattr(self.webrtc_ctx, 'video_receiver') and self.webrtc_ctx.video_receiver:
                            st.success("✅ Camera stream established! Ball tracking is active.")
                        else:
                            # Check if there are connection issues
                            if hasattr(self.webrtc_ctx.state, 'signalingState'):
                                if self.webrtc_ctx.state.signalingState == "closed":
                                    st.error("❌ Camera connection closed. Network issue or browser incompatible.")
                                elif self.webrtc_ctx.state.signalingState == "have-remote-offer":
                                    st.info("📡 Negotiating camera connection...")
                            else:
                                st.warning("⚠️ Camera connected but video stream not playing. Try clicking on the gray box above.")
                                # Check for error states
                                if hasattr(self.webrtc_ctx.state, 'error'):
                                    st.error(f"Camera Error: {self.webrtc_ctx.state.error}")
                    else:
                        # Provide more detailed troubleshooting information
                        st.info("📷 Waiting for camera connection... Make sure to allow camera permissions when prompted.")
                        st.warning("If you've denied permissions, please refresh the page and allow camera access when prompted.")

                        # Provide connection troubleshooting tips
                        with st.expander("Connection Troubleshooting"):
                            st.markdown("""
                            **If camera doesn't work:**

                            1. **Check firewall settings** - Some firewalls block WebRTC connections
                            2. **Try a different browser** - Chrome, Firefox, Safari work best
                            3. **Ensure HTTPS** - Browsers require secure context for camera access
                            4. **Check for VPN** - VPNs can interfere with WebRTC
                            5. **Click Start button** - If you see a gray box, click its internal start button
                            6. **Mobile networks** - Some mobile carriers restrict WebRTC
                            """)
                else:
                    st.warning("⚠️ Camera streamer could not be initialized. Check browser compatibility.")
                    st.info("Try using Chrome, Firefox, or Safari for the best WebRTC support.")
            except Exception as e:
                st.error(f"Error initializing camera: {str(e)}")
                st.info("Please ensure your browser supports WebRTC and camera access is permitted.")
                # Provide more specific error messages
                error_msg = str(e).lower()
                if "permission" in error_msg:
                    st.warning("⚠️ Camera permission was denied. Refresh the page and allow camera access.")
                elif "device" in error_msg or "camera" in error_msg:
                    st.error("❌ No camera device found. Please check if a camera is connected to your device.")
                else:
                    st.info("Try using a different browser or check your network connection.")

            # Add a refresh button for mobile users who might have denied permissions
            st.button("Refresh Camera Permissions")

            if self.webrtc_ctx and self.webrtc_ctx.video_processor:
                # Check if the video processor has a current frame
                if hasattr(self.webrtc_ctx.video_processor, 'current_frame') and self.webrtc_ctx.video_processor.current_frame is not None:
                    # Get the frame from the WebRTC processor
                    frame = self.webrtc_ctx.video_processor.current_frame
                    self.current_frame = frame.copy()
                    self.current_frame_number += 1

                    # Add current frame to replay buffer
                    self.replay_buffer.add_frame(frame.copy())

                    # Update our local tracking variables from the processor
                    if hasattr(self.webrtc_ctx.video_processor, 'current_detection'):
                        self.current_detection = self.webrtc_ctx.video_processor.current_detection
                    if hasattr(self.webrtc_ctx.video_processor, 'current_trajectory'):
                        self.current_trajectory = self.webrtc_ctx.video_processor.current_trajectory

                    # Draw overlays on current frame
                    display_frame = frame.copy()

                    if self.pitch_calibrator:
                        display_frame = self.draw_overlays(
                            display_frame,
                            self.current_detection,
                            self.current_trajectory,
                            self.pitch_calibrator
                        )

                    # WebRTC frames are in BGR format, but PIL expects RGB
                    # The draw_overlays function returns an RGB array, so no conversion needed
                    # But let's make sure the format is correct for Streamlit
                    if display_frame.dtype != np.uint8:
                        display_frame = display_frame.astype(np.uint8)

                    # Ensure the image is in RGB format for Streamlit
                    if len(display_frame.shape) == 3 and display_frame.shape[2] == 3:
                        # Check if it might be BGR by checking typical color distributions
                        # If red channel has very high values compared to others, it might be BGR
                        # Since draw_overlays uses PIL and returns RGB, we assume it's RGB
                        display_frame_rgb = display_frame
                    elif len(display_frame.shape) == 2:  # Grayscale
                        # Convert grayscale to RGB
                        display_frame_rgb = np.stack([display_frame] * 3, axis=-1)
                    else:
                        display_frame_rgb = display_frame

                    # Display the frame with overlays
                    video_placeholder.image(
                        display_frame_rgb,
                        caption="Live Tracking",
                        channels="RGB",  # Streamlit expects RGB format
                        use_column_width=True
                    )
                else:
                    # Show a more descriptive message when frame is not available yet
                    video_placeholder.info("📡 Waiting for camera stream... Video processor active, frame should appear shortly.")
                    st.info("The camera is connected but waiting for the first frame. This may take a few seconds.")

                    # Update status panels when frame is not available yet
                    detection_status.info("🟡 Waiting for camera feed...")
                    tracking_info.info("No trajectory data")
                    delivery_status.info("State: idle")
            else:
                # Show camera input area but no video stream yet
                video_placeholder.info("📷 Waiting for camera stream... Please allow camera access when prompted.")
                st.info("Please ensure camera permissions are granted to the browser. Look for permission prompts in your browser.")

                # Update status panels when no video processor is available yet
                detection_status.info("🟡 Waiting for camera feed...")
                tracking_info.info("No trajectory data")
                delivery_status.info("State: idle")
        else:
            st.info("Tracking is stopped. Click 'Start Tracking' to begin.")
            video_placeholder.info("Camera feed will appear here when tracking is active")
            st.warning("Camera access will be requested when you start tracking.")

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