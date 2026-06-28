# Goal 17 Plan - Dispatch Workbench UI Polish, Real Map, Advantage Focus

## 1. Requirement Analysis

The current Kandbox-style workbench implementation is structurally complete but not product-grade enough visually. The user feedback is explicit:

- Left navigation is unclear and lacks guidance.
- Pages feel too similar and too box-heavy.
- Information density is high but not prioritized, so users cannot see the algorithm advantage at a glance.
- The live map is the biggest weakness: it looks artificial, rider/merchant/order markers are visually chaotic, paths are confusing, and it should use a real map layer rather than a purely hand-drawn schematic.
- Map labels and names must be anonymized or removed to avoid exposing sensitive names.
- The UI should remove, merge, or rename low-value blocks.
- The core narrative must be algorithm strength: our method beats the baseline over time.
- Memory should be redesigned more like Hermes: global memory, accumulated patterns, recalled memories, rider/area/order portraits, and how memories are formed and used.
- The full chain should present the project advantage clearly, not merely show many technical widgets.
- The algorithm reasoning / inference display should be improved by referencing prior project patterns: the earliest project under `man` and the second dispatch-console project if those sources exist locally.

This goal is therefore a polish-and-restructure pass on top of Goal 16, not a rollback to the old frontend.

## 2. Product Direction

Priority order:

1. Real map layer and map readability.
2. Advantage-first live page.
3. Navigation clarity and page differentiation.
4. Memory redesign with Hermes-style memory structure.
5. Algorithm reasoning display redesign using prior project references where discoverable.
6. Reduce/merge low-value panels and simplify page copy.
7. Final QA on desktop and mobile.

The workbench should still keep the five route model unless a page becomes clearly redundant:

- Live: "实时推理 / 优势总览" with real map, minimal event stream, and dominant advantage cards.
- Decisions: "决策链路" focused on why our decision beats baseline, not raw procedural clutter.
- Reasoning view: show the algorithm's inferential chain with clear stages, evidence, and advantage deltas, borrowing useful display patterns from prior local projects.
- Memory: "长期记忆" with global memory, portraits, recall chain, and evidence of effect.
- Orders: "订单输入" simplified to filtered demand/risk view.
- Riders: "运力资源" simplified to supply/coverage view.

## 3. Design Principles

- Advantage-first: every primary page should expose a concise top-level statement of what improves.
- Progressive disclosure: show summary first, details second; avoid dense tables as the first thing users see.
- Real map: use a public tile provider such as OpenStreetMap raster tiles through Leaflet or a lightweight embedded tile map. Keep a deterministic fallback if CDN tiles fail.
- Map anonymization: remove merchant names, rider names, and sensitive exact labels from the map. Use `M-01`, `R-01`, `O-01` style identifiers and aggregate area labels.
- Map clarity: fewer route lines, current action highlighted, old routes faded, baseline shown only as deltas, no full-route clutter.
- Page differentiation: each page should have a distinct layout vocabulary and role, not five similar card grids.
- Hermes-style Memory: show memory layers, profiles, recall usage, feedback, confidence, and how memories are written back.
- Enterprise visual tone: restrained, clean, no game UI, no big-screen neon, no decorative clutter.

## 4. Implementation Strategy

Likely touched files:

- `web_agent_demo/day_replay_frontend.py`
- `web_agent_demo/dispatch_workbench_data.py`
- `tests/test_web_agent_demo.py`
- `tests/test_dispatch_workbench_data.py` if data contract changes are needed
- `goal/goal-17/*`

Implementation layers:

1. Data/model support:
   - Add anonymized display labels for map entities.
   - Add advantage narrative fields if needed: time saved, cost saved, timeout reduction, reliability benefit.
   - Add Memory grouping metadata: global patterns, rider portraits, area portraits, order-risk portraits, recall chain.

2. Live map:
   - Add Leaflet or equivalent real map assets.
   - Render map tile base.
   - Render anonymized markers.
   - Render a simplified active route and a separate differential baseline route layer.
   - Add a fallback schematic map when tile assets fail.
   - Reduce visible clutter by limiting simultaneous labels/routes.

3. Live page:
   - Make the algorithm advantage strip the first visible information layer.
   - Merge low-value event/summary panels into a concise "current decision" and "advantage timeline".
   - Keep start/pause/speed/mode controls, but make them less noisy.

4. Navigation and page differentiation:
   - Add left nav hints and page roles.
   - Rename pages if clearer.
   - Make each page visually and structurally distinct.

5. Memory:
   - Redesign as Hermes-style memory system:
     - global memory;
     - rider profile memory;
     - area/demand memory;
     - order risk memory;
     - active recalls;
     - feedback loop.
   - Show how memory is formed, recalled, and updated.

6. Algorithm reasoning:
   - Inspect local references for prior `man` and dispatch-console projects.
   - Extract display ideas that fit this project: reasoning stages, trace cards, replay chain, planner comparison, or decision evidence.
   - Redesign the reasoning display so users see why our algorithm wins, not only a procedural list.

7. QA:
   - Compile and tests.
   - Browser check: real map visible, labels anonymized, route clutter reduced, advantage cards visible, Memory sections clear, nav hints visible, no console errors, responsive behavior.

## 5. Risks

- External map tiles require network availability and may fail; fallback map must keep the demo usable.
- Leaflet or map CSS can increase complexity inside a generated static HTML file.
- Too much redesign can destabilize the already-working routes; tasks should be incremental and verified one at a time.
- Anonymization must not break existing filters and data references.
- Reducing panels must not remove required Goal 16 deliverables unless an equivalent clearer surface remains.

## 6. Verification Plan

Automated:

- `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/dispatch_workbench_data.py tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q`
- Static HTML checks for:
  - real map container and tile layer;
  - fallback map;
  - anonymized labels;
  - no raw merchant/rider names on map;
  - advantage-first hero;
  - nav hints;
  - Hermes-style Memory sections.

Browser:

- Open `#/live`.
- Verify tile map or fallback map renders.
- Verify map labels are anonymized.
- Verify active route and differential route are readable.
- Verify user can see our advantage in the first viewport.
- Verify start/pause/resume/speed still work.
- Verify Memory page has Hermes-style global memory / profile / recall / feedback structure.
- Verify algorithm reasoning / inference display clearly shows stage-by-stage advantage and incorporates useful patterns from prior local references when available.
- Verify Orders/Riders/Decisions remain usable and visually distinct.
- Verify desktop/tablet/phone widths.
- Verify browser console has zero errors.

## 7. Rollback Plan

- Keep changes isolated to frontend generator and data normalization.
- If real map tile integration fails, preserve fallback schematic and ship a clean anonymized fallback.
- If a page redesign breaks a route, revert that page only and keep prior verified behavior.
- If visual simplification removes required information, restore it as secondary/details content rather than primary clutter.
