# Debug Cycle 1 Audit - Tasks 1-3

## Scope

This audit covers:

- Task 1 goal setup, baseline audit and engine research.
- Task 2 broken adapter spike cleanup.
- Task 3 full-day simulation contract definition.

It does not implement Task 4 full-day order generation.

## Evidence Checked

- Goal files were re-read from disk before the audit:
  - `goal/goal-12/input.md`
  - `goal/goal-12/plan.md`
  - `goal/goal-12/tasks.md`
- Latest implementation commit before this audit:
  - `6d3a890 Add full-day simulation contract`
- Current day contract files:
  - `web_agent_demo/day_simulation.py`
  - `tests/test_day_simulation_contract.py`

## Contract Consistency

Validated by direct inspection and a Python reference script:

- `DayScenario` covers full-day replay metadata, map bounds, demand phases, shock profiles, algorithms and default controls.
- `DayOrder` covers merchant, creation/deadline, destination, demand phase, value, penalty and risk tags.
- `TimeSlice` covers cross-time-slice playback and compare triggers.
- `AlgorithmDayRun`, `AlgorithmFrame` and `SideBySideFrame` cover same-stream greedy vs AutoSolver comparison.
- `DayMetrics` and `MetricDelta` cover time, cost, timeout risk, coverage and utilization deltas.
- `ReasoningTrace` covers algorithm candidates, selected strategy, evidence, impact and time budget.
- `EvolutionMemoryEvent` covers recall, chosen algorithm, learned rule, confidence shift, writeback and `env-only-redacted` handling.

Reference audit output:

```text
contract_reference_audit=ok
frames=1
orders=1
reasoning_traces=1
evolution_events=1
```

## Determinism

The contract preview was built twice and serialized canonically.

```text
preview_equal=True
preview_sha256=1b5001de0c5a7f7d5d687d8689b7c777e722844bebba5549406e73d27bf58516
same_stream=True
privacy=env-only-redacted
endpoints=/api/day-simulation/frame,/api/day-simulation/memory,/api/day-simulation/run,/api/day-simulation/scenarios
```

This proves the current preview is deterministic and the baseline/challenger frames share the same order stream.

## Static And Test Checks

Commands run:

```text
python3 -m py_compile web_agent_demo/day_simulation.py tests/test_day_simulation_contract.py web_agent_demo/simulation_engine.py web_agent_demo/compare_engine.py web_agent_demo/server.py
python3 ascii scan for web_agent_demo/day_simulation.py and tests/test_day_simulation_contract.py
uv run --with pytest pytest
```

Results:

```text
ascii_scan=ok
83 passed in 21.82s
```

## Data Redaction And Secret Handling

Non-goal business-code scan command:

```text
rg -n "<redacted-user-model-domain-key-patterns>" --glob '!goal/**' --glob '!output/**' --glob '!.playwright-cli/**' .
```

Result:

```text
no matches
```

The raw user input remains only in `goal/goal-12/input.md`, which is intentionally not staged or committed.

## Rollback Safety

- The full-day contract was added in a separate module: `web_agent_demo/day_simulation.py`.
- Existing simulation and compare APIs remain unchanged.
- Existing focused and full test suites pass.
- If later full-day implementation regresses, the contract module can be reverted independently from the legacy simulation engine.

## Residual Risks

- `/api/day-simulation/*` endpoints are declared but not wired into `server.py` yet. This is expected for Task 3 and belongs to later backend/API tasks.
- The preview includes only one representative frame. Task 4 must generate real full-day order streams and time slices.
- Agent self-evolution is contractually represented, but actual memory loop generation is still Task 6.
- The old frontend is still present. Full replacement is Task 7.

## Verdict

Tasks 1-3 pass the Debug Cycle 1 gate. The repository has a clean, deterministic, redacted and test-covered contract baseline for implementing the full-day simulation generator next.
