"""
Live Tracking page for Cricket Ball Tracker
Displays real-time ball tracking with overlays
"""
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import time
from typing import Optional
import threading
from collections import deque
import sys
from pathlib import Path

# --- GLOBAL SCOPE ---
# Global lock for thread-safe operations
global_lock = threading.Lock()
track_container = {
    "detection": None,
    "trajectory": None,
    "frame": None,
    "current_frame_number": 0,
    "frame_skip_counter": 0  # For frame skipping on mobile
}

# Project Path Setup
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Component Imports
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
from src.replay.replay_buffer import ReplayBuffer

# WebRTC Imports
from streamlit_webrtc import webrtc_streamer, RTCConfiguration, WebRtcMode
import av

# --- WEBSTRTC CALLBACK (OUTSIDE CLASS) ---
def video_frame_callback(frame: av.VideoFrame, detector, tracker, segmenter, config):
    """
    Processes video frames in the background WebRTC thread.
    Mobile optimization: Process every 2nd frame only.
    """
    img = frame.to_ndarray(format="bgr24")

    # Frame skipping for mobile performance - process every 2nd frame
    with global_lock:
        track_container["frame_skip_counter"] += 1
        should_process = track_container["frame_skip_counter"] % 2 == 0

    if should_process:
        # Detection Logic
        try:
            # Triplet for movement detection logic
            frame_triplet = (img, img, img)
            detection = detector.detect(frame_triplet)
        except Exception:
            detection = None

        # Tracker Updates
        tracker.update(detection)

        # Impact Detection
        if config:
            calibrator = PitchCalibrator(config.pitch_config, config.batting_stumps)
            tracker.detect_impact(threshold=30.0, calibrator=calibrator, config=config)
        else:
            tracker.detect_impact(threshold=30.0)

        # Segmenter Updates
        segmenter.update(detection)

        # Trajectory Calculation
        pixels_per_meter = config.pitch_config.pixels_per_meter if config else None
        trajectory = tracker.get_trajectory(pixels_per_meter=pixels_per_meter)

        # Thread-safe update to global container
        with global_lock:
            track_container["detection"] = detection
            track_container["trajectory"] = trajectory
            track_container["current_frame_number"] += 1

    # Always update frame for display (even if not processing)
    with global_lock:
        track_container["frame"] = img.copy()

    return frame

