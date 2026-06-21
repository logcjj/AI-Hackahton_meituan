from __future__ import annotations

import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable


EPS = 1e-9
WILLINGNESS_TIE_BREAK = 1e-6
DEFAULT_TIME_BUDGET = 9.0
TARGET_SCORE_PER_TASK = 16.0
SEARCH_POOL_PER_COURIER = 120
LOCAL_SEARCH_MAX_ITERATIONS = 24
EARLY_STOP_EXPECTED_RATIO = 0.895
EARLY_STOP_BUDGET_FILL_RATIO = 0.98


@dataclass(frozen=True)
class CompetitionCandidate:
    task_ids: tuple[str, ...]
    task_key: str
    courier_id: str
    total_score: float
    willingness: float
    row_index: int

    @property
    def size(self) -> int:
        return len(self.task_ids)


def parse_candidates(input_text: str) -> list[CompetitionCandidate]:
    lines = input_text.strip().splitlines()
    if not lines:
        return []

    start = 1 if lines[0].strip().startswith("task_id_list") else 0
    candidates: list[CompetitionCandidate] = []
    for row_index, line in enumerate(lines[start:]):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, willingness_text = parts[:4]
        task_ids = tuple(task.strip() for task in task_key.split(",") if task.strip())
        if not task_ids or not courier_id.strip():
            continue
        try:
            total_score = float(score_text)
            willingness = float(willingness_text)
        except ValueError:
            continue
        candidates.append(
            CompetitionCandidate(
                task_ids=task_ids,
                task_key=",".join(task_ids),
                courier_id=courier_id.strip(),
                total_score=total_score,
                willingness=willingness,
                row_index=row_index,
            )
        )
    return candidates


def solve(input_text: str, time_budget: float = DEFAULT_TIME_BUDGET) -> list[tuple[str, list[str]]]:
    candidates = parse_candidates(input_text)
    solution = solve_candidates(candidates, time_budget=time_budget)
    return format_competition_solution(solution)


def solve_candidates(
    candidates: Iterable[CompetitionCandidate],
    time_budget: float = DEFAULT_TIME_BUDGET,
    score_budget: float | None = None,
) -> list[CompetitionCandidate]:
    pool = list(candidates)
    if not pool:
        return []

    tasks = sorted({task_id for candidate in pool for task_id in candidate.task_ids})
    budget = _default_score_budget(tasks, pool) if score_budget is None else float(score_budget)
    deadline = time.monotonic() + max(0.1, time_budget)
    search_pool = _build_search_pool(pool, budget)

    best: list[CompetitionCandidate] = []
    starts = [
        (1.1, 0.95, 0.20, 2),
        (1.1, 0.95, 0.20, 5),
        (1.2, 1.0, 0.15, 43),
        (1.0, 0.9, 0.18, 29),
        (0.8, 0.8, 0.0, 0),
        (0.8, 1.0, 0.0, 0),
        (1.0, 1.0, 0.0, 0),
        (1.2, 1.0, 0.0, 0),
        (1.0, 1.0, 0.20, 17),
    ]

    for alpha, beta, noise, seed in starts:
        if time.monotonic() > deadline - 0.05:
            break
        solution = _budgeted_greedy(search_pool, tasks, budget, alpha=alpha, beta=beta, noise=noise, seed=seed)
        solution = _local_improve_budget(solution, search_pool, tasks, budget, deadline)
        if _budgeted_solution_better(solution, best, tasks):
            best = solution
            if _good_enough_for_budget(best, tasks, budget):
                break

    if not best:
        best = _budgeted_greedy(search_pool, tasks, budget, alpha=1.0, beta=1.0)
    return _sorted_solution(best)


def format_competition_solution(solution: Iterable[CompetitionCandidate]) -> list[tuple[str, list[str]]]:
    return [(candidate.task_key, [candidate.courier_id]) for candidate in _sorted_solution(solution)]


def validate_competition_solution(solution: Iterable[CompetitionCandidate]) -> list[str]:
    violations: list[str] = []
    used_couriers: set[str] = set()
    for candidate in solution:
        if candidate.courier_id in used_couriers:
            violations.append(f"duplicate courier {candidate.courier_id}")
        used_couriers.add(candidate.courier_id)
    return violations


