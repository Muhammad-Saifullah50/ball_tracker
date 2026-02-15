"""
Replay page for Cricket Ball Tracker
Provides instant replay functionality with slow motion and frame-by-frame controls
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import time
from typing import Optional, Deque
from collections import deque
import threading

# Add the project root directory to the Python path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.replay.replay_buffer import ReplayBuffer
from src.replay.replay_renderer import ReplayRenderer
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.session_config import SessionConfig


class ReplayApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[SessionConfig] = None
        self.replay_buffer = ReplayBuffer()
        self.replay_renderer = None
        self.pitch_calibrator = None

        # Replay state
        self.current_replay_idx = 0
        self.current_frame_idx = 0
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 is normal speed
        self.replay_thread = None

        # Frame storage
        self.replay_frames = []
        self.replay_trajectory = None

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

    def load_replay_data(self):
        """Load replay data from the buffer."""
        # Get the replay buffer from the main tracking app session state if available
        if 'replay_buffer' in st.session_state:
            # Use the replay buffer from the main app
            self.replay_buffer = st.session_state['replay_buffer']

        # Initialize renderer with pitch calibrator
        if self.config:
            self.pitch_calibrator = PitchCalibrator(
                self.config.pitch_config,
                self.config.batting_stumps
            )
            self.replay_renderer = ReplayRenderer(self.pitch_calibrator)

    def get_available_deliveries(self):
        """Get the count of available deliveries in the buffer."""
        return self.replay_buffer.get_deliveries_count()

    def select_delivery(self, delivery_idx: int):
        """Select a delivery to replay."""
        delivery_data = self.replay_buffer.get_delivery(delivery_idx)
        if delivery_data:
            frames, trajectory = delivery_data
            self.replay_frames = list(frames)  # Convert deque to list
            self.replay_trajectory = trajectory
            self.current_frame_idx = 0
            return True
        return False

    def play_replay(self):
        """Start playing the replay."""
        self.is_playing = True

    def pause_replay(self):
        """Pause the replay."""
        self.is_playing = False

    def step_forward(self):
        """Step forward one frame."""
        if self.current_frame_idx < len(self.replay_frames) - 1:
            self.current_frame_idx += 1

    def step_backward(self):
        """Step backward one frame."""
        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1

    def reset_replay(self):
        """Reset to the beginning of the current replay."""
        self.current_frame_idx = 0
        self.is_playing = False

    def set_playback_speed(self, speed: float):
        """Set the playback speed."""
        self.playback_speed = speed

    def run(self):
        """Run the replay page."""
        st.title("🎬 Cricket Ball Tracker - Instant Replay")
        st.markdown("### Review deliveries with slow motion and frame-by-frame controls")

        if not self.load_config():
            st.stop()

        # Initialize or update replay data
        self.load_replay_data()

        # Show available deliveries
        delivery_count = self.get_available_deliveries()
        st.sidebar.markdown(f"**Available Deliveries:** {delivery_count}")

        # Delivery selection
        if delivery_count > 0:
            delivery_options = [f"Delivery {i+1}" for i in range(delivery_count)]
            selected = st.sidebar.selectbox("Select Delivery", delivery_options)
            selected_idx = delivery_options.index(selected)

            if 'current_delivery_idx' not in st.session_state or st.session_state.current_delivery_idx != selected_idx:
                st.session_state.current_delivery_idx = selected_idx
                success = self.select_delivery(selected_idx)
                if success:
                    st.success(f"Loaded delivery {selected_idx + 1}")
        else:
            st.info("No deliveries available for replay. Track some deliveries first.")
            st.stop()

        # Replay controls
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            if st.button("⏮️", key="start"):
                self.reset_replay()

        with col2:
            if st.button("⏪", key="prev_frame"):
                self.step_backward()

        with col3:
            if not self.is_playing:
                if st.button("▶️", key="play"):
                    self.play_replay()
            else:
                if st.button("⏸️", key="pause"):
                    self.pause_replay()

        with col4:
            if st.button("⏩", key="next_frame"):
                self.step_forward()

        with col5:
            speed = st.selectbox("Speed", ["1x", "0.5x", "0.25x", "0.1x"], index=0, key="speed_select")
            speed_map = {"1x": 1.0, "0.5x": 0.5, "0.25x": 0.25, "0.1x": 0.1}
            if self.playback_speed != speed_map[speed]:
                self.set_playback_speed(speed_map[speed])

        with col6:
            if st.button("⏹️", key="stop"):
                self.reset_replay()

        # Show replay frame
        if self.replay_frames and 0 <= self.current_frame_idx < len(self.replay_frames):
            current_frame = self.replay_frames[self.current_frame_idx].copy()

            # Render the current frame with overlays
            if self.replay_renderer:
                rendered_frame = self.replay_renderer.render_frame(
                    current_frame,
                    self.replay_trajectory,
                    self.current_frame_idx,
                    len(self.replay_frames)
                )
            else:
                rendered_frame = current_frame

            # Convert BGR to RGB for display
            rendered_frame_rgb = cv2.cvtColor(rendered_frame, cv2.COLOR_BGR2RGB)

            # Display the frame
            st.image(
                rendered_frame_rgb,
                caption=f"Delivery {st.session_state.get('current_delivery_idx', 0) + 1}, Frame {self.current_frame_idx + 1}/{len(self.replay_frames)}",
                channels="RGB",
                use_column_width=True
            )

            # Progress bar
            progress = (self.current_frame_idx + 1) / len(self.replay_frames)
            st.progress(progress)

            # Frame slider
            new_frame_idx = st.slider(
                "Frame",
                min_value=0,
                max_value=len(self.replay_frames) - 1,
                value=self.current_frame_idx,
                key="frame_slider"
            )
            if new_frame_idx != self.current_frame_idx:
                self.current_frame_idx = new_frame_idx

        # Auto-play functionality
        if self.is_playing and self.replay_frames:
            # Calculate delay based on playback speed (normal speed is 30fps)
            delay = 1.0 / (30.0 * self.playback_speed) if self.playback_speed > 0 else 0.1

            # Update frame index
            if self.current_frame_idx < len(self.replay_frames) - 1:
                self.current_frame_idx += 1
            else:
                self.is_playing = False  # Stop at the end

            time.sleep(delay)
            st.rerun()  # Refresh the page


def main():
    app = ReplayApp()
    app.run()


if __name__ == "__main__":
    main()