"""
Replay buffer for Cricket Ball Tracker
Stores video frames for instant replay functionality
"""
from collections import deque
from typing import Deque, Optional, Tuple
import cv2
import numpy as np
from ..models.ball_detection import Trajectory


class ReplayBuffer:
    """Buffer to store frames of recent deliveries for instant replay."""

    def __init__(self, max_deliveries: int = 2, max_frames_per_delivery: int = 300):
        """
        Initialize the replay buffer.

        Args:
            max_deliveries: Maximum number of complete deliveries to store
            max_frames_per_delivery: Maximum frames per delivery to store
        """
        self.max_deliveries = max_deliveries
        self.max_frames_per_delivery = max_frames_per_delivery
        self.deliveries: Deque[Tuple[Deque[np.ndarray], Optional[Trajectory]]] = deque(maxlen=max_deliveries)
        self.current_frame_buffer: Deque[np.ndarray] = deque(maxlen=max_frames_per_delivery)
        self.current_trajectory: Optional[Trajectory] = None

    def add_frame(self, frame: np.ndarray) -> None:
        """
        Add a frame to the current delivery buffer.

        Args:
            frame: Video frame to add to the buffer
        """
        # Add a copy of the frame to avoid reference issues
        self.current_frame_buffer.append(frame.copy())

    def start_new_delivery(self) -> None:
        """Start buffering a new delivery."""
        # If we have a current delivery with frames, save it
        if len(self.current_frame_buffer) > 0:
            self.save_current_delivery()

        # Reset for the new delivery
        self.current_frame_buffer.clear()
        self.current_trajectory = None

    def save_current_delivery(self) -> None:
        """Save the current delivery if it has frames."""
        if len(self.current_frame_buffer) > 0:
            # Add the current delivery to the deliveries buffer
            current_delivery = (self.current_frame_buffer.copy(), self.current_trajectory)
            self.deliveries.append(current_delivery)

            # Create a new frame buffer for the next delivery
            self.current_frame_buffer = deque(maxlen=self.max_frames_per_delivery)

    def set_current_trajectory(self, trajectory: Trajectory) -> None:
        """
        Set the trajectory for the current delivery.

        Args:
            trajectory: Trajectory to associate with current delivery
        """
        self.current_trajectory = trajectory

    def get_latest_delivery(self) -> Optional[Tuple[Deque[np.ndarray], Optional[Trajectory]]]:
        """
        Get the most recent delivery in the buffer.

        Returns:
            Tuple of (frames, trajectory) for the most recent delivery, or None if empty
        """
        if len(self.deliveries) > 0:
            return self.deliveries[-1]  # Return the last item
        return None

    def get_delivery(self, index: int) -> Optional[Tuple[Deque[np.ndarray], Optional[Trajectory]]]:
        """
        Get a specific delivery from the buffer.

        Args:
            index: Index of the delivery (0 is the oldest, -1 is the most recent)

        Returns:
            Tuple of (frames, trajectory) for the specified delivery, or None if index is invalid
        """
        if 0 <= index < len(self.deliveries):
            return self.deliveries[index]
        if -len(self.deliveries) <= index < 0:  # Handle negative indexing
            return self.deliveries[index]
        return None

    def get_deliveries_count(self) -> int:
        """
        Get the number of stored deliveries.

        Returns:
            Number of deliveries currently in the buffer
        """
        return len(self.deliveries)

    def get_current_frame_count(self) -> int:
        """
        Get the number of frames in the current delivery buffer.

        Returns:
            Number of frames in the current buffer
        """
        return len(self.current_frame_buffer)

    def clear_current_buffer(self) -> None:
        """Clear the current delivery buffer without saving."""
        self.current_frame_buffer.clear()
        self.current_trajectory = None

    def clear_all(self) -> None:
        """Clear all deliveries and the current buffer."""
        self.deliveries.clear()
        self.current_frame_buffer.clear()
        self.current_trajectory = None