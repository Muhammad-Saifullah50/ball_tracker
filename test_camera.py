"""
Simple camera test to troubleshoot WebRTC camera access issues
"""
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import av
import numpy as np

class SimpleVideoProcessor(VideoProcessorBase):
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # Simply return the frame as received
        img = frame.to_ndarray(format="bgr24")
        return img

def main():
    st.title("Camera Test - WebRTC Troubleshooting")
    st.write("This test helps diagnose camera access issues.")

    # Enhanced RTC configuration with multiple STUN servers
    webrtc_ctx = webrtc_streamer(
        key="test-camera",
        mode=WebRtcMode.RECVONLY,
        rtc_configuration=RTCConfiguration({
            "iceServers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun.cloudflare.com:3478"]},
                {"urls": ["stun:stun.stunprotocol.org:3478"]},
            ],
            "iceCandidatePoolSize": 10
        }),
        video_processor_factory=SimpleVideoProcessor,
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
        }
    )

    if webrtc_ctx:
        if hasattr(webrtc_ctx, 'state') and webrtc_ctx.state:
            if hasattr(webrtc_ctx.state, 'playing') and webrtc_ctx.state.playing:
                st.success("✅ Camera is connected and playing!")
            else:
                st.warning("⚠️ Camera connected but not playing. Check browser permissions.")
        else:
            st.info("📷 Camera stream active. Make sure to allow camera access in browser.")
    else:
        st.error("❌ Could not initialize camera streamer.")

    st.markdown("""
    ## Troubleshooting Guide:

    1. **Browser Permissions**:
       - Look for a camera icon in your browser's address bar
       - Click it and select "Always allow"

    2. **Browser Compatibility**:
       - Use Chrome, Firefox, or Safari
       - Avoid using in incognito/private mode initially

    3. **Mobile Devices**:
       - Use Chrome (Android) or Safari (iOS)
       - Tap on the gray box to activate camera

    4. **Network Issues**:
       - Corporate firewalls may block WebRTC
       - Try using a different network
    """)

    st.button("Retry Camera Access")

if __name__ == "__main__":
    main()