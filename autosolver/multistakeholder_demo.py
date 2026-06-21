# =============================================================================
# autosolver/multistakeholder_demo.py
# -----------------------------------------------------------------------------
# Offline Demo asset generator for the multi-stakeholder decision layer.
# Produces three figures (Pareto front hero, fairness scorecard panel, business
# flywheel causal diagram) and prints the headline numbers used in the docs.
#
# These are OFFLINE Demo assets (not on the 10s judged path).  matplotlib is
# used if available; otherwise the Pareto/scorecard figures fall back to a
# hand-written SVG so the deliverable never blocks on a missing dependency.
#
# Run:
#   python -m autosolver.multistakeholder_demo            # all assets + report data
#   python -m autosolver.multistakeholder_demo --no-real  # skip the real-case load
# =============================================================================
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from autosolver.competition_audit import parse_competition_rows
from autosolver import multistakeholder as ms

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
REAL_CASE = ROOT / "data" / "official_cases" / "large_seed301.txt"

# Palette (Meituan-ish warm yellow + slate, accessible contrast).
C_PLATFORM = "#1f3a5f"
C_RIDER = "#f2b705"
C_MERCHANT = "#e07a5f"
C_CUSTOMER = "#3d8361"
C_FRONT = "#d1495b"
C_GRID = "#dfe3e8"
C_INK = "#222b35"


# -----------------------------------------------------------------------------
# Demo instance builders.
# -----------------------------------------------------------------------------
def build_scarce_case(n_tasks: int = 60, n_couriers: int = 20, seed: int = 7) -> str:
    """A rider-scarce TSV where income leveling is a real lever (couriers reused)."""
    rnd = random.Random(seed)
    lines = ["task_id_list\tcourier_id\ttotal_score\twillingness"]
    for t in range(n_tasks):
        tid = f"T{t:04d}"
        for c in rnd.sample(range(n_couriers), rnd.randint(5, 9)):
            score = rnd.uniform(20, 90)
            will = rnd.uniform(0.15, 0.85)
            lines.append(f"{tid}\tC{c:03d}\t{score:.3f}\t{will:.4f}")
    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------------