def solution_metrics(solution: Iterable[CompetitionCandidate]) -> dict[str, float]:
    items = list(solution)
    per_task_acceptance = _per_task_acceptance(items)
    return {
        "assignments": float(len(items)),
        "covered_tasks": float(len(_covered_tasks(items))),
        "expected_accepts": sum(per_task_acceptance.values()),
        "min_task_acceptance": min(per_task_acceptance.values()) if per_task_acceptance else 0.0,
        "total_score": sum(candidate.total_score for candidate in items),
        "willingness": sum(candidate.willingness for candidate in items),
    }


def _candidate_cost(candidate: CompetitionCandidate) -> float:
    return candidate.total_score - candidate.willingness * WILLINGNESS_TIE_BREAK


def _better_candidate(a: CompetitionCandidate, b: CompetitionCandidate | None) -> bool:
    if b is None:
        return True
    if a.total_score < b.total_score - EPS:
        return True
    if abs(a.total_score - b.total_score) <= EPS and a.willingness > b.willingness + EPS:
        return True
    if abs(a.total_score - b.total_score) <= EPS and abs(a.willingness - b.willingness) <= EPS:
        return a.row_index < b.row_index
    return False


def _covered_tasks(solution: Iterable[CompetitionCandidate]) -> set[str]:
    return {task_id for candidate in solution for task_id in candidate.task_ids}


def _sorted_solution(solution: Iterable[CompetitionCandidate]) -> list[CompetitionCandidate]:
    return sorted(solution, key=lambda candidate: (candidate.task_ids[0], len(candidate.task_ids), candidate.courier_id))


def _probability(candidate: CompetitionCandidate) -> float:
    return min(1.0 - EPS, max(0.0, candidate.willingness))


def _default_score_budget(tasks: list[str], candidates: list[CompetitionCandidate]) -> float:
    if not tasks:
        return 0.0
    singles = [candidate for candidate in candidates if candidate.size == 1]
    min_cover = _min_cost_single_cover(tasks, singles)
    min_cover_score = sum(candidate.total_score for candidate in min_cover) if min_cover else 0.0
    target = TARGET_SCORE_PER_TASK * len(tasks)
    if min_cover_score and min_cover_score < target:
        return target
    return target if not min_cover_score else min_cover_score * 1.05


