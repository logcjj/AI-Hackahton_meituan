# Auto-generated evolved strategy: gen01_M1_003
# operator: M1   regime: normal   generation: 1
# parent: gen01_E1_001
# thought: [stub:refine(gen01_E1_001)] operator M1 (gen 1, parent gen01_E1_001). Rank by an objective-aware key for the normal regime: favour bundles only when their coverage gain beats the expected accepted score, protect against the 100/task all-rej
from __future__ import annotations


def propose(candidates, all_tasks, deadline, helpers):
    """Greedy disjoint dispatch driven by an evolved ranking key.

    A row is (task_key, task_ids, courier_id, score, willingness, row_index).
    We sort rows by `_rank(row)` (smaller = picked earlier), then greedily take
    rows whose courier is unused and whose tasks are still uncovered, forming a
    feasible disjoint assignment. The evolved part is `_rank`."""
    time_left = helpers.get("time_left")
    task_count = helpers.get("task_count", len(all_tasks))
    courier_count = helpers.get("courier_count", 1)
    scarcity = courier_count / max(1, task_count)

    def _rank(row):
        task_key, task_ids, courier_id, score, willingness, row_index = row
        n_tasks = len(task_ids)
        w = max(willingness, 1e-6)
        gfloor = max(w, 0.05)
        parent_key = (-n_tasks, score / max(n_tasks, 1), -w, score, -w)
        key = (len(task_ids), w * score + (1.0 - w) * 100.0, parent_key)
        return key

    used_couriers = set()
    covered_tasks = set()
    result = []
    rows = sorted(candidates, key=_rank)
    target = set(all_tasks)
    for task_key, task_ids, courier_id, score, willingness, row_index in rows:
        if time_left is not None and time_left(deadline) <= 0.01:
            break
        if courier_id in used_couriers:
            continue
        if any(task_id in covered_tasks for task_id in task_ids):
            continue
        used_couriers.add(courier_id)
        covered_tasks.update(task_ids)
        result.append((task_key, [courier_id]))
        if covered_tasks >= target:
            break
    return result
