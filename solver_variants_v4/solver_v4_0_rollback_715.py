import random
import time


def solve(input_text: str) -> list:
    deadline = time.monotonic() + 8.7
    lines = input_text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0

    candidates = []
    all_tasks = set()
    for row_index, line in enumerate(lines[start:]):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, willingness_text = parts[:4]
        task_key = task_key.strip()
        courier_id = courier_id.strip()
        task_ids = tuple(t.strip() for t in task_key.split(",") if t.strip())
        if not task_ids or not courier_id:
            continue
        try:
            score = float(score_text)
            willingness = float(willingness_text)
        except ValueError:
            continue
        candidates.append((task_key, task_ids, courier_id, score, willingness, row_index))
        for task_id in task_ids:
            all_tasks.add(task_id)

    if not candidates:
        return []

    solutions = []
    singles = [c for c in candidates if len(c[1]) == 1]
    courier_count = len({c[2] for c in candidates})
    task_count = len(all_tasks)
    avg_willingness = sum(c[4] for c in candidates) / len(candidates)
    scarce = courier_count <= task_count
    low_willingness = avg_willingness < 0.27
    abundant = courier_count >= len(all_tasks) * 3 // 2 and _singles_cover_all_tasks(singles, all_tasks)

    if singles:
        single_solution = _solve_single_task_multidispatch(singles, all_tasks)
        if not scarce:
            if not low_willingness:
                single_deadline = min(deadline, time.monotonic() + 5.5) if abundant else min(deadline, time.monotonic() + 1.0)
                single_solution = _destroy_repair_single_solution(single_solution, singles, all_tasks, single_deadline)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, deadline)
            single_solution = _rebalance_single_solution(single_solution, singles, all_tasks, deadline)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, deadline)
        solutions.append(single_solution)

        if abundant and time.monotonic() < deadline - 1.9:
            random_solution = _random_single_start_solution(singles, all_tasks, deadline)
            if random_solution:
                solutions.append(random_solution)

    if not abundant or low_willingness:
        modes = ("gain", "cover") if low_willingness else ("ratio", "gain", "cover")
        for mode in modes:
            if time.monotonic() < deadline - 0.35:
                solutions.append(_solve_disjoint_then_multidispatch(candidates, all_tasks, mode=mode, deadline=deadline))
        if time.monotonic() < deadline - 0.55:
            pair_solution = _solve_pair_potential_matching(
                candidates,
                all_tasks,
                deadline,
                lookahead=5 if low_willingness else 4,
                flexible_initial=low_willingness,
            )
            if pair_solution:
                solutions.append(pair_solution)
        if time.monotonic() < deadline - 0.25:
            solutions.append(_solve_sparse_cover(candidates, all_tasks, deadline))
    solutions.append(_fallback_official_greedy(candidates))

    best = min((s for s in solutions if s), key=lambda s: _solution_expected_cost(s, candidates, all_tasks))
    return best


def _singles_cover_all_tasks(singles, all_tasks):
    covered = {c[1][0] for c in singles}
    return all(task in covered for task in all_tasks)


def _solve_single_task_multidispatch(singles, all_tasks):
    selected = {task_id: [] for task_id in all_tasks}
    current_cost = {task_id: 100.0 for task_id in all_tasks}
    used_couriers = set()

    while True:
        best = None
        best_delta = 0.0
        best_new_cost = 0.0

        for cand in singles:
            task_key, task_ids, courier_id, score, willingness, row_index = cand
            if courier_id in used_couriers:
                continue
            task_id = task_ids[0]
            old_cost = current_cost.get(task_id, 100.0)
            new_cost = _group_expected_cost(selected.get(task_id, []), 1, extra=cand)
            delta = new_cost - old_cost
            if delta < best_delta - 1e-12:
                best_delta = delta
                best_new_cost = new_cost
                best = cand

        if best is None:
            break

        task_id = best[1][0]
        selected[task_id].append(best)
        current_cost[task_id] = best_new_cost
        used_couriers.add(best[2])

    # If a task received nothing, patch it with the best remaining single row.
    for task_id in sorted(all_tasks):
        if selected.get(task_id):
            continue
        options = [c for c in singles if c[1][0] == task_id and c[2] not in used_couriers]
        if not options:
            continue
        best = min(options, key=lambda c: _single_expected_cost(c))
        selected[task_id].append(best)
        used_couriers.add(best[2])

    result = []
    for task_id in sorted(selected):
        rows = selected[task_id]
        if not rows:
            continue
        rows = sorted(rows, key=lambda c: (c[3], -c[4], c[5]))
        result.append((task_id, [c[2] for c in rows]))
    return result


