---
id: "001"
title: "fix-stump-detection-message"
stage: "general"
date_iso: "2026-02-16"
surface: "agent"
model: "claude-opus-4-6"
feature: "none"
branch: "master"
user: "saifullah"
command: "manual-fix"
labels:
  - "bug-fix"
  - "ui"
  - "webcam"
  - "stump-detection"
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files_yaml:
  - "src/ui/pages/1_Setup.py"
tests_yaml:
  - "No specific tests added"
---

# Fix Stump Detection Message Issue

## PROMPT_TEXT
when i try to capture stumps with live camera and then try to capture frame i get a message that for now please upload a screenshot. why is this

## RESPONSE_TEXT
The issue was in the src/ui/pages/1_Setup.py file where the WebRTC implementation had timing issues. When users clicked the "Capture Frame for Stump Detection" button, the system was checking for frame data that might not have been processed yet due to threading delays in the WebRTC callback. This resulted in the fallback message asking users to upload a screenshot.

The fix involved:
1. Adding a proper waiting mechanism that checks the thread-safe container for frame data with a timeout
2. If no detection result was available from the callback, running detection directly on the captured frame
3. Providing better feedback and troubleshooting tips to the user
4. Removing the outdated message that suggested uploading screenshots

## OUTCOME
Users can now properly capture frames from the live camera for stump detection without encountering the fallback message. The system will wait briefly for frame data to be available, and if needed, run detection directly on the captured frame.

## EVALUATION
The fix addresses the core issue of the timing problem in WebRTC frame capture. The user experience is now more consistent and reliable when using the live camera for stump detection during setup.