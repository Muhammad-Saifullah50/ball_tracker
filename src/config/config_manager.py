"""
Configuration manager for Cricket Ball Tracker
"""
import json
import os
from typing import Dict, Any
from pathlib import Path
import dataclasses

from ..models.session_config import SessionConfig
from ..models.calibration import PitchConfig, StumpPosition, WideConfig, WallBoundary


class ConfigManager:
    """Loads and saves configuration from/to JSON files."""

    def __init__(self, config_dir: str = "config") -> None:
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        # Create individual config files if they don't exist
        self._ensure_config_files()

    def load_session_config(self) -> SessionConfig:
        """Load all config files into a SessionConfig."""
        try:
            # Load pitch config
            pitch_config = self._load_pitch_config()

            # Load stumps config
            stump_position = self._load_stump_config()

            # Load wide config
            wide_config = self._load_wide_config()

            # Load wall boundary
            wall_boundary = self._load_wall_boundary()

            # Load rules config for batsman handedness and other rules
            rules_config = self._load_rules_config()

            return SessionConfig(
                pitch_config=pitch_config,
                batting_stumps=stump_position,
                wide_config=wide_config,
                wall_boundary=wall_boundary,
                batsman_handedness=rules_config.get("batsman_handedness", "right"),
                stump_width_tolerance=rules_config.get("stump_width_tolerance", 1.0),
                lbw_strictness=rules_config.get("lbw_strictness", "standard"),
                edge_sensitivity=rules_config.get("edge_sensitivity", 0.7),
                confidence_threshold=rules_config.get("confidence_threshold", 0.5),
                camera_index=rules_config.get("camera_index", 0),
                resolution=tuple(rules_config.get("resolution", (640, 480)))
            )
        except FileNotFoundError:
            # If no config exists, return defaults
            return self.load_defaults()

    def save_session_config(self, config: SessionConfig) -> None:
        """Save SessionConfig to individual JSON files."""
        # Save pitch config
        self._save_pitch_config(config.pitch_config)

        # Save stumps config
        self._save_stump_config(config.batting_stumps)

        # Save wide config
        self._save_wide_config(config.wide_config)

        # Save wall boundary
        self._save_wall_boundary(config.wall_boundary)

        # Save rules config
        self._save_rules_config(config)

    def load_defaults(self) -> SessionConfig:
        """Return default configuration."""
        from ..models.session_config import BatsmanDetection

        return SessionConfig(
            pitch_config=PitchConfig(
                pitch_length=20.12,  # Standard 22 yards = 20.12 meters
                unit="meters",
                bowling_crease_px=(0, 0),
                batting_crease_px=(0, 0),
                pixels_per_meter=100.0  # Placeholder value
            ),
            batting_stumps=StumpPosition(
                off_stump_px=(0, 0),
                middle_stump_px=(0, 0),
                leg_stump_px=(0, 0),
                stump_width_px=100,
                stump_height_px=70,
                confidence=1.0,
                end="batting"
            ),
            wide_config=WideConfig(
                off_side_distance_m=0.83,  # Standard wide width
                leg_side_distance_m=0.83
            ),
            wall_boundary=WallBoundary(
                polygon_points=[(0, 0), (0, 0), (0, 0)]  # Minimum 3 points
            ),
            batsman_handedness="right"
        )

    def config_exists(self) -> bool:
        """Check if a saved configuration exists."""
        pitch_file = self.config_dir / "pitch_config.json"
        return pitch_file.exists()

    def _ensure_config_files(self) -> None:
        """Ensure all config files exist with default values."""
        files = [
            "pitch_config.json",
            "stump_config.json",
            "wide_config.json",
            "wall_boundary.json",
            "rules_config.json"
        ]

        for file_name in files:
            file_path = self.config_dir / file_name
            if not file_path.exists():
                # Create with default/empty values
                if file_name == "pitch_config.json":
                    default_data = {
                        "pitch_length": 20.12,
                        "unit": "meters",
                        "bowling_crease_px": [0, 0],
                        "batting_crease_px": [0, 0],
                        "pixels_per_meter": 100.0
                    }
                elif file_name == "stump_config.json":
                    default_data = {
                        "off_stump_px": [0, 0],
                        "middle_stump_px": [0, 0],
                        "leg_stump_px": [0, 0],
                        "stump_width_px": 100,
                        "stump_height_px": 70,
                        "confidence": 1.0,
                        "end": "batting"
                    }
                elif file_name == "wide_config.json":
                    default_data = {
                        "off_side_distance_m": 0.83,
                        "leg_side_distance_m": 0.83,
                        "off_line_px": [[0, 0], [0, 0]],
                        "leg_line_px": [[0, 0], [0, 0]]
                    }
                elif file_name == "wall_boundary.json":
                    default_data = {
                        "polygon_points": [[0, 0], [0, 0], [0, 0]],
                        "is_valid": True
                    }
                else:  # rules_config.json
                    default_data = {
                        "batsman_handedness": "right",
                        "stump_width_tolerance": 1.0,
                        "lbw_strictness": "standard",
                        "edge_sensitivity": 0.7,
                        "confidence_threshold": 0.5,
                        "camera_index": 0,
                        "resolution": [640, 480]
                    }

                with open(file_path, 'w') as f:
                    json.dump(default_data, f, indent=2)

    def _load_pitch_config(self) -> PitchConfig:
        """Load pitch configuration from JSON."""
        file_path = self.config_dir / "pitch_config.json"

        with open(file_path, 'r') as f:
            data = json.load(f)

        return PitchConfig(
            pitch_length=data["pitch_length"],
            unit=data["unit"],
            bowling_crease_px=tuple(data["bowling_crease_px"]),
            batting_crease_px=tuple(data["batting_crease_px"]),
            pixels_per_meter=data["pixels_per_meter"]
        )

    def _save_pitch_config(self, config: PitchConfig) -> None:
        """Save pitch configuration to JSON."""
        file_path = self.config_dir / "pitch_config.json"

        data = {
            "pitch_length": config.pitch_length,
            "unit": config.unit,
            "bowling_crease_px": list(config.bowling_crease_px),
            "batting_crease_px": list(config.batting_crease_px),
            "pixels_per_meter": config.pixels_per_meter
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_stump_config(self) -> StumpPosition:
        """Load stump configuration from JSON."""
        file_path = self.config_dir / "stump_config.json"

        with open(file_path, 'r') as f:
            data = json.load(f)

        return StumpPosition(
            off_stump_px=tuple(data["off_stump_px"]),
            middle_stump_px=tuple(data["middle_stump_px"]),
            leg_stump_px=tuple(data["leg_stump_px"]),
            stump_width_px=data["stump_width_px"],
            stump_height_px=data["stump_height_px"],
            confidence=data["confidence"],
            end=data["end"]
        )

    def _save_stump_config(self, config: StumpPosition) -> None:
        """Save stump configuration to JSON."""
        file_path = self.config_dir / "stump_config.json"

        data = {
            "off_stump_px": list(config.off_stump_px),
            "middle_stump_px": list(config.middle_stump_px),
            "leg_stump_px": list(config.leg_stump_px),
            "stump_width_px": config.stump_width_px,
            "stump_height_px": config.stump_height_px,
            "confidence": config.confidence,
            "end": config.end
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_wide_config(self) -> WideConfig:
        """Load wide configuration from JSON."""
        file_path = self.config_dir / "wide_config.json"

        with open(file_path, 'r') as f:
            data = json.load(f)

        return WideConfig(
            off_side_distance_m=data["off_side_distance_m"],
            leg_side_distance_m=data["leg_side_distance_m"],
            off_line_px=(tuple(data["off_line_px"][0]), tuple(data["off_line_px"][1])),
            leg_line_px=(tuple(data["leg_line_px"][0]), tuple(data["leg_line_px"][1]))
        )

    def _save_wide_config(self, config: WideConfig) -> None:
        """Save wide configuration to JSON."""
        file_path = self.config_dir / "wide_config.json"

        data = {
            "off_side_distance_m": config.off_side_distance_m,
            "leg_side_distance_m": config.leg_side_distance_m,
            "off_line_px": [list(config.off_line_px[0]), list(config.off_line_px[1])],
            "leg_line_px": [list(config.leg_line_px[0]), list(config.leg_line_px[1])]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_wall_boundary(self) -> WallBoundary:
        """Load wall boundary configuration from JSON."""
        file_path = self.config_dir / "wall_boundary.json"

        with open(file_path, 'r') as f:
            data = json.load(f)

        return WallBoundary(
            polygon_points=[tuple(point) for point in data["polygon_points"]],
            is_valid=data["is_valid"]
        )

    def _save_wall_boundary(self, config: WallBoundary) -> None:
        """Save wall boundary configuration to JSON."""
        file_path = self.config_dir / "wall_boundary.json"

        data = {
            "polygon_points": [list(point) for point in config.polygon_points],
            "is_valid": config.is_valid
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_rules_config(self) -> Dict[str, Any]:
        """Load rules configuration from JSON."""
        file_path = self.config_dir / "rules_config.json"

        with open(file_path, 'r') as f:
            return json.load(f)

    def _save_rules_config(self, config: SessionConfig) -> None:
        """Save rules configuration to JSON."""
        file_path = self.config_dir / "rules_config.json"

        data = {
            "batsman_handedness": config.batsman_handedness,
            "stump_width_tolerance": config.stump_width_tolerance,
            "lbw_strictness": config.lbw_strictness,
            "edge_sensitivity": config.edge_sensitivity,
            "confidence_threshold": config.confidence_threshold,
            "camera_index": config.camera_index,
            "resolution": list(config.resolution)
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)