def _single_expected_cost(cand):
    return cand[4] * cand[3] + (1.0 - cand[4]) * 100.0


def _group_expected_cost(rows, task_count, extra=None):
    if extra is not None:
        rows = list(rows) + [extra]
    if not rows:
        return 100.0 * task_count

    # The judge behaves much closer to "among the riders who accept, the winner
    # is not guaranteed to be the lowest-score one" than to strict list order.
    # Enumerating accepted subsets gives a robust estimate for multi-dispatch.
    rows = list(rows)
    n = len(rows)
    if n > 12:
        return _group_expected_cost_dp(rows, task_count)
    expected = 0.0
    for mask in range(1 << n):
        probability = 1.0
        score_sum = 0.0
        accepted = 0
        for index, cand in enumerate(rows):
            if mask >> index & 1:
                probability *= cand[4]
                score_sum += cand[3]
                accepted += 1
            else:
                probability *= 1.0 - cand[4]
        if accepted:
            expected += probability * (score_sum / accepted)
        else:
            expected += probability * (100.0 * task_count)
    return expected


def _group_expected_cost_dp(rows, task_count):
    reject_probability = 1.0
    for cand in rows:
        reject_probability *= 1.0 - cand[4]
    expected = reject_probability * (100.0 * task_count)

    for index, cand in enumerate(rows):
        probability = cand[4]
        if probability <= 0.0:
            continue
        dist = [1.0]
        for other_index, other in enumerate(rows):
            if other_index == index:
                continue
            p = other[4]
            next_dist = [0.0] * (len(dist) + 1)
            for count, value in enumerate(dist):
                next_dist[count] += value * (1.0 - p)
                next_dist[count + 1] += value * p
            dist = next_dist
        share = 0.0
        for accepted_others, value in enumerate(dist):
            share += value / (accepted_others + 1)
        expected += cand[3] * probability * share
    return expected


def _solve_disjoint_then_multidispatch(candidates, all_tasks, mode, deadline=None):
    selected = {}
    used_tasks = set()
    used_couriers = set()

    while True:
        if deadline is not None and time.monotonic() > deadline - 0.25:
            break
        best = None
        best_key = None
        for cand in candidates:
            task_key, task_ids, courier_id, score, willingness, row_index = cand
            if courier_id in used_couriers:
                continue
            if any(task_id in used_tasks for task_id in task_ids):
                continue
            old_cost = 100.0 * len(task_ids)
            new_cost = _group_expected_cost([cand], len(task_ids))
            gain = old_cost - new_cost
            if gain <= 1e-12:
                continue
            if mode == "gain":
                key = (gain, len(task_ids), gain / max(score, 1e-9), willingness, -score)
            elif mode == "cover":
                key = (len(task_ids), gain / max(score, 1e-9), gain, willingness, -score)
            else:
                key = (gain / max(score, 1e-9), len(task_ids), gain, willingness, -score)
            if best_key is None or key > best_key:
                best_key = key
                best = cand
        if best is None:
            break
        selected[best[0]] = [best]
        used_couriers.add(best[2])
        for task_id in best[1]:
            used_tasks.add(task_id)

    # Patch uncovered tasks with best non-conflicting rows.
    for task_id in sorted(all_tasks):
        if task_id in used_tasks:
            continue
        options = [
            cand for cand in candidates
            if task_id in cand[1]
            and cand[2] not in used_couriers
            and not any(t in used_tasks for t in cand[1])
        ]
        if not options:
            continue
        best = min(options, key=lambda c: _group_expected_cost([c], len(c[1])))
        selected[best[0]] = [best]
        used_couriers.add(best[2])
        for task in best[1]:
            used_tasks.add(task)

    _add_extra_dispatches(selected, candidates, used_couriers, deadline)
    return _format_selected(selected)