# Figure 1: Pareto front hero (efficiency vs rider income Gini).
# -----------------------------------------------------------------------------
def figure_pareto(points: list[ms.ParetoPoint], floor_points: list[dict], out_png: Path, out_svg: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        _svg_pareto_fallback(points, out_svg)
        return out_svg

    xs = [p.rider_income_gini for p in points]
    ys = [p.expected_cost for p in points]
    front = ms.pareto_efficient(points)
    fx = [p.rider_income_gini for p in front]
    fy = [p.expected_cost for p in front]

    fig, ax = plt.subplots(figsize=(8.6, 6.0), dpi=140)
    # All sweep points.
    ax.scatter(xs, ys, s=70, c=C_GRID, edgecolor=C_INK, zorder=2, label="alpha sweep points")
    # Non-dominated front line.
    order = sorted(range(len(front)), key=lambda i: fx[i])
    ax.plot([fx[i] for i in order], [fy[i] for i in order], "-o", color=C_FRONT,
            lw=2.6, ms=9, zorder=4, label="Pareto front (non-dominated)")
    # Annotate the two corners.
    for p in points:
        if abs(p.alpha - 0.0) < 1e-9:
            ax.annotate("alpha=0\npure efficiency\n(= production solver)",
                        (p.rider_income_gini, p.expected_cost),
                        textcoords="offset points", xytext=(12, 6), fontsize=9,
                        color=C_PLATFORM, fontweight="bold")
        if abs(p.alpha - 1.0) < 1e-9:
            ax.annotate("alpha=1\npure equity\n(income leveled)",
                        (p.rider_income_gini, p.expected_cost),
                        textcoords="offset points", xytext=(-10, -34), fontsize=9,
                        color=C_RIDER, fontweight="bold")
    # Wage-floor epsilon-constraint points (constant alpha=0, varying floor).
    if floor_points:
        gx = [d["rider_income_gini"] for d in floor_points]
        gy = [d["expected_cost"] for d in floor_points]
        ax.scatter(gx, gy, s=95, marker="D", c=C_CUSTOMER, edgecolor=C_INK,
                   zorder=5, label="rider wage-floor (epsilon-constraint)")
        for d in floor_points:
            ax.annotate(f"floor {d['floor']:.0f}/hr",
                        (d["rider_income_gini"], d["expected_cost"]),
                        textcoords="offset points", xytext=(6, -12), fontsize=8, color=C_CUSTOMER)

    ax.set_xlabel("Rider income Gini  (lower = fairer)", fontsize=12, color=C_INK)
    ax.set_ylabel("Expected cost  (official objective, lower = better)", fontsize=12, color=C_INK)
    ax.set_title("Efficiency vs Rider-Income Fairness: the four-party Pareto front\n"
                 "(epsilon-constraint sweep; lower-left is better on both axes)",
                 fontsize=13, color=C_INK, fontweight="bold")
    ax.grid(True, color=C_GRID, lw=0.8, zorder=0)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.text(0.01, -0.13, "Synthetic Demo signals (ETA, pay, wage) labelled in multistakeholder.SyntheticConfig.PROVENANCE; "
                         "expected_cost is the REAL official objective.",
            transform=ax.transAxes, fontsize=7.5, color="#7a828c")
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    return out_png


# -----------------------------------------------------------------------------
# Figure 2: Fairness scorecard panel (3 served parties + platform).
# -----------------------------------------------------------------------------
def figure_scorecard(eff_report: ms.StakeholderReport, fair_report: ms.StakeholderReport,
                     out_png: Path, out_svg: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        _svg_scorecard_fallback(eff_report, fair_report, out_svg)
        return out_svg

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.6), dpi=140)
    fig.suptitle("Three-party fairness scorecard:  efficiency-first  vs  fairness-aware",
                 fontsize=14, fontweight="bold", color=C_INK)

    def bars(ax, title, labels, eff_vals, fair_vals, better, color):
        x = np.arange(len(labels))
        w = 0.36
        ax.bar(x - w / 2, eff_vals, w, label="efficiency-first (alpha=0)", color=C_GRID, edgecolor=C_INK)
        ax.bar(x + w / 2, fair_vals, w, label="fairness-aware (alpha=0.7)", color=color, edgecolor=C_INK)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_title(f"{title}   ({better})", fontsize=11, color=C_INK, fontweight="bold")
        ax.grid(True, axis="y", color=C_GRID, lw=0.7)
        ax.legend(fontsize=7.5, loc="best")
        for i, (a, b) in enumerate(zip(eff_vals, fair_vals)):
            ax.text(i - w / 2, a, f"{a:.2f}", ha="center", va="bottom", fontsize=7)
            ax.text(i + w / 2, b, f"{b:.2f}", ha="center", va="bottom", fontsize=7)

    # Rider panel: Gini (lower better), 1-Jain*?, worst hourly (higher better).
    bars(axes[0, 0], "Rider", ["income Gini\n(lower better)", "1 - Jain\n(lower better)", "worst hourly /10\n(higher better)"],
         [eff_report.rider_income_gini, 1 - eff_report.rider_income_jain, eff_report.rider_worst_hourly / 10.0],
         [fair_report.rider_income_gini, 1 - fair_report.rider_income_jain, fair_report.rider_worst_hourly / 10.0],
         "fairness pulls Gini down, worst-hourly up", C_RIDER)

    # Merchant panel.
    bars(axes[0, 1], "Merchant", ["ready-gap min\n(lower better)", "exposure Gini\n(lower better)"],
         [eff_report.merchant_mean_ready_gap, eff_report.merchant_exposure_gini],
         [fair_report.merchant_mean_ready_gap, fair_report.merchant_exposure_gini],
         "out-of-oven alignment + fair exposure", C_MERCHANT)

    # Customer panel.
    bars(axes[1, 0], "Customer", ["max lateness min\n(lower better)", "mean ETA min\n(lower better)"],
         [eff_report.customer_max_lateness, eff_report.customer_mean_eta],
         [fair_report.customer_max_lateness, fair_report.customer_mean_eta],
         "lateness + ETA", C_CUSTOMER)

    # Platform panel.
    bars(axes[1, 1], "Platform", ["expected cost /100\n(lower better)", "fulfillment %\n(higher better)"],
         [eff_report.expected_cost / 100.0, eff_report.fulfillment_rate * 100],
         [fair_report.expected_cost / 100.0, fair_report.fulfillment_rate * 100],
         "the price of fairness", C_PLATFORM)

    fig.text(0.5, 0.005,
             "Gini/Jain/worst-hourly/ready-gap/ETA are SYNTHETIC Demo metrics (see PROVENANCE); "
             "expected_cost & fulfillment derive from the REAL competition fields.",
             ha="center", fontsize=7.5, color="#7a828c")
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    return out_png


