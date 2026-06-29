# Goal 18 Tasks

## Task 1 - Goal Setup And Current UI Clarity Audit

Status: Completed

Independent verification:
- `goal/goal-18/input.md`, `goal/goal-18/plan.md`, and `goal/goal-18/tasks.md` exist before frontend code edits.
- User screenshot and current browser UI are inspected.
- Current defects are mapped to concrete implementation tasks.

Work log:
- Created `goal/goal-18/` as the next available goal directory after `goal-17`.
- Saved the new `/goal` request verbatim in `goal/goal-18/input.md`, including the referenced screenshot path.
- Wrote `goal/goal-18/plan.md` with the concrete redesign direction:
  - Chinese-first navigation and page copy;
  - truthful Live page state before inference starts;
  - zoomable and more animated map;
  - human-readable decision reasoning;
  - simpler Orders and Riders pages;
  - final desktop/phone QA and archive.
- Wrote `goal/goal-18/tasks.md` with seven tasks and a debug cycle after every three tasks.
- Confirmed starting branch and state:
  - branch `codex/kandbox-dispatch-workbench`;
  - latest prior commit `7a0053f chore: archive dispatch workbench polish goal`;
  - worktree had no pre-existing uncommitted changes before goal setup.
- Inspected the user screenshot:
  - current compact nav shows only `FD`, `LM`, `PL`, `ME`, `JO`, and `WK`, which is not understandable to a non-technical viewer;
  - the Riders page screenshot still shows visible English such as `Workers`, `ORDERS`, `DECISIONS`, and `assigned by`;
  - the page looks like a narrow technical dashboard rather than a polished Chinese product surface.
- Browser-audited the current open page at `http://127.0.0.1:18772/?v=preview-open#/live`:
  - viewport was 643px wide;
  - shell columns were `78px minmax(0px, 1fr)`, so the sidebar collapsed too early;
  - each nav item's text block was hidden and only the abbreviation icon remained visible;
  - the nav icons were `LM`, `PL`, `ME`, `JO`, and `WK`;
  - visible route subtitle still used `Live Map 工作台`;
  - role card still showed `Weekday full-day delivery replay`;
  - Live headline showed `已节省 433.0 分钟` because the page had retained a prior paused/replayed state, reinforcing the user's concern that the system can appear to claim a full-day result before the viewer understands the inference process;
  - `.leaflet-control-zoom` buttons were absent, confirming the map cannot be zoomed through normal controls;
  - browser console reported 0 errors, so this is a product/UX issue rather than a crash.
- Browser-audited all five routes:
  - all routes contain repeated visible English/Kandbox terms such as `Dispatch`, `Live Map`, `Planner`, `Chart`, `Memory`, `Jobs`, `Orders`, `Workers`, `assigned`, `recall`, and `writeback`;
  - Live contains `Live Map / Advantage Console` and still foregrounds final savings copy;
  - Decisions contains `ReasonGraph Planner`, `Planner / Chart`, `candidate`, and too many English reasoning terms;
  - Memory is structurally better but still contains `Memory`, `Planner`, `recall`, and `writeback` in visible copy;
  - Orders contains `Demand Input Board`, `Jobs / Orders`, and the confusing heading `重点订单队列`;
  - Riders contains `Capacity Resource Board`, `Workers`, `assigned by our planner`, and visible rider card titles like `Courier 1` through `Courier 8`.
- Source-mapped the main defects:
  - `routeCopy` still uses abbreviation icons and English module names around `web_agent_demo/day_replay_frontend.py` lines 1717-1763;
  - the 1180px breakpoint hides `.nav-copy`, causing abbreviation-only navigation around lines 1636-1641;
  - Live pre-start/fallback copy still references final full-day savings and `Planner` around lines 2313-2325;
  - `pageHeader` calls still expose `Live Map / Advantage Console`, `ReasonGraph Planner`, `Demand Input Board`, and `Capacity Resource Board`;
  - Leaflet is initialized with `scrollWheelZoom: false` and `zoomControl: false`, making map zoom unavailable;
  - Orders and Riders metric captions still use English such as `assigned orders` and `assigned by our planner`.
- Mapped next implementation:
  - Task 2 should fix nav/readability and broad Chinese-first copy.
  - Task 3 should fix Live initial-state truthfulness, map zoom, movement visualization, and optional sound control.
  - Task 4 should rebuild Decisions into a plain Chinese reasoning process.
  - Task 5 should simplify Orders and Riders wording/layout.
  - Task 6 should do final visual polish toward a Chinese enterprise product feel.

Confidence loop:
- 100% confidence for Task 1 scope: the required goal files exist before frontend code edits, the user screenshot was visually inspected, the current browser UI was audited across all five routes, console state was checked, the specific source locations for the main defects were identified, and the findings are mapped to later tasks.

## Task 2 - Chinese Navigation And User-Facing Copy Cleanup

Status: Completed

