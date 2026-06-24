# Goal 12 Tasks

## Task 1 - Goal Setup, Baseline Audit, Engine Research

Status: Completed

Independent verification:
- `goal/goal-12/input.md`, `goal/goal-12/plan.md`, and `goal/goal-12/tasks.md` exist.
- Current git/worktree state is documented.
- External engine direction is documented without committing secrets.

Work log:
- Created `goal/goal-12/input.md`, `goal/goal-12/plan.md`, and `goal/goal-12/tasks.md`.
- Recorded the new full-day replay direction: all-day order stream, greedy vs AutoSolver comparison, KPI savings, reasoning trace, and memory evolution.
- Documented external engine candidates and selected the low-risk path: native deterministic full-day engine first, optional UXsim/SUMO-style adapter seam later.
- Audited current worktree and confirmed the existing partial adapter spike breaks `SimulationControls().normalized()` with `NameError: name '_normalize_engine_adapter' is not defined`.
- Confirmed the supplied sensitive model/domain/key patterns are not present in business code outside `goal/**` and `output/**`.
- Did not stage or commit Goal 12 input because it contains sensitive raw user material.

Confidence loop:
- 100% confidence for Task 1 scope: the required goal files exist, current failure state is documented and reproducible, and the next independently verifiable task is clearly isolated to restoring a testable baseline.

## Task 2 - Clean Broken Adapter Spike And Restore Testable Baseline

Status: Completed

Independent verification:
- `simulation_engine.py` no longer imports incomplete adapter code or references undefined normalization.
- Any retained adapter seam is tested or isolated.
- Focused tests for current simulation engine pass.

Work log:
- Removed the incomplete adapter spike from the working tree by deleting untracked `web_agent_demo/simulation_adapters.py`.
- Removed the broken `simulation_engine.py` adapter import/field/normalizer call, then restored the file to a no-diff clean baseline.
- Verified `SimulationControls().normalized()` and a create/advance simulation probe run successfully.
- Verified no remaining references to `simulation_adapters`, `adapter_effects`, `resolve_adapter`, `_normalize_engine_adapter`, or `engine_adapter` exist under `web_agent_demo` or `tests`.
- Ran focused tests with `uv run --with pytest pytest tests/test_delivery_simulation.py tests/test_compare_engine.py tests/test_simulation_api_contract.py`; 16 tests passed.
- No code commit was created because the tracked business code ended in a clean no-diff state; only untracked Goal 12 documentation remains.

Confidence loop:
- 100% confidence for Task 2 scope: the previously reproduced `NameError` is gone, the untracked broken adapter file is removed, current simulation controls are clean, and focused simulation/API tests pass.

## Task 3 - Define Full-Day Simulation Contract

Status: Completed

Independent verification:
- Backend dataclasses or schema cover day scenario, day order, time slice, side-by-side frame, day metrics, reasoning trace, and evolution memory event.
- Contract tests fail first or explicitly validate expected shape.

Work log:
- Added `web_agent_demo/day_simulation.py` with `DAY_SIMULATION_CONTRACT_VERSION`, planned day-simulation API endpoint constants, and dataclasses for `DayScenario`, `DayOrder`, `TimeSlice`, `AlgorithmDayRun`, `SideBySideFrame`, `DayMetrics`, `ReasoningTrace`, and `EvolutionMemoryEvent`.
- Added supporting contract objects for merchants, couriers, shocks, assignments, metric deltas, algorithm frames, and algorithm candidate scores so later tasks can generate a full-day replay without changing the product data shape.
- Added `day_scenario_catalog()`, `get_day_scenario()`, `build_contract_preview()`, and `day_contract_to_dict()` to provide a deterministic serializable preview of pure greedy vs AutoSolver on the same time slice.
- Added `tests/test_day_simulation_contract.py` to explicitly validate full-day phases, shock profiles, greedy-vs-AutoSolver frame structure, savings metrics, reasoning trace linkage, memory writeback, stable ids, and `env-only-redacted` secret handling.
- Verified the new Python module and test file use ASCII-only source text.
- Verified syntax with `python3 -m py_compile web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py`.
- Ran `uv run --with pytest pytest tests/test_day_simulation_contract.py tests/test_delivery_simulation.py tests/test_compare_engine.py tests/test_simulation_api_contract.py`; 20 tests passed.
- Ran a non-goal secret scan for supplied model/domain/key patterns; no business-code matches were found.