# -----------------------------------------------------------------------------
# Figure 3: Business flywheel causal diagram.
# -----------------------------------------------------------------------------
def figure_flywheel(out_png: Path, out_svg: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    except Exception:
        _svg_flywheel_fallback(out_svg)
        return out_svg

    nodes = [
        ("Better four-party\ndispatch", 0.50, 0.86, C_PLATFORM),
        ("On-time rate up\nETA-error down", 0.84, 0.62, C_CUSTOMER),
        ("Conversion &\nrepeat orders up", 0.72, 0.22, C_CUSTOMER),
        ("Unit cost down\nGMV up", 0.28, 0.22, C_MERCHANT),
        ("Three-sided\nliquidity up", 0.16, 0.62, C_RIDER),
    ]
    fig, ax = plt.subplots(figsize=(8.8, 7.4), dpi=140)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("The AutoSolver business flywheel\nfair, multi-party dispatch compounds into GMV",
                 fontsize=14, fontweight="bold", color=C_INK)

    pos = []
    for label, x, y, color in nodes:
        box = FancyBboxPatch((x - 0.13, y - 0.06), 0.26, 0.12,
                             boxstyle="round,pad=0.02,rounding_size=0.02",
                             linewidth=2, edgecolor=color, facecolor="white", zorder=3)
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center", fontsize=10.5,
                color=C_INK, fontweight="bold", zorder=4)
        pos.append((x, y))

    for i in range(len(pos)):
        x0, y0 = pos[i]
        x1, y1 = pos[(i + 1) % len(pos)]
        arr = FancyArrowPatch((x0, y0), (x1, y1),
                              connectionstyle="arc3,rad=0.22",
                              arrowstyle="-|>", mutation_scale=22,
                              lw=2.2, color="#9aa3ad", zorder=2,
                              shrinkA=26, shrinkB=26)
        ax.add_patch(arr)

    ax.text(0.5, 0.5, "FLYWHEEL", ha="center", va="center",
            fontsize=15, color="#c7cdd4", fontweight="bold", zorder=1)
    ax.text(0.5, 0.02,
            "Real anchors: Meituan four-party intelligent dispatch -> delivery time down >30%, "
            "rider 20->30 orders/day, ~$230M/yr saved;  Work4Food: fairness-as-constraint can cut cost up to 51.9%.",
            ha="center", fontsize=7.8, color="#7a828c", wrap=True)
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    return out_png


# -----------------------------------------------------------------------------
# SVG fallbacks (used only if matplotlib is unavailable).
# -----------------------------------------------------------------------------
def _svg_header(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Helvetica,Arial,sans-serif">'
            f'<rect width="{w}" height="{h}" fill="white"/>'
            f'<text x="{w/2}" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="{C_INK}">{title}</text>')