def _add_extra_dispatches(selected, candidates, used_couriers, deadline=None):
    by_key = {}
    for cand in candidates:
        by_key.setdefault(cand[0], []).append(cand)

    improved = True
    while improved:
        if deadline is not None and time.monotonic() > deadline - 0.2:
            break
        improved = False
        best = None
        best_delta = 0.0
        best_new_cost = 0.0
        for task_key, rows in selected.items():
            task_count = len(rows[0][1])
            old_cost = _group_expected_cost(rows, task_count)
            for cand in by_key.get(task_key, []):
                if cand[2] in used_couriers:
                    continue
                new_cost = _group_expected_cost(rows, task_count, extra=cand)
                delta = new_cost - old_cost
                if delta < best_delta - 1e-12:
                    best_delta = delta
                    best_new_cost = new_cost
                    best = (task_key, cand)
        if best is not None:
            task_key, cand = best
            selected[task_key].append(cand)
            used_couriers.add(cand[2])
            improved = True


def _solve_pair_potential_matching(candidates, all_tasks, deadline, lookahead=4, flexible_initial=False):
    by_key = {}
    singles = []
    for cand in candidates:
        by_key.setdefault(cand[0], []).append(cand)
        if len(cand[1]) == 1:
            singles.append(cand)

    edges = []
    for task_key, rows in by_key.items():
        if time.monotonic() > deadline - 0.45:
            break
        task_ids = rows[0][1]
        if len(task_ids) != 2:
            continue
        top_rows, cost = _best_group_rows(rows, len(task_ids), lookahead)
        if not top_rows:
            continue
        potential = 100.0 * len(task_ids) - cost
        if potential <= 1e-12:
            continue
        edges.append((potential, -cost, task_key, task_ids, top_rows))

    if not edges:
        return []

    edges.sort(reverse=True)
    selected = {}
    used_tasks = set()
    used_couriers = set()

    for _, _, task_key, task_ids, top_rows in edges:
        if any(task_id in used_tasks for task_id in task_ids):
            continue
        if flexible_initial:
            first_row = None
            for row in top_rows:
                if row[2] not in used_couriers:
                    first_row = row
                    break
            if first_row is None:
                continue
        else:
            first_row = top_rows[0]
            if first_row[2] in used_couriers:
                continue
        selected[task_key] = [first_row]
        used_couriers.add(first_row[2])
        for task_id in task_ids:
            used_tasks.add(task_id)
        if len(used_tasks) >= len(all_tasks):
            break

    for task_id in sorted(all_tasks):
        if task_id in used_tasks:
            continue
        options = [cand for cand in singles if cand[1][0] == task_id and cand[2] not in used_couriers]
        if not options:
            continue
        best = min(options, key=lambda c: _group_expected_cost([c], 1))
        selected[task_id] = [best]
        used_couriers.add(best[2])
        used_tasks.add(task_id)

    _add_extra_dispatches(selected, candidates, used_couriers, deadline)
    return _format_selected(selected)


def _best_group_rows(rows, task_count, limit):
    selected = []
    used_couriers = set()
    current_cost = 100.0 * task_count
    while len(selected) < limit:
        best = None
        best_delta = 0.0
        best_cost = 0.0
        for cand in rows:
            if cand[2] in used_couriers:
                continue
            new_cost = _group_expected_cost(selected, task_count, extra=cand)
            delta = new_cost - current_cost
            if delta < best_delta - 1e-12:
                best = cand
                best_delta = delta
                best_cost = new_cost
        if best is None:
            break
        selected.append(best)
        used_couriers.add(best[2])
        current_cost = best_cost
    return selected, current_cost


