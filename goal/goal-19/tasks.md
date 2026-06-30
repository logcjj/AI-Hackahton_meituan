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

Status: Completed

Independent verification:
- Page headers, command cards, role strips, guide text, helper text, and empty states are concise.
- Five main routes still communicate their purpose without explanatory paragraphs.
- No important controls or evidence are removed.

Work log:
- Removed explanation-heavy header surfaces from the rendered shell:
  - removed sidebar guide copy;
  - removed topbar subtitle DOM;
  - removed page header description, role strip, and page role card rendering;
  - removed hidden nav hint/module spans from rendered navigation.
- Compressed route copy into short product labels such as `地图 / 评分 / 事件`, `轮次 / 评分 / 输出`, and `沉淀 / 召回 / 反馈`.
- Reworked Live pre-start state:
  - `开始后累计验证` -> `累计优势 待计算`;
  - `全日结论暂不展示` -> `全日结论 待生成`;
  - `地图将自动推进` -> `地图推进 待启动`;
  - event caption now shows `事件 N`.
- Compressed Decisions page:
  - `本轮推理说明` -> `推理步骤`;
  - six-step reasoning labels are now `触发 / 订单 / 候选骑手 / 过滤 / 评分 / 输出`;
  - removed long "先解释为什么..." hero paragraph;
  - shortened right-side context and Live decision summary into field-style metrics.
- Compressed Memory page:
  - `记忆概览` -> `记忆状态`;
  - removed `这里不是...` and profile disclaimer paragraphs;
  - removed visible `用于调度` narrative from memory layer cards;
  - mapped `AutoSolver saves...` result headlines into Chinese short metrics.
- Compressed Orders and Riders:
  - removed `不录入、不编辑` and `不是人事后台` disclaimers;
  - `订单来源` -> `订单状态`;
  - `订单全集核对 / 只读证据，不做录入维护` -> `订单全集 / 全量订单`;
  - `只读运力池` -> `运力池`.
- Added display-layer Chinese mapping for business areas and merchant labels:
  - `Merchant 15 / metro_exit` now renders as `商家 15 / 地铁口`;
  - `office_core`, `mall_foodcourt`, and other area keys now render as Chinese labels in visible lists, filters, tables, and cards.
- Updated regression tests:
  - visual polish marker advanced to `chinese-enterprise-workbench-v4`;
  - required markers now assert short product labels;
  - forbidden markers prevent old explanatory copy from returning.
- Verification:
  - `python3 -m py_compile web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py`;
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py::WebAgentDemoTest::test_home_page_contains_dispatch_workbench_shell` -> passed;
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py` -> `19 passed`;
  - browser audit across Live, Decisions, Memory, Orders, Riders: visible noisy-copy count `0`, no horizontal overflow, no console errors.

Confidence loop:
- 100% confidence for Task 2 scope: the primary surfaces now use short product labels rather than explanatory paragraphs, the old self-talk phrases are forbidden by tests, browser verification covered all five routes, and no controls/evidence panels were removed.

## Task 3 - Visual Density And Layout Tightening

Status: Completed

Independent verification:
- Removing copy does not leave awkward empty space.
- Cards, timelines, tables, and map side panels look compact and professional.
- Desktop and mobile layouts remain stable.

Work log:
- Removed the visible duplicate page-title card:
  - `pageHeader()` now emits a hidden `page-anchor` structure marker only;
  - topbar remains the single visible route title;
  - all five routes now start directly with the workbench surface.
- Advanced the visual contract marker to `chinese-enterprise-workbench-v5`.
- Tightened layout density:
  - route view top padding reduced;
  - Live advantage hero padding/gap reduced;
  - Live headline size reduced from large presentation scale to dashboard scale;
  - Memory command center padding/gap and title size reduced;
  - Decisions/Orders/Riders command card padding/gap and title size reduced.
- Updated tests for the v5 visual contract.
- Verification:
  - `python3 -m py_compile web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py`;
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py::WebAgentDemoTest::test_home_page_contains_dispatch_workbench_shell` -> passed;
  - browser desktop audit at `1280x720`: visible `.page-head` count `0`, each route first card starts immediately under topbar, no horizontal overflow, no console errors;
  - browser mobile audit at `390x780`: readable Chinese nav, visible `.page-head` count `0`, no horizontal overflow;
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py` -> `19 passed`.

Confidence loop:
- 100% confidence for Task 3 scope: the visible duplicate title layer is gone, the main workbench surfaces are more compact, desktop/mobile browser layout is stable, and the regression tests pass.

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
