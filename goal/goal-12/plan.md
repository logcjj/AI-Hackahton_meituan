# Goal 12 Plan - Full-Day Delivery Simulation Replay

## 1. Requirement Analysis

The previous frontend direction is superseded. The new product narrative must be a full-day delivery simulation replay with comparison as the primary experience:

- Simulate an entire delivery day with time slices, courier movement, merchant bursts, order creation, congestion/weather/supply shocks, and visible dispatch consequences.
- Compare pure greedy against AutoSolver/adaptive agent on the exact same order stream.
- Quantify why AutoSolver is better using cumulative time, cost, timeout-risk, coverage, courier utilization, and money-saving metrics.
- Show readable algorithm reasoning tied to key decision points, not complex wireframes or ReasonGraph-first diagrams.
- Demonstrate self-evolution: memory recall, strategy choice, memory writeback, and future policy adjustment.
- Keep the map/simulation feel. 三国志-style or Sims-style is a reference for operational replay/game-like simulation, not a strict visual clone.

## 2. Current Context

- Current committed baseline is `84ca3ca Close simulation dispatch loop`.
- Current frontend/API is still built around a small tick-based sandbox in `web_agent_demo/server.py`, `web_agent_demo/simulation_engine.py`, and `web_agent_demo/compare_engine.py`.
- Existing strengths to reuse:
  - Local road-map visual primitives and route overlays.
  - Algorithm comparison engine with greedy, matching, flow, sparse cover, and AutoSolver agent result types.
  - Memory engine with recall/writeback concepts and env-only LLM configuration patterns.
- Current uncommitted risk:
  - `web_agent_demo/simulation_engine.py` has an incomplete adapter edit that references `_normalize_engine_adapter`, which is undefined.
  - `web_agent_demo/simulation_adapters.py` exists as an untracked spike and is not tested.
  - Goal/output/browser artifacts are untracked and should not be blindly staged.

## 3. External Engine Research

Shortlisted options from GitHub/open-source ecosystem:

- SUMO / TraCI: strong microscopic traffic simulator and realistic mobility backbone. Good for later high-fidelity integration, but heavier installation and scenario preparation.
- UXsim: lightweight Python traffic flow simulator. Good candidate for a local optional adapter because it can feed congestion/speed effects into the current Python backend.
- CityFlow: high-performance road network traffic simulator, useful as reference for traffic state and multi-agent comparison, but overkill for immediate demo.
- A/B Street: OpenStreetMap-based urban simulation. Strong inspiration for city replay and map-based simulation, but not a simple embeddable delivery dispatch engine.
- Mesa: Python agent-based modeling framework. Useful for order/courier agent modeling if we need a simulation engine abstraction.
- Phaser/Pixi/Leaflet/MapLibre-style frontend rendering: useful for game-like motion and replay. Current project already has Leaflet assets, so the lowest-risk path is to keep the map base and create a game-like replay layer.

Decision for this goal:

- Short term: build a native full-day discrete-event simulation engine and side-by-side replay contract.
- Mid term: keep an adapter seam for UXsim/SUMO effects, but do not block the demo on heavyweight external installation.
- Frontend: use the existing map style as base, but replace the whole UI composition with simulation replay, side-by-side comparison, timeline, KPIs, reasoning, and memory evolution panels.

## 4. Risks

- Sensitive input: user supplied API model/key/domain. The raw input is preserved in `input.md` due Goal Mode, but it must not be hardcoded, echoed in summaries, committed, or staged. Runtime usage must be env-only.
- Scope risk: replacing the frontend and adding full-day backend can break existing tests. Mitigate by adding API contract tests first and preserving legacy endpoints unless intentionally replaced.
- Visual risk: a game-like simulation can become decorative without proving algorithm value. Mitigate by making KPI savings and side-by-side replay the primary visual hierarchy.
- Engine risk: external traffic engines can add installation burden. Mitigate by designing adapters but shipping native deterministic simulation first.
- Current broken worktree risk: the partial adapter edit should be cleaned or completed before running full tests.

## 5. Execution Plan

1. Create Goal 12 docs, audit current state, and record engine research.
2. Clean the incomplete adapter change so tests can run from a known-good base.
3. Define and test the full-day simulation API contract.
4. Implement deterministic full-day scenario generation with realistic daily demand patterns.
5. Implement day-level greedy vs AutoSolver/adaptive comparison on the same event stream.
6. Implement memory evolution trace and optional env-only LLM predictor hook.
7. Replace the frontend shell with a full-day replay interface.
8. Add side-by-side maps, timeline, KPI strip, reasoning flow, memory evolution view, and controls.
9. Run browser verification and visual regression checks.
10. Final review and hardening across UX, code, tests, security, and data handling.

## 6. Verification

- Unit tests:
  - Day scenario generation is deterministic by seed.
  - Greedy and AutoSolver consume identical order streams.
  - Metrics compute valid cumulative time/cost/savings values.
  - Memory events are redacted and env-only for model/key/domain.
  - Legacy simulation APIs remain healthy until replaced.
- API tests:
  - `/api/day-simulation/scenarios`
  - `/api/day-simulation/run`
  - `/api/day-simulation/frame`
  - `/api/day-simulation/memory`
- Browser tests:
  - No console errors.
  - Side-by-side maps render.
  - Timeline scrubber changes frames.
  - KPI savings update.
  - Reasoning and memory panels are readable.
- Final full suite:
  - `python -m pytest`

## 7. Rollback Plan

- Keep new full-day engine in separate files first, then integrate via additive endpoints.
- Preserve existing committed endpoints while new UI stabilizes.
- If a frontend rewrite regresses, temporarily switch server root back to the old HTML while keeping backend tests.
- If optional external engine adapter causes dependency issues, default back to native local road graph.
- Do not stage or commit raw `goal/goal-12/input.md` because it contains sensitive material.

## 8. Task 1 Audit Notes

- Goal files created:
  - `goal/goal-12/input.md`
  - `goal/goal-12/plan.md`
  - `goal/goal-12/tasks.md`
- Worktree state at audit time:
  - `web_agent_demo/simulation_engine.py` is modified.
  - `web_agent_demo/simulation_adapters.py` is untracked.
  - Several older goal/browser/output artifacts remain untracked and unrelated to Goal 12 execution.
- Reproduced current failure:
  - `python3` import/call check on `SimulationControls().normalized()` fails with `NameError: name '_normalize_engine_adapter' is not defined`.
  - This confirms Task 2 must clean or complete the incomplete adapter spike before running the broader test suite.
- Sensitive input check:
  - Searched non-goal/non-output business files for the supplied model/domain/key patterns and found no matches.
  - `goal/goal-12/input.md` preserves raw user input due Goal Mode and must not be staged or committed.
- External engine direction recorded:
  - Native full-day discrete-event simulation is the immediate path.
  - UXsim/SUMO-style adapters should remain optional and non-blocking.
  - Existing map visual style can be retained, but the frontend product structure must be replaced around full-day replay and side-by-side comparison.