def _svg_pareto_fallback(points, out_svg):
    w, h = 820, 560
    pad = 70
    xs = [p.rider_income_gini for p in points]
    ys = [p.expected_cost for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    def px(x):
        return pad + (x - xmin) / ((xmax - xmin) or 1) * (w - 2 * pad)

    def py(y):
        return (h - pad) - (y - ymin) / ((ymax - ymin) or 1) * (h - 2 * pad)

    parts = [_svg_header(w, h, "Efficiency vs Rider-Income Gini  Pareto front")]
    parts.append(f'<line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" stroke="{C_INK}"/>')
    parts.append(f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h-pad}" stroke="{C_INK}"/>')
    pts_path = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in sorted(zip(xs, ys)))
    parts.append(f'<polyline points="{pts_path}" fill="none" stroke="{C_FRONT}" stroke-width="2.5"/>')
    for p in points:
        cx, cy = px(p.rider_income_gini), py(p.expected_cost)
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{C_PLATFORM}"/>')
        parts.append(f'<text x="{cx+8:.1f}" y="{cy:.1f}" font-size="9" fill="{C_INK}">a={p.alpha:.1f}</text>')
    parts.append(f'<text x="{w/2}" y="{h-20}" text-anchor="middle" font-size="12" fill="{C_INK}">Rider income Gini (lower fairer)</text>')
    parts.append(f'<text x="20" y="{h/2}" font-size="12" fill="{C_INK}" transform="rotate(-90 20 {h/2})">Expected cost (lower better)</text>')
    parts.append("</svg>")
    out_svg.write_text("\n".join(parts), encoding="utf-8")


def _svg_scorecard_fallback(eff, fair, out_svg):
    w, h = 820, 420
    parts = [_svg_header(w, h, "Fairness scorecard: efficiency-first vs fairness-aware")]
    rows = [
        ("rider income Gini (lower better)", eff.rider_income_gini, fair.rider_income_gini),
        ("rider worst hourly (higher better)", eff.rider_worst_hourly, fair.rider_worst_hourly),
        ("merchant ready-gap min (lower better)", eff.merchant_mean_ready_gap, fair.merchant_mean_ready_gap),
        ("customer max lateness (lower better)", eff.customer_max_lateness, fair.customer_max_lateness),
        ("platform expected cost (lower better)", eff.expected_cost, fair.expected_cost),
        ("platform fulfillment (higher better)", eff.fulfillment_rate, fair.fulfillment_rate),
    ]
    y = 70
    for name, a, b in rows:
        parts.append(f'<text x="40" y="{y}" font-size="12" fill="{C_INK}">{name}</text>')
        parts.append(f'<text x="500" y="{y}" font-size="12" fill="#888">eff={a:.3f}</text>')
        parts.append(f'<text x="650" y="{y}" font-size="12" fill="{C_FRONT}">fair={b:.3f}</text>')
        y += 48
    parts.append("</svg>")
    out_svg.write_text("\n".join(parts), encoding="utf-8")