def _build_search_pool(candidates: list[CompetitionCandidate], budget: float) -> list[CompetitionCandidate]:
    by_courier: dict[str, list[CompetitionCandidate]] = defaultdict(list)
    for candidate in candidates:
        if candidate.total_score <= budget + EPS:
            by_courier[candidate.courier_id].append(candidate)

    search: set[CompetitionCandidate] = set()
    for courier_candidates in by_courier.values():
        ranked_lists = [
            sorted(courier_candidates, key=lambda item: (item.total_score, -item.willingness))[:SEARCH_POOL_PER_COURIER],
            sorted(courier_candidates, key=lambda item: -(_probability(item) * item.size / max(item.total_score, EPS)))[:SEARCH_POOL_PER_COURIER],
            sorted(courier_candidates, key=lambda item: -(_probability(item) * item.size))[:SEARCH_POOL_PER_COURIER // 2],
            sorted(courier_candidates, key=lambda item: -(_probability(item) / max(item.total_score, EPS)))[:SEARCH_POOL_PER_COURIER // 2],
        ]
        for ranked in ranked_lists:
            search.update(ranked)
    return sorted(search, key=lambda candidate: candidate.row_index)


def _reject_probabilities(solution: Iterable[CompetitionCandidate], tasks: list[str]) -> dict[str, float]:
    reject = {task_id: 1.0 for task_id in tasks}
    for candidate in solution:
        keep_rejecting = 1.0 - _probability(candidate)
        for task_id in candidate.task_ids:
            reject[task_id] *= keep_rejecting
    return reject


def _per_task_acceptance(solution: Iterable[CompetitionCandidate]) -> dict[str, float]:
    tasks = sorted({task_id for candidate in solution for task_id in candidate.task_ids})
    reject = _reject_probabilities(solution, tasks)
    return {task_id: 1.0 - reject_probability for task_id, reject_probability in reject.items()}


def _expected_accepts(solution: Iterable[CompetitionCandidate], tasks: list[str]) -> float:
    reject = _reject_probabilities(solution, tasks)
    return _expected_from_reject(reject)


def _expected_from_reject(reject: dict[str, float]) -> float:
    return sum(1.0 - reject_probability for reject_probability in reject.values())


def _total_score(solution: Iterable[CompetitionCandidate]) -> float:
    return sum(candidate.total_score for candidate in solution)


def _add_delta(reject: dict[str, float], candidate: CompetitionCandidate) -> float:
    probability = _probability(candidate)
    return sum(reject[task_id] * probability for task_id in candidate.task_ids)


def _replacement_delta(
    reject: dict[str, float],
    removed: CompetitionCandidate,
    added: CompetitionCandidate,
) -> float:
    affected_tasks = set(removed.task_ids) | set(added.task_ids)
    removed_keep_rejecting = max(EPS, 1.0 - _probability(removed))
    added_keep_rejecting = 1.0 - _probability(added)
    delta = 0.0
    for task_id in affected_tasks:
        old_reject = reject[task_id]
        new_reject = old_reject
        if task_id in removed.task_ids:
            new_reject /= removed_keep_rejecting
        if task_id in added.task_ids:
            new_reject *= added_keep_rejecting
        delta += old_reject - new_reject
    return delta


def _budgeted_greedy(
    candidates: list[CompetitionCandidate],
    tasks: list[str],
    budget: float,
    alpha: float = 1.0,
    beta: float = 1.0,
    noise: float = 0.0,
    seed: int = 0,
) -> list[CompetitionCandidate]:
    rng = random.Random(seed)
    reject = {task_id: 1.0 for task_id in tasks}
    used_couriers: set[str] = set()
    solution: list[CompetitionCandidate] = []
    total_score = 0.0

    while True:
        best_candidate = None
        best_key = None
        for candidate in candidates:
            if candidate.courier_id in used_couriers:
                continue
            if total_score + candidate.total_score > budget + EPS:
                continue
            gain = _add_delta(reject, candidate)
            if gain <= EPS:
                continue
            score = (gain ** alpha) / (max(candidate.total_score, EPS) ** beta)
            if noise:
                score *= rng.uniform(1.0 - noise, 1.0 + noise)
            key = (score, gain, _probability(candidate), -candidate.total_score, -candidate.row_index)
            if best_key is None or key > best_key:
                best_key = key
                best_candidate = candidate

        if best_candidate is None:
            break

        solution.append(best_candidate)
        used_couriers.add(best_candidate.courier_id)
        total_score += best_candidate.total_score
        keep_rejecting = 1.0 - _probability(best_candidate)
        for task_id in best_candidate.task_ids:
            reject[task_id] *= keep_rejecting

    return solution


def _local_improve_budget(
    solution: list[CompetitionCandidate],
    candidates: list[CompetitionCandidate],
    tasks: list[str],
    budget: float,
    deadline: float,
) -> list[CompetitionCandidate]:
    current = list(solution)
    for _ in range(LOCAL_SEARCH_MAX_ITERATIONS):
        if time.monotonic() >= deadline - 0.02:
            break
        reject = _reject_probabilities(current, tasks)
        current_score = _total_score(current)
        selected_by_courier = {candidate.courier_id: candidate for candidate in current}

        best_added = None
        best_removed = None
        best_delta = EPS
        best_new_score = float("inf")
        best_assignment_delta = -1

        for candidate in candidates:
            owner = selected_by_courier.get(candidate.courier_id)
            if owner is not None:
                if owner == candidate:
                    continue
                new_score = current_score - owner.total_score + candidate.total_score
                if new_score > budget + EPS:
                    continue
                delta = _replacement_delta(reject, owner, candidate)
                assignment_delta = 0
                if _move_better(delta, new_score, assignment_delta, best_delta, best_new_score, best_assignment_delta):
                    best_delta = delta
                    best_new_score = new_score
                    best_assignment_delta = assignment_delta
                    best_removed = owner
                    best_added = candidate
                continue

            new_score = current_score + candidate.total_score
            if new_score <= budget + EPS:
                delta = _add_delta(reject, candidate)
                assignment_delta = 1
                if _move_better(delta, new_score, assignment_delta, best_delta, best_new_score, best_assignment_delta):
                    best_delta = delta
                    best_new_score = new_score
                    best_assignment_delta = assignment_delta
                    best_removed = None
                    best_added = candidate

            for removed in current:
                new_score = current_score - removed.total_score + candidate.total_score
                if new_score > budget + EPS:
                    continue
                delta = _replacement_delta(reject, removed, candidate)
                assignment_delta = 0
                if _move_better(delta, new_score, assignment_delta, best_delta, best_new_score, best_assignment_delta):
                    best_delta = delta
                    best_new_score = new_score
                    best_assignment_delta = assignment_delta
                    best_removed = removed
                    best_added = candidate

        if best_added is None:
            break
        if best_removed is None:
            current.append(best_added)
        else:
            current = [candidate for candidate in current if candidate != best_removed]
            current.append(best_added)

    return current


def _move_better(
    delta: float,
    new_score: float,
    assignment_delta: int,
    best_delta: float,
    best_new_score: float,
    best_assignment_delta: int,
) -> bool:
    if delta > best_delta + EPS:
        return True
    if abs(delta - best_delta) <= EPS:
        if assignment_delta > best_assignment_delta:
            return True
        if assignment_delta == best_assignment_delta and new_score < best_new_score - EPS:
            return True
    return False


def _budgeted_solution_better(
    candidate_solution: list[CompetitionCandidate],
    incumbent: list[CompetitionCandidate],
    tasks: list[str],
) -> bool:
    candidate_expected = _expected_accepts(candidate_solution, tasks)
    incumbent_expected = _expected_accepts(incumbent, tasks) if incumbent else -1.0
    if candidate_expected > incumbent_expected + EPS:
        return True
    if abs(candidate_expected - incumbent_expected) <= EPS:
        candidate_score = _total_score(candidate_solution)
        incumbent_score = _total_score(incumbent)
        if candidate_score < incumbent_score - EPS:
            return True
        if abs(candidate_score - incumbent_score) <= EPS and len(candidate_solution) > len(incumbent):
            return True
    return False


def _good_enough_for_budget(solution: list[CompetitionCandidate], tasks: list[str], budget: float) -> bool:
    if not tasks:
        return True
    expected_ratio = _expected_accepts(solution, tasks) / len(tasks)
    budget_fill_ratio = _total_score(solution) / max(budget, EPS)
    return expected_ratio >= EARLY_STOP_EXPECTED_RATIO and budget_fill_ratio >= EARLY_STOP_BUDGET_FILL_RATIO


class _MinCostFlow:
    def __init__(self, n_nodes: int) -> None:
        self.graph: list[list[list[float | int]]] = [[] for _ in range(n_nodes)]

    def add_edge(self, start: int, end: int, capacity: int, cost: float) -> None:
        forward = [end, capacity, cost, len(self.graph[end])]
        backward = [start, 0, -cost, len(self.graph[start])]
        self.graph[start].append(forward)
        self.graph[end].append(backward)

    def min_cost_flow(self, source: int, sink: int, max_flow: int) -> tuple[int, float]:
        flow = 0
        cost = 0.0
        n_nodes = len(self.graph)
        while flow < max_flow:
            dist = [float("inf")] * n_nodes
            in_queue = [False] * n_nodes
            prev_node = [-1] * n_nodes
            prev_edge = [-1] * n_nodes
            dist[source] = 0.0
            queue: deque[int] = deque([source])
            in_queue[source] = True

            while queue:
                node = queue.popleft()
                in_queue[node] = False
                for edge_index, edge in enumerate(self.graph[node]):
                    to_node, capacity, edge_cost, _ = edge
                    if capacity <= 0:
                        continue
                    next_cost = dist[node] + edge_cost
                    if next_cost + EPS < dist[to_node]:
                        dist[to_node] = next_cost
                        prev_node[to_node] = node
                        prev_edge[to_node] = edge_index
                        if not in_queue[to_node]:
                            queue.append(to_node)
                            in_queue[to_node] = True

            if prev_node[sink] == -1:
                break

            augment = max_flow - flow
            node = sink
            while node != source:
                edge = self.graph[prev_node[node]][prev_edge[node]]
                augment = min(augment, int(edge[1]))
                node = prev_node[node]

            node = sink
            while node != source:
                edge = self.graph[prev_node[node]][prev_edge[node]]
                reverse = self.graph[node][int(edge[3])]
                edge[1] = int(edge[1]) - augment
                reverse[1] = int(reverse[1]) + augment
                cost += float(edge[2]) * augment
                node = prev_node[node]
            flow += augment

        return flow, cost


def _min_cost_single_cover(tasks: list[str], singles: list[CompetitionCandidate]) -> list[CompetitionCandidate]:
    task_index = {task_id: index for index, task_id in enumerate(tasks)}
    couriers = sorted({candidate.courier_id for candidate in singles})
    courier_index = {courier_id: index for index, courier_id in enumerate(couriers)}
    if not tasks or not couriers:
        return []

    source = 0
    task_offset = 1
    courier_offset = task_offset + len(tasks)
    sink = courier_offset + len(couriers)
    flow = _MinCostFlow(sink + 1)
    for task_id in tasks:
        flow.add_edge(source, task_offset + task_index[task_id], 1, 0.0)
    for courier_id in couriers:
        flow.add_edge(courier_offset + courier_index[courier_id], sink, 1, 0.0)

    edge_to_candidate: dict[tuple[int, int], CompetitionCandidate] = {}
    best_by_pair: dict[tuple[str, str], CompetitionCandidate] = {}
    for candidate in singles:
        key = (candidate.task_ids[0], candidate.courier_id)
        if _better_candidate(candidate, best_by_pair.get(key)):
            best_by_pair[key] = candidate

    for candidate in best_by_pair.values():
        task_node = task_offset + task_index[candidate.task_ids[0]]
        courier_node = courier_offset + courier_index[candidate.courier_id]
        edge_position = len(flow.graph[task_node])
        flow.add_edge(task_node, courier_node, 1, _candidate_cost(candidate))
        edge_to_candidate[(task_node, edge_position)] = candidate

    sent, _ = flow.min_cost_flow(source, sink, len(tasks))
    if sent < len(tasks):
        return []

    solution: list[CompetitionCandidate] = []
    for (task_node, edge_position), candidate in edge_to_candidate.items():
        edge = flow.graph[task_node][edge_position]
        if int(edge[1]) == 0:
            solution.append(candidate)
    return solution


def _greedy_cover(candidates: list[CompetitionCandidate]) -> list[CompetitionCandidate]:
    solution: list[CompetitionCandidate] = []
    used_tasks: set[str] = set()
    used_couriers: set[str] = set()
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate.total_score / max(1, candidate.size),
            candidate.total_score,
            -candidate.willingness,
            candidate.row_index,
        ),
    )
    for candidate in ordered:
        if candidate.courier_id in used_couriers:
            continue
        if any(task_id in used_tasks for task_id in candidate.task_ids):
            continue
        solution.append(candidate)
        used_couriers.add(candidate.courier_id)
        used_tasks.update(candidate.task_ids)
    return solution


