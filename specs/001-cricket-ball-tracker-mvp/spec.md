# Feature Specification: Cricket Ball Tracker MVP

**Feature Branch**: `001-cricket-ball-tracker-mvp`
**Created**: 2026-02-15
**Status**: Clarified
**Input**: User description: "Cricket Ball Tracker MVP — Pitch Calibration, Ball Detection & Decision System for home cricket dispute resolution"

## Clarifications

### Session 2026-02-15

- Q: How does the system know when a delivery starts and ends? → A: System auto-detects delivery start when the ball enters the frame moving toward the batsman, and delivery end when the ball comes to rest or exits the frame. No manual button press required.
- Q: Single config or multiple saved profiles for pitch setup? → A: Single config (one active setup, overwritten on recalibration). Multiple profiles deferred post-MVP.
- Q: Camera positioned behind the bowler or behind the wicketkeeper? → A: Behind the bowler (ball moves away from camera toward batsman). Matches broadcast main camera angle; optimal for TrackNet and wide detection.
- Q: How many deliveries should the rolling replay buffer hold? → A: Last 2 deliveries only for MVP. Minimal memory footprint.
- Q: Are decisions automatic or on-demand? → A: Wides and caught behind (wall rule) are auto-flagged after each delivery. LBW is on-demand — user must press an appeal button to trigger review.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pitch Calibration & Setup (Priority: P1)

Before a game starts, the user sets up the system by positioning a single straight-on camera, entering the pitch length (bowling crease to batting crease), and calibrating reference points. The system detects stumps and crease lines via camera feed. The user configures wide corridor distances (off-side and leg-side from stumps) and draws the wall boundary zone for the caught-behind rule directly on the camera frame. The user also indicates whether the batsman is left-handed or right-handed. Configuration is saved and can be reused across sessions.

**Why this priority**: Every other feature depends on knowing the pitch dimensions, stump positions, wide corridors, and wall boundaries. Without calibration, no decisions can be made.

**Independent Test**: Can be fully tested by launching the Streamlit UI, entering pitch dimensions, seeing stump detection overlay, drawing wall boundaries, and verifying the configuration persists on reload.

**Acceptance Scenarios**:

1. **Given** the app is launched for the first time, **When** the user enters pitch length in meters or feet, **Then** the system stores the pitch length and displays it on screen.
2. **Given** a camera feed is active, **When** the system processes the frame, **Then** stumps are detected and highlighted with bounding boxes on the video feed.
3. **Given** stumps are detected, **When** the user enters wide corridor distances, **Then** wide lines are drawn on the video overlay at the configured distance from each stump.
4. **Given** the setup screen is active, **When** the user draws a boundary zone on the camera frame, **Then** the wall boundary is stored as a polygon and displayed as an overlay.
5. **Given** a complete configuration exists, **When** the user closes and reopens the app, **Then** the previous configuration is loaded automatically.
6. **Given** the setup screen is active, **When** the user selects batsman handedness (left or right), **Then** the off-stump reference adjusts accordingly for LBW calculations.

---

### User Story 2 - Ball Detection & Trajectory Tracking (Priority: P1)

During play, the system continuously processes the camera feed to detect the cricket ball in each frame using the TrackNet model (which uses 3 consecutive frames). Detected ball positions are connected into a continuous trajectory using a Kalman filter. The system calculates ball speed, identifies swing/deviation, and marks the bounce point (where the ball pitches). The trajectory is displayed as an overlay on the video feed in real time.

**Why this priority**: Ball detection is the core capability. Without knowing where the ball is across frames, no tracking, impact detection, or decisions are possible.

**Independent Test**: Can be tested by bowling a ball in front of the camera and verifying the system draws the trajectory path on the video, shows speed, and marks the bounce point.

**Acceptance Scenarios**:

