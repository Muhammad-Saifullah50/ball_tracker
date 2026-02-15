# Data Model: Cricket Ball Tracker MVP

**Date**: 2026-02-15
**Branch**: `001-cricket-ball-tracker-mvp`

## Entities

### PitchConfig

Represents the physical pitch dimensions entered during calibration.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| pitch_length | float | Distance between bowling and batting crease | > 0, max 30.0 |
| unit | str | "meters" or "feet" | enum: ["meters", "feet"] |
| bowling_crease_px | tuple[int, int] | Pixel coordinates of bowling crease center | within frame bounds |
| batting_crease_px | tuple[int, int] | Pixel coordinates of batting crease center | within frame bounds |
| pixels_per_meter | float | Calculated: pixel distance / real distance | > 0 |

**Derived**: `pixels_per_meter = euclidean_distance(bowling_crease_px, batting_crease_px) / pitch_length_in_meters`

---

### StumpPosition

Detected or manually marked stump coordinates.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| off_stump_px | tuple[int, int] | Pixel position of off-stump (top) | within frame |
| middle_stump_px | tuple[int, int] | Pixel position of middle-stump (top) | within frame |
| leg_stump_px | tuple[int, int] | Pixel position of leg-stump (top) | within frame |
| stump_width_px | int | Pixel distance off-stump to leg-stump | > 0 |
| stump_height_px | int | Pixel height of stumps | > 0 |
| confidence | float | Detection confidence (1.0 if manually set) | 0.0 to 1.0 |
| end | str | "batting" or "bowling" | enum |

**Relationships**: Belongs to PitchConfig. Detected via YOLOv8 during calibration.

---

### WideConfig

Configurable wide corridor distances.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| off_side_distance_m | float | Wide distance from off-stump (meters) | >= 0 |
| leg_side_distance_m | float | Wide distance from leg-stump (meters) | >= 0 |
| off_line_px | tuple[tuple[int,int], tuple[int,int]] | Calculated pixel line for off-side wide | computed |
| leg_line_px | tuple[tuple[int,int], tuple[int,int]] | Calculated pixel line for leg-side wide | computed |

**Derived from**: StumpPosition + PitchConfig.pixels_per_meter

---

### WallBoundary

User-drawn polygon defining the catch zone behind the wicket.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| polygon_points | list[tuple[int, int]] | Ordered vertices of the boundary polygon | >= 3 points |
| is_valid | bool | All points within camera frame | computed |

**Source**: Drawn via streamlit-drawable-canvas, stored as JSON.

---

### BallDetection

Per-frame ball detection from TrackNet.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| frame_number | int | Sequential frame index within delivery | >= 0 |
| x | float | Horizontal pixel position | within frame |
| y | float | Vertical pixel position | within frame |
| confidence | float | TrackNet heatmap peak confidence | 0.0 to 1.0 |
| timestamp_ms | float | Frame timestamp in milliseconds | >= 0 |
| visibility | str | "visible", "occluded", or "absent" | enum |

---

### Trajectory

Ordered sequence of BallDetections forming a delivery path.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| delivery_id | str | Unique identifier for the delivery | UUID |
| detections | list[BallDetection] | Ordered ball positions | >= 1 |
| speed_kmh | float | Calculated ball speed | >= 0 |
| bounce_point | BallDetection \| None | Detection where ball pitches | nullable |
| impact_points | list[ImpactEvent] | All detected impacts | list |
| deviation_px | float | Max lateral deviation from straight line | >= 0 |
| is_complete | bool | Full trajectory captured (no gaps) | bool |
| kalman_state | dict | Final Kalman filter state vector | internal |

**State transitions**: building → complete → analyzed

---

### ImpactEvent

A detected impact during a delivery.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| impact_type | str | "bat", "pad", "ground", "stumps", "wall" | enum |
| position_px | tuple[int, int] | Pixel location of impact | within frame |
| frame_number | int | Frame where impact detected | >= 0 |
| confidence | float | Impact detection confidence | 0.0 to 1.0 |
| velocity_change | float | Magnitude of velocity change at impact | >= 0 |
| is_in_boundary | bool | Impact within wall boundary (if wall) | bool |

**Detection method**: Kalman filter acceleration spike > threshold

---

### LBWDecision

