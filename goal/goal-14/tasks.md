# Goal 14 Tasks

## Task 1 - Goal Setup And Current Map Audit

Status: Completed

Independent verification:
- `goal/goal-14/input.md`, `goal/goal-14/plan.md`, and `goal/goal-14/tasks.md` exist.
- Current map implementation is inspected before code changes.

Work log:
- Created `goal/goal-14/input.md`, `goal/goal-14/plan.md`, and `goal/goal-14/tasks.md` before product code changes.
- Inspected `web_agent_demo/day_replay_frontend.py` and confirmed the current replay panels have no Leaflet/MapLibre runtime object, no real tile URL, and no real map engine state.
- Confirmed current map rendering is CSS schematic only: `.map-stage`, `.district`, `.road`, `.pin`, `.route-svg`, `positionStyle()`, `routePath()` and `stageBaseHtml()` use `screen_x/screen_y` percentages.
- Confirmed backend day simulation payload already contains `lat`/`lng` for merchants, courier positions, order destinations and route polyline points, so a real map engine can render from existing data without changing the backend contract.

Confidence loop:
- 100% confidence for Task 1 scope: the user criticism is validated by source evidence, and the lowest-risk correction is to add a frontend real map engine that consumes existing lat/lng simulation data while preserving schematic fallback.

## Task 2 - Implement Real Map Engine Layer

Status: Pending

Independent verification:
- Frontend includes a real map engine integration and uses lat/lng simulation data.
- Schematic map remains only as fallback, not the primary path.

Work log:
-

Confidence loop:
-

## Task 3 - Tests And Browser Verification

Status: Pending

Independent verification:
- Focused/full tests pass.
- Browser evidence proves real map engine state and visible layers.
- Sensitive scan is clean.

Work log:
-

Confidence loop:
-

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Pending

Independent verification:
- Re-run critical checks after implementation.
- Any defect found is fixed before ending.

Work log:
-

Confidence loop:
-
