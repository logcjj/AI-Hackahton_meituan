# =============================================================================
# autosolver/offline/reevo_runner_v2.py
# -----------------------------------------------------------------------------
# Offline driver for the REAL LLM-powered ReEvo/EoH/FunSearch heuristic-evolution
# loop. This is the only place an API may be hit; nothing here runs on the online
# competition solve path.
#
# The original autosolver/offline/reevo_runner.py is intentionally a hard `raise`
# (it guards the online path from ever importing the SDK). Per the global rule we
# do NOT edit it — this is a brand-new sibling module.
#
# Usage
#   # Deterministic offline stub (no API key needed; fully demoable end-to-end):
#   python3 -m autosolver.offline.reevo_runner_v2 --generations 8 --children 3
#
#   # Real LLM-driven evolution (needs ANTHROPIC_API_KEY in the environment):
#   export ANTHROPIC_API_KEY=sk-ant-...
#   python3 -m autosolver.offline.reevo_runner_v2 --llm --generations 6 --children 3
#
# Models when --llm is set:
#   generator / reflector : claude-sonnet-4-6  (use --hq for claude-opus-4-8)
#   cheap breadth proposals: claude-haiku-4-5
#
# Outputs (all written under the repo; absolute paths printed at the end):
#   autosolver_agent/evolution_state/strategy_registry.json   (accepted/promoted)
#   autosolver_agent/evolution_state/evolution_memory.jsonl    (reflections+trials)
#   autosolver_agent/evolution_state/generated_strategies/*.py (every candidate)
#   autosolver/offline/evolved/<best>.py + manifest.json       (solver_v3 pool)
# =============================================================================
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make the repo root importable when run as a script.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from autosolver_agent.llm_evolution import (  # noqa: E402
    EvolutionConfig,
    EvolutionEngine,
    GENERATOR_MODEL,
    GENERATOR_MODEL_HQ,
)


def run_offline_evolution(
    *,
    generations: int = 8,
    children: int = 3,
    train_per_regime: int = 1,
    heldout_per_regime: int = 2,
    fast_instances: int = 4,
    use_llm: bool = False,
    hq: bool = False,
    seed: int = 20260620,
    observer=None,
) -> dict:
    """Programmatic entry point. Returns the run summary dict."""
    if use_llm and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "use_llm=True requires ANTHROPIC_API_KEY in the environment. "
            "Run without --llm to use the deterministic offline stub generator."
        )
    cfg = EvolutionConfig(
        generations=generations,
        children_per_generation=children,
        train_per_regime=train_per_regime,
        heldout_per_regime=heldout_per_regime,
        fast_instances=fast_instances,
        use_llm=use_llm,
        seed=seed,
    )
    engine = EvolutionEngine(cfg, observer=observer)
    if use_llm and hq:
        # Upgrade the generator model in place for maximum quality.
        from autosolver_agent.llm_evolution import LLMGenerator

        engine.generator = LLMGenerator(engine.client, GENERATOR_MODEL_HQ)
    return engine.run()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generations", type=int, default=8)
    ap.add_argument("--children", type=int, default=3, help="children proposed per generation")
    ap.add_argument("--train-per-regime", type=int, default=1)
    ap.add_argument("--heldout-per-regime", type=int, default=2)
    ap.add_argument("--fast-instances", type=int, default=4)
    ap.add_argument("--llm", action="store_true", help="use the real anthropic SDK (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--hq", action="store_true", help=f"use {GENERATOR_MODEL_HQ} instead of {GENERATOR_MODEL}")
    ap.add_argument("--seed", type=int, default=20260620)
    ap.add_argument("--quiet", action="store_true", help="suppress per-event JSON lines")
    args = ap.parse_args(argv)

    events: list[dict] = []

    def observer(event: dict) -> None:
        events.append(event)
        if not args.quiet:
            print(json.dumps(event, ensure_ascii=False), flush=True)

    if args.llm and not os.environ.get("ANTHROPIC_API_KEY"):
        print("[reevo_runner_v2] ANTHROPIC_API_KEY not set — falling back to the deterministic "
              "offline STUB generator. To run the real LLM loop, set the key and re-run with --llm.",
              file=sys.stderr)
        args.llm = False

    summary = run_offline_evolution(
        generations=args.generations,
        children=args.children,
        train_per_regime=args.train_per_regime,
        heldout_per_regime=args.heldout_per_regime,
        fast_instances=args.fast_instances,
        use_llm=args.llm,
        hq=args.hq,
        seed=args.seed,
        observer=observer,
    )

    print("\n=== EVOLUTION SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nState written under:")
    print(f"  {(_ROOT / 'autosolver_agent' / 'evolution_state' / 'strategy_registry.json')}")
    print(f"  {(_ROOT / 'autosolver_agent' / 'evolution_state' / 'evolution_memory.jsonl')}")
    print(f"  {(_ROOT / 'autosolver' / 'offline' / 'evolved')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