Result of an on-demand LBW review.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| delivery_id | str | Reference to delivery | UUID |
| pitching_zone | str | "in_line", "outside_off", "outside_leg" | enum |
| impact_zone | str | "in_line", "outside_off" | enum |
| projected_hitting_stumps | bool | Would ball have hit stumps? | bool |
| projected_path | list[tuple[int, int]] | Pixel path from impact to stumps | list |
| stump_zone_hit | str \| None | "off", "middle", "leg" or None | nullable enum |
| handedness | str | "right" or "left" | enum |
| result | str | "OUT" or "NOT_OUT" | enum |
| reason | str | Human-readable explanation | non-empty |
| confidence | float | Decision confidence score | 0.0 to 1.0 |

---

### WideDecision

Auto-evaluated wide result after each delivery.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| delivery_id | str | Reference to delivery | UUID |
| ball_position_at_crease_px | tuple[int, int] | Ball position when crossing batting crease | within frame |
| off_line_distance_px | float | Pixel distance from off-side wide line | float |
| leg_line_distance_px | float | Pixel distance from leg-side wide line | float |
| result | str | "WIDE" or "NOT_WIDE" | enum |
| side | str \| None | "off" or "leg" (if wide) | nullable enum |
| confidence | float | Decision confidence score | 0.0 to 1.0 |

---

### CaughtBehindDecision

Auto-evaluated caught-behind (wall rule) result.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| delivery_id | str | Reference to delivery | UUID |
| edge_detected | bool | Was bat contact detected before wall hit? | bool |
| edge_point_px | tuple[int, int] \| None | Where edge occurred | nullable |
| ground_bounce_before_wall | bool | Did ball bounce before hitting wall? | bool |
| wall_hit_in_boundary | bool | Did ball hit within drawn boundary? | bool |
| result | str | "OUT" or "NOT_OUT" | enum |
| reason | str | Human-readable explanation | non-empty |
| confidence | float | Decision confidence score | 0.0 to 1.0 |

---

### Delivery

Complete record of one ball bowled.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| delivery_id | str | Unique identifier | UUID |
| timestamp_start | float | Start time (ball enters frame) | >= 0 |
| timestamp_end | float | End time (ball at rest or exits frame) | > start |
| trajectory | Trajectory | Full ball trajectory | required |
| impact_events | list[ImpactEvent] | All impacts during delivery | list |
| lbw_decision | LBWDecision \| None | LBW review result (if appealed) | nullable |
| wide_decision | WideDecision | Auto-evaluated wide result | required |
| caught_behind_decision | CaughtBehindDecision | Auto-evaluated caught behind | required |
| frames | list[ndarray] | Raw frames for replay (JPEG compressed) | buffer |

**Lifecycle**: detecting → tracking → complete → decisions_applied

---

### BatsmanDetection

Detected batsman position and handedness.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| bounding_box | tuple[int, int, int, int] | x, y, width, height | within frame |
| handedness | str | "right" or "left" | enum |
| handedness_confidence | float | Auto-detection confidence | 0.0 to 1.0 |
| is_manual_override | bool | User manually set handedness | bool |

---

### SessionConfig

All configuration for a session, persisted as JSON.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| pitch_config | PitchConfig | Pitch dimensions | required |
| batting_stumps | StumpPosition | Batting end stump positions | required |
| wide_config | WideConfig | Wide corridor distances | required |
| wall_boundary | WallBoundary | Catch zone polygon | required |
| batsman_handedness | str | "right" or "left" | enum |
| stump_width_tolerance | float | Multiplier for LBW stump zone | 0.5 to 3.0 |
| lbw_strictness | str | "strict", "standard", "lenient" | enum |
| edge_sensitivity | float | Threshold for edge detection | 0.0 to 1.0 |
| confidence_threshold | float | Minimum confidence for OUT | 0.0 to 1.0 |
| camera_index | int | OpenCV camera device index | >= 0 |
| resolution | tuple[int, int] | Camera resolution (width, height) | positive |

**Persistence**: Single active config in `config/` directory as JSON files. Overwritten on recalibration.

---

## Entity Relationships

```
SessionConfig
├── PitchConfig
│   └── pixels_per_meter (derived)
├── StumpPosition (batting end)
├── WideConfig (derived from StumpPosition + PitchConfig)
├── WallBoundary
└── BatsmanDetection

Delivery
├── Trajectory
│   ├── BallDetection[] (from TrackNet)
│   └── ImpactEvent[] (from Kalman filter analysis)
├── WideDecision (auto-evaluated)
├── CaughtBehindDecision (auto-evaluated)
└── LBWDecision (on-demand, nullable)
```
