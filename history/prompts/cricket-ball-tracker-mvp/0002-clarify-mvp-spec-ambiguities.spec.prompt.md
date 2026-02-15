---
id: 0002
title: Clarify MVP Spec Ambiguities
stage: spec
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: cricket-ball-tracker-mvp
branch: 001-cricket-ball-tracker-mvp
user: saifullah
command: /sp.clarify
labels: ["clarification", "spec", "mvp", "delivery-lifecycle", "config", "camera", "replay", "decisions"]
links:
  spec: specs/001-cricket-ball-tracker-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-cricket-ball-tracker-mvp/spec.md
tests:
  - null
---

## Prompt

/sp.clarify

(Context: User ran clarification workflow on the MVP spec. 5 questions asked and answered covering delivery lifecycle trigger, config persistence, camera position, replay buffer size, and decision trigger mode.)

## Response snapshot

5 clarifications completed and integrated into spec:
1. Delivery lifecycle: auto-detect start/end from ball motion (no manual button)
2. Config persistence: single active config, overwritten on recalibration (no multiple profiles for MVP)
3. Camera position: behind the bowler (ball moves away from camera)
4. Replay buffer: last 2 deliveries only for MVP
5. Decision triggers: wides and caught behind auto-flagged; LBW on-demand via user appeal

Added FR-028 through FR-031. Updated user stories 4 (LBW), 5 (Wide), 6 (Caught Behind). Updated SessionConfig and Delivery entities. Spec status changed from Draft to Clarified.

## Outcome

- ✅ Impact: Spec refined with 5 critical clarifications reducing downstream ambiguity
- 🧪 Tests: N/A — specification phase
- 📁 Files: spec.md updated with Clarifications section, new FRs, updated stories and entities
- 🔁 Next prompts: Run /sp.plan to create implementation plan
- 🧠 Reflection: All 5 questions were high-impact — delivery lifecycle and decision triggers would have caused significant rework if left ambiguous during implementation

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