1. **Given** the camera is active and calibrated, **When** a ball is bowled, **Then** the system detects the ball position in each frame with at least 90% detection rate.
2. **Given** the ball is detected across multiple frames, **When** the trajectory is computed, **Then** a continuous path is drawn as an overlay on the video feed.
3. **Given** a ball is bowled, **When** the ball bounces on the pitch, **Then** the system identifies and marks the bounce point on the trajectory overlay.
4. **Given** a ball is tracked from release to destination, **When** the delivery completes, **Then** the system displays the ball speed in km/h.
5. **Given** a ball that swings or deviates, **When** the trajectory is computed, **Then** the deviation from a straight line is visible in the trajectory overlay.
6. **Given** varying ball types (tape ball, tennis ball, cricket ball), **When** the ball is bowled, **Then** the system detects it regardless of color or size within supported range.

---

### User Story 3 - Impact Detection (Priority: P2)

When the ball makes contact with an object (bat, pad, ground, stumps, or wall), the system detects the impact event by analyzing sudden changes in trajectory direction or speed. The system classifies the type of impact and records the impact location relative to calibrated reference points (stumps, crease, wall boundary).

**Why this priority**: Impact detection feeds directly into all decision modules (LBW, caught behind, bowled). Without knowing what the ball hit, no decisions can be adjudicated.

**Independent Test**: Can be tested by bowling deliveries that hit different objects (bat, pad, stumps) and verifying the system correctly classifies each impact type and marks the impact point.

**Acceptance Scenarios**:

1. **Given** a ball is tracked, **When** the ball hits the bat, **Then** the system detects the impact and classifies it as "bat contact."
2. **Given** a ball is tracked, **When** the ball hits the batsman's pad, **Then** the system detects the impact and classifies it as "pad contact."
3. **Given** a ball is tracked, **When** the ball hits the stumps, **Then** the system detects the impact and classifies it as "stump hit."
4. **Given** a ball is tracked, **When** the ball hits the wall within the drawn boundary, **Then** the system detects the impact and classifies it as "wall hit."
5. **Given** a ball is tracked, **When** no impact occurs (clean miss), **Then** the system does not generate a false impact event.

---

### User Story 4 - LBW Decision Engine (Priority: P2)

When an LBW appeal is made, the user presses the appeal button to trigger the LBW review (on-demand only). The system analyzes: (a) where the ball pitched — in line with stumps, outside off-stump, or outside leg-stump; (b) where the ball hit the pad — in line or outside off-stump; (c) the predicted trajectory — would the ball have gone on to hit the stumps? The system outputs OUT or NOT OUT with a confidence score and a visual overlay showing the ball path, impact point, pitching point, and projected path to stumps. The off-stump reference automatically adjusts based on batsman handedness.

**Why this priority**: LBW is the most common and contentious dispute in home cricket. This is the primary value proposition of the product.

**Independent Test**: Can be tested by bowling deliveries that hit the pad and triggering LBW review, then verifying the system shows the correct decision with visual evidence.

**Acceptance Scenarios**:

1. **Given** a delivery hits the pad, **When** the user triggers LBW review, **Then** the system displays where the ball pitched relative to the stumps.
2. **Given** the ball pitched outside leg-stump, **When** LBW is reviewed, **Then** the decision is NOT OUT (pitched outside leg).
3. **Given** the ball pitched in line and hit the pad in line, **When** trajectory projection shows the ball hitting the stumps, **Then** the decision is OUT with a confidence score.
4. **Given** the ball pitched in line and hit the pad in line, **When** trajectory projection shows the ball missing the stumps, **Then** the decision is NOT OUT (missing stumps).
5. **Given** the ball hit the pad outside off-stump, **When** the batsman was playing a shot, **Then** the decision is NOT OUT (impact outside off).
6. **Given** a right-handed batsman, **When** LBW is reviewed, **Then** the off-stump reference is on the batsman's right side.
7. **Given** a left-handed batsman, **When** LBW is reviewed, **Then** the off-stump reference flips to the batsman's left side.
8. **Given** any LBW decision, **When** the result is displayed, **Then** a visual overlay shows the ball path, pitching point, impact point, and projected trajectory to stumps.

