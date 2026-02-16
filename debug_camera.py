"""
Debug script to test camera functionality in Live Tracking
"""
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import av
import threading

# Global lock for thread-safe operations
global_lock = threading.Lock()
track_container = {
    "frame": None,
    "detection": None,
    "trajectory": None,
    "current_frame_number": 0
}

def video_frame_callback(frame: av.VideoFrame):
    """Simple callback for testing"""
    img = frame.to_ndarray(format="bgr24")

    # Store frame in thread-safe container
    with global_lock:
        track_container["frame"] = img.copy()

    return frame

def main():
    st.title("Camera Test - Live Tracking")
    st.write("Testing camera access for Live Tracking page")

    # Use streamlit-webrtc for continuous camera access with WebRTC
    # Updated to SENDRECV mode and modern video_frame_callback approach
    try:
        webrtc_ctx = webrtc_streamer(
            key="debug-ball-tracking",
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
            video_frame_callback=video_frame_callback,
            media_stream_constraints={
                "video": {
                    "facingMode": "environment",  # Use rear camera by default for better cricket tracking
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
            },
            desired_playing_state=True  # Start playing when the component is ready, but still requires user gesture
        )

        if webrtc_ctx:
            # Check if the stream is active with better error handling
            # Access the playing state through the state attribute
            if hasattr(webrtc_ctx, 'state') and webrtc_ctx.state:
                if hasattr(webrtc_ctx.state, 'playing') and webrtc_ctx.state.playing:
                    st.success("✅ Camera connected! Ball tracking is active.")
                    # Additional message for gray box issue
                    st.info("💡 If you see a gray box instead of video, click/tap on it to activate the camera feed.")
                elif hasattr(webrtc_ctx.state, 'video_receiver') and webrtc_ctx.state.video_receiver:
                    st.success("✅ Camera stream established! Ball tracking is active.")
                else:
                    # Check if there are connection issues
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
            st.warning("⚠️ Camera streamer could not be initialized. Check browser compatibility.")
            st.info("Try using Chrome, Firefox, or Safari for the best WebRTC support.")

        # Show current frame info
        with global_lock:
            if track_container["frame"] is not None:
                st.write(f"Frame received: {track_container['frame'].shape}")

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

if __name__ == "__main__":
    main()