"""
Setup page for Cricket Ball Tracker
Handles pitch calibration, stump detection, wall boundary drawing, and rules configuration
"""
import streamlit as st
import numpy as np
from PIL import Image
import json
import sys
from pathlib import Path

# Add the project root directory to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from src.config.config_manager import ConfigManager
from src.detection.stump_detector import StumpDetector
from src.calibration.pitch_calibrator import PitchCalibrator
from src.models.session_config import SessionConfig

import threading
# Import streamlit-webrtc components
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import av

# Global lock for thread-safe operations between WebRTC thread and Streamlit UI thread for stump detection
stump_global_lock = threading.Lock()
stump_track_container = {
    "last_detection": None,
    "frame": None
}


def stump_video_frame_callback(frame: av.VideoFrame):
    """
    Modern callback approach to process video frames for stump detection with thread safety
    """
    # Convert av.VideoFrame to numpy array
    img = frame.to_ndarray(format="bgr24")

    # For setup purposes, we'll just return the original frame
    # But we can run detection in the background
    detector = StumpDetector()
    try:
        detection = detector.detect_stumps(img)
    except Exception as e:
        # Detection failed, continue with original frame but log the error
        detection = None

    # Store results in thread-safe container
    with stump_global_lock:
        stump_track_container["frame"] = img.copy()
        stump_track_container["last_detection"] = detection

    # Return the original frame for display
    return frame


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

        # Option to upload image or use live camera for calibration
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("Upload a photo of stumps", type=["jpg", "jpeg", "png"], key="stump_upload")
        with col2:
            st.markdown("**Or use live camera:**")
            st.info("💡 Make sure to allow camera permissions when prompted. On mobile, use Chrome or Safari for best results.")
            # Use streamlit-webrtc for live camera access with WebRTC
            # Updated to SENDRECV mode and modern video_frame_callback approach
            webrtc_ctx = webrtc_streamer(
                key="stump-detection",
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
                video_frame_callback=stump_video_frame_callback,
                media_stream_constraints={
                    "video": {
                        "facingMode": "environment",  # Use rear camera on mobile
                        "width": {"ideal": 1280},
                        "height": {"ideal": 720}
                    },
                    "audio": False
                },
                async_processing=True,
                video_html_attrs={
                    "style": {"width": "100%", "maxWidth": "600px", "height": "auto", "objectFit": "cover"},
                    "controls": False,
                    "autoPlay": True,
                    "playsInline": True,
                    "muted": True
                },
                desired_playing_state=True  # Start playing when the component is ready, but still requires user gesture
            )
            if webrtc_ctx:
                # Check if the stream is active with better error handling
                # The webrtc_ctx has a playing property that indicates if the stream is active
                if hasattr(webrtc_ctx, 'playing') and webrtc_ctx.playing:
                    st.success("✅ Camera connected! If you see a gray box, tap on it to start the video. Point it at the stumps.")
                    # Additional message for gray box issue
                    st.info("💡 If you see a gray box instead of video, click/tap on it to activate the camera feed.")
                elif hasattr(webrtc_ctx, 'video_receiver') and webrtc_ctx.video_receiver:
                    st.success("✅ Camera stream established! Point it at the stumps.")
                else:
                    # Check if there are connection issues
                    if hasattr(webrtc_ctx, 'state') and webrtc_ctx.state:
                        if hasattr(webrtc_ctx.state, 'signalingState'):
                            if webrtc_ctx.state.signalingState == "closed":
                                st.error("❌ Camera connection closed. Network issue or browser incompatible.")
                            elif webrtc_ctx.state.signalingState == "have-remote-offer":
                                st.info("📡 Negotiating camera connection...")
                        else:
                            st.warning("⚠️ Camera connected but video stream not playing. Try clicking on the gray box above.")
                            # Check for error states
                            if hasattr(webrtc_ctx.state, 'error'):
                                st.error(f"Camera Error: {webrtc_ctx.state.error}")
                    else:
                        st.warning("⚠️ Camera may need to be started. Click on the gray box to start streaming.")
            else:
                # Provide more detailed troubleshooting information
                st.info("📷 Waiting for camera connection... Make sure to allow camera permissions when prompted.")
                st.warning("If you've denied permissions, please refresh the page and allow camera access when prompted.")

                # Provide connection troubleshooting tips
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

        # Process uploaded file if provided
        if uploaded_file is not None:
            # Read the uploaded image
            pil_image = Image.open(uploaded_file)
            frame = np.array(pil_image)

            # Ensure the frame is in the right format
            if frame.shape[-1] == 4:  # If RGBA, convert to RGB
                frame = frame[:, :, :3]

            # Display the uploaded image
            st.image(pil_image, caption="Uploaded Frame", use_column_width=True)

            # Try to detect stumps using our detector
            detector = StumpDetector()
            # Convert RGB to BGR for OpenCV processing
            frame_bgr = frame[:, :, ::-1]  # RGB to BGR
            stump_pos = detector.detect_stumps(frame_bgr)

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
                st.warning("Could not detect stumps. Please use a clearer image.")

        # Process live camera stream if available
        elif webrtc_ctx and webrtc_ctx.playing:
            st.info("Point your camera at the stumps. Click the 'Capture Frame' button below when ready.")

            # Create a button to capture the current frame for processing
            if st.button("Capture Frame for Stump Detection"):
                # Get the most recent detection from the thread-safe container
                with stump_global_lock:
                    last_detection = stump_track_container["last_detection"]
                    current_frame = stump_track_container["frame"]

                if current_frame is not None and last_detection is not None:
                    # Convert frame to PIL image for display
                    if current_frame is not None:
                        pil_image = Image.fromarray(current_frame)
                        st.image(pil_image, caption="Captured Frame", use_column_width=True)

                        if last_detection and last_detection.confidence > 0.5:  # Add confidence threshold
                            st.success("Stumps detected!")
                            st.json({
                                "off_stump": last_detection.off_stump_px,
                                "middle_stump": last_detection.middle_stump_px,
                                "leg_stump": last_detection.leg_stump_px,
                                "confidence": last_detection.confidence
                            })

                            # Update config with detected stumps
                            config.batting_stumps = last_detection

                            # Calculate pixels per meter based on known pitch length
                            config.pitch_config.pixels_per_meter = 100.0
                            if last_detection.off_stump_px and last_detection.leg_stump_px:
                                # Calculate distance between stumps and use that to estimate pixels per meter
                                stump_distance_px = ((last_detection.off_stump_px[0] - last_detection.leg_stump_px[0])**2 +
                                                   (last_detection.off_stump_px[1] - last_detection.leg_stump_px[1])**2)**0.5
                                # Standard cricket stumps are 8.8 inches apart = 0.224 meters
                                config.pitch_config.pixels_per_meter = stump_distance_px / 0.224
                        else:
                            st.warning("Could not detect stumps or low confidence. Please adjust camera and try again.")
                else:
                    # In a complete implementation with WebRTC, we would capture the current frame
                    # when the user clicks the button and process it for stump detection
                    # This requires more advanced WebRTC handling which is a limitation of this approach
                    # without a more complex implementation
                    st.warning("For now, please take a screenshot of the live camera feed and upload it above, or use the photo capture option.")

        # Provide help text if neither input is provided
        else:
            st.info("Please either upload a photo or use the live camera to capture the stumps setup.")

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