---

### User Story 5 - Wide Detection (Priority: P2)

After each delivery, the system automatically checks whether the ball passed outside the configured wide corridor (auto-flagged, no user action needed). The system compares the ball's lateral position at the batting crease against the wide lines. If the ball passed outside the corridor, it is flagged as WIDE with a visual overlay showing the wide corridor and ball path.

**Why this priority**: Wides are frequently disputed in home cricket, especially with varying pitch widths and informal rules.

**Independent Test**: Can be tested by bowling deliveries at varying widths and verifying the system correctly flags wides and non-wides with visual evidence.

**Acceptance Scenarios**:

1. **Given** a delivery passes outside the configured wide line on the off-side, **When** the ball crosses the batting crease, **Then** the system flags it as WIDE.
2. **Given** a delivery passes outside the configured wide line on the leg-side, **When** the ball crosses the batting crease, **Then** the system flags it as WIDE.
3. **Given** a delivery passes within the wide corridor, **When** the ball crosses the batting crease, **Then** the system does not flag it as a wide.
4. **Given** any wide decision, **When** the result is displayed, **Then** a visual overlay shows the wide corridor lines and the ball's path at the batting crease.

---

### User Story 6 - Caught Behind: Wall Rule (Priority: P2)

After each delivery, the system automatically checks for caught-behind wall rule (auto-flagged, no user action needed). When the ball edges the bat and travels toward the wall behind the wicket, the system tracks the ball after the edge. If the ball hits the wall within the user-drawn boundary zone directly (without bouncing on the ground first), the system declares OUT. If the ball bounces before hitting the wall, it is NOT OUT. The system provides visual evidence showing the edge detection, ball path after edge, and whether a ground bounce occurred.

**Why this priority**: The wall-catch rule is unique to home cricket and is a major source of disputes. Visual evidence settles these arguments definitively.

**Independent Test**: Can be tested by edging deliveries toward the wall and verifying the system correctly identifies direct wall hits vs. bounced-then-wall hits.

**Acceptance Scenarios**:

1. **Given** a ball edges the bat, **When** the ball hits the wall boundary directly without bouncing, **Then** the decision is OUT.
2. **Given** a ball edges the bat, **When** the ball bounces on the ground before hitting the wall, **Then** the decision is NOT OUT.
3. **Given** a ball edges the bat, **When** the ball hits the wall outside the drawn boundary zone, **Then** the decision is NOT OUT.
4. **Given** a ball does not edge the bat, **When** it hits the wall, **Then** no caught-behind decision is triggered.
5. **Given** any caught-behind decision, **When** the result is displayed, **Then** visual evidence shows the edge point, ball trajectory after edge, and whether ground contact occurred before wall contact.

---

### User Story 7 - Instant Replay (Priority: P3)

After any delivery, the user can request an instant replay. The system plays back the delivery in slow motion (0.25x or 0.5x speed) with trajectory overlays, impact markers, and decision graphics. Frame-by-frame stepping is available. The replay is available within 3 seconds of the request. A rolling buffer stores recent deliveries for replay access.

**Why this priority**: Replay provides visual evidence for manual review, even when automated decisions are uncertain. However, the core decision engines deliver more direct value.

**Independent Test**: Can be tested by bowling a delivery, requesting a replay, and verifying playback controls (slow-mo, frame-step) work with trajectory overlay visible.

**Acceptance Scenarios**:

1. **Given** a delivery has been bowled, **When** the user requests a replay, **Then** the replay is available within 3 seconds.
2. **Given** a replay is playing, **When** the user selects 0.25x speed, **Then** the replay plays at quarter speed with smooth playback.
3. **Given** a replay is playing, **When** the user selects 0.5x speed, **Then** the replay plays at half speed.
4. **Given** a replay is playing, **When** the user steps frame-by-frame, **Then** each frame advances one at a time with trajectory overlay visible.
5. **Given** a replay is playing, **When** a decision was made (LBW, wide, caught behind), **Then** the decision graphics are overlaid on the replay.
6. **Given** multiple deliveries have been bowled, **When** the user scrolls through recent deliveries, **Then** the last 2 deliveries in the rolling buffer are accessible for replay.

