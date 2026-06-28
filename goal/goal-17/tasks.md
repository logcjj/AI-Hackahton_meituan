# Goal 17 Tasks

## Task 1 - Goal Setup And Current UI Audit

Status: Completed

Independent verification:
- `goal/goal-17/input.md`, `goal/goal-17/plan.md`, and `goal/goal-17/tasks.md` exist before code edits.
- Current UI issues are inspected from the running app and mapped to concrete fixes.
- Existing branch and worktree state are recorded.

Work log:
- Created `goal/goal-17/` using the next available goal number after `goal-16`.
- Saved the updated user objective verbatim in `goal/goal-17/input.md`, including the later addition about improving algorithm reasoning / inference display by referencing prior `man` and dispatch-console projects.
- Wrote `goal/goal-17/plan.md` with concrete direction for:
  - real map foundation;
  - map anonymization;
  - advantage-first live page;
  - left navigation clarity;
  - page differentiation;
  - Hermes-style Memory redesign;
  - algorithm reasoning display redesign using prior local references when discoverable;
  - simplification and QA.
- Wrote `goal/goal-17/tasks.md` with seven implementation tasks and a debug loop after each three-task group.
- Confirmed current branch is `codex/kandbox-dispatch-workbench` and the worktree was clean before goal setup.
- Confirmed the previous preview server is still running at `http://127.0.0.1:18772`, which was used for UI audit.
- Browser-audited the current Live page:
  - no real map engine is present (`Leaflet`/real-map container absent);
  - map is a custom schematic with 18 merchant dots, 1 rider dot, 2 order dots, and 2 route lines at the audited frame;
  - the map text only exposes mode and legend, not a readable city/map context;
  - the first visible page has 17 card-like blocks, making advantage cards compete with operational panels;
  - left nav labels are unclear: `LM Real-time inference Live Map`, `PL Decisions Planner / Chart`, `ME Memory History / assistance`, `JO Orders Jobs / Orders`, `WK Riders Workers`.
- Browser-audited all five routes:
  - Live has 17 card-like blocks and the same dense card vocabulary as other pages.
  - Decisions has 17 card-like blocks and 10 stages, but the page emphasizes procedure more than why our algorithm wins.
  - Memory has 49 card-like blocks, causing severe information overload.
  - Orders shows 207 table rows, so it still reads like a dense table instead of a distilled demand/risk input view.
  - Riders shows 18 rider cards and headings like `Courier 1`, `Courier 2`, etc., which is both visually noisy and not sufficiently anonymized for sensitive names.
- Confirmed current pages are structurally different but visually too similar:
  - `live-grid`;
  - `decision-grid`;
  - `memory-workspace`;
  - `input-workspace`;
  - `resource-workspace`;
  - all still rely heavily on equal-weight cards and panels.
- Searched for local prior references:
  - no obvious local `man` directory was found under the current repository;
  - `docs/deliverables/未来规划.md` contains a ReasonGraph-style reasoning-chain visualization plan;
  - `docs/deliverables/项目文档.md` contains strategy/planner descriptions for algorithm reasoning;
  - these files should be inspected in Task 6 when redesigning algorithm inference / reasoning display.
- Mapped the audit into concrete next fixes:
  - Task 2 should replace the schematic map with real map tiles plus fallback and anonymized markers.
  - Task 3 should make the first viewport advantage-first and remove/merge low-value Live panels.
  - Task 4 should redesign left navigation with role hints and make page identities clearer.
  - Task 5 should rebuild Memory around Hermes-style global memory, portraits, recall chain, writeback, and feedback instead of 49 similar cards.
  - Task 6 should simplify Orders/Riders/Decisions and improve reasoning display using local reference material where useful.

Confidence loop:
- 100% confidence for Task 1 scope: the updated goal files exist before code edits, the current UI was inspected in browser across all five pages, specific defects were mapped to later tasks, and local reference entry points for algorithm reasoning redesign were identified.

## Task 2 - Real Map Foundation And Sensitive Label Anonymization

Status: Pending

Independent verification:
- Live page has a real map layer or a deterministic real-map fallback.
- Map entity labels are anonymized and do not expose merchant/rider names.
- Marker categories are visually clear for riders, merchants, orders, hotspots, active route, and route delta.
- Existing live controls still render.

Work log:

Confidence loop:

## Task 3 - Live Page Advantage-First Simplification

Status: Pending

Independent verification:
- First viewport clearly shows our algorithm advantage over baseline.
- Low-value panels are removed, merged, or pushed into secondary details.
- Start/pause/speed/mode still work.
- Live page no longer feels like a noisy grid of equal cards.

Work log:

Confidence loop:

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Pending

Independent verification:
- Re-read `input.md`, `plan.md`, and `tasks.md`.
- Browser-run the live page.
- Verify real map readability, anonymization, reduced clutter, advantage-first layout, and no console errors.
- Fix any found defect before continuing.

Work log:

Confidence loop:

## Task 4 - Navigation Clarity And Page Differentiation

Status: Pending

Independent verification:
- Left navigation has useful page hints and clear module roles.
- Pages have distinct visual structures and names, not five similar card grids.
- Users can understand what each page is for before clicking deeply.

Work log:

Confidence loop:

## Task 5 - Hermes-Style Memory Redesign

Status: Pending

Independent verification:
- Memory page is redesigned around global memory, profile memory, recall chain, writeback, and feedback.
- Memory is presented as long-term system memory, not logs, documents, or assets.
- Memory page clearly shows how memory improves dispatch decisions.

Work log:

Confidence loop:

## Task 6 - Orders, Riders, Decisions, And Algorithm Reasoning Simplification

Status: Pending

Independent verification:
- Orders page emphasizes demand/risk input instead of a dense CRUD table.
- Riders page emphasizes capacity/coverage instead of personnel inventory.
- Decisions page and live inference reasoning emphasize why our algorithm wins instead of raw procedural clutter.
- Local prior references are inspected for the earlier `man` project and second dispatch-console project if discoverable.
- Useful prior reasoning-display patterns are incorporated or explicitly rejected with rationale.
- Required fields remain accessible.

Work log:

Confidence loop:

## Debug Cycle 2 - Tasks 4-6 Comprehensive Check

Status: Pending

Independent verification:
- Re-read `input.md`, `plan.md`, and `tasks.md`.
- Browser-run all five pages.
- Verify nav clarity, page differentiation, Memory redesign, simplified Orders/Riders/Decisions, responsive behavior, and no console errors.
- Fix any found defect before continuing.

Work log:

Confidence loop:

## Task 7 - Final Visual Polish, QA, And Archive

Status: Pending

Independent verification:
- Full automated tests pass.
- Browser QA passes on desktop and phone.
- Goal folder has completion/archive note.
- Final result directly addresses the user's critique: cleaner UI, real map, anonymized map labels, clearer algorithm advantage, better Memory, less clutter.

Work log:

Confidence loop:
