# Task 10 Audit - Optional External Engine Adapter Seam

## Scope

Task 10 adds an explicit seam for external simulation engines while keeping the native local full-day discrete-event replay as the only active/default execution path. Optional engines are exposed as metadata and capability status only; they are not imported, installed, or required.

## External Engine References

- UXsim: `https://github.com/toruseo/UXsim`
- Eclipse SUMO / TraCI: `https://eclipse.dev/sumo/`
- CityFlow: `https://cityflow-project.github.io/`
- Mesa: `https://mesa.readthedocs.io/`

## Implementation Evidence

- Added `web_agent_demo/day_engine_adapters.py`.
- Added `DayEngineAdapterCapability` metadata for:
  - `native-local`
  - `uxsim`
  - `sumo-traci`
  - `cityflow`
  - `mesa-abm`
- Added `engine_adapter` to `DaySimulationControls` with `native-local` as default.
- Added normalization so unknown adapter ids fall back to `native-local`.
- Optional dependency status is detected with `importlib.util.find_spec`; no optional engine module is imported or required.
- Added `/api/day-simulation/engines`.
- Added engine metadata to `/api/day-simulation/scenarios`, `/api/day-simulation/run`, `/api/day-simulation/frame`, and `/api/day-simulation/memory`.
- Added tests verifying native default behavior, optional capability metadata, fallback behavior, source/install metadata, and no optional module imports.

## Verification Evidence

- `python3 -m py_compile web_agent_demo/day_engine_adapters.py web_agent_demo/day_simulation.py web_agent_demo/server.py tests/test_day_engine_adapters.py tests/test_web_agent_demo.py` passed.
- Focused tests passed: `uv run --with pytest pytest tests/test_day_engine_adapters.py tests/test_web_agent_demo.py tests/test_day_simulation_contract.py tests/test_day_simulation_generator.py tests/test_day_simulation_comparison.py tests/test_day_simulation_memory_evolution.py` with 37 tests passed.
- Full suite passed: `uv run --with pytest pytest` with 103 tests passed.
- Non-goal sensitive scan found no business-code matches for the supplied model/domain/key patterns.
- Probe for requested `sumo-traci`/`uxsim` returned:
  - default adapter `native-local`
  - selected adapter `native-local`
  - active adapter `native-local`
  - optional capabilities `uxsim`, `sumo-traci`, `cityflow`, `mesa-abm` as `optional-not-installed`
  - generated run remained healthy with 89 orders and 40 frames.

## Confidence Loop

Question: am I 100% confident Task 10 is complete?

Answer: yes for Task 10 scope. The code now exposes a clear external-engine seam, keeps native local as the only active/default engine, lists UXsim/SUMO-style adapters only as optional capabilities unless dependencies exist, avoids importing optional modules, preserves current simulation behavior, and passes focused/full tests plus sensitive-scan checks.
