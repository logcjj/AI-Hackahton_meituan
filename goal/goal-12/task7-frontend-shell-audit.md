# Task 7 Frontend Shell Audit

Date: 2026-06-24

## Scope

Task 7 replaces the old home-page frontend shell with a full-day delivery replay product shell. It does not complete the later live API wiring, detailed timeline controls, final visual hardening, or optional external engine adapter.

## Implemented

- Added `web_agent_demo/day_replay_frontend.py`.
- Updated `web_agent_demo/server.py` so `render_index()` returns the new full-day replay shell.
- Updated `tests/test_web_agent_demo.py` so the home-page contract validates the new shell and rejects the old sandbox shell.

## Product Shell Evidence

The rendered home page now exposes:

- `id="day-replay-shell"` as the root product shell.
- `id="kpi-strip"` with time saved, cost saved, delivered count, timeout risk, average ETA, and utilization.
- `id="side-by-side-replay"` with `id="greedy-map-panel"` and `id="autosolver-map-panel"`.
- `id="reasoning-flow-panel"` for readable decision flow.
- `id="memory-evolution-panel"` and `id="memory-evolution-stack"` for memory recall, writeback, and future policy shift.
- `id="replay-controls"` with scenario, courier count, order scale, weather, timeline scrubber, play, pause, and compare controls.

The rendered home page no longer exposes:

- `id="simulation-sandbox"`
- `id="simulation-map"`
- `id="algorithm-compare-table"`
- `id="run-compare"`
- legacy `/api/simulation/session`, `/api/simulation/tick`, `/api/compare/run`, `/api/memory/recall`, or `/api/predictor/rank` frontend dependencies.

## Bootstrap Data

The shell embeds a cached deterministic full-day comparison for immediate first paint:

- Seed: `frontend-shell`
- Controls: 18 couriers, 0.38 order scale, mixed weather, weekday congestion.
- Frames: 40
- Orders: 207
- Memory events: 120
- Memory event types: `memory_recall`, `memory_writeback`, `future_policy_shift`
- Baseline algorithm: `nearest_greedy`
- Challenger algorithm: `autosolver_agent`
- Secret handling: `env-only-redacted`

The shell advertises the planned day simulation endpoints:

- `/api/day-simulation/scenarios`
- `/api/day-simulation/run`
- `/api/day-simulation/frame`
- `/api/day-simulation/memory`

## Verification

Commands run:

- `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/server.py tests/test_web_agent_demo.py`
- `uv run --with pytest pytest tests/test_web_agent_demo.py`
- `uv run --with pytest pytest tests/test_web_agent_demo.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- `uv run --with pytest pytest`
- Non-goal/non-output sensitive pattern scan for supplied model/domain/key patterns.
- Static render probe checking new shell, absence of old shell, no `<table>`, no old ReasonGraph/candidate preview markers, full-day bootstrap frames/events, and env-only privacy.
- Playwright CLI desktop load at `127.0.0.1:8787`.
- Playwright CLI mobile resize to `390x844`.

Results:

- `tests/test_web_agent_demo.py`: 14 passed.
- Frontend plus day simulation focused tests: 33 passed.
- Full suite: 99 passed.
- Sensitive pattern scan: no business-code matches.
- Desktop Playwright probe:
  - Page title: `AutoSolver Agent - 全日配送模拟推演`
  - `window.__AUTO_SOLVER_DAY_REPLAY_READY__ === true`
  - Frames: 40
  - KPI rendered: `433.0m`
  - Old shell absent.
  - Console warnings/errors: 0.
  - Side-by-side replay grid rendered as two columns.
- Mobile Playwright probe:
  - Viewport: `390x844`
  - `window.__AUTO_SOLVER_DAY_REPLAY_READY__ === true`
  - Old shell absent.
  - Replay grid rendered as one column.
  - KPI grid rendered as two columns.
  - Body overflow is `auto`, with scrollable document height.
  - Console warnings/errors: 0.

## Residual Risks

- The old HTML body still exists as unreachable legacy code after the new `render_index()` return. Runtime output is replaced, but this can be cleaned in a later code hygiene pass if desired.
- The new shell uses cached embedded bootstrap data for first paint. Live `/api/day-simulation/*` endpoint wiring is still pending for Task 8/9.
- Detailed timeline interactions, map replay controls, and final visual hardening are pending later tasks.

## Decision

Task 7 is accepted. The old frontend shell is no longer rendered, the new product shell centers full-day simulation and algorithm comparison, responsive desktop/mobile load checks pass, and all tests remain green.