---

### User Story 8 - Configurable Rules Engine (Priority: P3)

Before or during a session, the user can adjust rules parameters through the Streamlit UI. This includes: stump width tolerance (wider for beginners), LBW strictness, wide corridor distances, edge detection sensitivity, and the confidence threshold required for an OUT decision. Settings are saved per session and can be adjusted between deliveries.

**Why this priority**: Configurability ensures the system works for different skill levels and house rules, but the system is functional with sensible defaults even without customization.

**Independent Test**: Can be tested by changing rules parameters in the UI and verifying subsequent decisions reflect the updated rules.

**Acceptance Scenarios**:

1. **Given** the rules configuration screen, **When** the user increases stump width tolerance, **Then** the LBW engine uses the wider stump zone for trajectory projection.
2. **Given** the rules configuration screen, **When** the user changes wide corridor distance, **Then** subsequent wide decisions use the updated distance.
3. **Given** the rules configuration screen, **When** the user adjusts the confidence threshold for OUT, **Then** decisions below the threshold are reported as NOT OUT (insufficient confidence).
4. **Given** rules have been configured, **When** the user starts a new session, **Then** default rules are loaded unless the user explicitly loads a saved configuration.

---

### User Story 9 - Player Detection & Batsman Handedness (Priority: P2)

The system uses YOLOv8 to detect the batsman in the camera frame. It determines whether the batsman is left-handed or right-handed based on their stance. This information is used to set the correct off-stump reference for LBW decisions. The user can also manually override the detected handedness.

**Why this priority**: Batsman handedness directly affects LBW decisions (off-stump is on opposite sides for left and right-handers). Incorrect handedness leads to wrong LBW calls.

**Independent Test**: Can be tested by having a batsman take stance (left and right) and verifying the system correctly identifies handedness and adjusts the stump reference.

**Acceptance Scenarios**:

1. **Given** a right-handed batsman takes stance, **When** the system processes the frame, **Then** the batsman is detected and handedness is classified as right-handed.
2. **Given** a left-handed batsman takes stance, **When** the system processes the frame, **Then** the batsman is detected and handedness is classified as left-handed.
3. **Given** the system detects handedness incorrectly, **When** the user manually overrides the handedness, **Then** the system uses the manual selection for all subsequent decisions.
4. **Given** a batsman is detected, **When** handedness is determined, **Then** the off-stump reference for LBW automatically adjusts to the correct side.

---

### Edge Cases

