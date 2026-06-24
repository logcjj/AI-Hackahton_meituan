# Goal 13 Plan - Completion Claim Re-Audit

## 1. Requirement Analysis

The user is challenging the previous completion claim. The correct response is not to defend the prior `complete` status, but to re-audit the current project state against the full Goal 12 requirement set and prove whether the shipped functionality is actually complete.

Key requirements to verify:

- The previous frontend is fully discarded from the rendered product, with no stale old-shell UI reachable from `/`.
- The new frontend supports full-day simulation replay rather than a small tick sandbox.
- Greedy and AutoSolver compare side by side on the same day/order stream.
- The UI shows time/cost/KPI savings and explains why AutoSolver is better.
- The UI shows readable algorithm reasoning tied to decision points.
- The UI demonstrates Memory/self-evolution: recall, writeback, future policy shift, and env-only external predictor seam.
- The simulation covers realistic day phases, orders, couriers, merchants, shocks, congestion, weather, and supply dynamics.
- Optional external simulation engine support is represented safely without forcing heavyweight dependencies.
- APIs, tests, browser behavior, and security/secrets handling remain sound.
- The previous completion archive is accurate or must be corrected.

## 2. Context

- Goal 12 was marked complete after Task 12 and commit `1b20ee4 Complete replay goal final audit`.
- The user now correctly asks whether all functionality was actually checked before completion.
- Current worktree is authoritative; prior summaries are not proof.
- `goal/goal-12/input.md` remains untracked because it preserves sensitive raw input and must not be staged accidentally.

## 3. Risks

- Completion bias: treating existing tests as proof without checking they cover each requirement.
- Browser risk: static tests may pass while runtime controls, timeline, API calls, or layout are broken.
- Old-code risk: stale legacy frontend or incompatible API paths may still be reachable.
- Security risk: raw API credentials may leak into committed files, rendered HTML, or API payloads.
- Process risk: marking this audit complete before the requirement-by-requirement evidence is strong.

## 4. Execution Plan

1. Create Goal 13 docs before any code changes.
2. Derive an explicit requirement matrix from Goal 12 input/plan/tasks and current source.
3. Inspect current source and tests to map evidence for each requirement.
4. Run static, unit, API, browser, and security audits against the matrix.
5. Fix any defect found, then re-run the relevant checks.
6. Record all evidence and unresolved risks in Goal 13.
7. Only call `update_goal(status="complete")` if every requirement is proven by current evidence.

## 5. Verification

- Goal 13 docs exist before code changes.
- Requirement matrix has pass/fail/weak-evidence status for every explicit requirement.
- `python3 -m py_compile` passes for relevant Python modules and tests.
- Focused day-simulation/frontend tests pass.
- Full test suite passes.
- API probes validate day-simulation endpoints.
- Browser automation validates root load, controls, timeline, side-by-side panels, KPI updates, reasoning highlights, memory panel, desktop/mobile layout, and no console/network errors.
- Sensitive scan excludes raw goal input/output artifacts and finds no business-code leaks.

## 6. Rollback/Correction Plan

- If functionality is incomplete, update Goal 12 completion documentation to reflect the gap and fix the implementation.
- If only the audit documentation was insufficient, add evidence without changing product code.
- If previous completion was materially wrong, keep this goal active until corrected rather than claiming success.