def _format_selected(selected):
    result = []
    for task_key in sorted(selected, key=lambda k: selected[k][0][1]):
        rows = sorted(selected[task_key], key=lambda c: (c[3], -c[4], c[5]))
        result.append((task_key, [c[2] for c in rows]))
    return result


def _result_to_selected(result, row_map):
    selected = {}
    for task_key, courier_ids in result:
        rows = []
        for courier_id in courier_ids:
            cand = row_map.get((task_key, courier_id))
            if cand is not None:
                rows.append(cand)
        if rows:
            selected[task_key] = rows
    return selected


def _destroy_repair_single_solution(result, singles, all_tasks, deadline):
    row_map = {(c[0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result

    best = selected
    rng = random.Random(123)
    iteration = 0
    max_iterations = 900 if len(all_tasks) >= 35 else 350

    while iteration < max_iterations and time.monotonic() < deadline - 0.05:
        iteration += 1
        losses = []
        for task_key, rows in best.items():
            old_cost = _group_expected_cost(rows, 1)
            for cand in rows:
                new_rows = [r for r in rows if r != cand]
                new_cost = _group_expected_cost(new_rows, 1) if new_rows else 100.0
                losses.append((new_cost - old_cost, cand[5], cand))
        if not losses:
            break
        losses.sort(key=lambda x: (x[0], x[1]))
        pool = [cand for _, _, cand in losses[: min(40, len(losses))]]
        remove_count = rng.choice([2, 3, 4, 5, 6, 8])
        removed = set(rng.sample(pool, min(remove_count, len(pool))))

        partial = {}
        for task_key, rows in best.items():
            kept = [cand for cand in rows if cand not in removed]
            if kept:
                partial[task_key] = kept

        noise = rng.choice([0.0, 0.10, 0.20, 0.35])
        candidate = _greedy_repair_single(partial, singles, all_tasks, random.Random(iteration), noise)
        if _selected_cost(candidate, all_tasks) < _selected_cost(best, all_tasks) - 1e-9:
            best = candidate

    return _format_selected(best)


def _greedy_repair_single(selected, singles, all_tasks, rng, noise):
    selected = {k: list(v) for k, v in selected.items()}
    used_couriers = {cand[2] for rows in selected.values() for cand in rows}
    current_cost = {k: _group_expected_cost(v, 1) for k, v in selected.items()}

    for task_id in all_tasks:
        if task_id not in selected:
            selected[task_id] = []
            current_cost[task_id] = 100.0

    while True:
        scored = []
        for cand in singles:
            task_key, task_ids, courier_id, score, willingness, row_index = cand
            if courier_id in used_couriers:
                continue
            old_cost = current_cost.get(task_key, 100.0)
            new_cost = _group_expected_cost(selected.get(task_key, []), 1, extra=cand)
            gain = old_cost - new_cost
            if gain <= 1e-12:
                continue
            value = gain
            if noise:
                value *= rng.uniform(1.0 - noise, 1.0 + noise)
            scored.append((value, gain, willingness, -score, -row_index, cand, new_cost))
        if not scored:
            break
        scored.sort(reverse=True)
        pick = scored[rng.randrange(min(3, len(scored)))]
        cand = pick[5]
        new_cost = pick[6]
        selected.setdefault(cand[0], []).append(cand)
        current_cost[cand[0]] = new_cost
        used_couriers.add(cand[2])

    return {k: v for k, v in selected.items() if v}


def _random_single_start_solution(singles, all_tasks, deadline):
    if time.monotonic() > deadline - 1.8:
        return []
    local_deadline = min(deadline, time.monotonic() + 1.8)
    selected = _greedy_repair_single({}, singles, all_tasks, random.Random(18), 0.5)
    result = _format_selected(selected)
    result = _reassign_single_solution(result, singles, all_tasks, local_deadline)
    result = _rebalance_single_solution(result, singles, all_tasks, local_deadline)
    result = _reassign_single_solution(result, singles, all_tasks, local_deadline)
    return result


def _selected_cost(selected, all_tasks):
    covered = 0
    total = 0.0
    for rows in selected.values():
        if not rows:
            continue
        task_count = len(rows[0][1])
        covered += task_count
        total += _group_expected_cost(rows, task_count)
    total += 100.0 * (len(all_tasks) - covered)
    return total


class _MinCostFlow:
    def __init__(self, n):
        self.graph = [[] for _ in range(n)]

    def add_edge(self, start, end, capacity, cost):
        forward = [end, capacity, cost, len(self.graph[end])]
        backward = [start, 0, -cost, len(self.graph[start])]
        self.graph[start].append(forward)
        self.graph[end].append(backward)

    def min_cost_flow(self, source, sink, amount):
        sent = 0
        n = len(self.graph)
        while sent < amount:
            dist = [float("inf")] * n
            in_queue = [False] * n
            prev_node = [-1] * n
            prev_edge = [-1] * n
            dist[source] = 0.0
            queue = [source]
            in_queue[source] = True
            head = 0
            while head < len(queue):
                node = queue[head]
                head += 1
                in_queue[node] = False
                for edge_index, edge in enumerate(self.graph[node]):
                    to_node, capacity, cost, _ = edge
                    if capacity <= 0:
                        continue
                    new_dist = dist[node] + cost
                    if new_dist + 1e-12 < dist[to_node]:
                        dist[to_node] = new_dist
                        prev_node[to_node] = node
                        prev_edge[to_node] = edge_index
                        if not in_queue[to_node]:
                            queue.append(to_node)
                            in_queue[to_node] = True
            if prev_node[sink] == -1:
                break
            node = sink
            while node != source:
                edge = self.graph[prev_node[node]][prev_edge[node]]
                reverse = self.graph[node][edge[3]]
                edge[1] -= 1
                reverse[1] += 1
                node = prev_node[node]
            sent += 1
        return sent


def _reassign_single_solution(result, singles, all_tasks, deadline):
    row_map = {(c[0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    best_cost = _selected_cost(selected, all_tasks)
    for _ in range(3):
        if time.monotonic() > deadline - 0.15:
            break
        candidate = _reassign_selected_once(selected, row_map)
        candidate_cost = _selected_cost(candidate, all_tasks)
        if candidate_cost < best_cost - 1e-9:
            selected = candidate
            best_cost = candidate_cost
        else:
            break
    return _format_selected(selected)


def _rebalance_single_solution(result, singles, all_tasks, deadline):
    row_map = {(c[0], c[2]): c for c in singles}
    single_by_task_courier = {(c[1][0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result

    for task_id in all_tasks:
        selected.setdefault(task_id, [])

    move_count = 0
    max_moves = min(12, len(all_tasks))
    while move_count < max_moves and time.monotonic() < deadline - 0.2:
        best = None
        best_delta = 0.0
        for from_task, from_rows in selected.items():
            if len(from_rows) <= 1:
                continue
            old_from_cost = _group_expected_cost(from_rows, 1)
            for old_cand in from_rows:
                courier_id = old_cand[2]
                from_after = [cand for cand in from_rows if cand != old_cand]
                from_delta = _group_expected_cost(from_after, 1) - old_from_cost
                for to_task, to_rows in selected.items():
                    if to_task == from_task:
                        continue
                    new_cand = single_by_task_courier.get((to_task, courier_id))
                    if new_cand is None:
                        continue
                    old_to_cost = _group_expected_cost(to_rows, 1) if to_rows else 100.0
                    new_to_cost = _group_expected_cost(to_rows, 1, extra=new_cand)
                    delta = from_delta + new_to_cost - old_to_cost
                    if delta < best_delta - 1e-12:
                        best_delta = delta
                        best = (from_task, to_task, old_cand, new_cand)

        if best is None:
            break

        from_task, to_task, old_cand, new_cand = best
        selected[from_task] = [cand for cand in selected[from_task] if cand != old_cand]
        selected[to_task].append(new_cand)
        move_count += 1

    return _format_selected({task_key: rows for task_key, rows in selected.items() if rows})


def _reassign_selected_once(selected, row_map):
    couriers = sorted({cand[2] for rows in selected.values() for cand in rows})
    slots = []
    for task_key in sorted(selected):
        rows = selected[task_key]
        for index, old in enumerate(rows):
            others = [cand for i, cand in enumerate(rows) if i != index]
            slots.append((task_key, others))

    if not couriers or not slots:
        return selected

    source = 0
    courier_offset = 1
    slot_offset = courier_offset + len(couriers)
    sink = slot_offset + len(slots)
    flow = _MinCostFlow(sink + 1)
    edge_map = {}

    for i, courier_id in enumerate(couriers):
        flow.add_edge(source, courier_offset + i, 1, 0.0)
    for j in range(len(slots)):
        flow.add_edge(slot_offset + j, sink, 1, 0.0)

    for i, courier_id in enumerate(couriers):
        courier_node = courier_offset + i
        for j, (task_key, others) in enumerate(slots):
            if any(cand[2] == courier_id for cand in others):
                continue
            cand = row_map.get((task_key, courier_id))
            if cand is None:
                continue
            cost = _group_expected_cost(others + [cand], 1)
            edge_index = len(flow.graph[courier_node])
            flow.add_edge(courier_node, slot_offset + j, 1, cost)
            edge_map[(courier_node, edge_index)] = (j, cand)

    if flow.min_cost_flow(source, sink, len(slots)) < len(slots):
        return selected

    new_selected = {task_key: [] for task_key in selected}
    for (node, edge_index), (slot_index, cand) in edge_map.items():
        if flow.graph[node][edge_index][1] == 0:
            task_key = slots[slot_index][0]
            new_selected[task_key].append(cand)

    if any(len(new_selected.get(k, [])) != len(v) for k, v in selected.items()):
        return selected
    return new_selected


def _solve_sparse_cover(candidates, all_tasks, deadline):
    best = []
    for mode in ("cover", "gain", "ratio"):
        if time.monotonic() > deadline - 0.25:
            break
        solution = _sparse_greedy(candidates, mode)
        if not best or _simple_result_score(solution, candidates, all_tasks) < _simple_result_score(best, candidates, all_tasks):
            best = solution
    should_beam = (
        len(all_tasks) <= 60
        and len(candidates) <= 60000
        and len({c[2] for c in candidates}) <= 80
        and time.monotonic() < deadline - 1.0
    )
    if should_beam:
        beam = _sparse_beam_search(candidates, all_tasks, deadline)
        if beam and _simple_result_score(beam, candidates, all_tasks) < _simple_result_score(best, candidates, all_tasks):
            best = beam
    return best


def _sparse_beam_search(candidates, all_tasks, deadline):
    task_list = sorted(all_tasks)
    task_index = {task: idx for idx, task in enumerate(task_list)}
    by_courier = {}
    for cand in candidates:
        mask = 0
        ok = True
        for task in cand[1]:
            if task not in task_index:
                ok = False
                break
            mask |= 1 << task_index[task]
        if not ok:
            continue
        cost = _group_expected_cost([cand], len(cand[1]))
        benefit = 100.0 * len(cand[1]) - cost
        if benefit <= 1e-12:
            continue
        row = (mask, benefit, cost, cand)
        by_courier.setdefault(cand[2], []).append(row)

    if not by_courier:
        return []

    small_sparse = len(candidates) <= 10000 and len(by_courier) <= 25
    per_courier_limit = 45 if small_sparse else 28
    courier_items = []
    for courier, rows in by_courier.items():
        best_by_mask = {}
        for mask, benefit, cost, cand in rows:
            old = best_by_mask.get(mask)
            if old is None or cost < old[2] - 1e-12:
                best_by_mask[mask] = (mask, benefit, cost, cand)
        pruned = sorted(best_by_mask.values(), key=lambda r: (_popcount(r[0]), r[1], -r[2]), reverse=True)[:per_courier_limit]
        courier_items.append((courier, pruned))

    # Process high-impact couriers first to keep the beam compact.
    courier_items.sort(key=lambda item: max((r[1] for r in item[1]), default=0.0), reverse=True)
    beam = {0: (0.0, ())}
    beam_width = 12000 if small_sparse else (900 if len(courier_items) <= 30 else 520)
    for _, rows in courier_items:
        if time.monotonic() > deadline - 0.25:
            break
        next_beam = dict(beam)
        for mask, (benefit, path) in beam.items():
            for cand_mask, cand_benefit, _, cand in rows:
                if mask & cand_mask:
                    continue
                new_mask = mask | cand_mask
                new_benefit = benefit + cand_benefit
                old = next_beam.get(new_mask)
                if old is None or new_benefit > old[0] + 1e-12:
                    next_beam[new_mask] = (new_benefit, path + (cand,))
        if len(next_beam) > beam_width:
            ranked = sorted(
                next_beam.items(),
                key=lambda item: (item[1][0], _popcount(item[0])),
                reverse=True,
            )[:beam_width]
            beam = dict(ranked)
        else:
            beam = next_beam

    best_mask, (best_benefit, best_path) = max(
        beam.items(),
        key=lambda item: (item[1][0], _popcount(item[0])),
    )
    return [(cand[0], [cand[2]]) for cand in best_path]


def _popcount(value):
    return bin(value).count("1")


def _sparse_greedy(candidates, mode):
    used_tasks = set()
    used_couriers = set()
    result = []
    while True:
        best = None
        best_key = None
        for cand in candidates:
            task_key, task_ids, courier_id, score, willingness, row_index = cand
            if courier_id in used_couriers:
                continue
            new_tasks = [task for task in task_ids if task not in used_tasks]
            if len(new_tasks) != len(task_ids):
                continue
            task_count = len(task_ids)
            gain = 100.0 * task_count - _group_expected_cost([cand], task_count)
            if gain <= 1e-12:
                continue
            if mode == "cover":
                key = (task_count, gain / max(score, 1e-9), gain, willingness, -score)
            elif mode == "gain":
                key = (gain, task_count, gain / max(score, 1e-9), willingness, -score)
            else:
                key = (gain / max(score, 1e-9), task_count, gain, willingness, -score)
            if best_key is None or key > best_key:
                best_key = key
                best = cand
        if best is None:
            break
        result.append((best[0], [best[2]]))
        used_couriers.add(best[2])
        for task in best[1]:
            used_tasks.add(task)
    return result


def _simple_result_score(result, candidates, all_tasks):
    return _solution_expected_cost(result, candidates, all_tasks)


def _solution_expected_cost(result, candidates, all_tasks):
    row_map = {(c[0], c[2]): c for c in candidates}
    used_tasks = set()
    used_couriers = set()
    total = 0.0
    for task_key, courier_ids in result:
        rows = []
        for courier_id in courier_ids:
            cand = row_map.get((task_key, courier_id))
            if cand is None or courier_id in used_couriers:
                return float("inf")
            used_couriers.add(courier_id)
            rows.append(cand)
        if not rows:
            return float("inf")
        for task_id in rows[0][1]:
            if task_id in used_tasks:
                return float("inf")
            used_tasks.add(task_id)
        total += _group_expected_cost(rows, len(rows[0][1]))
    total += 100.0 * (len(all_tasks) - len(used_tasks))
    return total


def _fallback_official_greedy(candidates):
    ordered = sorted(candidates, key=lambda c: c[3])
    assigned_couriers = set()
    assigned_tasks = set()
    result = []
    for task_key, task_ids, courier_id, score, willingness, row_index in ordered:
        if courier_id in assigned_couriers:
            continue
        if any(task_id in assigned_tasks for task_id in task_ids):
            continue
        assigned_couriers.add(courier_id)
        for task_id in task_ids:
            assigned_tasks.add(task_id)
        result.append((task_key, [courier_id]))
    return result
