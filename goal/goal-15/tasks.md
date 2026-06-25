# Goal 15 Tasks

## Task 1 - Goal Setup And Engine Gap Audit

Status: Completed

Independent verification:
- `goal/goal-15/input.md`, `goal/goal-15/plan.md`, and `goal/goal-15/tasks.md` exist before new code edits continue.
- The current engine gap is documented from source evidence.

Work log:
- Created `goal/goal-15/input.md`, `goal/goal-15/plan.md`, and `goal/goal-15/tasks.md` before continuing engine code changes for this goal.
- Audited current source and confirmed the existing gap is real:
  - `web_agent_demo/day_engine_adapters.py` still described optional engines as adapter seams instead of active runtime integration.
  - `web_agent_demo/day_simulation.py` produced frame-level courier snapshots and route overlays, but not authoritative per-frame runtime traces for the frontend.
  - `web_agent_demo/day_replay_frontend.py` still inferred motion from frame-to-frame deltas and still carried visible label paths in map pins / markers.
- Confirmed optional third-party engines (`uxsim`, `mesa`, `traci`, `cityflow`) are not installed in the current environment, so the correct near-term implementation is to promote the in-process simulator into an explicit runtime engine rather than pretend an external simulator is active.

Confidence loop:
- 100% confidence for Task 1 scope: the source-level audit identifies the exact technical reason the user still perceives the result as fake simulation, and the lowest-risk aligned fix is to make the backend simulator explicit and authoritative instead of adding more frontend-only motion effects.

## Task 2 - Backend CourierSim Trace Runtime

Status: Completed

Independent verification:
- Backend frames include authoritative simulation trace data.
- Engine adapter payload describes an active runtime simulator rather than a metadata-only seam.

Work log:
- Extended `web_agent_demo/day_simulation.py` so each algorithm frame now carries `simulation_trace` with explicit `engine_id`, `engine_provider`, `engine_mode`, emitted tick metadata, event queue, courier tracks, and label-visibility flags.
- Corrected assignment capture and route overlay generation so the backend trace reflects courier start, merchant pickup, and destination dropoff geometry rather than only frame-level snapshots.
- Updated `web_agent_demo/day_engine_adapters.py` to describe the active runtime as `CourierSim event simulator` with `agent-based-discrete-event-simulation` semantics and `courier-agent-sim-v1` payload versioning.
- Verified at runtime from the page bootstrap contract that frame `F-TS-1000` includes `simulation_trace.engine_id = courier-agent-sim-v1`, `engine_provider = AutoSolver CourierSim in-process event simulator`, `emitted_tick_count = 21`, `event_queue_length = 12`, `courier_track_count = 4`, `map_labels_visible = false`, and `road_name_labels = []`.

Confidence loop:
- 100% confidence for Task 2 scope: the backend contract now exposes an explicit simulator runtime and authoritative courier traces, and the browser-visible bootstrap payload proves the frontend is receiving that data rather than inventing motion locally.

## Task 3 - Frontend Trace-Driven Motion And Label Removal

Status: Completed

Independent verification:
- Frontend motion is driven by backend traces.
- Real-map and fallback paths show no visible marker/map labels.

Work log:
- Reworked `web_agent_demo/day_replay_frontend.py` so real-map motion is driven by `algorithmFrame.simulation_trace.courier_tracks` through `animatePanelTracks()` and no longer inferred only from previous/next frame snapshots.
- Updated engine status copy and runtime metadata to surface `CourierSim runtime + Leaflet renderer`, emitted ticks, runtime tick, event count, moving courier count, marker count, and route count.
- Removed visible label text from real-map markers, fallback pins, burst markers, and tile titles; real map now uses the no-label tile provider path `cartodb-nolabels`.
- Browser QA on `http://127.0.0.1:8794/` proved continuous motion inside the same frame: after replay resumed on frame `F-TS-1200`, `runtime tick` advanced from `6` to `13` to `20` while the timeline stayed at `12:00`, and sampled courier marker coordinates changed continuously across the same frame.
- Browser DOM QA confirmed both real markers and fallback pins render with empty text, transparent color, and `font-size: 0px`, and both map stages report `tileProvider = cartodb-nolabels` with no visible map-label text nodes.
- Saved browser evidence to `goal/goal-15/browser-qa-runtime.png` and `goal/goal-15/browser-qa-map-scrolled.png`.

Confidence loop:
- 100% confidence for Task 3 scope: frontend motion is now trace-driven at sub-frame tick resolution, marker movement is continuous in the browser, and both real-map and fallback paths suppress visible names/labels.

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Completed

Independent verification:
- Re-run critical checks after Tasks 1-3.
- Any defect found is fixed before ending the cycle.

Work log:
- Re-read `goal/goal-15/input.md`, `goal/goal-15/plan.md`, and `goal/goal-15/tasks.md` before continuing after context handoff, per workflow requirement.
- Detected that port `8794` was occupied by an older Python demo process, replaced it with a fresh server started from the current worktree, and re-ran browser QA against the updated build.
- Re-validated browser behavior with the visible in-app browser session:
  - engine title shows `CourierSim runtime + Leaflet renderer`;
  - runtime detail shows emitted ticks, runtime tick, events, moving couriers, markers, routes, and frame id;
  - console warnings/errors are empty;
  - the map screenshot shows unlabeled markers on a no-label basemap.
- Re-ran syntax and regression checks:
  - `python3 -m py_compile web_agent_demo/day_simulation.py web_agent_demo/day_engine_adapters.py web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py tests/test_day_simulation_contract.py tests/test_day_simulation_comparison.py tests/test_day_engine_adapters.py`
  - `uv run --with pytest pytest -q`
  - Result: `103 passed in 49.01s`
- Confirmed no further code fixes were required after the comprehensive verification pass.

Confidence loop:
- 100% confidence for the current Goal 15 implementation state: backend trace contract, frontend runtime animation, label suppression, browser behavior, and automated tests all agree, and the specific user complaint about “fake simulation with blinking/jump effects and undeleted names” is directly addressed by measured runtime evidence.