# --- MAIN APP CLASS ---
class LiveTrackingApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[SessionConfig] = None
        self.is_tracking = False
        self.webrtc_ctx = None

        # Components
        self.ball_detector = BallDetector()
        self.ball_tracker = BallTracker(fps=10.0)  # Match mobile frame rate
        self.delivery_segmenter = DeliverySegmenter()
        self.pitch_calibrator = None
        self.lbw_engine = None
        self.wide_engine = None
        self.caught_behind_engine = None
        self.replay_buffer = ReplayBuffer()

        # States
        self.current_frame = None
        self.current_detection = None
        self.current_trajectory = None
        self.current_frame_number = 0
        self.current_lbw_decision = None
        self.current_wide_decision = None
        self.current_caught_behind_decision = None

    def load_config(self):
        """Loads session config from session_state or file."""
        if 'session_config' in st.session_state:
            self.config = st.session_state.session_config
            return True
        try:
            self.config = self.config_manager.load_session_config()
            st.session_state.session_config = self.config
            return True
        except Exception:
            st.error("No configuration found. Please complete setup first.")
            return False

    def draw_overlays(self, frame, detection, trajectory, calibrator):
        """Draws visual feedback on frames using PIL - lightweight for mobile."""
        if not isinstance(frame, Image.Image):
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            pil_image = Image.fromarray(frame)
        else:
            pil_image = frame.copy()

        draw = ImageDraw.Draw(pil_image, "RGBA")

        # Ball Detection Overlay - simplified for mobile
        if detection:
            x, y = int(detection.x), int(detection.y)
            draw.ellipse([x-6, y-6, x+6, y+6], fill=(0, 255, 0, 180), outline=(0, 255, 0), width=2)

        # Trajectory Overlay - limit points for mobile performance
        if trajectory and len(trajectory.detections) > 1:
            # Only draw last 15 points to reduce rendering load
            recent_detections = trajectory.detections[-15:]
            points = [(int(d.x), int(d.y)) for d in recent_detections]
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=(255, 0, 0, 200), width=2)

        return np.array(pil_image)

    def evaluate_lbw(self, pad_impact):
        """Applies LBW logic based on a specific impact."""
        if not self.current_trajectory or not self.config:
            st.error("Missing data for LBW check.")
            return

        if not self.lbw_engine:
            self.lbw_engine = LBWEngine(self.pitch_calibrator)

        decision = self.lbw_engine.evaluate(
            self.current_trajectory, 
            pad_impact, 
            self.config.batsman_handedness
        )
        self.current_lbw_decision = decision
        st.success(f"LBW: {decision.result} - {decision.reason}")

    def run(self):
        """Main UI logic."""
        st.title("🏏 Cricket Ball Tracker - Live Tracking")

        # Mobile performance notice
        st.info("📱 Ultra-low mode for Galaxy J3 Pro (320x240 @ 10fps, processing every 2nd frame)")

        if not self.load_config():
            st.stop()

        if self.config:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )

        # Controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Start Tracking", type="primary"):
                self.is_tracking = True
        with col2:
            if st.button("Stop Tracking"):
                self.is_tracking = False
        with col3:
            if st.button("LBW Appeal"):
                if self.current_trajectory and self.current_trajectory.impact_points:
                    pad_impacts = [i for i in self.current_trajectory.impact_points if i.impact_type == "pad"]
                    if pad_impacts:
                        self.evaluate_lbw(pad_impacts[-1])

        # Placeholder for the processed video
        video_placeholder = st.empty()

        # WebRTC Component - Optimized for low-end mobile (Galaxy J3 Pro 2016)
        self.webrtc_ctx = webrtc_streamer(
            key="ball-tracking",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration({
                "iceServers": [
                    {"urls": ["stun:stun.l.google.com:19302"]},
                    {"urls": ["stun:stun.cloudflare.com:3478"]},
                    {"urls": ["stun:stun.stunprotocol.org:3478"]},
                    {"urls": ["stun:stun.services.mozilla.com:3478"]}
                ],
                "iceCandidatePoolSize": 10,
                "iceTransportPolicy": "all"
            }),
            video_frame_callback=lambda frame: video_frame_callback(
                frame,
                self.ball_detector,
                self.ball_tracker,
                self.delivery_segmenter,
                self.config
            ),
            media_stream_constraints={
                "video": {
                    "facingMode": "environment",
                    "width": {"ideal": 320, "min": 240, "max": 480},
                    "height": {"ideal": 240, "min": 180, "max": 360},
                    "frameRate": {"ideal": 10, "min": 8, "max": 15},
                    "aspectRatio": {"ideal": 1.333}
                },
                "audio": False
            },
            async_processing=True,
            video_html_attrs={
                "style": {"width": "100%", "maxWidth": "480px", "height": "auto"},
                "controls": False,
                "autoPlay": True,
                "playsInline": True,
                "muted": True
            }
        )

        # UI Loop - Pull data from the WebRTC thread
        if self.webrtc_ctx and self.webrtc_ctx.state.playing:
            # Thread-safe read
            with global_lock:
                self.current_frame = track_container["frame"]
                self.current_detection = track_container["detection"]
                self.current_trajectory = track_container["trajectory"]

            if self.current_frame is not None:
                display_frame = self.current_frame.copy()

                # Apply Overlays
                if self.is_tracking and self.pitch_calibrator:
                    display_frame = self.draw_overlays(
                        display_frame,
                        self.current_detection,
                        self.current_trajectory,
                        self.pitch_calibrator
                    )

                # Convert BGR (OpenCV) to RGB (Streamlit)
                display_frame_rgb = display_frame[:, :, ::-1]

                video_placeholder.image(
                    display_frame_rgb,
                    caption="Live Feed (Mobile Optimized)",
                    channels="RGB",
                    use_column_width=True
                )

# --- ENTRY POINT ---
def main():
    app = LiveTrackingApp()
    app.run()

if __name__ == "__main__":
    main()