Confidence loop:
- 100% confidence for Task 3 scope: every required contract concept is represented in backend dataclasses, the preview serializes through the existing simulation serializer, tests validate the intended shape directly, and sensitive LLM configuration remains represented only as env-only/redacted metadata.

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Completed

Independent verification:
- Re-run focused tests and static checks for modified files.
- Review API contract consistency, data redaction, deterministic behavior, and rollback safety.

Work log:
- Added `goal/goal-12/debug-cycle-1-audit.md` with the comprehensive Tasks 1-3 audit.
- Re-read `goal/goal-12/input.md`, `goal/goal-12/plan.md`, and `goal/goal-12/tasks.md` before auditing.
- Inspected `web_agent_demo/day_simulation.py` and `tests/test_day_simulation_contract.py` for contract coverage and test intent.
- Ran a deterministic preview check; two serialized previews were equal, had SHA-256 `1b5001de0c5a7f7d5d687d8689b7c777e722844bebba5549406e73d27bf58516`, used the same order stream for baseline/challenger, exposed the planned `/api/day-simulation/*` endpoints, and kept privacy as `env-only-redacted`.
- Ran a reference-integrity script confirming frame, run, reasoning, memory, order and time-slice ids are linked correctly and the time/cost deltas match baseline minus challenger metrics.
- Ran `python3 -m py_compile web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py web_agent_demo/simulation_engine.py web_agent_demo/compare_engine.py web_agent_demo/server.py`.
- Ran an ASCII-only source scan for `web_agent_demo/day_simulation.py` and `tests/test_day_simulation_contract.py`; it passed.
- Ran full tests with `uv run --with pytest pytest`; 83 tests passed.
- Ran a non-goal business-code secret scan for supplied model/domain/key patterns; no matches were found.

Confidence loop:
- 100% confidence for Debug Cycle 1 scope: Tasks 1-3 are internally consistent, deterministic, test-covered, redacted, and rollback-safe. Remaining gaps are explicitly deferred to Task 4+ rather than hidden defects in the current contract layer.

## Task 4 - Implement Full-Day Scenario Generator

Status: Completed

Independent verification:
- Generates deterministic full-day order streams with morning, lunch, afternoon, dinner, night, weather, congestion, merchant burst, and courier supply patterns.
- Same seed produces identical orders and shocks.

Work log:
- Added `DaySimulationWorld` and `generate_full_day_world()` in `web_agent_demo/day_simulation.py`.
- Generated deterministic merchants, courier shifts, shocks, time slices and orders from seed plus `DaySimulationControls`.
- Covered all required demand phases: breakfast, lunch peak, afternoon tea, dinner peak and night supply gap.
- Covered required dynamic shocks: rain slowdown, merchant burst, road congestion and courier shortage.
- Added per-slice weather, congestion, courier supply, `compare_due`, shock ids and order ids so later replay and algorithm comparison can run from a single world state.
- Added order details needed by later comparison: merchant, creation/deadline, destination, prep time, priority, basket value, penalty and risk tags.
- Added `day_world_to_dict()` for deterministic serialization through the existing serializer.
- Added `tests/test_day_simulation_generator.py` covering same-seed determinism, different-seed variation, full-day phase/shock coverage, valid order/time-slice/shock references, control scaling and night shortage supply reduction.
- Verified syntax with `python3 -m py_compile web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py`.
- Ran focused tests with `uv run --with pytest pytest tests/test_day_simulation_generator.py tests/test_day_simulation_contract.py tests/test_delivery_simulation.py tests/test_compare_engine.py tests/test_simulation_api_contract.py`; 25 tests passed.
- Ran full tests with `uv run --with pytest pytest`; 88 tests passed.
- Ran ASCII-only scan for the new Python source and non-goal business-code secret scan; both passed.
- Final deterministic probe for seed `task4-final` produced SHA-256 `51c5d7faa29fbe87540992e243b1676d4283ae7c976bb06152524623ee8340d4`, 64 slices and 539 orders.

