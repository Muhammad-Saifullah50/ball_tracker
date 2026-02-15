---
description: "Task list for Cricket Ball Tracker MVP implementation"
---

# Tasks: Cricket Ball Tracker MVP

**Input**: Design documents from `/specs/001-cricket-ball-tracker-mvp/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL for this feature. Only specific decision engine tests are required (per constitution: 100% coverage for decision engine).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan in src/
- [x] T002 Initialize Python 3.11+ project with dependencies from quickstart.md
- [x] T003 [P] Configure linting with ruff and type checking with mypy
- [x] T004 [P] Create requirements.txt with all specified dependencies
- [x] T005 [P] Create config/ directory with gitignore pattern

---
## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 [P] Create base models in src/models/__init__.py
- [x] T007 Create BallDetection model in src/models/ball_detection.py
- [x] T008 Create Trajectory model in src/models/ball_detection.py
- [x] T009 Create PitchConfig model in src/models/calibration.py
- [x] T010 Create StumpPosition model in src/models/calibration.py
- [x] T011 Create WideConfig model in src/models/calibration.py
- [x] T012 Create WallBoundary model in src/models/calibration.py
- [x] T013 Create ImpactEvent model in src/models/delivery.py
- [x] T014 Create Delivery model in src/models/delivery.py
- [x] T015 Create LBWDecision model in src/models/decisions.py
- [x] T016 Create WideDecision model in src/models/decisions.py
- [x] T017 Create CaughtBehindDecision model in src/models/decisions.py
- [x] T018 Create BatsmanDetection model in src/models/session_config.py
- [x] T019 Create SessionConfig model in src/models/session_config.py
- [x] T020 Create ConfigManager in src/config/config_manager.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Pitch Calibration & Setup (Priority: P1) 🎯 MVP

**Goal**: Enable user to set up the system by calibrating pitch dimensions, detecting stumps, drawing wall boundaries, and configuring wide corridors.

**Independent Test**: Can be fully tested by launching the Streamlit UI, entering pitch dimensions, seeing stump detection overlay, drawing wall boundaries, and verifying the configuration persists on reload.

### Implementation for User Story 1

- [x] T021 [P] Create StumpDetector class in src/detection/stump_detector.py
- [x] T022 [P] Create PitchCalibrator class in src/calibration/pitch_calibrator.py
- [x] T023 [P] Create streamlit-drawable-canvas setup in Setup page
- [x] T024 Create YOLOv8 model loading for stump detection
- [x] T025 Implement UI for pitch length input in pages/1_Setup.py
- [x] T026 Implement UI for stump detection and manual adjustment in pages/1_Setup.py
- [x] T027 Implement UI for wide corridor configuration in pages/1_Setup.py
- [x] T028 Implement UI for wall boundary drawing in pages/1_Setup.py
- [x] T029 Implement UI for batsman handedness selection in pages/1_Setup.py
- [x] T030 Save configuration to JSON files via ConfigManager
- [x] T031 Load existing configuration if available in app.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Ball Detection & Trajectory Tracking (Priority: P1)

**Goal**: Continuously process camera feed to detect cricket ball using TrackNet, connect detections into trajectory with Kalman filter, calculate speed, identify bounce point.

**Independent Test**: Can be tested by bowling a ball in front of the camera and verifying the system draws the trajectory path on the video, shows speed, and marks the bounce point.

### Implementation for User Story 2

- [x] T032 Create BallDetector class in src/detection/ball_detector.py
- [x] T033 [P] Create BallTracker class with Kalman filter in src/tracking/ball_tracker.py
- [x] T034 Create DeliverySegmenter class in src/tracking/delivery_segmenter.py
- [x] T035 Load TrackNet ONNX model (placeholder, will be added later)
- [x] T036 Integrate BallDetector and BallTracker into Live Tracking page
- [x] T037 Implement trajectory overlay rendering on video feed
- [x] T038 Implement bounce point detection and marking
- [x] T039 Implement ball speed calculation using calibrated pitch length
- [x] T040 Display trajectory path, speed and bounce point in UI

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Impact Detection (Priority: P2)

**Goal**: Detect when ball makes contact with objects (bat, pad, ground, stumps, wall) by analyzing trajectory changes and record impact location.

**Independent Test**: Can be tested by bowling deliveries that hit different objects (bat, pad, stumps) and verifying the system correctly classifies each impact type and marks the impact point.

### Implementation for User Story 3

- [x] T041 [P] Enhance BallTracker with impact detection logic
- [x] T042 Create impact classification based on velocity change magnitude
- [x] T043 Implement different impact types (bat, pad, ground, stumps, wall)
- [x] T044 Record impact location relative to calibrated reference points
- [x] T045 Add impact visualization to trajectory overlay
- [x] T046 Integrate impact detection with delivery processing pipeline

**Checkpoint**: User Stories 1, 2, and 3 now work independently

---

## Phase 6: User Story 4 - LBW Decision Engine (Priority: P2)

**Goal**: On-demand LBW review analyzing where ball pitched and hit pad, and projecting trajectory to stumps to determine if it would hit them.

**Independent Test**: Can be tested by bowling deliveries that hit the pad and triggering LBW review, then verifying the system shows the correct decision with visual evidence.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T047 [P] [US4] Create test for LBW pitching point analysis in tests/unit/test_decision_engine/test_lbw_engine.py
- [x] T048 [P] [US4] Create test for LBW impact point analysis in tests/unit/test_decision_engine/test_lbw_engine.py
- [x] T049 [P] [US4] Create test for trajectory projection to stumps in tests/unit/test_decision_engine/test_lbw_engine.py
- [x] T050 [P] [US4] Create test for LBW decision output with confidence score in tests/unit/test_decision_engine/test_lbw_engine.py

### Implementation for User Story 4

- [x] T051 Create LBWEngine class in src/decision_engine/lbw_engine.py
- [x] T052 Implement pitching zone analysis logic
- [x] T053 Implement impact zone analysis logic
- [x] T054 Implement trajectory projection to stumps
- [x] T055 Implement off-stump reference adjustment for batsman handedness
- [x] T056 Add LBW appeal button to Live Tracking page
- [x] T057 Display LBW decision with visual overlay showing path and projected trajectory
- [x] T058 Add confidence score to LBW decision output

**Checkpoint**: All decision engine components should have 100% test coverage

---

## Phase 7: User Story 5 - Wide Detection (Priority: P2)

**Goal**: Automatically check if ball passes outside configured wide corridor after each delivery and flag as WIDE.

**Independent Test**: Can be tested by bowling deliveries at varying widths and verifying the system correctly flags wides and non-wides with visual evidence.

### Tests for User Story 5 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T059 [P] [US5] Create test for wide corridor boundary check in tests/unit/test_decision_engine/test_wide_engine.py
- [x] T060 [P] [US5] Create test for ball position at batting crease in tests/unit/test_decision_engine/test_wide_engine.py

### Implementation for User Story 5

- [x] T061 Create WideEngine class in src/decision_engine/wide_engine.py
- [x] T062 Implement ball position check at batting crease against wide lines
- [x] T063 Auto-evaluate wide after each delivery completion
- [x] T064 Display wide decisions with visual evidence on Live Tracking page
- [x] T065 Add wide corridor overlay visualization

**Checkpoint**: Wide detection now works independently

---

## Phase 8: User Story 6 - Caught Behind: Wall Rule (Priority: P2)

**Goal**: Automatically check for caught-behind wall rule: if ball edges bat and hits wall directly without bouncing, declare OUT.

**Independent Test**: Can be tested by edging deliveries toward the wall and verifying the system correctly identifies direct wall hits vs. bounced-then-wall hits.

### Tests for User Story 6 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T066 [P] [US6] Create test for edge detection logic in tests/unit/test_decision_engine/test_caught_behind_engine.py
- [x] T067 [P] [US6] Create test for bounce detection before wall hit in tests/unit/test_decision_engine/test_caught_behind_engine.py
- [x] T068 [P] [US6] Create test for wall boundary check in tests/unit/test_decision_engine/test_caught_behind_engine.py

### Implementation for User Story 6

- [x] T069 Create CaughtBehindEngine class in src/decision_engine/caught_behind_engine.py
- [x] T070 Implement edge detection logic after bat contact
- [x] T071 Implement bounce detection logic between edge and wall hit
- [x] T072 Implement wall boundary check for direct hits
- [x] T073 Auto-evaluate caught-behind after each delivery
- [x] T074 Display caught-behind decisions with visual evidence

**Checkpoint**: All decision engine tests have 100% coverage

---

## Phase 9: User Story 7 - Instant Replay (Priority: P3)

**Goal**: Provide instant replay functionality with slow motion and frame-by-frame controls, storing last 2 deliveries in rolling buffer.

**Independent Test**: Can be tested by bowling a delivery, requesting a replay, and verifying playback controls (slow-mo, frame-step) work with trajectory overlay visible.

### Implementation for User Story 7

- [x] T075 Create ReplayBuffer class in src/replay/replay_buffer.py
- [x] T076 Create ReplayRenderer class in src/replay/replay_renderer.py
- [x] T077 Implement frame buffering during delivery tracking
- [x] T078 Implement slow motion playback at 0.25x and 0.5x speeds
- [x] T079 Implement frame-by-frame stepping functionality
- [x] T080 Create Replay page with playback controls in pages/3_Replay.py
- [x] T081 Add trajectory and decision overlays to replay frames
- [x] T082 Implement rolling buffer for last 2 deliveries

**Checkpoint**: Replay functionality now works independently

---

## Phase 10: User Story 8 - Configurable Rules Engine (Priority: P3)

**Goal**: Allow users to adjust rules parameters through UI including stump tolerance, LBW strictness, wide distances, edge sensitivity, confidence thresholds.

**Independent Test**: Can be tested by changing rules parameters in the UI and verifying subsequent decisions reflect the updated rules.

### Implementation for User Story 8

- [x] T083 Create Rules configuration page in pages/4_Rules.py
- [x] T084 Implement UI for stump width tolerance adjustment
- [x] T085 Implement UI for LBW strictness levels (strict/standard/lenient)
- [x] T086 Implement UI for wide corridor distance adjustment
- [x] T087 Implement UI for edge detection sensitivity
- [x] T088 Implement UI for confidence threshold adjustment
- [x] T089 Apply rule changes to decision engines in real-time

**Checkpoint**: Rules engine now configurable

---

## Phase 11: User Story 9 - Player Detection & Batsman Handedness (Priority: P2)

**Goal**: Use YOLOv8 to detect batsman in camera frame, determine handedness based on stance, allow manual override.

**Independent Test**: Can be tested by having a batsman take stance (left and right) and verifying the system correctly identifies handedness and adjusts the stump reference.

### Tests for User Story 9 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T090 [P] [US9] Create test for batsman detection in tests/unit/test_detection/test_stump_detector.py
- [x] T091 [P] [US9] Create test for handedness classification in tests/unit/test_detection/test_stump_detector.py

### Implementation for User Story 9

- [x] T092 Enhance StumpDetector with batsman detection capability
- [x] T093 Implement handedness classification from bat position relative to body
- [x] T094 Add manual override capability for handedness in UI
- [x] T095 Integrate handedness detection with LBW decision engine
- [x] T096 Display detected/selected handedness in UI with override option

**Checkpoint**: Batsman handedness detection now works

---

## Phase 12: UI Integration & Overlay Rendering

**Goal**: Create overlay rendering system to show all data on video feeds

- [x] T097 Create OverlayRenderer class in src/ui/components/overlay_renderer.py
- [x] T098 Implement trajectory path rendering with OpenCV
- [x] T099 Implement impact point marking with different colors per type
- [x] T100 Implement decision graphics (LBW path, wide lines, etc.)
- [x] T101 Create VideoDisplay component in src/ui/components/video_display.py

**Checkpoint**: All visual overlays now render correctly on video feeds

---

## Phase 13: Main Application & Background Processing

**Goal**: Integrate all modules and implement background CV processing thread

- [x] T102 Implement main Streamlit app in src/ui/app.py
- [x] T103 Create background thread for CV processing with proper synchronization
- [x] T104 Integrate all modules into processing pipeline
- [x] T105 Implement delivery state management
- [x] T106 Handle auto-start/end detection and delivery segmentation
- [x] T107 Implement camera initialization error handling

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T108 [P] Documentation updates in README.md
- [x] T109 Code cleanup and refactoring based on coding standards
- [x] T110 Performance optimization to ensure <33ms per frame
- [x] T111 [P] Additional unit tests in tests/unit/
- [x] T112 Error handling and logging across all modules
- [x] T113 Run quickstart.md validation
- [x] T114 Integration tests for full delivery pipeline in tests/integration/
- [x] T115 Performance tests for ball detection and tracking
- [x] T116 Final end-to-end testing and validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Requires calibration from US1
- **User Story 3 (P3)**: Can start after US2 - Requires ball tracking capability
- **User Story 4 (P2)**: Can start after US1 and US2 - Requires calibration and tracking
- **User Story 5 (P2)**: Can start after US1 and US2 - Requires calibration and tracking
- **User Story 6 (P2)**: Can start after US1, US2, and US3 - Requires impact detection
- **User Story 7 (P3)**: Can start after US2 - Requires tracking
- **User Story 8 (P3)**: Can start after US4, US5, US6 - Requires decision engines
- **User Story 9 (P2)**: Can start after US1 - Requires calibration

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 4

```bash
# Launch all tests for User Story 4 together:
Task: "Create test for LBW pitching point analysis in tests/unit/test_decision_engine/test_lbw_engine.py"
Task: "Create test for LBW impact point analysis in tests/unit/test_decision_engine/test_lbw_engine.py"
Task: "Create test for trajectory projection to stumps in tests/unit/test_decision_engine/test_lbw_engine.py"
Task: "Create test for LBW decision output with confidence score in tests/unit/test_decision_engine/test_lbw_engine.py"

# Launch all implementation for User Story 4 together:
Task: "Create LBWEngine class in src/decision_engine/lbw_engine.py"
Task: "Implement pitching zone analysis logic"
Task: "Implement impact zone analysis logic"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Calibration)
4. Complete Phase 4: User Story 2 (Ball Tracking)
5. **STOP and VALIDATE**: Test US1 and US2 together
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo
3. Add User Story 2 → Test with US1 → Deploy/Demo (MVP!)
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Add User Story 6 → Test independently → Deploy/Demo
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Calibration)
   - Developer B: User Story 2 (Ball Tracking)
   - Developer C: Begin User Story 3 (Impact Detection)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence