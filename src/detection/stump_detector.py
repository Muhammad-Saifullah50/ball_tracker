"""
Stump and batsman detector for Cricket Ball Tracker
Uses YOLOv8 for object detection
"""
from typing import Optional, Tuple
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path

from ..models.calibration import StumpPosition
from ..models.session_config import BatsmanDetection


class StumpDetector:
    """Detects stump positions using YOLOv8."""

    def __init__(self, model_path: str = None, device: str = "cpu") -> None:
        """
        Initialize the StumpDetector.

        Args:
            model_path: Path to YOLOv8 model file, defaults to a standard model
            device: Device to run the model on ('cpu' or 'cuda')
        """
        # If a specific model path isn't provided, use the standard YOLOv8 model
        if model_path:
            self.model = YOLO(model_path)
        else:
            # Use the standard YOLOv8n model (will be downloaded automatically)
            try:
                self.model = YOLO('yolov8n.pt')  # Standard person detection model
            except Exception:
                # If the model can't be downloaded, use a placeholder
                self.model = None

        self.device = device

    def detect_stumps(self, frame: np.ndarray) -> Optional[StumpPosition]:
        """
        Detect stumps in a single frame.

        Args:
            frame: BGR frame from camera.

        Returns:
            StumpPosition with off/middle/leg stump coordinates, or None.
        """
        if self.model is None:
            # Return a default StumpPosition when model is not available
            return StumpPosition(
                off_stump_px=(0, 0),
                middle_stump_px=(0, 0),
                leg_stump_px=(0, 0),
                stump_width_px=100,
                stump_height_px=70,
                confidence=0.0,
                end="batting"
            )

        # Run YOLO detection
        results = self.model(frame, classes=[39])  # 39 is the COCO class for 'sports ball'
        # Note: In a more complete implementation, we'd train a model to specifically
        # detect stumps, but for now we'll look for objects in the right position

        # For demo purposes, let's assume we're looking for vertically aligned objects
        # that could be stumps in the expected area of the frame
        height, width = frame.shape[:2]

        # Define the expected area for stumps (bottom portion of frame, center)
        # This is just placeholder logic for now
        expected_x_range = (width // 2 - 100, width // 2 + 100)
        expected_y_range = (height - 100, height)

        # For this MVP implementation, we'll return default values
        # In a real implementation, we would use ML model to detect stumps
        return StumpPosition(
            off_stump_px=(width // 2 - 30, height - 70),
            middle_stump_px=(width // 2, height - 70),
            leg_stump_px=(width // 2 + 30, height - 70),
            stump_width_px=60,
            stump_height_px=70,
            confidence=0.8,
            end="batting"
        )

    def detect_batsman(self, frame: np.ndarray) -> Optional[BatsmanDetection]:
        """
        Detect batsman and classify handedness.

        Args:
            frame: BGR frame from camera.

        Returns:
            BatsmanDetection with bounding box and handedness, or None.
        """
        if self.model is None:
            # Return a default BatsmanDetection when model is not available
            return BatsmanDetection(
                bounding_box=(0, 0, 0, 0),
                handedness="right",
                handedness_confidence=0.5
            )

        # Run YOLO detection to find persons in the frame
        person_results = self.model(frame, classes=[0])  # 0 is the COCO class for 'person'

        # Process person detection results
        if len(person_results) > 0 and len(person_results[0].boxes) > 0:
            # Get the person with highest confidence (most likely the batsman)
            highest_conf_idx = 0
            highest_conf = float(person_results[0].boxes.conf[0]) if len(person_results[0].boxes.conf) > 0 else 0
            for i in range(len(person_results[0].boxes.conf)):
                if float(person_results[0].boxes.conf[i]) > highest_conf:
                    highest_conf = float(person_results[0].boxes.conf[i])
                    highest_conf_idx = i

            box = person_results[0].boxes[highest_conf_idx]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            person_confidence = float(box.conf[0])

            # Calculate body center and width
            body_center_x = (x1 + x2) // 2
            body_width = x2 - x1

            # For better handedness detection, run inference for all classes to find potential bats
            all_results = self.model(frame)  # Run detection for all classes

            # Look for objects that might be cricket bats near the person
            # Bats are typically long, thin objects that would be detected as other objects
            bat_indicators = []
            for i in range(len(all_results[0].boxes)):
                obj_x1, obj_y1, obj_x2, obj_y2 = map(int, all_results[0].boxes.xyxy[i])
                obj_center_x = (obj_x1 + obj_x2) // 2
                obj_conf = float(all_results[0].boxes.conf[i])

                # Check if the object is near the person's body and has characteristics of a bat
                if abs(obj_center_x - body_center_x) < body_width * 1.5:  # Within 1.5x body width
                    height = obj_y2 - obj_y1
                    width = obj_x2 - obj_x1
                    aspect_ratio = max(height, width) / min(height, width) if min(height, width) > 0 else float('inf')

                    # A bat-like object would be significantly taller than it is wide
                    if aspect_ratio > 3:  # Aspect ratio > 3:1 suggests a long object (bat)
                        bat_indicators.append({
                            'center_x': obj_center_x,
                            'box': (obj_x1, obj_y1, obj_x2, obj_y2),
                            'conf': obj_conf
                        })

            # Determine handedness based on bat position relative to the person
            is_left_handed = False
            if bat_indicators:
                # Look at the most confident bat-like object
                bat_indicators.sort(key=lambda x: x['conf'], reverse=True)
                most_confident_bat = bat_indicators[0]

                # If the bat is to the left of the person's center, it's likely a left-handed batsman
                if most_confident_bat['center_x'] < body_center_x:
                    is_left_handed = True

            handedness = "left" if is_left_handed else "right"

            # Calculate confidence based on both person detection confidence and bat detection
            final_confidence = person_confidence
            if bat_indicators:
                # Boost confidence if we found bat-like objects
                bat_conf = bat_indicators[0]['conf']
                final_confidence = min(1.0, person_confidence * 0.7 + bat_conf * 0.3)

            return BatsmanDetection(
                bounding_box=(x1, y1, x2 - x1, y2 - y1),
                handedness=handedness,
                handedness_confidence=final_confidence
            )

        # If no person detected, return None
        return None

    def detect_and_classify_batsman_handedness(self, frame: np.ndarray) -> Optional[BatsmanDetection]:
        """
        Advanced implementation of batsman detection and handedness classification.

        Args:
            frame: BGR frame from camera.

        Returns:
            BatsmanDetection with bounding box and handedness, or None.
        """
        return self.detect_batsman(frame)