Confidence loop:
- 100% confidence for Task 4 scope: the full-day generator creates deterministic, varied, cross-time-slice input data covering all required phases and disruptions, all references are tested, and existing code remains green.

## Task 5 - Implement Same-Day Algorithm Comparison

Status: Pending

Independent verification:
- Greedy baseline and AutoSolver/adaptive agent run over the same day stream.
- Produces cumulative time, cost, timeout, coverage, utilization, and savings metrics.
- Includes decision points explaining where AutoSolver differs from greedy.

Work log:
-

Confidence loop:
-

## Task 6 - Implement Memory Evolution Trace

Status: Pending

Independent verification:
- Recall/writeback/future-policy-shift events are generated per important time slice.
- LLM predictor configuration is env-only and redacted.
- Fallback predictor works without external API.

Work log:
-

Confidence loop:
-

## Debug Cycle 2 - Tasks 4-6 Comprehensive Check

Status: Pending

Independent verification:
- Full-day backend tests pass.
- Metrics are internally consistent and demonstrate fair same-stream comparison.
- Memory events contain no raw secrets.

Work log:
-

Confidence loop:
-

## Task 7 - Replace Frontend Shell With Replay Product

Status: Pending

Independent verification:
- Old frontend composition is replaced by full-day replay UI.
- Primary view is simulation + comparison, not candidate tables or line diagrams.
- Responsive shell loads on desktop and mobile widths.

Work log:
-

Confidence loop:
-

## Task 8 - Add Side-By-Side Map Replay And Timeline Controls

Status: Pending

Independent verification:
- Greedy and AutoSolver panels show the same day/time frame side by side.
- Timeline scrubber, play/pause/speed, scenario, and courier/order controls update replay state.
- Riders, merchants, orders, congestion, and bursts are visible.

Work log:
-

Confidence loop:
-

## Task 9 - Add KPI Savings, Reasoning Flow, And Decision Highlights

Status: Pending

Independent verification:
- KPI strip shows time saved, cost saved, delivered count, timeout risk, ETA, and utilization.
- Reasoning panel explains key decisions in readable business language.
- Decision highlights connect to map entities and time slices.

Work log:
-

Confidence loop:
-

## Debug Cycle 3 - Tasks 7-9 Comprehensive Check

Status: Pending

Independent verification:
- Browser audit has no console/network errors.
- Side-by-side replay remains readable and aligned at multiple viewports.
- Metrics update correctly through the timeline.

Work log:
-

Confidence loop:
-

## Task 10 - Optional External Engine Adapter Seam

Status: Pending

Independent verification:
- Native local engine remains default.
- UXsim/SUMO-style adapter metadata is exposed only as optional capability unless installed.
- No optional dependency breaks local tests.

Work log:
-

Confidence loop:
-

## Task 11 - Browser Verification And Visual Hardening

Status: Pending

Independent verification:
- Playwright/browser screenshot artifacts prove the new UI loads and functions.
- No obvious overlap, clipping, unreadable text, or stale old-frontend affordances.

Work log:
-

Confidence loop:
-

## Task 12 - Final Review, Security, And Completion Archive

Status: Pending

Independent verification:
- Full test suite passes or failures are explicitly documented.
- Review covers C-side UX, code architecture, API contracts, security/secrets, and rollback.
- Goal folder is marked complete/archived after all tasks are complete.

Work log:
-

Confidence loop:
-
