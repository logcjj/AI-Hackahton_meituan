# Goal 16 Plan - Kandbox-Style Delivery Dispatch Workbench Rebuild

## 1. Requirement Analysis

The goal is a full frontend rebuild for a food-delivery intelligent dispatch demo. This is not a patch to the current single-page replay UI. The new frontend must follow the product skeleton of Kandbox Dispatch: a multi-page dispatch workbench where resources, jobs, live map, planning/decision views, scores, drawers, timelines, and contextual details are separated but linked through one dispatch state model.

The required product mapping is:

- Kandbox Workers -> Rider page
- Kandbox Jobs / Orders -> Order page
- Kandbox Planner / Chart / Gantt -> Decision page
- Kandbox Live Map / GanttMap -> Real-time inference page
- Kandbox Planner Score -> Algorithm comparison scorecard
- Kandbox historical / dispatch assistance context -> Memory page

The implementation must expose five primary pages:

- Real-time inference page
- Orders page
- Riders page
- Decision page
- Memory page

The front-end narrative must be "real-time intelligent dispatch workbench", not "dashboard", "CRUD admin", or "single big map".

## 2. Reverse-Engineering Inputs

Sources checked before code edits:

- Kandbox Dispatch live entry: `https://kd1.kandbox.tech/`
- Kandbox docs guide: `https://disp.kuaihe.tech/guide/getting-started`
- Kandbox Pick-Drop Food Delivery scenario: `https://disp.kuaihe.tech/scenario/pickdrop`
- Public client repository: `https://github.com/kandboxAI/dispatch_client`
- Live app entry assets indicate a Vue / Vuetify app shell with visible module strings for Planner, Workers, Jobs, Gantt, score, team, job, worker, and dispatch.
- The public client repository shows step-environment flows that create Teams, Workers, Jobs, Location Groups, horizon start times, and Pick-Drop job streams through API calls.
- The Pick-Drop scenario confirms the relevant business pattern: an order creates pickup/dropoff jobs, riders are dispatchable workers, and live planning assigns work as time advances.

Reverse-engineered product principles to apply:

- Use an enterprise shell with persistent navigation and route-level workspaces.
- Treat Orders and Riders as input/resource views, not manual maintenance forms.
- Treat Live Map as the primary operations surface, not the whole product.
- Treat Planner / Chart as a separate planning and reasoning view.
- Keep score / planner result cards close to the live map, not buried in a table.
- Use drawers, contextual cards, timelines, compact metrics, map layers, and detail panes instead of full-screen tables.
- Keep visual style restrained: light enterprise surface, neutral grays, dark ink, muted status colors, thin borders, small charts, controlled motion.

## 3. Current Project Context

- Current app is a Python-served static frontend from `web_agent_demo/day_replay_frontend.py`.
- `web_agent_demo/server.py` serves `/` through `render_day_replay_index()`.
- Existing frontend is a large single generated HTML/CSS/JS string with full-day replay behavior.
- Existing backend day simulation already exposes contract-like data from `web_agent_demo/day_simulation.py`.
- There is no npm/Vite frontend project in this repository.
- The safest replacement path is to rewrite the static frontend generator into a new multi-page workbench while preserving the Python server entrypoint and simulation data access.

## 4. Product Architecture

Route design:

- `/` -> redirect/render the Real-time inference workspace by default.
- `#/live` -> Real-time inference page.
- `#/decisions` -> Decision page.
- `#/memory` -> Memory page.
- `#/orders` -> Orders page.
- `#/riders` -> Riders page.

Module split inside the static frontend:

- App shell: top system bar, left nav, scenario selector, status area.
- Data model: preloaded full-day orders, riders, decisions, memory, metrics, and map anchors.
- Router: hash route state and page switching.
- Simulation engine: local timer, play/pause/resume, speed, mode, current time, released events.
- Map layer: merchants, orders, riders, routes, hotspots, old-route fade, differential overlay.
- Scorecard layer: cumulative baseline vs our algorithm and advantage deltas.
- Decision layer: rounds, filters, candidates, scores, final action, abandoned actions, result writeback.
- Memory layer: new memories, curated memories, active recalls, feedback, confidence, recall counts.
- Orders layer: full-day order set, filters by time/area/status/risk, algorithm result columns.
- Riders layer: full-day rider resources, shifts, load, task chains, free-time estimate, mini map.

## 5. Page-Level Design

Real-time inference page:

- Fixed control strip with Start Inference, Pause/Continue, speed, mode switch.
- Main map workspace showing our algorithm as primary route layer.
- Right-side floating cumulative comparison scorecard.
- Bottom event stream, current round summary, and compact cumulative metrics.
- Automatic full-day progression after one click; no per-round manual stepping.
- Animation must be restrained: order pulse, smooth rider movement, old route fade, new route takeover.

