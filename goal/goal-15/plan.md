# Goal 15 Plan - Engine Upgrade From Visual Replay To Actual Simulation Runtime

## 1. Requirement Analysis

The new target is no longer "make the map look better". The user wants the engine itself improved.

The current gap is concrete:

- The frontend still behaves like a replay surface with visual motion interpolation.
- Optional adapters such as UXsim / SUMO / CityFlow are described, but they are not active runtime engines in the current local demo.
- Marker labels and map text are still visible in multiple paths, which conflicts with the user's request to remove names.

The corrected target for this goal:

- Expose a real local runtime simulator with explicit engine/tick/event state.
- Generate authoritative backend simulation traces for courier motion instead of frontend-only blinking/jump effects.
- Make the frontend consume those traces as the primary motion source.
- Remove visible map names / marker labels from both real-map and fallback paths.

## 2. Current Context

- The relevant backend files are `web_agent_demo/day_simulation.py` and `web_agent_demo/day_engine_adapters.py`.
- The relevant frontend file is `web_agent_demo/day_replay_frontend.py`.
- There are already in-progress uncommitted changes in those files that move the design toward a real backend trace.
- Optional third-party simulators (`uxsim`, `mesa`, `traci`, `cityflow`) are not installed in the current environment, so the safest path is to make the in-process simulator itself explicit, inspectable, and authoritative.

## 3. Concrete Execution Strategy

Short-term implementation in this goal:

1. Promote the current local engine into an explicit courier-agent simulator runtime instead of describing it as a metadata-only replay.
2. Extend the day-simulation contract so each frame carries backend-generated simulation traces:
   - engine id / provider / mode
   - event queue
   - fixed timestep metadata
   - courier track samples
3. Update route overlays so they represent actual courier pickup + dropoff paths.
4. Change the frontend to animate from `simulation_trace` with `requestAnimationFrame` instead of deducing motion only from previous/next frame snapshots.
5. Remove text labels and visible names from map markers, fallback pins, and other map overlays.
6. Update tests so they assert the new engine data and label-free rendering.

## 4. Risks

- Contract changes may break API tests if the new simulation trace is not serialized consistently.
- The frontend may still regress into jumpy motion if animation state is not synchronized with frame changes and reruns.
- Removing labels must not accidentally remove required status text outside the map.
- Optional engine adapters must not falsely claim active external integration when unavailable.

## 5. Verification

- `py_compile` passes for the touched backend/frontend files.
- Focused replay/day-simulation test suite passes.
- Full test suite passes.
- Browser verification confirms:
  - engine status shows a runtime simulator rather than a metadata-only seam;
  - the page exposes backend simulation traces;
  - courier motion is driven by emitted ticks, not only frame jumps;
  - no visible map names / marker labels appear in real-map mode;
  - fallback mode also keeps marker labels suppressed;
  - console and page errors remain zero.

## 6. Rollback Plan

- If the trace-driven animation destabilizes the UI, keep the new backend trace contract but temporarily fall back to non-animated trace endpoints instead of reverting the whole engine upgrade.
- If a test or browser regression appears, isolate the regression to the trace renderer or adapter payload without reverting unrelated user changes.
