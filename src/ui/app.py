"""
Main application entry point for Cricket Ball Tracker
"""
import streamlit as st
import sys
from pathlib import Path

# Add the project root directory to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from src.config.config_manager import ConfigManager


def main():
    st.set_page_config(
        page_title="Cricket Ball Tracker",
        page_icon="🏏",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize config manager
    config_manager = ConfigManager()

    st.title("🏏 Cricket Ball Tracker MVP")
    st.markdown("""
    ### A Computer Vision Application for Home Cricket

    This application provides:
    - Ball detection and trajectory tracking
    - Instant replays with visual overlays
    - Automated decision support for LBW, wides, and caught-behind
    - Configurable rules engine for different skill levels

    **Mobile Usage**: For best results on mobile devices:
    - Use Chrome (Android) or Safari (iOS)
    - Ensure you have granted camera permissions
    - Point your rear camera at the cricket setup
    - Use in a well-lit environment for better detection

    **Note**: This is an MVP implementation focused on home cricket dispute resolution.
    """)

    # Check if configuration exists
    if not config_manager.config_exists():
        st.warning("No configuration found. Please complete the setup first.")
        st.info("Navigate to the 'Setup' page using the sidebar to configure your pitch.")
    else:
        st.success("Configuration loaded successfully!")
        config = config_manager.load_session_config()
        st.markdown(f"**Current Setup:** {config.pitch_config.pitch_length:.2f}m pitch, "
                   f"{config.batsman_handedness}-handed batsman")

    st.markdown("---")
    st.markdown("### How to Use")
    st.markdown("""
    1. **Setup**: Configure your pitch dimensions, camera position, and rules
    2. **Live Tracking**: Start tracking deliveries in real-time
    3. **Replay**: Review deliveries with slow motion and decision graphics
    4. **Rules**: Adjust rules parameters for different skill levels

    **For Mobile Users**: When prompted, please allow camera access permissions for the best experience.
    """)

    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This application uses computer vision to track cricket balls and assist with
    decision-making in home cricket games. All processing runs locally on your
    computer with no cloud dependency.

    **Technology Stack:**
    - OpenCV for computer vision
    - TrackNet for ball detection
    - YOLOv8 for object detection
    - Streamlit for the user interface
    - Kalman filter for trajectory tracking
    """)


if __name__ == "__main__":
    main()