def _svg_flywheel_fallback(out_svg):
    w, h = 760, 680
    cx, cy, r = w / 2, h / 2 + 10, 230
    labels = ["Better four-party dispatch", "On-time up / ETA-error down",
              "Conversion & repeat up", "Unit cost down / GMV up", "Three-sided liquidity up"]
    parts = [_svg_header(w, h, "AutoSolver business flywheel")]
    pts = []
    for i, lab in enumerate(labels):
        ang = -math.pi / 2 + i * 2 * math.pi / len(labels)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        pts.append((x, y))
        parts.append(f'<rect x="{x-90:.0f}" y="{y-22:.0f}" width="180" height="44" rx="10" fill="white" stroke="{C_PLATFORM}" stroke-width="2"/>')
        parts.append(f'<text x="{x:.0f}" y="{y+4:.0f}" text-anchor="middle" font-size="11" fill="{C_INK}">{lab}</text>')
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        parts.append(f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="#9aa3ad" stroke-width="2"/>')
    parts.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="16" fill="#c7cdd4" font-weight="bold">FLYWHEEL</text>')
    parts.append("</svg>")
    out_svg.write_text("\n".join(parts), encoding="utf-8")


# -----------------------------------------------------------------------------
# Driver.
# -----------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-real", action="store_true", help="skip loading the real official case")
    parser.add_argument("--capacity", type=int, default=4)
    args = parser.parse_args(argv)

    ASSETS.mkdir(parents=True, exist_ok=True)
    summary: dict = {"provenance": [list(t) for t in ms.SyntheticConfig.PROVENANCE]}

    # ---- Scarce Demo case: Pareto front + scorecard ----
    text = build_scarce_case()
    rows, tasks = parse_competition_rows(text)
    points = ms.pareto_front(rows, tasks, courier_capacity=args.capacity)
    front = ms.pareto_efficient(points)

    # Wage-floor epsilon-constraint points (alpha=0, varying floor).
    base = points[0]
    floor_points = []
    for floor in (base.rider_worst_hourly + 2, base.rider_worst_hourly + 5, base.rider_worst_hourly + 8):
        asg = ms.fairness_aware_reoptimize(rows, tasks, alpha=0.0, min_hourly=floor, courier_capacity=args.capacity)
        rep = ms.evaluate_stakeholders(asg, rows, tasks)
        floor_points.append({
            "floor": floor,
            "expected_cost": rep.expected_cost,
            "rider_income_gini": rep.rider_income_gini,
            "rider_worst_hourly": rep.rider_worst_hourly,
            "covered": rep.covered_tasks,
            "total": rep.total_tasks,
            "cost_delta_pct": (rep.expected_cost - base.expected_cost) / base.expected_cost * 100,
        })

    f1 = figure_pareto(points, floor_points, ASSETS / "ms-pareto-front.png", ASSETS / "ms-pareto-front.svg")

    eff_rep = points[0].report                                   # alpha=0
    # closest to alpha=0.7
    fair_rep = min(points, key=lambda p: abs(p.alpha - 0.7)).report
    f2 = figure_scorecard(eff_rep, fair_rep, ASSETS / "ms-scorecard.png", ASSETS / "ms-scorecard.svg")
    f3 = figure_flywheel(ASSETS / "ms-flywheel.png", ASSETS / "ms-flywheel.svg")

    summary["pareto"] = [
        {"alpha": p.alpha, "expected_cost": p.expected_cost, "rider_income_gini": p.rider_income_gini,
         "rider_worst_hourly": p.rider_worst_hourly, "fulfillment_rate": p.fulfillment_rate,
         "customer_max_lateness": p.customer_max_lateness}
        for p in points
    ]
    summary["pareto_nondominated"] = len(front)
    summary["wage_floor"] = floor_points
    summary["scorecard_efficiency"] = ms.fairness_scorecard(eff_rep).__dict__
    summary["scorecard_fairness"] = ms.fairness_scorecard(fair_rep).__dict__
    summary["assets"] = [str(f1), str(f2), str(f3)]

    # ---- Real official case validation (platform utility == official cost) ----
    if not args.no_real and REAL_CASE.exists():
        try:
            import solver_v2  # type: ignore
            real_text = REAL_CASE.read_text(encoding="utf-8")
            sol = solver_v2.solve(real_text)
            from autosolver.competition_audit import result_metrics
            rrows, rtasks = parse_competition_rows(real_text)
            m = result_metrics(sol, rrows, rtasks)
            rrep, rsc = ms.analyze_solution(real_text, sol)
            summary["real_case"] = {
                "official_expected_cost": m["expected_cost"],
                "ms_expected_cost": rrep.expected_cost,
                "match": abs(m["expected_cost"] - rrep.expected_cost) < 1e-6,
                "Uc": rrep.Uc, "Ur": rrep.Ur, "Um": rrep.Um, "Up": rrep.Up, "U": rrep.U,
                "fulfillment_rate": rrep.fulfillment_rate,
                "scorecard": rsc.__dict__,
            }
        except Exception as e:  # pragma: no cover
            summary["real_case_error"] = repr(e)

    out_json = ASSETS / "ms-summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("provenance",)}, ensure_ascii=False, indent=2)[:4000])
    print("\nassets written to:", ASSETS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