Decision page:

- Left decision-round timeline.
- Middle reasoning canvas with trigger, input orders, candidate riders, filtering, scoring, final action, rejected alternatives, result, writeback.
- Right context pane with input context, output result, round summary, and metric effect.
- Data is generated from the same simulation source used by live inference.

Memory page:

- Four non-asset sections: newly formed memories, curated memories, currently hit memories, memory effect feedback.
- Card fields: trigger scenario, context summary, strategy summary, decision result, feedback, confidence, recall count, latest hit time.
- Visual tone should feel like system long-term memory, not log or documentation center.

Orders page:

- Full-day preloaded order universe.
- Filters: time band, business area, status, risk.
- Shows order id, merchant / pickup, created time, promised time, status, risk, area, entered inference, baseline result, our result.
- Layout is dispatch input visibility, not CRUD management.

Riders page:

- Full-day preloaded rider universe.
- Shows rider id/name, online state, shift, area, current load, task chain, estimated free time, performance summary, mini map.
- Layout is resource inventory visibility, not HR admin.

## 6. Data Flow

Real-time inference data flow:

1. Build or reuse one full-day scenario contract at bootstrap.
2. Normalize it into orders, riders, map anchors, decision rounds, memory entries, cumulative metrics, and timeline events.
3. User clicks Start Inference once.
4. A timer advances simulated time by selected speed.
5. Orders and events are released when their event time is reached.
6. Rider positions interpolate along current assigned route samples.
7. Scorecard recomputes cumulative baseline vs our algorithm deltas.
8. Decision and Memory pages read from the same generated source, filtered by current/released time when relevant.

Decision page data flow:

1. Each decision round references released orders and candidate riders.
2. The round stores trigger reason, filtering stages, candidate scores, final action, rejected alternatives, result, and writeback.
3. Timeline selection changes the middle reasoning canvas and right summary pane.
4. Live page can expose current round; Decision page exposes all rounds.

Memory data structure:

- `id`
- `stage`: `new | curated | active | feedback`
- `triggerScenario`
- `contextSummary`
- `strategySummary`
- `decisionResult`
- `effectFeedback`
- `confidence`
- `recallCount`
- `latestHitAt`
- `linkedDecisionId`
- `tags`

## 7. Visual System

Visual direction:

- Enterprise dispatch workstation.
- Light neutral background, compact white cards, charcoal navigation, muted blue-green accent, amber risk accent, restrained red for baseline risk.
- Thin borders, soft but minimal shadows, compact typography, dense but readable cards.
- No game UI, no large-screen neon visuals, no decorative clutter.

CSS tokens:

- Background: warm gray / slate neutral surfaces.
- Accent: dispatch teal / graphite / controlled amber.
- Baseline route: muted red.
- Our route: controlled teal.
- Differential route: amber.
- Typography: use existing platform font fallbacks; avoid decorative "PPT" styling.

## 8. Risks

- The current frontend is monolithic, so the rewrite may accidentally retain old structure unless the shell is replaced deliberately.
- A single static file can become too large; component-like functions must keep sections maintainable.
- Real map animation can become visually noisy if baseline and challenger routes are both fully drawn.
- Orders/Riders can degrade into CRUD tables; their copy and layout must emphasize dispatch input/resource visibility.
- Memory can look like a log list; it must stay organized as remembered strategy patterns with recall/effect evidence.
- Browser verification may require a running Python server and available Leaflet CDN.

## 9. Verification

Automated verification:

- Python compile check for touched Python files.
- Existing pytest suite or focused tests if full suite is too slow.
- Static contract checks for page routes, controls, data fields, and bootstrap JSON.

Browser verification:

- Start local server.
- Open `http://127.0.0.1:<port>/`.
- Verify five primary nav routes exist.
- Verify `/` defaults to real-time inference.
- Verify Start Inference starts automatic time progression.
- Verify pause/resume and speed controls work.
- Verify map shows merchants, orders, riders, route motion, hotspots, and route transition effects.
- Verify scorecard values change dynamically and show our cumulative advantage over baseline.
- Verify Decisions, Memory, Orders, and Riders pages render required fields.
- Verify responsive layout at desktop and narrower widths.
- Verify console errors are zero.

## 10. Rollback Plan

- Keep changes isolated to the frontend generator and, if needed, small backend contract helpers.
- If the multi-page shell breaks runtime data, preserve server routing and temporarily mount static sample data until the normalization layer is fixed.
- If Leaflet fails, keep a deterministic schematic fallback map so the workbench remains demonstrable.
- If performance regresses, reduce animation layers before simplifying product structure.

