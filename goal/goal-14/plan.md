# Goal 14 Plan - Real Map And Simulation Engine Correction

## 1. Requirement Analysis

The user rejected the current effect because it still looks like a schematic map and does not visibly include a real simulation/map engine.

The target state must improve the current replay product in two concrete ways:

- Real map: the replay panels should render on a real map base layer, not only CSS roads/grids.
- Engine effect: the UI should expose an actual frontend map/simulation engine state and render courier/order/merchant/route layers from the generated lat/lng data.

## 2. Current Context

- Current frontend is `web_agent_demo/day_replay_frontend.py`.
- Current backend day simulation already produces real-ish lat/lng positions in `Position` objects.
- Current frontend renders those positions only through CSS percentage coordinates and schematic roads.
- Current engine adapter code is metadata-only; it does not create a visible runtime engine in the browser.
- The page is currently served locally at root through `web_agent_demo/server.py`.

## 3. Concrete Correction Strategy

Short-term implementation in this goal:

- Add a browser-side real map engine using Leaflet with OpenStreetMap raster tiles.
- Render each replay panel with a Leaflet map instance.
- Keep a CSS schematic fallback only when external tiles or Leaflet fail.
- Use the simulation payload lat/lng positions to render merchant, courier, order markers and assignment routes on the map.
- Update map layers whenever the timeline frame changes, controls rerun, or reasoning highlight changes.
- Surface engine state in the UI: engine provider, tile provider, active layer counts, fallback status and current frame.

Why Leaflet:

- It is lightweight, works with plain HTML, and can use OpenStreetMap tiles without a build step.
- It makes the "real map" visible immediately.
- It does not require a heavyweight SUMO/UXsim install for the frontend map engine.

## 4. Risks

- External CDN/tile network may fail; the page needs a fallback and visible engine status.
- Tests may run offline; static tests should verify the real-engine integration markers without requiring tile downloads.
- Browser verification must confirm a Leaflet object exists and tile layers are present when network is available.
- Need to avoid exposing user-provided secrets.
- Need to preserve existing day-simulation APIs and tests.

## 5. Execution Plan

1. Create Goal 14 docs before code changes.
2. Audit current frontend map rendering and data shape.
3. Add Leaflet CSS/JS includes and map containers inside both replay panels.
4. Implement `initRealMapEngine`, map layer state, marker/route conversion from lat/lng, fallback handling, and engine status rendering.
5. Update tests to assert real map engine markers and old schematic-only implementation is no longer the sole path.
6. Run py_compile, focused tests, full tests, sensitive scan, and browser verification.
7. Commit safe files only.

## 6. Verification

- Static render contains Leaflet CSS/JS, OpenStreetMap tile URL, real-map engine data markers and engine status DOM.
- Focused web tests pass.
- Full test suite passes.
- Browser verification confirms:
  - `window.__AUTO_SOLVER_DAY_REPLAY__.realMapEngine` exists.
  - Both greedy and AutoSolver panels have Leaflet map instances when loaded.
  - Tile layer containers exist or fallback status is explicitly shown.
  - Marker and route layer counts are non-zero.
  - Timeline changes update layer counts and frame id.
  - Console has no errors.
- Sensitive business-code scan finds no supplied model/domain/key patterns.

## 7. Rollback Plan

- If Leaflet fails in browser, keep schematic fallback active and document the failure.
- If integration destabilizes tests, isolate map-engine code behind defensive feature detection.
- Revert only this goal's tracked changes if necessary; do not touch unrelated untracked artifacts.