- What happens when the camera feed drops or freezes mid-delivery? The system must discard the incomplete delivery and warn the user rather than produce a wrong decision.
- What happens when the ball goes out of frame during a delivery? The system must mark the trajectory as incomplete and indicate low confidence on any subsequent decision.
- What happens when lighting conditions change suddenly (cloud cover, sunset)? The system should continue tracking with degraded confidence rather than producing false detections.
- What happens when multiple objects resemble the ball (e.g., a second ball on the pitch)? The system should track the moving object and ignore stationary ones.
- What happens when the batsman obscures the ball from the camera angle? The system should use trajectory prediction (Kalman filter) to interpolate through the occlusion.
- What happens when the wall boundary is partially outside the camera frame? The system should warn during setup that the boundary must be fully visible.
- What happens when the ball is bowled but no stumps are detected? The system must warn the user to recalibrate before adjudicating decisions.
- What happens when pitch length is entered as zero or negative? The system must reject invalid inputs with a clear error message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept pitch length input in meters or feet and convert between units.
- **FR-002**: System MUST detect stump positions in the camera frame using YOLOv8 and display bounding boxes.
- **FR-003**: System MUST allow the user to draw wall boundary zones on the camera frame and store them as polygons.
- **FR-004**: System MUST accept wide corridor distances (off-side and leg-side) relative to stump positions.
- **FR-005**: System MUST detect the cricket ball in each frame using TrackNet (3-frame input) with at least 90% detection rate under normal conditions.
- **FR-006**: System MUST connect per-frame ball detections into a continuous trajectory using a Kalman filter.
- **FR-007**: System MUST calculate ball speed in km/h using the calibrated pitch length for pixel-to-real-world conversion.
- **FR-008**: System MUST detect the ball's bounce point (where it pitches) from trajectory analysis.
- **FR-009**: System MUST detect impact events (bat, pad, stumps, wall, ground) from trajectory changes.
- **FR-010**: System MUST classify impact types and record impact location relative to calibrated reference points.
- **FR-011**: System MUST evaluate LBW appeals by analyzing pitching point, impact point, and projected trajectory to stumps.
- **FR-012**: System MUST adjust the off-stump reference based on batsman handedness (left or right).
- **FR-013**: System MUST predict post-impact ball trajectory using physics-based extrapolation (gravity, swing continuation).
- **FR-014**: System MUST flag deliveries as WIDE when the ball passes outside the configured wide corridor at the batting crease.
- **FR-015**: System MUST detect edges (bat contact followed by trajectory deflection) for caught-behind wall rule.
- **FR-016**: System MUST determine whether the ball hit the wall directly or bounced first after an edge.
- **FR-017**: System MUST provide instant replay with slow motion (0.25x, 0.5x) and frame-by-frame stepping.
- **FR-018**: System MUST overlay trajectory paths, impact points, decision graphics, and wide corridor lines on video.
- **FR-019**: System MUST provide configurable rules parameters (stump tolerance, LBW strictness, wide distances, edge sensitivity, confidence threshold).
- **FR-020**: System MUST persist calibration and rules configuration across sessions.
- **FR-021**: System MUST output every decision with a confidence score and visual evidence.
- **FR-022**: System MUST detect batsman presence and classify handedness (left/right) using YOLOv8.
- **FR-023**: System MUST allow manual override of detected batsman handedness.
- **FR-024**: System MUST maintain a rolling buffer of the last 2 deliveries for replay access.
- **FR-025**: System MUST display all overlays and decisions through a Streamlit-based UI.
- **FR-026**: System MUST process all data locally with no cloud or network dependency for core features.
- **FR-027**: System MUST gracefully handle camera feed interruptions with user warnings instead of wrong decisions.
- **FR-028**: System MUST auto-detect delivery start when the ball enters the frame moving toward the batsman, and delivery end when the ball comes to rest or exits the frame.
- **FR-029**: System MUST segment the video stream into individual deliveries based on auto-detected start/end boundaries for tracking, decisions, and replay.
- **FR-030**: System MUST auto-evaluate wide and caught-behind (wall rule) decisions after each delivery without user intervention.
- **FR-031**: System MUST evaluate LBW only when the user explicitly triggers an appeal via the UI.

### Key Entities

