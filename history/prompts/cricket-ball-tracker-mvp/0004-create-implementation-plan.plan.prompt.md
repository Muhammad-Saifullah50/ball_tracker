---
id: 0004
title: Create Implementation Plan
stage: plan
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: cricket-ball-tracker-mvp
branch: 001-cricket-ball-tracker-mvp
user: saifullah
command: /sp.plan
labels: ["plan", "architecture", "tracknet", "yolov8", "kalman", "streamlit", "research"]
links:
  spec: specs/001-cricket-ball-tracker-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-cricket-ball-tracker-mvp/plan.md
  - specs/001-cricket-ball-tracker-mvp/research.md
  - specs/001-cricket-ball-tracker-mvp/data-model.md
  - specs/001-cricket-ball-tracker-mvp/quickstart.md
  - specs/001-cricket-ball-tracker-mvp/contracts/module-interfaces.md
tests:
  - null
---

## Prompt

/sp.plan

(Context: User initiated implementation planning after spec was fully clarified with 31 FRs and 5 clarifications.)

## Response snapshot

Created full implementation plan with 5 artifacts:
1. **plan.md** — Technical context, constitution check (all PASS), project structure (7 modules), 5 architecture decisions (background thread processing, ONNX inference, two-phase calibration, hybrid replay, auto/on-demand decision triggers)
2. **research.md** — 6 research topics: TrackNet v2 (ONNX ~25ms CPU), YOLOv8n (calibration-only), filterpy Kalman filter (6D state), Streamlit architecture (cv2.VideoCapture + background thread + @st.fragment), JSON config persistence, physics-based LBW projection
3. **data-model.md** — 13 entities with fields, types, validation rules, relationships, and state transitions
4. **quickstart.md** — Developer setup guide with dependencies, commands, project structure
5. **contracts/module-interfaces.md** — Python interface contracts for 7 modules (BallDetector, BallTracker, PitchCalibrator, LBWEngine, WideEngine, CaughtBehindEngine, ReplayBuffer, ConfigManager)

Agent context (CLAUDE.md) updated with technology stack.

## Outcome

- ✅ Impact: Full implementation plan ready; all constitution gates PASS; clear modular architecture
- 🧪 Tests: N/A — planning phase
- 📁 Files: 5 artifacts created in specs/001-cricket-ball-tracker-mvp/
- 🔁 Next prompts: Run /sp.tasks to generate actionable implementation tasks
- 🧠 Reflection: Key insight — Streamlit display caps at 10-15fps but processing runs at 30fps via background thread. This is acceptable for MVP. TrackNet CPU inference is borderline (25ms) — ONNX optimization is critical.

## Evaluation notes (flywheel)

- Failure modes observed: Research agents couldn't web fetch (permissions denied) — fell back to knowledge-based research which was sufficient
- Graders run and results (PASS/FAIL): Constitution check — 10/10 PASS pre-design, 8/8 PASS post-design
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