Independent verification:
- Sidebar/compact/mobile navigation uses readable Chinese labels, not abbreviation-only `LM/PL/ME/JO/WK`.
- Main visible labels, subtitles, cards, and route roles avoid confusing English/Chinese mixing.
- Structural test attributes can remain, but visible copy is Chinese and understandable.

Work log:
- Replaced abbreviation-first navigation:
  - brand changed from `FD / Food Dispatch` to `调度 / 外卖调度`;
  - route icons changed from `LM/PL/ME/JO/WK` to Chinese one-character cues;
  - route labels changed to `实时推理 / 决策过程 / 长期记忆 / 订单池 / 骑手运力`.
- Fixed responsive navigation:
  - at `max-width: 1180px`, the sidebar now keeps readable Chinese route names instead of hiding `.nav-copy`;
  - at `max-width: 720px`, the top navigation displays the five Chinese page names and hides only the decorative icon.
- Converted main page copy from mixed English/reference terms to Chinese product language:
  - removed visible `Live Map / Advantage Console`, `ReasonGraph Planner`, `Hermes Memory Hub`, `Demand Input Board`, `Capacity Resource Board`;
  - page headers now use `实时推演总览`, `算法推理过程`, `长期记忆中心`, `订单池看板`, `骑手运力看板`;
  - the page role strip no longer says `Kandbox: ...`, while structural `data-*` markers remain.
- Updated user-facing data labels:
  - statuses now show `待释放 / 已进推理 / 已分配 / 已送达 / 超时风险`;
  - risks show `低风险 / 中风险 / 高风险`;
  - rider states show `可接单 / 配送中 / 临近下线 / 离线`;
  - demand phases, weather, shock tags, memory stages, memory channels, and profile types now have Chinese display labels.
- Cleaned decision and memory visible reasoning text:
  - algorithm labels now show `最近距离基线`, `成本优先基线`, `风险感知基线`, `我方智能调度方案`;
  - common English reasoning summaries from the replay data are translated in the display layer;
  - counts and units now read as `单`, `名骑手`, `次回写`, `分钟`, `毫秒`.
- Simplified orders/riders copy at the label level:
  - `订单输入` changed to `订单池`;
  - `重点订单队列` changed to `需关注订单`;
  - `运力资源` changed to `骑手运力`;
  - rider cards no longer show `Courier 1` style names as the main visible title, using `骑手 RID` instead.
- Synchronized route payload labels in `web_agent_demo/dispatch_workbench_data.py`.
- Updated frontend/data tests so Chinese labels are the contract and old visible English/abbreviations are forbidden.
- Verification run:
  - `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/dispatch_workbench_data.py tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py` -> `19 passed`
  - `uv run --with pytest pytest -q` -> `107 passed`
- Browser verification:
  - restarted `127.0.0.1:18772` with the updated server code;
  - at 643px width, nav displayed `实时推理 / 决策过程 / 长期记忆 / 订单池 / 骑手运力`, not `LM/PL/ME/JO/WK`;
  - at 390px width across all five routes, nav remained readable, no horizontal overflow, no old visible page titles, and no console errors;
  - restored the browser to the Live page after verification.

Confidence loop:
- 100% confidence for Task 2 scope: automated tests pass, the browser confirmed readable Chinese navigation at the user screenshot width and phone width, all five route headers are Chinese-first, old visible English page titles and abbreviation-only nav labels are covered by regression tests, and the remaining English found by static scan is internal data/test code rather than primary visible UI copy. Map zoom/motion, pre-start result truthfulness, and deeper page simplification are intentionally deferred to later tasks.

## Task 3 - Live Page Truthful State And Map Interaction Upgrade

Status: Completed

Independent verification:
- Before start, Live page does not present final full-day savings as already inferred.
- Start/pause/continue/speed/mode controls still work.
- Map zoom controls are visible and browser-verified.
- Active route and moving rider/vehicle marker make replay movement understandable.
- Optional sound control is user-triggered and does not autoplay.
- No sensitive map labels leak.

Work log:
- Reworked Live page pre-start advantage copy:
  - initial headline is now `等待开始推理`;
  - the target strip says `开始后累计验证 / 全日结论暂不展示 / 地图将自动推进`;
  - removed the old pre-start `全日可节省` / `全日目标` contradiction from visible first-screen state;
  - topbar now says `优势验证 / 开始后累计` instead of presenting a final saved-minute value before inference.
- Added a clearer map action layer:
  - `map-action-status` explains the current state before start, during route takeover, during rider movement, and while waiting for the first route;
  - active rider/order text is Chinese and scoped to anonymized rider/order IDs;
  - the overlay has `pointer-events: none` and is positioned away from Leaflet controls so it cannot block zoom.
- Upgraded map interaction:
  - enabled Leaflet `zoomControl`, `scrollWheelZoom`, `boxZoom`, and `doubleClickZoom`;
  - browser-verified that clicking zoom changes tile level from 13 to 14;
  - kept the anonymous no-label tile layer and fallback deterministic coordinate map.
