"""
Rules configuration page for Cricket Ball Tracker
Allows users to adjust rules parameters through UI
"""
import streamlit as st
from typing import Optional
import sys
from pathlib import Path

# Add the project root directory to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from src.config.config_manager import ConfigManager
from src.models.session_config import SessionConfig


class RulesApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[SessionConfig] = None

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

    def save_config(self):
        """Save the current configuration."""
        if self.config:
            self.config_manager.save_session_config(self.config)
            # Also update the session state
            st.session_state.session_config = self.config
            st.success("Configuration saved successfully!")

    def run(self):
        """Run the rules configuration page."""
        st.title("⚙️ Cricket Ball Tracker - Rules Configuration")
        st.markdown("### Adjust rules parameters to customize decision behavior")

        if not self.load_config():
            st.stop()

        st.header("LBW Rules")

        # LBW Strictness
        lbw_options = {
            "Lenient": "lenient",
            "Standard": "standard",
            "Strict": "strict"
        }
        lbw_selected = st.selectbox(
            "LBW Strictness Level",
            options=list(lbw_options.keys()),
            index=list(lbw_options.values()).index(self.config.lbw_strictness) if self.config.lbw_strictness in lbw_options.values() else 1,
            help="How strict the LBW decision should be"
        )
        if self.config:
            self.config.lbw_strictness = lbw_options[lbw_selected]

        # Stump Tolerance
        stump_tolerance = st.slider(
            "Stump Tolerance (pixels)",
            min_value=0.1,
            max_value=5.0,
            value=self.config.stump_width_tolerance if self.config.stump_width_tolerance else 1.0,
            step=0.1,
            help="How close to stumps the ball needs to be to hit them"
        )
        if self.config:
            self.config.stump_width_tolerance = stump_tolerance

        st.markdown("---")
        st.header("Wide Rules")

        # Wide distance adjustment (in meters)
        off_side_distance = st.slider(
            "Off-side Wide Distance (meters)",
            min_value=0.1,
            max_value=2.0,
            value=self.config.wide_config.off_side_distance_m if hasattr(self.config, 'wide_config') and self.config.wide_config else 0.83,
            step=0.01,
            help="Distance from stumps for off-side wide"
        )

        leg_side_distance = st.slider(
            "Leg-side Wide Distance (meters)",
            min_value=0.1,
            max_value=2.0,
            value=self.config.wide_config.leg_side_distance_m if hasattr(self.config, 'wide_config') and self.config.wide_config else 0.83,
            step=0.01,
            help="Distance from stumps for leg-side wide"
        )

        if hasattr(self.config, 'wide_config') and self.config.wide_config:
            self.config.wide_config.off_side_distance_m = off_side_distance
            self.config.wide_config.leg_side_distance_m = leg_side_distance

        st.markdown("---")
        st.header("Caught Behind Rules")

        # Edge Sensitivity
        edge_sensitivity = st.slider(
            "Edge Detection Sensitivity",
            min_value=0.1,
            max_value=1.0,
            value=self.config.edge_sensitivity if self.config.edge_sensitivity else 0.7,
            step=0.05,
            help="How sensitive the edge detection is (higher = more sensitive)"
        )
        if self.config:
            self.config.edge_sensitivity = edge_sensitivity

        st.markdown("---")
        st.header("General Decision Rules")

        # Confidence Threshold
        confidence_threshold = st.slider(
            "Minimum Confidence Threshold",
            min_value=0.1,
            max_value=1.0,
            value=self.config.confidence_threshold if self.config.confidence_threshold else 0.5,
            step=0.05,
            help="Minimum confidence required for decisions to be shown"
        )
        if self.config:
            self.config.confidence_threshold = confidence_threshold

        st.markdown("---")
        # Display current config values for reference
        with st.expander("Current Configuration Values"):
            st.json({
                "lbw_strictness": self.config.lbw_strictness if self.config else "N/A",
                "stump_width_tolerance": self.config.stump_width_tolerance if self.config else "N/A",
                "edge_sensitivity": self.config.edge_sensitivity if self.config else "N/A",
                "confidence_threshold": self.config.confidence_threshold if self.config else "N/A",
                "wide_config": {
                    "off_side_distance_m": self.config.wide_config.off_side_distance_m if hasattr(self.config, 'wide_config') and self.config.wide_config else "N/A",
                    "leg_side_distance_m": self.config.wide_config.leg_side_distance_m if hasattr(self.config, 'wide_config') and self.config.wide_config else "N/A",
                } if hasattr(self.config, 'wide_config') and self.config.wide_config else "N/A"
            })

        # Save button
        if st.button("💾 Save Configuration", type="primary"):
            self.save_config()


def main():
    app = RulesApp()
    app.run()


if __name__ == "__main__":
    main()