def _solution_indexes(solution: Iterable[CompetitionCandidate]):
    by_task: dict[str, CompetitionCandidate] = {}
    by_courier: dict[str, CompetitionCandidate] = {}
    for candidate in solution:
        by_courier[candidate.courier_id] = candidate
        for task_id in candidate.task_ids:
            by_task[task_id] = candidate
    return by_task, by_courier


def _replace_candidates(
    solution: list[CompetitionCandidate],
    removed: set[CompetitionCandidate],
    added: Iterable[CompetitionCandidate],
) -> list[CompetitionCandidate]:
    return [candidate for candidate in solution if candidate not in removed] + list(added)


def _improves(new_items: Iterable[CompetitionCandidate], old_items: Iterable[CompetitionCandidate]) -> bool:
    new = list(new_items)
    old = list(old_items)
    new_tasks = len(_covered_tasks(new))
    old_tasks = len(_covered_tasks(old))
    if new_tasks != old_tasks:
        return new_tasks > old_tasks
    new_score = sum(candidate.total_score for candidate in new)
    old_score = sum(candidate.total_score for candidate in old)
    if new_score < old_score - EPS:
        return True
    if abs(new_score - old_score) <= EPS:
        return sum(candidate.willingness for candidate in new) > sum(candidate.willingness for candidate in old) + EPS
    return False


