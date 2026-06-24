# Goal 13 Task 2 Static/API/Test Audit

Date: 2026-06-25

## Commands Run

- `python3 -m py_compile web_agent_demo/server.py web_agent_demo/day_replay_frontend.py web_agent_demo/day_simulation.py web_agent_demo/day_engine_adapters.py tests/test_web_agent_demo.py tests/test_day_engine_adapters.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- `uv run --with pytest pytest tests/test_web_agent_demo.py tests/test_day_engine_adapters.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- `uv run --with pytest pytest`
- `uv run --with pytest pytest --collect-only -q tests/test_web_agent_demo.py tests/test_day_engine_adapters.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- Sensitive business-code scan excluding `goal/**`, `output/**`, and `.playwright-cli/**`.
- Old frontend marker scan for rendered/source residues.
- Direct Python probes for root render output, world generation, comparison fairness, API payloads, memory events, and engine fallback.

## Results

- Python compile: passed.
- Focused tests: 37 passed.
- Full test suite: 103 passed.
- Sensitive business-code scan: no matches.
- Old frontend source scan: old shell strings only appear in `tests/test_web_agent_demo.py` as negative assertions.
- Root render probe: new markers are present and old frontend markers are absent from actual HTML output.

## Direct Probe Evidence

Root HTML:
- Length: 1,093,371 bytes.
- New markers present: `day-replay-shell`, `full-day-simulation-replay`, `side-by-side-replay`, `memory-evolution-panel`, `timeline-scrubber`.
- Old markers absent: `simulation-sandbox`, `algorithm-compare-table`, `/api/compare/run`, `/api/memory/recall`, old ReasonGraph text, `candidate_preview`.

Generated world:
- Orders: 205.
- Merchants: 18.
- Couriers: 18.
- Time slices: 64.
- Phases: `afternoon_tea`, `breakfast`, `dinner_peak`, `lunch_peak`, `night_supply_gap`.
- Shock types: `courier_shortage`, `merchant_burst`, `rain_slowdown`, `road_congestion`.
- Supply range: 5 to 15 active couriers.

Comparison payload:
- Frames: 40.
- Orders: 206.
- Baseline/challenger active orders match for every frame.
- Baseline/challenger assigned order ids match for every frame.
- AutoSolver saved 42,440.136 seconds versus greedy in total time cost.
- AutoSolver saved 530.698 yuan versus greedy.
- Timeout risk delta: -0.1088.
- Memory event types: `future_policy_shift`, `memory_recall`, `memory_writeback`.
- Memory events: 120.
- Every frame and reasoning trace links memory event ids.
- Privacy payload uses `env-only-redacted`.

API payloads:
- `/api/day-simulation/scenarios` direct handler status: `ok`.
- `/api/day-simulation/engines` direct handler status: `ok`.
- Optional engine requests such as `sumo-traci`, `uxsim`, and `cityflow` select `native-local`.
- Engine capabilities expose `native-local`, `uxsim`, `sumo-traci`, `cityflow`, and `mesa-abm`.
- `/api/day-simulation/run` direct handler status: `ok`, 166 orders, 40 frames.
- `/api/day-simulation/frame` direct handler status: `ok`, frame index 3, linked time slice present.
- `/api/day-simulation/memory` direct handler status: `ok`, three memory events for the selected frame.

## Test Coverage Mapping

- Frontend shell/API payload coverage: `tests/test_web_agent_demo.py::test_home_page_contains_full_day_replay_shell`, `test_home_page_bootstrap_contains_full_day_contract_preview`, `test_day_simulation_api_payloads_support_replay_controls`, `test_evolution_loop_uses_dynamic_replay_panel`.
- Engine seam coverage: `tests/test_day_engine_adapters.py::*`.
- Contract coverage: `tests/test_day_simulation_contract.py::*`.
- World generation coverage: `tests/test_day_simulation_generator.py::*`.
- Same-stream comparison and metric coverage: `tests/test_day_simulation_comparison.py::*`.
- Memory evolution and env redaction coverage: `tests/test_day_simulation_memory_evolution.py::*`.
- Legacy compatibility coverage: full suite includes `tests/test_compare_engine.py`, `tests/test_delivery_simulation.py`, `tests/test_simulation_api_contract.py`, and older web demo tests.

## Findings

- I found two audit-script mistakes while probing: I first assumed frame algorithm payloads had `order_ids`, then assumed metrics used `total_time_s`. The real schema uses `active_order_ids`/`assignments[*].order_id` and `total_time_cost_s`. These were not product defects, but they confirm the user's criticism is valid: completion claims need schema-accurate evidence, not memory or assumptions.
- No Task 2 product defect was found.
- Browser runtime behavior remains unproven by Task 2 and must be audited in Task 3 before any final completion claim.
