"""
Ball detector for Cricket Ball Tracker
Uses TrackNet for ball detection in video frames
"""
import numpy as np
import cv2
from typing import Optional, Tuple
from pathlib import Path

from ..models.ball_detection import BallDetection


class BallDetector:
    """Detects ball position using TrackNet model."""

    def __init__(self, model_path: str = None, device: str = "cpu") -> None:
        """
        Initialize the BallDetector.

        Args:
            model_path: Path to TrackNet model file, defaults to a placeholder
            device: Device to run the model on ('cpu' or 'cuda')
        """
        self.device = device

        # For the MVP, we'll implement a simple color-based ball detection
        # as a placeholder until we integrate the actual TrackNet model
        self.model_path = model_path
        self.model_loaded = False
        self.tracknet_model = None

        # If model path is provided and model exists, we'll load it
        if model_path and Path(model_path).exists():
            try:
                # Actual TrackNet model loading would go here
                # For the MVP implementation, using ONNX Runtime for TrackNet
                import onnxruntime as ort
                self.tracknet_model = ort.InferenceSession(model_path)
                self.model_loaded = True
            except ImportError:
                print("ONNX Runtime not installed, using color-based detection")
                self.model_loaded = False
            except Exception as e:
                print(f"Warning: Could not load model from {model_path}: {e}, using color-based detection")
                self.model_loaded = False

    def detect(self, frame_triplet: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> Optional[BallDetection]:
        """
        Detect ball in a set of 3 consecutive frames.

        Args:
            frame_triplet: Three consecutive BGR frames (oldest, middle, newest)

        Returns:
            BallDetection with position and confidence, or None if not detected.

        Raises:
            DetectionError: If model inference fails.
        """
        # If model is loaded, use TrackNet
        if self.model_loaded and self.tracknet_model:
            try:
                return self._detect_ball_tracknet(frame_triplet)
            except Exception as e:
                print(f"TrackNet inference failed: {e}, falling back to color detection")
                # Fall back to color detection
                middle_frame = frame_triplet[1]
                return self._detect_ball_color_based(middle_frame)
        else:
            # Use simple color-based detection for MVP
            middle_frame = frame_triplet[1]
            return self._detect_ball_color_based(middle_frame)

    def _detect_ball_tracknet(self, frame_triplet: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> Optional[BallDetection]:
        """
        Detect ball using TrackNet model.
        This processes 3 consecutive frames to detect the ball.
        """
        # Resize frames to TrackNet input size (typically 640x360)
        tracknet_input_size = (640, 360)

        # Resize each frame in the triplet
        resized_frames = []
        for frame in frame_triplet:
            resized = cv2.resize(frame, tracknet_input_size)
            # Convert BGR to RGB and normalize to [0,1]
            resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            resized_normalized = resized_rgb.astype(np.float32) / 255.0
            resized_frames.append(resized_normalized)

        # Stack the 3 frames along the channel dimension
        # TrackNet expects input shape: (batch_size, 3, height, width, 3) or similar
        # Actual TrackNet implementation may vary
        input_tensor = np.stack(resized_frames, axis=0)  # Shape: (3, H, W, C)
        input_tensor = np.transpose(input_tensor, (0, 3, 1, 2))  # Shape: (3, C, H, W)
        input_tensor = np.expand_dims(input_tensor, axis=0)  # Shape: (1, 3, C, H, W)

        # Run inference
        # Note: This is a simplified representation of TrackNet inference
        # Actual TrackNet may have different input/output requirements
        try:
            result = self.tracknet_model.run(None, {'input': input_tensor.astype(np.float32)})

            # Process result (simplified - actual TrackNet output processing varies)
            # TrackNet typically outputs a heatmap indicating ball position
            heatmap = result[0]  # Actual index may vary based on model

            # Find the maximum value in the heatmap (ball position)
            if heatmap.ndim > 2:  # If heatmap has multiple channels/frames
                # Take the latest frame's heatmap
                latest_heatmap = heatmap[0, -1]  # Assuming shape includes batch and frame dims
            else:
                latest_heatmap = heatmap[0]

            # Find the position of the maximum value
            y_pos, x_pos = np.unravel_index(np.argmax(latest_heatmap), latest_heatmap.shape)

            # Convert coordinates back to original frame size
            # This is a simplified conversion - would need proper scaling in practice
            orig_height, orig_width = frame_triplet[1].shape[:2]
            scale_x = orig_width / tracknet_input_size[0]
            scale_y = orig_height / tracknet_input_size[1]

            x_orig = int(x_pos * scale_x)
            y_orig = int(y_pos * scale_y)

            # Use the max value as confidence
            confidence = float(np.max(latest_heatmap))

            # Create and return BallDetection object
            # The frame_number and timestamp would normally come from the tracking context
            return BallDetection(
                frame_number=0,  # Would be passed in actual usage
                x=x_orig,
                y=y_orig,
                confidence=min(1.0, confidence),  # Ensure confidence is in [0,1]
                timestamp_ms=0.0,  # Would be passed in actual usage
                visibility="visible"
            )
        except Exception as e:
            # If TrackNet fails, fall back to the color-based method
            print(f"TrackNet processing failed: {e}")
            return self._detect_ball_color_based(frame_triplet[1])

    def warmup(self) -> None:
        """Run a dummy inference to initialize the model."""
        # For the actual TrackNet model, this would run a dummy inference
        # For our MVP, we don't need to do anything special
        pass

    def _detect_ball_color_based(self, frame: np.ndarray) -> Optional[BallDetection]:
        """
        Detect the cricket ball using color-based approach.
        This is a placeholder for the TrackNet model in the MVP.
        """
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define range for red/orange cricket ball in HSV
        # These values are approximate and may need adjustment
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])

        # Create masks for the red/orange color range
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2

        # Apply some morphological operations to clean up the mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour
            largest_contour = max(contours, key=cv2.contourArea)

            # Only consider contours that are large enough to be a ball
            if cv2.contourArea(largest_contour) > 50:  # Minimum area threshold
                # Get the center of the contour
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # Estimate confidence based on contour properties
                    # Larger, more circular contours get higher confidence
                    area = cv2.contourArea(largest_contour)
                    perimeter = cv2.arcLength(largest_contour, True)

                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        # Normalize confidence between 0 and 1
                        confidence = min(1.0, area / 1000.0) * min(1.0, circularity)
                    else:
                        confidence = min(1.0, area / 1000.0)

                    # Create and return BallDetection object
                    height, width = frame.shape[:2]
                    frame_number = 0  # This would be passed in a real implementation

                    return BallDetection(
                        frame_number=frame_number,
                        x=cx,
                        y=cy,
                        confidence=confidence,
                        timestamp_ms=0.0,  # Would be passed in a real implementation
                        visibility="visible"
                    )

        # If no ball is detected, return None
        return None


class DetectionError(Exception):
    """Custom exception for detection errors."""
    pass