- **PitchConfig**: Pitch length, unit (meters/feet), bowling crease position, batting crease position. Related to stump and crease positions.
- **StumpPosition**: Detected stump coordinates (off-stump, middle, leg-stump) for both ends. Derived from YOLOv8 detection, anchored to pitch config.
- **WideConfig**: Off-side distance, leg-side distance from stumps. Used to draw wide corridor overlay and adjudicate wides.
- **WallBoundary**: User-drawn polygon defining the catch zone on the wall behind the wicket.
- **BallDetection**: Per-frame ball position (x, y coordinates, confidence score, timestamp). Produced by TrackNet.
- **Trajectory**: Ordered sequence of BallDetections forming a delivery path. Includes speed, deviation, bounce point, and impact points.
- **ImpactEvent**: Type (bat, pad, ground, stumps, wall), location, frame number, confidence. Derived from trajectory analysis.
- **LBWDecision**: Pitching zone, impact zone, projected path, handedness reference, result (OUT/NOT OUT), confidence score.
- **WideDecision**: Ball position at batting crease, wide corridor reference, result (WIDE/NOT WIDE), confidence score.
- **CaughtBehindDecision**: Edge detected (yes/no), ball path after edge, ground bounce before wall (yes/no), wall hit within boundary (yes/no), result (OUT/NOT OUT), confidence score.
- **Delivery**: Complete record of one ball — trajectory, impact events, decisions, replay buffer reference. Lifecycle: auto-detected start (ball enters frame moving) → tracking → end (ball at rest or exits frame).
- **SessionConfig**: All rules parameters, pitch config, wide config, wall boundary, batsman handedness. Single active config persisted locally; overwritten on recalibration. Multiple profiles deferred post-MVP.
- **BatsmanDetection**: Batsman bounding box, handedness classification (left/right), confidence, manual override flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ball detection rate of 90% or higher under normal daylight conditions across supported ball types (tape ball, tennis ball, cricket ball).
- **SC-002**: Ball tracking produces a continuous trajectory for at least 85% of deliveries without gaps requiring manual intervention.
- **SC-003**: LBW decisions match the expected outcome (validated against known test deliveries) at least 85% of the time.
- **SC-004**: Wide decisions correctly classify deliveries as wide or not-wide at least 90% of the time against configured corridor.
- **SC-005**: Caught-behind wall rule correctly distinguishes direct wall hits from bounced-then-wall hits at least 85% of the time.
- **SC-006**: Instant replay is available within 3 seconds of user request.
- **SC-007**: Video processing maintains at least 30 frames per second during active tracking on consumer hardware (standard laptop/desktop with webcam).
- **SC-008**: System memory usage stays below 2GB during active tracking sessions.
- **SC-009**: All decisions display a confidence score and visual evidence overlay — no black-box outcomes.
- **SC-010**: Pitch calibration and setup completes in under 5 minutes for a first-time user.
- **SC-011**: Saved configuration loads in under 2 seconds on subsequent sessions.
- **SC-012**: Batsman handedness detection is correct at least 80% of the time, with manual override always available.

## Assumptions

- The camera is positioned straight-on behind the bowler (ball moves away from camera toward batsman) for optimal ball tracking and wide adjudication.
- Lighting is natural daylight or adequate artificial light — the system is not expected to work in darkness or extreme low light.
- One camera is used for MVP; dual-camera 3D triangulation is out of scope.
- The pitch surface is relatively flat and the ball behaves predictably (no extreme rough surfaces).
- Users have basic familiarity with using a laptop and webcam — detailed technical knowledge is not required.
- Consumer hardware means a standard laptop/desktop (2020 or newer) with a USB webcam or smartphone camera.
- TrackNet model will be pre-trained or fine-tuned before deployment — training pipeline is out of scope for MVP.
- YOLOv8 model will use pre-trained weights with fine-tuning for stumps and batsman detection.
- Ball speed calculation assumes the ball travels approximately in the plane of the pitch (2D projection from single camera).

## Constraints

- Single camera only — no multi-camera synchronization.
- All processing must run locally — no cloud APIs or network calls for core features.
- Consumer hardware only — must run on a standard laptop without dedicated GPU (CPU inference).
- No audio input — all detection is vision-based only.
- No no-ball detection in this version.
- No facial recognition or player identification beyond batsman handedness.

## Out of Scope

- No-ball detection (front-foot or height).
- Multi-camera 3D trajectory reconstruction.
- Audio-based edge detection (snickometer).
- Player identification or facial recognition.
- Cloud processing, streaming, or remote access.
- Professional stadium or broadcast integration.
- Training pipeline for ML models (pre-trained models assumed).
- Score tracking or match management.
- Bowling analysis (action, arm speed, release point).
