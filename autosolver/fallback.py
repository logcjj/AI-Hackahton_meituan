from __future__ import annotations


from autosolver.candidate_gen import MIN_ACCEPT_PROB, feasible_single, generate_candidates, make_single_candidate
from autosolver.greedy import greedy_marginal
from autosolver.state import SolverState


class FallbackChain:
    def fallback_2_greedy(self, instance):
        try:
            candidates = generate_candidates(instance, time_budget=0.3)
            solution = greedy_marginal(candidates, instance, time_budget=0.3)
            if solution:
                return solution
        except Exception:
            pass
        return self.fallback_1_top_p(instance)

    def fallback_1_top_p(self, instance):
        try:
            solution = []
            state = SolverState(instance)
            order_priority = sorted(instance.orders, key=lambda order: -max(instance.p[instance.order_pos(order.id)]))
            for order in order_priority:
                order_idx = instance.order_pos(order.id)
                for rider_idx in sorted(range(len(instance.riders)), key=lambda index: -instance.p[order_idx][index]):
                    probability = float(instance.p[order_idx][rider_idx])
                    if probability < MIN_ACCEPT_PROB:
                        break
                    rider = instance.riders[rider_idx]
                    if not feasible_single(order, rider, instance):
                        continue
                    candidate = make_single_candidate(order, rider, instance)
                    if not state.rider_compatible(candidate):
                        continue
                    solution.append(candidate)
                    state.apply(candidate)
                    break
            return solution
        except Exception:
            return self.fallback_0_reject_all(instance)

    def fallback_0_reject_all(self, instance):
        return []
