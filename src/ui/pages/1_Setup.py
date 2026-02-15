"""
Setup page for Cricket Ball Tracker
Handles pitch calibration, stump detection, wall boundary drawing, and rules configuration
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import json
from pathlib import Path

# Add the project root directory to the Python path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.detection.stump_detector import StumpDetector
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.session_config import SessionConfig


def main():
    st.title("Cricket Ball Tracker - Setup")
    st.markdown("### Configure your pitch and camera settings")

    # Initialize config manager
    config_manager = ConfigManager()

    # Check if a configuration already exists
    if config_manager.config_exists():
        st.info("Configuration already exists. You can load it or create a new one.")
        if st.button("Load Existing Configuration"):
            session_config = config_manager.load_session_config()
            st.session_state.session_config = session_config
            st.success("Configuration loaded successfully!")
        else:
            # Initialize session state if not already done
            if 'session_config' not in st.session_state:
                st.session_state.session_config = config_manager.load_defaults()
    else:
        # Initialize session state with defaults
        if 'session_config' not in st.session_state:
            st.session_state.session_config = config_manager.load_defaults()

    # Get current config
    config = st.session_state.session_config

    # Create tabs for different setup steps
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pitch Calibration",
        "Stump Detection",
        "Wide Configuration",
        "Wall Boundary",
        "Batsman Settings"
    ])

    with tab1:
        st.header("Pitch Calibration")

        # Pitch length input
        pitch_length = st.number_input(
            "Pitch Length (meters)",
            min_value=5.0,
            max_value=50.0,
            value=config.pitch_config.pitch_length,
            step=0.1
        )

        # Camera selection
        camera_index = st.number_input(
            "Camera Index",
            min_value=0,
            value=config.camera_index,
            help="0 for default camera, higher numbers for additional cameras"
        )

        # Resolution selection
        resolution_options = {
            "640x480": (640, 480),
            "800x600": (800, 600),
            "1280x720": (1280, 720)
        }
        resolution_names = list(resolution_options.keys())
        current_resolution = f"{config.resolution[0]}x{config.resolution[1]}"
        if current_resolution not in resolution_names:
            current_resolution = "640x480"
        selected_resolution = st.selectbox(
            "Camera Resolution",
            options=resolution_names,
            index=resolution_names.index(current_resolution)
        )
        resolution = resolution_options[selected_resolution]

        # Update config with new values
        config.pitch_config.pitch_length = pitch_length
        config.camera_index = camera_index
        config.resolution = resolution

    with tab2:
        st.header("Stump Detection")

        # Option to capture current frame for calibration
        if st.button("Capture Frame for Stump Calibration"):
            # Attempt to capture from camera
            cap = cv2.VideoCapture(config.camera_index)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()

                if ret:
                    # Convert BGR to RGB for display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    st.image(frame_rgb, caption="Captured Frame", use_column_width=True)

                    # Try to detect stumps using our detector
                    detector = StumpDetector()
                    stump_pos = detector.detect_stumps(frame)

                    if stump_pos:
                        st.success("Stumps detected!")
                        st.json({
                            "off_stump": stump_pos.off_stump_px,
                            "middle_stump": stump_pos.middle_stump_px,
                            "leg_stump": stump_pos.leg_stump_px,
                            "confidence": stump_pos.confidence
                        })

                        # Update config with detected stumps
                        config.batting_stumps = stump_pos

                        # Calculate pixels per meter based on known pitch length
                        # For demo, we'll just set a default value
                        config.pitch_config.pixels_per_meter = 100.0
                        if stump_pos.off_stump_px and stump_pos.leg_stump_px:
                            # Calculate distance between stumps and use that to estimate pixels per meter
                            stump_distance_px = ((stump_pos.off_stump_px[0] - stump_pos.leg_stump_px[0])**2 +
                                               (stump_pos.off_stump_px[1] - stump_pos.leg_stump_px[1])**2)**0.5
                            # Standard cricket stumps are 8.8 inches apart = 0.224 meters
                            config.pitch_config.pixels_per_meter = stump_distance_px / 0.224
                    else:
                        st.warning("Could not detect stumps. Please adjust camera position and try again.")
                else:
                    st.error("Could not capture from camera. Please check the camera index and permissions.")
            else:
                st.error(f"Could not open camera at index {config.camera_index}. Please check the index and permissions.")

    with tab3:
        st.header("Wide Configuration")

        # Wide corridor distances
        off_side_distance = st.number_input(
            "Off-side Wide Distance (meters)",
            min_value=0.1,
            max_value=2.0,
            value=config.wide_config.off_side_distance_m,
            step=0.01,
            help="Distance from off-stump to wide line"
        )

        leg_side_distance = st.number_input(
            "Leg-side Wide Distance (meters)",
            min_value=0.1,
            max_value=2.0,
            value=config.wide_config.leg_side_distance_m,
            step=0.01,
            help="Distance from leg-stump to wide line"
        )

        # Update config
        config.wide_config.off_side_distance_m = off_side_distance
        config.wide_config.leg_side_distance_m = leg_side_distance

    with tab4:
        st.header("Wall Boundary (Caught Behind Rule)")

        # We'll use a workaround to demonstrate the concept without streamlit-drawable-canvas
        # In a real implementation, we would use streamlit-drawable-canvas for interactive drawing
        st.info("Wall boundary defines the zone where the ball must hit to count as a catch.")
        st.markdown("""
        In the full implementation, this would use an interactive canvas to draw the boundary.
        For now, you can define boundary points manually.
        """)

        # Simple input for wall boundary (in production, use streamlit-drawable-canvas)
        st.markdown("### Wall Boundary Points")
        col1, col2 = st.columns(2)

        with col1:
            num_points = st.number_input("Number of boundary points", min_value=3, max_value=10, value=len(config.wall_boundary.polygon_points))

        # Create inputs for each point
        boundary_points = []
        cols = st.columns(num_points)
        for i in range(num_points):
            with cols[i % len(cols)]:
                if i < len(config.wall_boundary.polygon_points):
                    default_x, default_y = config.wall_boundary.polygon_points[i]
                else:
                    default_x, default_y = (50 + i * 50, 50)

                point_x = st.number_input(f"Point {i+1} X", value=default_x, key=f"bx_{i}")
                point_y = st.number_input(f"Point {i+1} Y", value=default_y, key=f"by_{i}")
                boundary_points.append((int(point_x), int(point_y)))

        # Update config with boundary points
        config.wall_boundary.polygon_points = boundary_points
        config.wall_boundary.is_valid = len(boundary_points) >= 3

    with tab5:
        st.header("Batsman Settings")

        # Batsman handedness selection
        handedness = st.radio(
            "Batsman Handedness",
            options=["right", "left"],
            index=0 if config.batsman_handedness == "right" else 1,
            help="Select the handedness of the batsman for correct LBW decisions"
        )

        # Manual override for handedness detection
        st.markdown("""
        The system will automatically detect batsman handedness, but you can override it here if needed.
        """)

        # Update config
        config.batsman_handedness = handedness

    # Display current configuration summary
    with st.expander("Current Configuration Summary"):
        st.json({
            "pitch_length": config.pitch_config.pitch_length,
            "camera_index": config.camera_index,
            "resolution": config.resolution,
            "stump_positions": {
                "off": config.batting_stumps.off_stump_px,
                "middle": config.batting_stumps.middle_stump_px,
                "leg": config.batting_stumps.leg_stump_px
            },
            "wide_distances": {
                "off_side": config.wide_config.off_side_distance_m,
                "leg_side": config.wide_config.leg_side_distance_m
            },
            "batsman_handedness": config.batsman_handedness
        })

    # Save configuration button
    if st.button("Save Configuration"):
        try:
            config_manager.save_session_config(config)
            st.session_state.session_config = config
            st.success("Configuration saved successfully!")

            # Provide next steps
            st.info("Configuration saved. You can now go to the Live Tracking page to start using the system.")
        except Exception as e:
            st.error(f"Error saving configuration: {str(e)}")


if __name__ == "__main__":
    main()