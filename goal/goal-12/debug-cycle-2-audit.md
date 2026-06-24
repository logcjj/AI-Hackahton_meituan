# Debug Cycle 2 Audit - Tasks 4-6

Date: 2026-06-24

## Scope

This audit covers the backend work completed in Tasks 4-6:

- Task 4: deterministic full-day scenario generation.
- Task 5: same-day greedy versus AutoSolver comparison.
- Task 6: memory recall, writeback, future policy shift, and env-only predictor hook.

No functional code changes were required during this debug cycle.

## Files Reviewed

- `goal/goal-12/input.md`
- `goal/goal-12/plan.md`
- `goal/goal-12/tasks.md`
- `web_agent_demo/day_simulation.py`
- `tests/test_day_simulation_contract.py`
- `tests/test_day_simulation_generator.py`
- `tests/test_day_simulation_comparison.py`
- `tests/test_day_simulation_memory_evolution.py`

## Commands Run

- `python3 -m py_compile web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- `uv run --with pytest pytest tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- `uv run --with pytest pytest`
- `rg -n "\bsk-[A-Za-z0-9]{20,}\b|windhub|deepseek-v3|https://windhub|AUTOSOLVER_LLM_API_KEY=.*\bsk-[A-Za-z0-9]{20,}\b" --glob '!goal/**' --glob '!output/**' --glob '!.playwright-cli/**' .`
- `LC_ALL=C grep -n '[^ -~]' web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py`
- Independent Python probe validating determinism, same-stream fairness, metric deltas, memory links, and env redaction.

## Verification Results

- Python compile check passed.
- Focused day-simulation tests passed: 19 passed.
- Full suite passed: 98 passed.
- Non-goal/non-output sensitive pattern scan had no matches.
- ASCII scan for new Python day-simulation files had no matches.
- Independent probe summary:
  - Seed: `debug-cycle-2`
  - Controls: 22 couriers, 0.5 order scale, mixed weather, weekday congestion.
  - Orders: 267
  - Frames: 40
  - Memory events: 120
  - World SHA-256: `4873d84bb679659360f34de8b1fa3de8642401d51d24dfa41d669ee548cd9376`
  - Comparison SHA-256: `9c0f4a7b03e6e24a3cfd47937903c881ad7cd73bcae92a36243f122c88a2fd99`
  - Time saved: 67019.575 seconds
  - Cost saved: 710.349 yuan
  - Timeout risk delta: -0.1159
  - Predictor provider under configured env: `external-env-hook`
  - Raw env values were absent from serialized output.

## Audit Findings

### Deterministic Generation

`generate_full_day_world()` is deterministic for the same seed and controls. The world includes the required full-day phases and dynamic shocks:

- Breakfast
- Lunch peak
- Afternoon tea
- Dinner peak
- Night supply gap
- Rain slowdown
- Merchant burst
- Road congestion
- Courier shortage

The generator keeps order ids, time-slice ids, shock references, courier supply, congestion, weather, and `compare_due` metadata consistent.

### Same-Stream Algorithm Fairness

`run_full_day_comparison()` builds one `DaySimulationWorld` and runs both algorithms against that same order stream. The independent probe verified that every emitted side-by-side frame compares identical active order ids and identical assignment order ids between baseline and challenger.

Both baseline and challenger assign all generated orders in the checked scenarios, so current metric deltas compare behavior rather than missing work.

### Metric Consistency

Per-frame deltas match the arithmetic between cumulative baseline and challenger metrics:

- `time_saved_s = baseline.total_time_cost_s - challenger.total_time_cost_s`
- `cost_saved_yuan = baseline.total_cost_yuan - challenger.total_cost_yuan`
- `timeout_risk_delta = challenger.timeout_risk - baseline.timeout_risk`

The full-day aggregate metrics show AutoSolver improvement on total time, cost, average ETA, and timeout risk for the tested deterministic scenarios.

### Memory Evolution Linkage

Memory evolution linkage is internally consistent:

- Each emitted frame has three memory events.
- Each trace has the same memory event ids as its frame.
- Each event points back to the correct frame id.
- Challenger run receives memory event ids.
- Baseline run remains memory-free.
- Event types cover `memory_recall`, `memory_writeback`, and `future_policy_shift`.

`memory_mode="off"` remains covered by tests and disables frame, trace, and run memory links.

### Env-Only Redaction

The predictor hook exposes only env placeholders:

- `env:AUTOSOLVER_LLM_BASE_URL`
- `env:AUTOSOLVER_LLM_MODEL`

It does not return raw base URL, API key, or model values, and `used_external_api` remains false. The non-goal business-code scan found no supplied key/model/domain patterns. `goal/goal-12/input.md` intentionally preserves raw user input for Goal Mode and must remain untracked.

### Rollback Safety

The full-day backend is additive. The current legacy simulation and existing tests remain green. If needed, rollback is low-risk: remove `web_agent_demo/day_simulation.py` and its tests before frontend/API integration. No old frontend or server behavior has been modified in Tasks 4-6.

## Residual Risks

- The new full-day backend is not yet exposed through live `/api/day-simulation/*` endpoints.
- The frontend has not yet been replaced with the replay product shell.
- The native local simulation is realistic enough for the demo, but the optional external UXsim/SUMO-style adapter seam is still deferred.
- Current memory evolution is deterministic demonstration logic. The future real predictor API must keep the same env-only redaction boundary.

## Decision

Tasks 4-6 are accepted. The implementation is deterministic, fair for same-stream comparison, internally metric-consistent, memory-linked, redacted, and covered by focused and full test suites. Proceed to Task 7.