def _improve_single_swaps(
    solution: list[CompetitionCandidate],
    singles: list[CompetitionCandidate],
) -> list[CompetitionCandidate]:
    by_single_task: dict[str, list[CompetitionCandidate]] = defaultdict(list)
    for candidate in singles:
        by_single_task[candidate.task_ids[0]].append(candidate)

    improved = True
    current = list(solution)
    while improved:
        improved = False
        by_task, by_courier = _solution_indexes(current)
        for task_id, old_candidate in list(by_task.items()):
            if old_candidate.size != 1:
                continue
            for candidate in sorted(by_single_task.get(task_id, []), key=lambda item: (_candidate_cost(item), item.row_index)):
                courier_owner = by_courier.get(candidate.courier_id)
                if courier_owner is not None and courier_owner != old_candidate:
                    continue
                if _improves([candidate], [old_candidate]):
                    current = _replace_candidates(current, {old_candidate}, [candidate])
                    improved = True
                    break
            if improved:
                break
    return current


def _improve_with_bundles(
    solution: list[CompetitionCandidate],
    candidates: list[CompetitionCandidate],
) -> list[CompetitionCandidate]:
    by_pair: dict[tuple[str, ...], CompetitionCandidate] = {}
    singles_by_task_courier: dict[tuple[str, str], CompetitionCandidate] = {}
    for candidate in candidates:
        if candidate.size == 1:
            singles_by_task_courier[(candidate.task_ids[0], candidate.courier_id)] = candidate
        elif candidate.size == 2:
            key = tuple(sorted(candidate.task_ids))
            if _better_candidate(candidate, by_pair.get(key)):
                by_pair[key] = candidate

    current = list(solution)
    improved = True
    while improved:
        improved = False
        by_task, by_courier = _solution_indexes(current)
        best_next: list[CompetitionCandidate] | None = None
        best_score_delta = 0.0
        best_willingness_delta = 0.0

        for bundle in by_pair.values():
            task_owners = {by_task.get(task_id) for task_id in bundle.task_ids}
            if None in task_owners:
                continue
            removed = {owner for owner in task_owners if owner is not None}
            removed_tasks = _covered_tasks(removed)
            if removed_tasks != set(bundle.task_ids):
                continue
            courier_owner = by_courier.get(bundle.courier_id)
            if courier_owner is not None and courier_owner not in removed:
                continue
            old_score = sum(candidate.total_score for candidate in removed)
            old_willingness = sum(candidate.willingness for candidate in removed)
            score_delta = bundle.total_score - old_score
            willingness_delta = bundle.willingness - old_willingness
            if score_delta < best_score_delta - EPS or (
                abs(score_delta - best_score_delta) <= EPS and willingness_delta > best_willingness_delta + EPS
            ):
                best_next = _replace_candidates(current, removed, [bundle])
                best_score_delta = score_delta
                best_willingness_delta = willingness_delta

        for selected in list(current):
            if selected.size != 2:
                continue
            replacements = _best_split(selected, current, singles_by_task_courier)
            if not replacements:
                continue
            score_delta = sum(item.total_score for item in replacements) - selected.total_score
            willingness_delta = sum(item.willingness for item in replacements) - selected.willingness
            if score_delta < best_score_delta - EPS or (
                abs(score_delta - best_score_delta) <= EPS and willingness_delta > best_willingness_delta + EPS
            ):
                best_next = _replace_candidates(current, {selected}, replacements)
                best_score_delta = score_delta
                best_willingness_delta = willingness_delta

        if best_next is not None:
            current = best_next
            improved = True

    return current


def _best_split(
    bundle: CompetitionCandidate,
    current: list[CompetitionCandidate],
    singles_by_task_courier: dict[tuple[str, str], CompetitionCandidate],
) -> list[CompetitionCandidate]:
    _, by_courier = _solution_indexes(candidate for candidate in current if candidate != bundle)
    free_couriers = {courier for _, courier in singles_by_task_courier}
    free_couriers = {courier for courier in free_couriers if courier not in by_courier}
    options: list[list[CompetitionCandidate]] = []
    first_task, second_task = bundle.task_ids
    for first_courier in free_couriers:
        first = singles_by_task_courier.get((first_task, first_courier))
        if first is None:
            continue
        for second_courier in free_couriers:
            if second_courier == first_courier:
                continue
            second = singles_by_task_courier.get((second_task, second_courier))
            if second is not None:
                options.append([first, second])
    if not options:
        return []
    return min(options, key=lambda items: (sum(_candidate_cost(item) for item in items), -sum(item.willingness for item in items)))
