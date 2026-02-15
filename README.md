# Cricket Ball Tracker

A computer vision application for home cricket that tracks ball trajectories, provides instant replays, and adjudicates decisions (LBW, caught behind) based on custom rules. Built to resolve disputes during home cricket games.

## Features

- **Ball Detection & Real-time Tracking**: Uses computer vision to detect and track cricket balls with Kalman filter for smooth trajectory prediction
- **Trajectory Analysis**: Calculates speed, swing, spin, and deviation for each delivery
- **Impact Detection**: Identifies when ball makes contact with bat, pad, ground, stumps, or wall
- **Instant Replay System**: Slow motion and multi-angle views with trajectory overlays
- **Automated Decision Engines**:
  - LBW Decision Engine with trajectory prediction
  - Caught Behind Detection (edge detection before catch)
  - Wide Ball Detection based on configured boundaries
- **Configurable Rules Engine**: Adjustable parameters for different skill levels and house rules
- **Stump & Crease Recognition**: Provides reference coordinates for accurate decisions
- **Player Position Tracking**: Detects batsman stance and foot position
- **Match Data Storage**: Statistics and historical delivery data

## Technology Stack

- **Python 3.11+** with OpenCV 4.8+, PyTorch 2.0+, Ultralytics (YOLOv8)
- **TrackNetv2**: For accurate ball detection using 3 consecutive frames
- **Kalman Filter**: For smooth trajectory tracking using filterpy library
- **Streamlit**: For web-based real-time display and user interface
- **ONNX Runtime**: For optimized model inference
- **JSON**: For configuration persistence (no database dependency)

## Architecture

The application is built with a modular architecture:

- `src/detection/`: Ball and stump detection modules
- `src/tracking/`: Trajectory tracking and delivery segmentation
- `src/decision_engine/`: Decision logic for LBW, Wide, and Caught Behind
- `src/replay/`: Replay buffer and rendering
- `src/ui/`: Streamlit-based user interface
- `src/config/`: Configuration management
- `src/models/`: Data models and schemas

## Getting Started

1. **Setup**: Navigate to the Setup page to calibrate your pitch dimensions, detect stumps, draw wall boundaries, and configure wide corridors
2. **Live Tracking**: Start real-time tracking to monitor deliveries and get automated decisions
3. **Replay**: Review deliveries with slow motion and frame-by-frame controls
4. **Rules**: Adjust decision parameters for different skill levels

## Use Cases

This application is designed for:
- Home/backyard cricket games where disputes arise
- Training sessions to analyze deliveries
- Casual games without professional umpires
- Visual verification of close calls

## Performance

- Real-time tracking at 30fps with <33ms per frame processing
- Low memory usage (<2GB during active tracking)
- All processing runs locally with no cloud dependency

## Development

The project follows a Spec-Driven Development (SDD) methodology with:
- Test-driven development (TDD) with 100% coverage for decision engines
- Type hints for all functions
- Conventional commits and feature branches
- Modular design with clear separation of concerns