- Added motion cues:
  - moving rider pins now pulse and show `移动中` in fallback mode;
  - Leaflet rider markers expose `data-motion="moving"`;
  - active progress route segments are rendered for moving rider/order pairs;
  - the action card describes which rider is executing which order and the route progress percentage.
- Added optional engine sound:
  - `引擎音效：关` is the default and does not autoplay;
  - sound can only turn on after the user clicks the toggle;
  - sound stops on pause, completion, or leaving the Live route while keeping the user's explicit toggle state.
- Fixed runtime state cleanup:
  - added `stopLiveRuntime()` so switching away from Live clears the timer and stops sound;
  - final replay state now displays `推演完成`, and the pause/continue button becomes `已完成` until the user starts a new run.
- Updated regression tests with markers for the new sound control, truthful pre-start copy, map action status, zoom settings, motion helpers, and completion state.
- Verification run:
  - `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/dispatch_workbench_data.py tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
  - `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py` -> `19 passed`
  - `uv run --with pytest pytest -q` -> `107 passed`
- Browser verification:
  - restarted `127.0.0.1:18772` with the latest code;
  - refreshed `http://127.0.0.1:18772/?v=open-now#/live`;
  - confirmed initial Live state shows `等待开始推理`, `全日结论暂不展示`, `未开始`, and `引擎音效：关`;
  - confirmed forbidden pre-start text `全日可节省` / `全天可节省` is not visible;
  - confirmed Leaflet zoom control exists and clicking zoom changes tile level from 13 to 14;
  - confirmed start/pause/continue controls switch between `自动推理中` and `已暂停`;
  - confirmed speed can switch to `4x` and mode can switch to `叠加`;
  - confirmed after auto-advancing, the map action card shows an active rider executing an order and Leaflet has moving rider pins;
  - confirmed sound remains off before user action, toggles to `引擎音效：开` only after click, and was turned back off after testing;
  - confirmed browser console page errors: none.

Confidence loop:
- 100% confidence for Task 3 scope: automated tests and browser checks cover the user's three core Live-page complaints. The page no longer claims full-day savings before inference starts, map zoom is both visible and actually clickable, the replay has a clear moving-rider/action narrative, sound is explicit user-triggered feedback rather than autoplay, and page errors are clean. One discovered defect, the action card blocking the zoom control, was fixed and re-verified by observing the tile level change after clicking zoom.

## Debug Cycle 1 - Tasks 1-3 Comprehensive Check

Status: Pending

Independent verification:
- Re-read `input.md`, `plan.md`, and `tasks.md`.
- Run automated tests.
- Browser-check Live page, nav, initial-state truthfulness, map zoom, motion, sound control, desktop/mobile layout, and console errors.
- Fix any discovered defect before continuing.

Work log:

Confidence loop:

## Task 4 - Decisions Page Human-Readable Reasoning Redesign

Status: Pending

Independent verification:
- Decisions page is visibly a Chinese "算法推理过程" page.
- It explains trigger, orders, riders, filtering, scoring, final action, rejected alternatives, and memory feedback in a simple sequence.
- English-heavy visible concepts like `ReasonGraph Planner`, `candidate path`, and `Planner / Chart` are removed or hidden from user-facing copy.
- Required decision evidence remains accessible.

Work log:

Confidence loop:

## Task 5 - Orders And Riders Simplification

Status: Pending

Independent verification:
- Orders page is framed as a preloaded order pool/demand board, not manual input or CRUD.
- Confusing copy such as "重点订单队列" is replaced with clearer Chinese.
- Orders first screen is simple and readable.
- Riders page is framed as rider capacity/dispatch coverage, not HR/resource inventory.
- Riders first screen is simple and readable.

Work log:

Confidence loop:

## Task 6 - Visual Polish Toward Chinese Enterprise Product Style

Status: Pending

Independent verification:
- Overall frontend feels more like a polished Chinese enterprise workbench.
- Typography, colors, spacing, page headers, and cards are cleaner and less developer-demo-like.
- The UI is simpler without losing the core algorithm advantage narrative.
- Desktop and phone layouts remain stable.

Work log:

Confidence loop:

## Debug Cycle 2 - Tasks 4-6 Comprehensive Check

Status: Pending

Independent verification:
- Re-read `input.md`, `plan.md`, and `tasks.md`.
- Run automated tests.
- Browser-check Decisions, Orders, Riders, visual polish, desktop/mobile layout, and console errors.
- Fix any discovered defect before continuing.

Work log:

Confidence loop:

## Task 7 - Final QA, Completion Audit, And Archive

Status: Pending

Independent verification:
- Full automated tests pass.
- Browser QA passes on desktop and phone across all five routes.
- Live replay clearly shows why the system is running and how advantage accumulates.
- Map zoom/motion are verified.
- User-facing copy is Chinese-first and understandable.
- Goal folder has completion/archive note.

Work log:

Confidence loop:
