# Goal 18 Plan - Dispatch Workbench Clarity, Chinese UX, Live Map Motion

## 1. Requirement Analysis

The user is reacting to the current Goal 17 frontend after seeing it in the browser and screenshot. The core issues are not about adding more features; they are about clarity, recognizability, and narrative.

Explicit feedback:

- The left navigation is still unclear because it collapses to unreadable abbreviations like `LM`, `PL`, `ME`, `JO`, and `WK`.
- The product should feel closer to a polished large-company Chinese web product, such as Meituan/Baidu-style information architecture, rather than a developer demo.
- Too much English remains in labels, section names, route subtitles, and system copy. Mixed English/Chinese makes the UI hard to understand.
- The Live page should not claim "全日可节省 433 分钟" before inference starts, because that reads as a logical contradiction.
- The map should be zoomable and easier to understand.
- The live replay feels static. The user wants a more visual motion solution: simulated vehicle/rider movement, route animation, and optionally engine-style sound feedback.
- The Decisions page does not explain the algorithm reasoning in a human-readable way; it is too English-heavy and too complex.
- Orders should not imply manual order input. It should be a simple preloaded order/demand view.
- Orders and Riders are still too cluttered; confusing phrases like "重点订单队列" should be simplified or renamed.
- The most important remaining problem is the map: it must be clearer, more beautiful, more interactive, and better at explaining what is happening.

## 2. Product Direction

The next revision should not add density. It should simplify.

Main direction:

- Replace abbreviation-only navigation with readable Chinese labels even in compact/mobile states.
- Remove or translate English product-copy from user-facing surfaces.
- Make Live page state truthful:
  - before start: show "待推理" and "开始后将累计验证优势";
  - during replay: show current cumulative advantage;
  - after full replay: show final full-day advantage.
- Improve map experience:
  - keep Leaflet zoom/pan controls visible and usable;
  - add clear map action layer with current rider/order/merchant focus;
  - add moving vehicle/rider indicator along active route;
  - add route pulse/progress animation;
  - add optional sound toggle using Web Audio, not autoplay.
- Decisions page should become a clear Chinese "算法推理过程":
  - trigger;
  - available orders;
  - candidate riders;
  - filters;
  - score comparison;
  - final assignment;
  - why rejected alternatives lost;
  - memory feedback.
- Orders page should become "订单池 / 需求看板", not "输入".
- Riders page should become "骑手运力 / 运力看板", not HR/resource inventory.
- Use clear Chinese field names and short explanations; avoid clever but vague terms.

## 3. Visual System Direction

Target tone:

- Chinese enterprise web app.
- Clean, commercial, credible.
- Familiar enough for non-technical viewers.
- Closer to Meituan/Baidu-style product clarity:
  - readable sidebar labels;
  - primary action bar;
  - simple KPI cards;
  - step-by-step explanation panels;
  - restrained yellow/green/blue accent system;
  - no cryptic abbreviations as primary navigation.

Avoid:

- English module names as primary labels.
- "Kandbox", "ReasonGraph", "Planner", "Chart", "Workers", "Jobs" as visible user-facing copy unless shown in developer-only hidden markers or tests.
- Dense card grids.
- Vague names like "重点订单队列" when the user cannot infer the meaning.
- Showing final full-day result before the replay starts as if already inferred.

## 4. Implementation Strategy

Likely touched files:

- `web_agent_demo/day_replay_frontend.py`
- `tests/test_web_agent_demo.py`
- `web_agent_demo/dispatch_workbench_data.py` only if labels/data contracts need adjustment
- `goal/goal-18/*`

Implementation layers:

1. Navigation and copy cleanup:
   - Replace nav icon abbreviations with Chinese short labels.
   - Ensure collapsed/mobile nav remains readable.
   - Remove visible English route subtitles and role cards.
   - Keep machine-readable data attributes for tests if needed.

2. Live page truthfulness:
   - Before start, do not show final advantage as the main headline.
   - Show "等待开始推理" and explain results will be accumulated during replay.
   - Move final full-day result into a "推演完成后显示" / "历史全量回放目标" secondary hint or only after finish.

3. Map interaction and motion:
   - Expose Leaflet zoom controls.
   - Add map action status explaining current active assignment.
   - Animate active route progress.
   - Add moving rider/vehicle marker along route.
   - Add optional "引擎音效" toggle that starts only after user click and can be turned off.
   - Ensure no sensitive labels leak.

4. Decisions simplification:
   - Rename visible surface to "算法推理过程".
   - Convert English-heavy labels into plain Chinese.
   - Show a small number of sequential reasoning steps.
   - Translate candidate path concepts into "采纳方案 / 放弃方案 / 放弃原因".

5. Orders and Riders simplification:
   - Orders: rename to "订单池"; explain all data is preloaded, no manual input.
   - Replace "重点订单队列" with clearer wording such as "当前需要关注的订单".
   - Riders: rename to "骑手运力"; show online/忙碌/即将空闲/区域覆盖, not personnel language.
   - Reduce redundant fields and keep details secondary.

6. QA and archive:
   - Re-run automated tests.
   - Browser check desktop and phone.
   - Confirm no visible English-heavy copy in key surfaces.
   - Confirm no pre-start final-result contradiction.
   - Confirm map zoom and motion work.
   - Confirm goal archive complete.

## 5. Risks

- Existing tests assert many English/Kandbox strings; tests must be updated carefully to preserve structural contract while removing user-facing English.
- Leaflet zoom can be disabled accidentally by overlay CSS; browser verification must interact with zoom state.
- Web Audio cannot autoplay; sound must be user-initiated and optional.
- Route animation should be clear but not game-like.
- Removing too much detail can break the original requirement that decisions remain traceable. Details should remain secondary, not disappear.

## 6. Verification Plan

Automated:

- `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/dispatch_workbench_data.py tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q`

Static checks:

- No visible nav abbreviations `LM`, `PL`, `ME`, `JO`, `WK` as primary nav labels.
- Key route/page headings are Chinese.
- Live initial headline does not equal final full-day saved minutes before start.
- User-facing copy avoids visible `Workers`, `Jobs`, `Planner`, `Chart`, `ReasonGraph`, and similar English-heavy terms.
- Orders page does not imply manual order entry.

Browser:

- Desktop:
  - five routes render;
  - nav readable;
  - Live starts in "等待开始推理" state;
  - clicking start updates cumulative advantage over time;
  - map zoom controls work;
  - moving marker / route progress visible;
  - optional sound toggle works after click and can stop;
  - no console errors.
- Phone:
  - nav remains readable, not abbreviation-only;
  - no horizontal overflow;
  - Live, Decisions, Orders, Riders are readable.

## 7. Rollback Plan

- Keep each change scoped to the frontend generator and tests.
- If motion or sound causes instability, keep map zoom/readability and disable sound or animation behind a control.
- If copy simplification removes required evidence, restore it in a collapsible/secondary panel.
- If browser tile/CDN assets fail, retain deterministic fallback map.
