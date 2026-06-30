# Goal 19 Plan - Reduce Self-Talk And Professionalize Dispatch Workbench

## 1. Requirement Analysis

The user says the current UI still contains too much "self-talk" and explanatory filler. The problem is not that the product lacks information; the problem is that the interface keeps narrating itself. The next iteration should feel more like a mature enterprise dispatch system:

- concise module titles;
- short state labels;
- fewer explanatory paragraphs;
- fewer marketing-style phrases;
- fewer "why this page exists" sentences;
- clearer product hierarchy;
- stronger visual restraint.

The user also asked to "look at others", so this iteration should briefly reference mature dispatch/SaaS dashboard patterns before editing:

- page surfaces should favor command bars, filters, KPI strips, maps, timelines, and dense evidence panels;
- explanatory copy should move out of the primary surface or be removed;
- visible text should mostly be nouns, states, metrics, and actions;
- no decorative "AI narration" should remain in the main workbench.

## 2. Scope

Primary files:

- `web_agent_demo/day_replay_frontend.py`
- `tests/test_web_agent_demo.py`
- `goal/goal-19/tasks.md`

Potential supporting file:

- `web_agent_demo/dispatch_workbench_data.py` only if visible labels come from data payloads.

## 3. Product Direction

Change the interface from "demo explaining itself" to "operator workbench":

- Live page:
  - keep controls, map, scorecards, event stream;
  - remove instructional paragraphs around the page header, map, event flow, and summary cards;
  - use short operational labels such as `待推理`, `运行中`, `暂停`, `累计优势`, `当前动作`.

- Decisions page:
  - keep the timeline and traceability;
  - compress reasoning into a small stepper and concise evidence blocks;
  - avoid long sentences that explain the algorithm like a script.

- Memory page:
  - make it feel like a memory state console, not a narrated knowledge base;
  - use short labels: `新记忆`, `已整理`, `命中`, `反馈`.

- Orders page:
  - keep read-only order pool;
  - remove "this is not CRUD" style explanatory copy from the primary surface;
  - show filters, KPIs, focus list, and compact evidence table.

- Riders page:
  - keep read-only capacity board;
  - remove HR/backend disclaimers from the primary surface;
  - show area coverage, state, load, task chain, and compact rider cards.

## 4. Visual Direction

The style should be closer to real enterprise SaaS:

- calmer page headers;
- compact control bars;
- smaller helper text;
- more whitespace discipline;
- fewer soft narrative cards;
- no big promotional copy;
- no redundant page role strips;
- no "guide" or "how to read this" panels on first screen.

## 5. Execution Plan

1. Inspect mature public references and the current rendered UI for visible self-talk.
2. Source-map verbose copy and redundant UI blocks.
3. Remove or compress explanation-heavy surfaces across all five pages.
4. Tighten visual spacing so removal does not leave awkward empty cards.
5. Add regression tests that prevent verbose/demo copy from returning.
6. Run automated tests and browser QA on all routes.
7. Commit the completed work and update this goal record.

## 6. Risks

- Removing too much text can make the demo hard to understand for first-time viewers.
- Decisions and Memory still need traceability; evidence should be preserved in compact form.
- Tests may currently depend on old explanatory copy and need to be updated carefully.
- Visual spacing can break after hiding/removing text-heavy blocks.

## 7. Verification Plan

Automated:

- `python3 -m py_compile web_agent_demo/day_replay_frontend.py tests/test_web_agent_demo.py`
- `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q`

Static checks:

- No visible "自述式" phrases such as `用于展示`, `我们把`, `不是`, `说明`, `怎么看`, `为什么`, `开始后将`, `本页`, `工作台方式` in primary UI blocks unless they are essential controls or labels.
- No old English/Kandbox visible copy returns.
- Main headings are short Chinese product labels.

Browser:

- Open all five routes on desktop and mobile.
- Confirm no horizontal overflow.
- Confirm Live can start/pause/zoom and scorecards update.
- Confirm Decisions timeline still changes the selected round.
- Confirm Orders/Riders filters still work.
- Confirm console has no page errors.

## 8. Rollback Plan

- Keep edits scoped to frontend rendering and tests.
- If a page becomes too terse, restore only short field labels or compact chips, not paragraphs.
- If layout breaks after removing copy, adjust CSS spacing rather than reintroducing narration.
