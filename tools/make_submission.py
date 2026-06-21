#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    Path("solver.py"),
    Path("README.md"),
    Path("docs/README.md"),
    Path("docs/PROJECT_STRUCTURE.md"),
    Path("docs/ARCHIVE_INDEX.md"),
    Path("docs/deliverables/产品说明文档.md"),
    Path("docs/deliverables/项目文档.md"),
    Path("docs/deliverables/作品简介.md"),
    Path("docs/assets/architecture-overview.svg"),
    Path("docs/assets/agent-loop.svg"),
    Path("docs/assets/verification-evidence.svg"),
    Path("docs/assets/web-agent-home.png"),
    Path("docs/assets/web-agent-large-run.png"),
    Path("docs/assets/evolution-panel-large.png"),
    Path("docs/assets/evolution-panel-tiny.png"),
    Path("archive/runs/official_submit_20260520_132026_70222083.json"),
]
OPTIONAL_FILES = [
    Path("autosolver_agent/__init__.py"),
    Path("autosolver_agent/system.py"),
    Path("autosolver_agent/evolution.py"),
    Path("web_agent_demo/__init__.py"),
    Path("web_agent_demo/sample_cases.py"),
    Path("web_agent_demo/server.py"),
    Path("web_agent_demo/generated_cases/high_noise_seed601.txt"),
    Path("web_agent_demo/generated_cases/large_seed302.txt"),
    Path("web_agent_demo/generated_cases/low_willingness_seed501.txt"),
    Path("web_agent_demo/generated_cases/medium_seed201.txt"),
    Path("web_agent_demo/generated_cases/medium_seed202.txt"),
    Path("web_agent_demo/generated_cases/medium_seed203.txt"),
    Path("web_agent_demo/generated_cases/scarce_couriers_seed401.txt"),
    Path("web_agent_demo/generated_cases/small_seed100.txt"),
    Path("web_agent_demo/generated_cases/tiny_seed42.txt"),
    Path("tools/__init__.py"),
    Path("tools/agent_trace_demo.py"),
    Path("tools/render_lineage.py"),
    Path("tools/make_submission.py"),
    Path("tests/__init__.py"),
    Path("tests/agent_capabilities/__init__.py"),
    Path("tests/agent_capabilities/_trace_fixture.py"),
    Path("tests/agent_capabilities/test_cap1_exploration.py"),
    Path("tests/agent_capabilities/test_cap2_evaluation.py"),
    Path("tests/agent_capabilities/test_cap3_adaptation.py"),
    Path("tests/agent_capabilities/test_cap4_anytime_and_packaging.py"),
    Path("tests/test_agent_evolution.py"),
    Path("tests/test_web_agent_demo.py"),
]


def sha(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    h.update(path.read_bytes())
    return h.hexdigest()


def run_gate(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def conflict_marker_gate() -> tuple[int, str]:
    bad = []
    for rel in (Path("solver.py"), Path("README.md"), Path("docs/PROJECT_STRUCTURE.md")):
        for lineno, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith(("<<<<<<<", "=======", ">>>>>>>")):
                bad.append(f"{rel}:{lineno}:{line}")
    return (1 if bad else 0), "\n".join(bad)


def run_gates() -> list[tuple[str, int, str]]:
    gates: list[tuple[str, int, str]] = []
    code, output = conflict_marker_gate()
    gates.append(("conflict markers", code, output))
    commands = [
        ("py_compile", [sys.executable, "-m", "py_compile", "solver.py"], 30),
        ("unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], 90),
        ("large bench", [sys.executable, "_bench.py", "solver.py", "1"], 45),
    ]
    for name, cmd, timeout in commands:
        code, output = run_gate(cmd, timeout=timeout)
        gates.append((name, code, output))
    return gates


def copy_file(src_rel: Path, output_dir: Path) -> None:
    src = ROOT / src_rel
    if not src.exists():
        raise FileNotFoundError(src_rel)
    dst = output_dir / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_manifest(output_dir: Path, copied: list[Path], gates: list[tuple[str, int, str]]) -> Path:
    lines = [
        "# AutoSolver Submission Manifest",
        "",
        f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"source_root: {ROOT}",
        "",
        "## Files",
        "",
    ]
    for rel in copied:
        path = ROOT / rel
        lines.append(f"- {rel}")
        lines.append(f"  - bytes: {path.stat().st_size}")
        lines.append(f"  - sha1: {sha(path, 'sha1')}")
        lines.append(f"  - sha256: {sha(path, 'sha256')}")
    lines.extend(["", "## Gates", ""])
    for name, code, output in gates:
        status = "PASS" if code == 0 else "FAIL"
        lines.append(f"### {name}: {status}")
        if output.strip():
            lines.append("```text")
            lines.append(output.strip()[-4000:])
            lines.append("```")
        else:
            lines.append("_No output._")
        lines.append("")
    manifest = output_dir / "MANIFEST.txt"
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a clean local AutoSolver delivery bundle.")
    parser.add_argument("--output", default=f"submission_{dt.datetime.now():%Y%m%d_%H%M%S}")
    parser.add_argument("--skip-gates", action="store_true")
    parser.add_argument("--required-only", action="store_true")
    args = parser.parse_args(argv)
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    gates: list[tuple[str, int, str]] = []
    if not args.skip_gates:
        gates = run_gates()
        failures = [name for name, code, _output in gates if code != 0]
        if failures:
            manifest = write_manifest(output_dir, [], gates)
            print(f"Gate failure(s): {', '.join(failures)}")
            print(f"MANIFEST.txt: {manifest}")
            return 1

    copied: list[Path] = []
    for rel in REQUIRED_FILES:
        copy_file(rel, output_dir)
        copied.append(rel)
    if not args.required_only:
        for rel in OPTIONAL_FILES:
            if (ROOT / rel).exists():
                copy_file(rel, output_dir)
                copied.append(rel)

    manifest = write_manifest(output_dir, copied, gates)
    print(f"Created delivery bundle: {output_dir}")
    print(f"MANIFEST.txt: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
