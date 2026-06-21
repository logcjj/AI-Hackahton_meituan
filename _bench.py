#!/usr/bin/env python3
"""Local bench for solver.py: runs solve(text), reports time + proxy score."""
import importlib.util, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "official_cases"


def load_solver(path: Path):
    spec = importlib.util.spec_from_file_location("solver_mod", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_input(text):
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("task_id"):
        lines = lines[1:]
    cands = []
    all_tasks = set()
    for ln in lines:
        parts = ln.split("\t")
        if len(parts) < 4:
            continue
        task_str = parts[0]
        task_list = tuple(x.strip() for x in task_str.replace("[", "").replace("]", "").split(",") if x.strip())
        courier = parts[1].strip()
        score = float(parts[2])
        will = float(parts[3])
        cands.append((task_str, list(task_list), courier, score, will, len(cands)))
        for t in task_list:
            all_tasks.add(t)
    return cands, sorted(all_tasks)


def run(solver_path, case, n=2):
    mod = load_solver(solver_path)
    text = case.read_text()
    cands, all_tasks = parse_input(text)
    score_fn = mod._solution_expected_cost
    for i in range(1, n + 1):
        t0 = time.monotonic()
        out = mod.solve(text)
        dt = time.monotonic() - t0
        lut = {(c[0], c[2]): c for c in cands}
        covered = set()
        for task_str, couriers in out:
            for cid in couriers:
                r = lut.get((task_str, cid))
                if r is not None:
                    covered.update(r[1])
                    break
        try:
            proxy = f"{score_fn(out, cands, all_tasks):.2f}"
        except Exception as e:
            proxy = f"err:{e!r}"
        print(f"  [{case.name}] trial={i} time={dt:.2f}s proxy={proxy} groups={len(out)} covered={len(covered)}/{len(all_tasks)}")


def main():
    solver_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "solver.py"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    print(f"solver={solver_path}")
    cases = sorted(c for c in DATA_DIR.glob("*.txt") if c.name != "example_solution.txt")
    if not cases:
        print("no test cases"); return
    for case in cases:
        run(solver_path, case, n=n)


if __name__ == "__main__":
    main()
