# Goal 13 Requirement Matrix

Status terms:
- `Unverified`: source or test exists, but the current audit has not yet proven runtime behavior.
- `Needs stronger evidence`: existing evidence is indirect or too narrow.
- `Pass`: current-state evidence directly proves the requirement.
- `Fail`: current-state evidence contradicts the requirement.

## Sources Used To Derive Requirements

- `goal/goal-12/plan.md`
- `goal/goal-12/tasks.md`
- `web_agent_demo/day_simulation.py`
- `web_agent_demo/day_replay_frontend.py`
- `web_agent_demo/day_engine_adapters.py`
- `web_agent_demo/server.py`
- `tests/test_web_agent_demo.py`
- `tests/test_day_simulation_*.py`
- `tests/test_day_engine_adapters.py`

## Requirements

| ID | Requirement | Current source indicators | Evidence required before completion decision | Status |
| --- | --- | --- | --- | --- |
| R1 | Goal 13 process docs exist before product code changes. | `goal/goal-13/input.md`, `plan.md`, `tasks.md` created before any product edit. | File existence plus git diff showing no product-code modifications before docs. | Pass |
| R2 | Root frontend fully discards old small sandbox UI. | `server.render_index()` returns `render_day_replay_index()`; old HTML block was removed in `1b20ee4`. | Render `/` and verify old markers are absent from actual HTML and browser DOM, not just source grep. | Pass |
| R3 | Product is a full-day simulation replay, not only tick sandbox. | `day_replay_frontend.py` uses `data-product-mode="full-day-simulation-replay"` and bootstraps `run_full_day_comparison()`. | Static bootstrap payload and browser runtime must expose many frames spanning day time slices. | Pass |
| R4 | Simulation generates realistic day coverage: merchants, couriers, orders, phases, weather, congestion, shocks, and supply changes. | `generate_full_day_world()` and generator tests exist. | Independent probe must validate required phases and shock types in current payload. | Pass |
| R5 | Greedy and AutoSolver compare on the exact same order stream. | `run_full_day_comparison()` builds `baseline_run` and `challenger_run`; comparison tests exist. | Probe must compare order ids/assignment frames and prove same-stream fairness. | Pass |
| R6 | Metrics quantify why AutoSolver is better. | `DayMetrics`, `MetricDelta`, KPI cards for time/cost/delivered/risk/ETA/utilization. | Unit/API/browser evidence must show positive or directionally correct saved time/cost/risk deltas and visible KPI updates. | Pass |
| R7 | Side-by-side replay is visible and synchronized. | `side-by-side-replay`, `greedy-map`, `autosolver-map`, shared `timeline-scrubber`. | Browser evidence must show both panels present, same frame, aligned active orders, and timeline changes both views. | Pass |
| R8 | Replay controls work. | Scenario, courier count, order scale, weather, speed, play/pause, timeline controls exist in frontend. | Browser interaction must prove scrub, play, speed, and control-triggered API rerun update state without console errors. | Pass |
| R9 | Algorithm reasoning is readable and tied to decision points. | Reasoning timeline cards render candidate scores, selected strategy, highlighted orders/couriers. | Browser interaction must prove reasoning cards update highlights and decision summary. | Pass |
| R10 | Memory self-evolution is demonstrated. | `memory_recall`, `memory_writeback`, `future_policy_shift` events in backend and frontend. | API/browser evidence must show all event types, frame links, confidence changes, and visible memory cards. | Pass |
| R11 | External LLM predictor handling is env-only and redacted. | Day simulation evidence uses `env-only-redacted`; tests cover env hook/fallback. | Sensitive scans and API payload probes must show no raw model/key/domain in business code or serialized payloads. | Pass |
| R12 | Optional external engine seam exists without hard dependency. | `day_engine_adapters.py`, `/api/day-simulation/engines`, native fallback. | API and tests must prove optional engines are metadata-only and unavailable/unknown adapters fall back to `native-local`. | Pass |
| R13 | Day-simulation API endpoints are healthy. | GET scenarios/engines/frame/memory and POST run handlers exist. | Live server or direct handler probes must validate status, payload shape, and non-error responses. | Pass |
| R14 | Existing backend compatibility remains intact. | Legacy `/api/compare/run`, simulation endpoints, and tests remain. | Full test suite plus targeted scan should confirm compatibility was not broken by frontend replacement. | Pass |
| R15 | Desktop and mobile layouts are usable. | Responsive CSS and prior screenshots exist. | Fresh browser audit must validate dimensions, no collapsed maps, no horizontal overflow, and readable panels. | Pass |
| R16 | Browser runtime is clean. | Prior browser audits reported no console/network errors. | Fresh browser run must collect console errors/warnings and failed network responses. | Pass |
| R17 | Tests are green and meaningful for the above scope. | 103-test suite exists, focused day replay tests exist. | Re-run compile, focused tests, full tests, and map each test group to requirements. | Pass |
| R18 | Goal 12 completion archive is accurate or corrected. | `goal/goal-12/COMPLETED.md`, `final-review-completion-audit.md`. | After R1-R17, decide whether archive can stand or needs correction. | Unverified |

## Initial Assessment

Tasks 2 and 3 prove static/backend/API/test/security and browser runtime requirements. R18 remains open until the debug cycle and final audit decide whether the previous completion archive stands or needs correction.
