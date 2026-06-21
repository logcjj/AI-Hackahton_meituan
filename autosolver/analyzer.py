from __future__ import annotations

from collections import Counter


def summarize_instance(instance):
    probabilities = [value for row in instance.p for value in row]
    return {
        'id': instance.id,
        'orders': len(instance.orders),
        'riders': len(instance.riders),
        'avg_accept_probability': sum(probabilities) / len(probabilities) if probabilities else 0.0,
        'score_direction': instance.score_direction,
    }


def summarize_candidates(candidates):
    counter = Counter('bundle' if candidate.is_bundle else 'single' for candidate in candidates)
    probabilities = [candidate.probability for candidate in candidates]
    return {
        'total_candidates': len(candidates),
        'single_candidates': counter['single'],
        'bundle_candidates': counter['bundle'],
        'avg_candidate_probability': sum(probabilities) / len(probabilities) if probabilities else 0.0,
    }
