# Debug Cycle 3 Audit - Tasks 7-9

## Scope

This audit covers the full-day replay frontend shell, side-by-side replay controls, KPI savings, reasoning flow, and decision highlights added in Tasks 7-9.

## Issue Found And Fixed

- Found a real desktop layout defect during browser audit: at `1440x900`, `.map-stage` height collapsed to `0px`.
- Root cause: the shell had five direct grid children but only four explicit grid rows. After adding replay minimum height, the control row consumed the large replay row and pushed the maps out incorrectly.
- Fix: changed the shell row template to five rows: hero, KPI, controls, replay, bottom. Also made the page scrollable and added explicit replay/theater/map minimum heights.
- Regression guard: `tests/test_web_agent_demo.py` now asserts `overflow: auto`, the five-row grid template, `min-height: 540px`, and `min-height: 280px`.

## Verification Evidence

- Re-read `goal/goal-12/input.md`, `goal/goal-12/plan.md`, and `goal/goal-12/tasks.md` before auditing.
- Syntax check passed: `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/day_simulation.py`.
- Frontend tests passed: `uv run --with pytest pytest tests/test_web_agent_demo.py` with 15 tests passed.
- Focused Tasks 7-9 tests passed: `uv run --with pytest pytest tests/test_web_agent_demo.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py` with 34 tests passed.
- Full suite passed: `uv run --with pytest pytest` with 100 tests passed.
- Non-goal sensitive scan found no business-code matches for the supplied model/domain/key patterns.
- Desktop browser audit at `1440x900` on `127.0.0.1:8790`:
  - Page ready with 40 frames and 207 orders.
  - Old shell absent.
  - Side-by-side grid columns were `697px 697px`.
  - Greedy and AutoSolver panels were aligned side by side.
  - Map heights were 331px and 312px after the fix.
  - KPI values changed after moving to frame 8.
  - Reasoning-card click activated one card, highlighted 24 pins and 16 routes, and updated the decision summary.
- Mobile browser audit at `390x844`:
  - Replay grid became one column.
  - KPI grid became two columns.
  - Greedy and AutoSolver panels stacked vertically.
  - Map heights were 280px and 280px.
  - No horizontal overflow; scroll width equaled client width.
  - Reasoning-card highlight still worked with 19 highlighted pins and 8 highlighted routes.
- Console/network audit:
  - Browser console reported 0 errors and 0 warnings.
  - Network request list showed only `GET /` returning 200.

## Confidence Loop

Question: am I 100% confident Debug Cycle 3 is complete?

Answer: yes for Debug Cycle 3 scope. The audit found a real visual regression, fixed it, added a regression test marker, and re-verified Tasks 7-9 through static checks, focused tests, full tests, desktop browser layout, mobile browser layout, timeline KPI updates, decision highlight behavior, console checks, network checks, and sensitive-scan checks.
