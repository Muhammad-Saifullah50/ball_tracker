# Cricket Ball Tracker — Features

## Core Features

### 1. Pitch Calibration & Setup
- User inputs pitch length (bowling crease to batting crease) in meters or feet
- Mark or detect stump positions on camera
- Crease line detection/marking
- Wide corridor configuration (off-side and leg-side distances from stumps)
- Wall boundary drawing for caught behind rule
- Camera: single, straight-on position
- One-time setup before play; persist config for reuse

### 2. Ball Detection
- Locate the cricket ball in each video frame
- ML-based object detection (YOLO or similar) fine-tuned for cricket balls
- Handle varying ball colors (red, white, tennis ball, tape ball)
- Robust to backyard conditions (lighting, shadows, background clutter)
- Performance: <33ms per frame (30fps target)

### 3. Ball Tracking
- Connect per-frame detections into continuous trajectory
- Kalman filter or state estimation for prediction and occlusion handling
- Outputs: full trajectory path, speed, swing/deviation, bounce point, impact point
- Handle fast-moving and spinning deliveries

### 4. Impact Detection
- Classify ball contact events: bat, pad, ground, stumps, wall, missed
- Detect trajectory direction/speed changes indicating impact
- Spatial correlation with known reference points (stumps, crease, wall boundary)
- Key events: pitching (bounce), bat contact, pad contact, stump hit, wall hit

### 5. LBW Decision Engine
- Determine where the ball pitched (in line, outside off, outside leg)
- Determine where the ball hit the pad (in line or outside off)
- Predict trajectory post-impact — would it have hit the stumps?
- Output: OUT / NOT OUT with confidence score and visual overlay
- Configurable strictness (stump zone tolerance, pitching rules)

### 6. Wide Detection
- Track where the ball passes the batting crease laterally
- Compare ball position against configurable wide corridor
- Wide corridor: configurable distance either side of stumps
- Camera: straight-on single camera
- Output: WIDE / NOT WIDE with overlay showing corridor and ball path

### 7. Caught Behind — Wall Rule
- Detect edge off the bat (trajectory deflection)
- Track ball after deflection toward wall boundary
- Ball must hit wall directly — any bounce before wall = NOT OUT
- Wall boundary: user-drawn zone on camera frame during setup
- Output: OUT / NOT OUT with confidence and trajectory replay

### 8. Instant Replay System
- On-demand playback of recent deliveries
- Slow motion (0.25x, 0.5x)
- Frame-by-frame stepping
- Trajectory overlay on video
- Decision graphics (ball path, stump zone, impact point, wide corridor)
- Available within 3 seconds of request
- Rolling buffer of recent deliveries

### 9. Rules Engine
- Configurable parameters for all decision modules
- Stump width tolerance (adjustable for skill levels)
- LBW strictness (pitching rules, benefit of the doubt)
- Wide corridor distances
- Edge sensitivity threshold
- Confidence threshold for OUT decisions
- Caught behind: wall boundary zone, direct hit required
- Support for house rules per session

---

## Out of Scope (for now)
- No-ball detection
- Multi-camera 3D triangulation
- Audio-based edge detection (snickometer)
- Player identification / facial recognition
- Cloud processing or remote streaming
- Professional stadium setups

---

## Build Order

```
1. Pitch Calibration & Setup
2. Ball Detection
3. Ball Tracking
4. Impact Detection
5. LBW Engine
6. Wide Detection
7. Caught Behind (Wall Rule)
8. Instant Replay
9. Rules Engine
```

Each feature depends on the ones above it. Calibration is the foundation; detection and tracking feed all decision modules; replay and rules tie everything together.
