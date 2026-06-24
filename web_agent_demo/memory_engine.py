from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PREDICTOR_ENV_VARS = ("AUTOSOLVER_LLM_BASE_URL", "AUTOSOLVER_LLM_API_KEY", "AUTOSOLVER_LLM_MODEL")


@dataclass(frozen=True)
class MemoryRecallBundle:
    mode: str
    source: str
    scenario_memory: tuple[dict[str, Any], ...]
    decision_memory: tuple[dict[str, Any], ...]
    strategy_memory: tuple[dict[str, Any], ...]
    evolution_memory: tuple[dict[str, Any], ...]
    effect_on_ranking: str

    @classmethod
    def off(cls) -> "MemoryRecallBundle":
        return cls("off", "external-disabled", (), (), (), (), "Memory mode is off; ranking uses current tick metrics only.")


@dataclass(frozen=True)
class PredictorTrace:
    mode: str
    provider: str
    model: str
    used_external_api: bool
    timeout_ms: int
    status: str
    secret_handling: str
    ranking_reason: str
    ranked_algorithms: tuple[dict[str, Any], ...]


class SimulationMemoryStore:
    """Hermes-style USER/MEMORY split adapted to dispatch simulation decisions."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "memory_events.jsonl"
        self.registry_path = self.root / "strategy_registry.json"
        self.lock_path = self.root / ".memory.lock"

    def recall_similar_context(
        self,
        features: Any,
        candidate_algorithm_ids: tuple[str, ...] | list[str] | None = None,
        limit: int = 5,
        mode: str = "read-only",
    ) -> MemoryRecallBundle:
        if mode == "off":
            return MemoryRecallBundle.off()
        feature_dict = _to_plain_dict(features)
        candidates = set(candidate_algorithm_ids or ())
        scenario_hash = _scenario_hash(feature_dict)
        events = self._read_events()
        registry = self._read_registry()

        scenario_memory = []
        decision_memory = []
        for event in events:
            event_features = event.get("features") or {}
            similarity = _feature_similarity(feature_dict, event_features)
            if similarity <= 0:
                continue
            if event.get("event_type") in {"scenario_seen", "compare_completed"}:
                scenario_memory.append({**_compact_event(event), "similarity": round(similarity, 4)})
            if event.get("event_type") in {"strategy_selected", "strategy_rejected", "compare_completed"}:
                decision_memory.append({**_compact_event(event), "similarity": round(similarity, 4)})

        strategy_memory = []
        evolution_memory = []
        for algorithm_id, item in registry.items():
            if candidates and algorithm_id not in candidates and item.get("source_algorithm_id") not in candidates:
                continue
            similarity = max(
                [_feature_similarity(feature_dict, seen.get("features") or {}) for seen in item.get("seen_contexts", [])]
                or [1.0 if item.get("last_scenario_hash") == scenario_hash else 0.0]
            )
            memory_item = {
                "algorithm_id": algorithm_id,
                "source_algorithm_id": item.get("source_algorithm_id"),
                "status": item.get("status", "candidate"),
                "attempts": int(item.get("attempts", 0)),
                "selected_count": int(item.get("selected_count", 0)),
                "avg_score": round(float(item.get("avg_score", 0.0)), 4),
                "avg_timeout_risk": round(float(item.get("avg_timeout_risk", 0.0)), 4),
                "avg_no_accept_risk": round(float(item.get("avg_no_accept_risk", 0.0)), 4),
                "similarity": round(similarity, 4),
                "last_reason": item.get("last_reason", ""),
            }
            if item.get("evolution_type"):
                evolution_memory.append(memory_item)
            else:
                strategy_memory.append(memory_item)

        strategy_memory = tuple(sorted(strategy_memory, key=lambda item: (-item["similarity"], -item["avg_score"], item["algorithm_id"]))[:limit])
        scenario_memory = tuple(sorted(scenario_memory, key=lambda item: (-item["similarity"], item["event_id"]))[:limit])
        decision_memory = tuple(sorted(decision_memory, key=lambda item: (-item["similarity"], item["event_id"]))[:limit])
        evolution_memory = tuple(sorted(evolution_memory, key=lambda item: (-item["similarity"], -item["avg_score"], item["algorithm_id"]))[:limit])
        effect = _ranking_effect((*strategy_memory, *evolution_memory))
        return MemoryRecallBundle(mode, "local-jsonl", scenario_memory, decision_memory, strategy_memory, evolution_memory, effect)

    def record_compare_result(self, compare_result: Any) -> None:
        compare_run = compare_result.compare_run
        features = _to_plain_dict(compare_run.scenario_features)
        scenario_hash = _scenario_hash(features)
        selected = compare_result.selected
        selected_algorithm_id = selected.algorithm_id
        events = [
            {
                "event_type": "scenario_seen",
                "scenario_hash": scenario_hash,
                "compare_run_id": compare_run.compare_run_id,
                "tick_id": compare_run.tick_id,
                "features": features,
                "decision_summary": f"Scenario observed with {features.get('active_order_count', 0)} active orders.",
                "privacy": {"secret_free": True},
            },
            {
                "event_type": "compare_completed",
                "scenario_hash": scenario_hash,
                "compare_run_id": compare_run.compare_run_id,
                "tick_id": compare_run.tick_id,
                "features": features,
                "algorithm_id": selected_algorithm_id,
                "metrics": _to_plain_dict(selected.metrics),
                "decision_summary": selected.reason,
                "privacy": {"secret_free": True},
            },
            {
                "event_type": "strategy_selected",
                "scenario_hash": scenario_hash,
                "compare_run_id": compare_run.compare_run_id,
                "tick_id": compare_run.tick_id,
                "features": features,
                "algorithm_id": selected_algorithm_id,
                "metrics": _to_plain_dict(selected.metrics),
                "decision_summary": selected.reason,
                "privacy": {"secret_free": True},
            },
        ]
        for result in compare_result.results:
            if result.algorithm_id != selected_algorithm_id:
                events.append(
                    {
                        "event_type": "strategy_rejected",
                        "scenario_hash": scenario_hash,
                        "compare_run_id": compare_run.compare_run_id,
                        "tick_id": compare_run.tick_id,
                        "features": features,
                        "algorithm_id": result.algorithm_id,
                        "metrics": _to_plain_dict(result.metrics),
                        "decision_summary": result.reason,
                        "privacy": {"secret_free": True},
                    }
                )

        with _FileLock(self.lock_path):
            for event in events:
                self._append_event_unlocked(event)
            registry = self._read_registry_unlocked()
            selected_source = getattr(selected, "source_algorithm_id", None)
            for result in compare_result.results:
                selected_for_learning = result.algorithm_id == selected_algorithm_id
                if selected_algorithm_id == "autosolver_agent" and result.algorithm_id != "autosolver_agent":
                    selected_for_learning = result.algorithm_id == selected_source
                registry[result.algorithm_id] = _updated_strategy_entry(
                    registry.get(result.algorithm_id, {}),
                    result,
                    features,
                    scenario_hash,
                    selected_for_learning,
                )
            transition_events = _evolve_registry_states(registry, scenario_hash, compare_run.compare_run_id, compare_run.tick_id, features)
            for event in transition_events:
                self._append_event_unlocked(event)
            self._write_registry_unlocked(registry)

    def append_memory_event(self, event: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        event = _normalize_memory_event(event)
        if dry_run:
            return event
        with _FileLock(self.lock_path):
            self._append_event_unlocked(event)
        return event

    def register_evolution_candidate(
        self,
        strategy_id: str,
        source_algorithm_id: str,
        features: Any,
        reason: str,
    ) -> dict[str, Any]:
        feature_dict = _to_plain_dict(features)
        scenario_hash = _scenario_hash(feature_dict)
        event = {
            "event_type": "evolution_candidate_generated",
            "scenario_hash": scenario_hash,
            "compare_run_id": "",
            "tick_id": "",
            "features": feature_dict,
            "algorithm_id": strategy_id,
            "decision_summary": reason,
            "privacy": {"secret_free": True},
        }
        with _FileLock(self.lock_path):
            registry = self._read_registry_unlocked()
            registry[strategy_id] = {
                **registry.get(strategy_id, {}),
                "status": "draft",
                "evolution_type": "generated_candidate",
                "source_algorithm_id": source_algorithm_id,
                "attempts": int(registry.get(strategy_id, {}).get("attempts", 0)),
                "selected_count": int(registry.get(strategy_id, {}).get("selected_count", 0)),
                "avg_score": float(registry.get(strategy_id, {}).get("avg_score", 0.0)),
                "last_reason": reason,
                "last_scenario_hash": scenario_hash,
                "seen_contexts": _append_seen_context(registry.get(strategy_id, {}), feature_dict, scenario_hash),
            }
            self._append_event_unlocked(event)
            self._write_registry_unlocked(registry)
        return registry[strategy_id]

    def record_evolution_trial(
        self,
        strategy_id: str,
        accepted: bool,
        metrics: dict[str, Any],
        features: Any,
        reason: str,
    ) -> dict[str, Any]:
        feature_dict = _to_plain_dict(features)
        scenario_hash = _scenario_hash(feature_dict)
        with _FileLock(self.lock_path):
            registry = self._read_registry_unlocked()
            entry = dict(registry.get(strategy_id, {"evolution_type": "generated_candidate"}))
            attempts = int(entry.get("attempts", 0)) + 1
            selected_count = int(entry.get("selected_count", 0)) + (1 if accepted else 0)
            score = float(metrics.get("score", 0.0))
            entry.update(
                {
                    "status": _evolution_status(attempts, selected_count, score, accepted),
                    "attempts": attempts,
                    "selected_count": selected_count,
                    "avg_score": _running_average(float(entry.get("avg_score", 0.0)), attempts - 1, score),
                    "last_reason": reason,
                    "last_scenario_hash": scenario_hash,
                    "seen_contexts": _append_seen_context(entry, feature_dict, scenario_hash),
                    "rollback_action": None if accepted else "removed_from_active_pool",
                }
            )
            registry[strategy_id] = entry
            event_type = "evolution_promoted" if entry["status"] == "promoted" else "evolution_rolled_back" if entry["status"] == "rolled_back" else "strategy_trial"
            self._append_event_unlocked(
                {
                    "event_type": event_type,
                    "scenario_hash": scenario_hash,
                    "compare_run_id": "",
                    "tick_id": "",
                    "features": feature_dict,
                    "algorithm_id": strategy_id,
                    "metrics": metrics,
                    "decision_summary": reason,
                    "privacy": {"secret_free": True},
                }
            )
            self._write_registry_unlocked(registry)
        return entry

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        events = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def _read_registry(self) -> dict[str, dict[str, Any]]:
        with _FileLock(self.lock_path):
            return self._read_registry_unlocked()

    def _read_registry_unlocked(self) -> dict[str, dict[str, Any]]:
        if not self.registry_path.exists():
            return {}
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _write_registry_unlocked(self, registry: dict[str, dict[str, Any]]) -> None:
        tmp_path = self.registry_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.registry_path)

    def _append_event_unlocked(self, event: dict[str, Any]) -> None:
        event = _normalize_memory_event(event)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def rank_algorithms_with_predictor(
    features: Any,
    candidate_results: tuple[Any, ...],
    recall: MemoryRecallBundle | None,
    mode: str = "fallback",
    timeout_ms: int = 800,
    env: dict[str, str] | None = None,
) -> PredictorTrace:
    env_values = dict(os.environ if env is None else env)
    candidate_ids = tuple(result.algorithm_id for result in candidate_results)
    if mode not in {"fallback", "auto", "external"}:
        mode = "fallback"
    has_external_env = all(env_values.get(name) for name in PREDICTOR_ENV_VARS)
    if mode == "external" and has_external_env:
        external = _external_predictor(features, candidate_results, recall, env_values, timeout_ms)
        if external is not None:
            return external
    if mode == "auto" and has_external_env:
        external = _external_predictor(features, candidate_results, recall, env_values, timeout_ms)
        if external is not None:
            return external

    ranked = _fallback_rankings(candidate_results, recall)
    status = "skipped" if mode in {"auto", "external"} and not has_external_env else "fallback"
    reason = "External predictor is disabled because required env vars are absent." if status == "skipped" else "Local heuristic ranked algorithms using current metrics and recalled strategy memory."
    return PredictorTrace(
        mode=mode,
        provider="local-heuristic",
        model="local-heuristic-v1",
        used_external_api=False,
        timeout_ms=timeout_ms,
        status=status,
        secret_handling="env-only-redacted",
        ranking_reason=reason,
        ranked_algorithms=ranked or tuple({"algorithm_id": algorithm_id, "rank": index + 1, "reason": "fallback order"} for index, algorithm_id in enumerate(candidate_ids)),
    )


def _external_predictor(
    features: Any,
    candidate_results: tuple[Any, ...],
    recall: MemoryRecallBundle | None,
    env: dict[str, str],
    timeout_ms: int,
) -> PredictorTrace | None:
    base_url = env.get("AUTOSOLVER_LLM_BASE_URL", "").rstrip("/")
    api_key = env.get("AUTOSOLVER_LLM_API_KEY", "")
    model = env.get("AUTOSOLVER_LLM_MODEL", "")
    if not base_url or not api_key or not model:
        return None
    payload = {
        "model": model,
        "scenario_features": _to_plain_dict(features),
        "candidate_algorithms": [_compact_result(result) for result in candidate_results],
        "memory": _to_plain_dict(recall) if recall is not None else {},
    }
    request = urllib.request.Request(
        f"{base_url}/predictor/rank",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(0.1, timeout_ms / 1000.0)) as response:
            raw = json.loads(response.read().decode("utf-8"))
        ranked = raw.get("ranked_algorithms") or raw.get("ranking") or ()
        normalized = tuple(_normalize_ranked_item(item, index) for index, item in enumerate(ranked))
        if not normalized:
            return None
        return PredictorTrace(
            mode="external",
            provider="external-http",
            model=model,
            used_external_api=True,
            timeout_ms=timeout_ms,
            status="ok",
            secret_handling="env-only-redacted",
            ranking_reason=str(raw.get("reason") or "External predictor returned a ranked strategy list."),
            ranked_algorithms=normalized,
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _fallback_rankings(candidate_results: tuple[Any, ...], recall: MemoryRecallBundle | None) -> tuple[dict[str, Any], ...]:
    memory_boost = {}
    recalled_items = (*recall.strategy_memory, *recall.evolution_memory) if recall is not None else ()
    for item in recalled_items:
        algorithm_id = str(item.get("source_algorithm_id") or item.get("algorithm_id"))
        status_boost = {"promoted": 7.0, "trusted": 4.0, "candidate": 2.0, "draft": 0.5}.get(str(item.get("status")), 0.0)
        memory_boost[algorithm_id] = max(
            memory_boost.get(algorithm_id, 0.0),
            float(item.get("similarity", 0.0)) * (float(item.get("avg_score", 0.0)) * 0.22 + status_boost),
        )
    scored = []
    for result in candidate_results:
        metrics = result.metrics
        score = float(metrics.score) + memory_boost.get(result.algorithm_id, 0.0)
        scored.append((score, result.algorithm_id, memory_boost.get(result.algorithm_id, 0.0), result))
    ranked = []
    for rank, (score, algorithm_id, boost, result) in enumerate(sorted(scored, reverse=True), start=1):
        reason = "current metrics"
        if boost > 0:
            reason = f"current metrics plus similar-memory boost {boost:.2f}"
        ranked.append(
            {
                "algorithm_id": algorithm_id,
                "rank": rank,
                "score": round(score, 4),
                "memory_boost": round(boost, 4),
                "reason": reason,
                "coverage_rate": result.metrics.coverage_rate,
                "timeout_risk": result.metrics.timeout_risk,
            }
        )
    return tuple(ranked)


def _updated_strategy_entry(
    current: dict[str, Any],
    result: Any,
    features: dict[str, Any],
    scenario_hash: str,
    selected: bool,
) -> dict[str, Any]:
    attempts = int(current.get("attempts", 0)) + 1
    selected_count = int(current.get("selected_count", 0)) + (1 if selected else 0)
    metrics = result.metrics
    entry = {
        **current,
        "status": current.get("status", "candidate"),
        "attempts": attempts,
        "selected_count": selected_count,
        "avg_score": _running_average(float(current.get("avg_score", 0.0)), attempts - 1, float(metrics.score)),
        "avg_timeout_risk": _running_average(float(current.get("avg_timeout_risk", 0.0)), attempts - 1, float(metrics.timeout_risk)),
        "avg_no_accept_risk": _running_average(float(current.get("avg_no_accept_risk", 0.0)), attempts - 1, float(metrics.no_accept_risk)),
        "last_reason": result.reason,
        "last_scenario_hash": scenario_hash,
        "last_seen": _now(),
        "seen_contexts": _append_seen_context(current, features, scenario_hash),
    }
    if selected_count >= 2 and entry["avg_score"] >= 68.0:
        entry["status"] = "promoted"
    elif attempts >= 2 and selected_count > 0:
        entry["status"] = "trusted"
    elif attempts >= 3 and selected_count == 0 and entry["avg_score"] < 45.0:
        entry["status"] = "rolled_back"
        entry["rollback_action"] = "removed_from_active_pool"
    return entry


def _evolve_registry_states(
    registry: dict[str, dict[str, Any]],
    scenario_hash: str,
    compare_run_id: str,
    tick_id: str,
    features: dict[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for algorithm_id, item in registry.items():
        previous = item.get("_last_emitted_status")
        status = item.get("status")
        if status in {"promoted", "rolled_back"} and previous != status:
            item["_last_emitted_status"] = status
            events.append(
                {
                    "event_type": "evolution_promoted" if status == "promoted" else "evolution_rolled_back",
                    "scenario_hash": scenario_hash,
                    "compare_run_id": compare_run_id,
                    "tick_id": tick_id,
                    "features": features,
                    "algorithm_id": algorithm_id,
                    "metrics": {
                        "avg_score": item.get("avg_score"),
                        "attempts": item.get("attempts"),
                        "selected_count": item.get("selected_count"),
                    },
                    "decision_summary": f"{algorithm_id} moved to {status}.",
                    "privacy": {"secret_free": True},
                }
            )
    return events


def _normalize_memory_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    normalized.setdefault("event_id", _stable_id("memory", normalized.get("event_type"), normalized.get("compare_run_id"), normalized.get("tick_id"), normalized.get("algorithm_id"), normalized.get("decision_summary")))
    normalized.setdefault("created_at", _now())
    normalized.setdefault("scenario_hash", _scenario_hash(normalized.get("features") or {}))
    normalized.setdefault("compare_run_id", "")
    normalized.setdefault("tick_id", "")
    normalized.setdefault("features", {})
    normalized.setdefault("algorithm_id", "")
    normalized.setdefault("metrics", {})
    normalized.setdefault("decision_summary", "")
    normalized["privacy"] = {"secret_free": True, **dict(normalized.get("privacy") or {})}
    normalized["privacy"]["secret_free"] = True
    return normalized


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "algorithm_id": event.get("algorithm_id"),
        "compare_run_id": event.get("compare_run_id"),
        "scenario_hash": event.get("scenario_hash"),
        "decision_summary": event.get("decision_summary"),
        "metrics": event.get("metrics") or {},
    }


def _compact_result(result: Any) -> dict[str, Any]:
    return {
        "algorithm_id": result.algorithm_id,
        "metrics": _to_plain_dict(result.metrics),
        "risk_flags": list(result.risk_flags),
        "reason": result.reason,
    }


def _normalize_ranked_item(item: Any, index: int) -> dict[str, Any]:
    if isinstance(item, str):
        return {"algorithm_id": item, "rank": index + 1, "reason": "external ranking"}
    return {
        "algorithm_id": str(item.get("algorithm_id") or item.get("id") or ""),
        "rank": int(item.get("rank") or index + 1),
        "score": float(item.get("score", 0.0)),
        "reason": str(item.get("reason") or "external ranking"),
    }


def _ranking_effect(strategy_memory: tuple[dict[str, Any], ...]) -> str:
    if not strategy_memory:
        return "No similar strategy memory found; ranking uses current tick metrics."
    best = strategy_memory[0]
    display_algorithm = best.get("source_algorithm_id") or best["algorithm_id"]
    return f"Similar memory favors {display_algorithm} with avg score {best['avg_score']:.1f} and similarity {best['similarity']:.2f}."


def _append_seen_context(current: dict[str, Any], features: dict[str, Any], scenario_hash: str) -> list[dict[str, Any]]:
    contexts = list(current.get("seen_contexts") or [])
    contexts.append({"scenario_hash": scenario_hash, "features": features, "seen_at": _now()})
    return contexts[-12:]


def _feature_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    if not left or not right:
        return 0.0
    score = 0.0
    weight = 0.0
    for key, item_weight in (("scenario_id", 0.22), ("scene_type", 0.18), ("weather", 0.14), ("traffic_profile", 0.08)):
        weight += item_weight
        if left.get(key) == right.get(key):
            score += item_weight
    for key, item_weight in (("order_pressure", 0.14), ("courier_pressure", 0.1), ("avg_willingness", 0.08), ("congestion_level", 0.06)):
        weight += item_weight
        score += item_weight * max(0.0, 1.0 - abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))))
    return score / max(weight, 1e-9)


def _scenario_hash(features: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "scenario_id": features.get("scenario_id"),
            "scene_type": features.get("scene_type"),
            "weather": features.get("weather"),
            "traffic_profile": features.get("traffic_profile"),
            "pressure": round(float(features.get("order_pressure", 0.0)), 1),
            "willingness": round(float(features.get("avg_willingness", 0.0)), 1),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]


def _evolution_status(attempts: int, selected_count: int, score: float, accepted: bool) -> str:
    if accepted and selected_count >= 2 and score >= 68.0:
        return "promoted"
    if accepted:
        return "candidate"
    if attempts >= 1:
        return "rolled_back"
    return "rejected"


def _running_average(previous_average: float, previous_count: int, value: float) -> float:
    return round((previous_average * previous_count + value) / max(1, previous_count + 1), 6)


def _to_plain_dict(value: Any) -> Any:
    if value is None:
        return {}
    if dataclasses.is_dataclass(value):
        return {key: _to_plain_dict(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_plain_dict(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_plain_dict(item) for item in value]
    return value


def _stable_id(*parts: object) -> str:
    return hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class _FileLock:
    def __init__(self, path: Path, timeout_s: float = 2.0) -> None:
        self.path = path
        self.timeout_s = timeout_s
        self.fd: int | None = None

    def __enter__(self) -> "_FileLock":
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, str(os.getpid()).encode("utf-8"))
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                time.sleep(0.01)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
