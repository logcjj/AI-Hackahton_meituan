# Goal 17 Completion Archive

Status: Completed and archived

Completed at: 2026-06-29

Branch: `codex/kandbox-dispatch-workbench`

## Final Outcome

The dispatch demo frontend was polished into a cleaner Kandbox-style enterprise dispatch workbench focused on proving algorithm advantage. The final implementation addresses the user's critique:

- Left navigation now has Chinese module labels, role badges, hints, and Kandbox module mappings.
- Pages are differentiated by layout role and route theme instead of looking like the same card grid.
- The Live page is advantage-first, with dominant cumulative comparison, real Leaflet map, fallback map, live controls, compact event flow, and compact current-decision summary.
- Map labels are anonymized with `M-01`, `R-01`, and `O-001` style refs; raw merchant/rider/area names are not rendered on the map.
- Memory is redesigned as a Hermes-style long-term memory hub with global layers, profiles, active recall, writeback, and feedback.
- Decisions uses a ReasonGraph-style advantage-first reasoning surface with candidate elimination and required evidence fields.
- Orders and Riders are framed as dispatch input/resource views, not CRUD or personnel tables.
- Mobile layout is explicitly one-column at phone width with a five-column top nav and no horizontal overflow.
- Leaflet CDN assets are version-pinned and protected with SRI plus anonymous CORS.

## Final Verification

Automated checks:

- `python3 -m py_compile web_agent_demo/day_replay_frontend.py web_agent_demo/dispatch_workbench_data.py tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py`
- `uv run --with pytest pytest -q tests/test_web_agent_demo.py tests/test_dispatch_workbench_data.py` -> 19 passed
- `uv run --with pytest pytest -q` -> 107 passed

Browser checks:

- Desktop QA covered `#/live`, `#/decisions`, `#/memory`, `#/orders`, and `#/riders`.
- Phone QA covered the same five routes at 390px width.
- Live interaction QA verified start, pause, continue, 4x speed, automatic frame progression, event flow, round summary, cumulative advantage, route updates, and no sensitive map title leaks.
- SRI browser smoke verified Leaflet integrity/crossorigin attributes render and the Live map still reaches Leaflet mode.
- Browser page console errors were zero in final checks.

## Archive Notes

This goal folder is archived as complete. The authoritative task log remains in `goal/goal-17/tasks.md`; this file is the completion/archive marker for the folder.
