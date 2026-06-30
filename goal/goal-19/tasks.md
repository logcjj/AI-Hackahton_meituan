# Goal 19 Tasks

## Task 1 - Reference And Current UI Self-Talk Audit

Status: Completed

Independent verification:
- `goal/goal-19/input.md`, `goal/goal-19/plan.md`, and `goal/goal-19/tasks.md` exist before frontend edits.
- Current UI and source are inspected for verbose/self-narrating copy.
- At least one external/public product reference direction is checked.

Work log:
- Created `goal/goal-19/` and saved the user's latest request before frontend edits.
- Wrote the execution plan and task list for this specific refinement pass.
- Checked public reference direction for mature dispatch/SaaS workbenches:
  - Kandbox Dispatch keeps the product split around workers/jobs/planner/map/score rather than page-length explanation;
  - Fleetbase/Onfleet-style dispatch surfaces emphasize maps, task/driver lists, filters, status chips, KPIs, and route/event state;
  - the useful lesson for this pass is to remove explanatory narration and keep labels, metrics, controls, and evidence.
- Audited the current local preview across all five routes in the in-app browser.
- Browser audit found the main remaining self-talk:
  - Live still shows a verbose waiting-state round result: `首轮决策尚未生成；当前仅展示已进入队列的订单和资源上下文。`;
  - Memory has multiple paragraphs like `这里不是日志列表...`, `用于调度：...`, and long strategy sentences;
  - Orders still exposes `只读证据，不做录入维护`;
  - Decisions uses long step sentences such as `本轮把...不让单个订单孤立决策`;
  - Riders is mostly cleaner but still has secondary explanatory captions.
- Source-mapped the remaining verbose surfaces:
  - `pageHeader()` still renders description, role strip, and page role card;
  - route copy still stores nav hints/subtitles/outcome text;
  - `renderMemoryPage()`, `renderMemoryLayerCard()`, and memory profile/evidence renderers contain the longest visible narrative copy;
  - `renderDecisionAdvantageHero()`, `renderDecisionStepFlow()`, `renderDecisionContext()`, and `renderRoundSummary()` contain sentence-style reasoning copy;
  - `renderOrdersPage()` and `renderRidersPage()` still include disclaimer-style copy.
- No frontend code was modified during this audit task.

Confidence loop:
- 100% confidence for Task 1 scope: the new goal files exist, the latest user request is preserved, public reference direction was checked, current rendered pages were browser-audited, and the remaining self-talk surfaces are mapped to concrete functions for Task 2.

## Task 2 - Primary Surface Copy Compression

Status: Pending

Independent verification:
- Page headers, command cards, role strips, guide text, helper text, and empty states are concise.
- Five main routes still communicate their purpose without explanatory paragraphs.
- No important controls or evidence are removed.

Work log:

Confidence loop:

## Task 3 - Visual Density And Layout Tightening

Status: Pending

Independent verification:
- Removing copy does not leave awkward empty space.
- Cards, timelines, tables, and map side panels look compact and professional.
- Desktop and mobile layouts remain stable.

Work log:

Confidence loop:

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Pending

Independent verification:
- Re-read `input.md`, `plan.md`, and `tasks.md`.
- Run automated tests.
- Browser-check all five routes on desktop and mobile.
- Fix any regression before continuing.

Work log:

Confidence loop:

## Task 4 - Regression Tests And Final Polish

Status: Pending

Independent verification:
- Tests prevent verbose/demo/self-talk copy from returning.
- Live, Decisions, Memory, Orders, and Riders still satisfy the core workbench requirements.
- Full automated tests pass.

Work log:

Confidence loop:

## Task 5 - Commit, Optional Push, And Goal Archive

Status: Pending

Independent verification:
- Worktree contains only intended changes.
- Commit is created.
- If remote publishing is appropriate, push to `main` via SSH.
- Goal folder records completion/archive status.

Work log:

Confidence loop:
