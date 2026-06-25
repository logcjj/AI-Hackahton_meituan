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

Status: Completed

Independent verification:
- Frontend includes a real map engine integration and uses lat/lng simulation data.
- Schematic map remains only as fallback, not the primary path.

Work log:
- Added Leaflet 1.9.4 CSS/JS and OpenStreetMap tile configuration to the day replay shell.
- Added a `.real-map-engine` layer inside each map stage and wrapped the previous CSS map in `.schematic-layer` so the CSS map is now a fallback/overlay instead of the primary renderer.
- Added `replayState.realMapEngine` with provider, tile provider, tile URL, status, fallback reason and per-panel runtime handles.
- Implemented `latLng`, `removeRealMapPanel`, `realMapIcon`, `renderRealMapPanel`, and `setRealMapEngineStatus`.
- Rendered merchants, couriers, active orders and route polylines from existing simulation `lat`/`lng` data into two Leaflet map instances, one for greedy and one for AutoSolver.
- Added visible `data-map-engine-status`, `data-tile-provider`, `data-marker-count`, and `data-route-count` attributes so the runtime engine state is inspectable.
- Updated focused web tests to assert Leaflet/OpenStreetMap markers and real-map engine functions.
- Verified with `python3 -m py_compile web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py`.
- Verified with `uv run --with pytest pytest tests/test_web_agent_demo.py`: 15 passed.
- Started local service on `http://127.0.0.1:8794/` and opened it in the system browser.
- Verified in system Chrome via Playwright: `window.L` exists, `engineStatus` is `leaflet-osm`, two Leaflet containers exist, OSM tile images loaded at 256px, marker count is 44, route count is 8, tile errors are 0, console errors are 0.
- Captured browser evidence at `goal/goal-14/task2-real-map-browser.png`.

Confidence loop:
- 100% confidence for Task 2 scope: the primary map renderer is now a real Leaflet/OpenStreetMap runtime using simulation lat/lng data, both comparison panels create real map instances, the old schematic layer is no longer the sole renderer, and automated plus browser verification confirms visible map tiles, markers and routes.

## Task 3 - Tests And Browser Verification

Status: Completed

Independent verification:
- Focused/full tests pass.
- Browser evidence proves real map engine state and visible layers.
- Sensitive scan is clean.

Work log:
- Verified current service is running on `http://127.0.0.1:8794/` and serving the Leaflet/OpenStreetMap map markers.
- Ran full automated suite with `uv run --with pytest pytest`: 103 passed.
- Ran `python3 -m py_compile web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py`: passed.
- Ran business-code sensitive scan excluding `goal/**`, `output/**`, and `.playwright-cli/**` for supplied key/domain/model patterns: zero matches.
- Ran real browser QA in system Chrome using Playwright with normal keyboard/click inputs.
- Verified initial browser state: `window.L` exists, `realMapEngine.status` is `leaflet-osm`, both map panels have Leaflet containers, marker count is 44, route count is 8, tile errors are 0, console/page errors are 0.
- Verified timeline keyboard input updates engine state from `F-TS-1000` to `F-TS-1100`; marker count updates to 46 and route count updates to 10.
- Verified play/pause interaction keeps the Leaflet map engine stable at `leaflet-osm` with non-zero markers/routes.
- Verified viewport has no horizontal overflow and both map regions are visible without clipping in the checked 1600x920 viewport.
- Captured browser audit JSON at `goal/goal-14/task3-browser-audit.json`.
- Captured visual evidence at `goal/goal-14/task3-browser-initial.png` and `goal/goal-14/task3-browser-timeline.png`.

Confidence loop:
- 100% confidence for Task 3 scope: focused and full tests pass, browser evidence proves the real map engine and visible map layers before and after user interaction, screenshots confirm this is not the old schematic-only map, and sensitive business-code scan is clean.

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Pending

Independent verification:
- Re-run critical checks after implementation.
- Any defect found is fixed before ending.

Work log:
-

Confidence loop:
-
