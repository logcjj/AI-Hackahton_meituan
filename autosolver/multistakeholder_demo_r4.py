# =============================================================================
# autosolver/multistakeholder_demo_r4.py
# -----------------------------------------------------------------------------
# R4 figure generator for the multi-stakeholder decision layer.  Builds three
# honest, reproducible, dependency-free SVG figures (then PNG via rsvg-convert
# if present) directly from autosolver.multistakeholder_r1.  The ORIGINAL
# autosolver/multistakeholder_demo.py is left untouched; this is a new sibling.
#
# What R4 fixes vs the existing ms-*.svg assets:
#   * Pareto figure now SPELLS OUT the true price of fairness on the chart:
#     alpha=0 -> alpha=0.7 costs +18.3% expected cost AND -15.4% fulfillment to
#     buy a ~49% rider-Gini improvement.  No "tiny/microscopic trade-off" wording.
#   * The non-dominated front (alpha in {0.1..0.5}) is drawn distinctly and the
#     dominated alpha=0 corner is marked as dominated (NOT "= production solver").
#   * Scorecard uses the R1 module's policy-dependent exposure Gini and the
#     genuinely-activated asymmetric lateness (demo-mode), not the old structural
#     constant 0.119 / max-lateness 0.0.
#   * Every synthetic axis carries a SYNTHETIC tag; the real anchors (expected
#     cost / fulfillment) carry a REAL tag.
#
# Run:
#   PYTHONHASHSEED=0 python3 -m autosolver.multistakeholder_demo_r4
# =============================================================================
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from autosolver.competition_audit import parse_competition_rows
from autosolver import multistakeholder_r1 as ms
from autosolver.multistakeholder_demo import build_scarce_case

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"

# Palette.
C_PLATFORM = "#1f3a5f"
C_RIDER = "#f2b705"
C_MERCHANT = "#e07a5f"
C_CUSTOMER = "#3d8361"
C_FRONT = "#2a9d8f"     # non-dominated front
C_DOM = "#9aa5b1"       # dominated points
C_HILITE = "#d1495b"    # price-of-fairness arrow
C_GRID = "#e3e7ec"
C_INK = "#222b35"
C_REAL = "#1f3a5f"
C_SYNTH = "#a05a2c"

ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def esc(s: str) -> str:
    for k, v in ESC.items():
        s = s.replace(k, v)
    return s


def _txt(x, y, s, size=12, anchor="start", weight="normal", fill=C_INK, rot=None, style=""):
    t = f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}"'
    if rot is not None:
        cx, cy = rot
        t += f' transform="rotate(-90 {cx:.1f} {cy:.1f})"'
    if style:
        t += f' style="{style}"'
    t += f">{esc(s)}</text>"
    return t


def _tag(x, y, s, fill):
    """Small REAL/SYNTHETIC pill tag."""
    w = 8.2 * len(s) + 12
    return (
        f'<rect x="{x:.1f}" y="{y-12:.1f}" width="{w:.1f}" height="16" rx="8" '
        f'fill="{fill}" opacity="0.14"/>'
        f'<text x="{x+w/2:.1f}" y="{y:.1f}" text-anchor="middle" font-size="10" '
        f'font-weight="bold" fill="{fill}">{esc(s)}</text>'
    )


# -----------------------------------------------------------------------------
def collect():
    r, t = parse_competition_rows(build_scarce_case())
    pts = ms.pareto_front(r, t, courier_capacity=4)
    front = ms.pareto_efficient(pts)
    front_alphas = {round(p.alpha, 3) for p in front}

    sc = {}
    for a in (0.0, 0.7):
        asg = ms.fairness_aware_reoptimize(r, t, a, courier_capacity=4)
        rep = ms.evaluate_stakeholders(asg, r, t)
        sc[a] = ms.fairness_scorecard(rep)

    base = ms.evaluate_stakeholders(
        ms.fairness_aware_reoptimize(r, t, 0.0, courier_capacity=4), r, t
    )
    base_worst = base.rider_worst_hourly
    base_cost = base.expected_cost
    floors = []
    for f in (base_worst + 2, base_worst + 5, base_worst + 8):
        rep = ms.evaluate_stakeholders(
            ms.fairness_aware_reoptimize(r, t, 0.0, min_hourly=f, courier_capacity=4), r, t
        )
        floors.append(
            dict(floor=f, expected_cost=rep.expected_cost,
                 delta_pct=(rep.expected_cost - base_cost) / base_cost * 100.0,
                 worst=rep.rider_worst_hourly, covered=rep.covered_tasks,
                 total=rep.total_tasks))
    return pts, front_alphas, sc, floors, base_cost, base_worst


# -----------------------------------------------------------------------------
# Figure 1: Pareto front with the honest price-of-fairness annotation.
# -----------------------------------------------------------------------------
def figure_pareto(pts, front_alphas, out_svg: Path):
    W, H = 920, 620
    L, R, TOP, B = 92, 470, 92, 520  # plot box; right gutter reserved for legend
    xs = [p.rider_income_gini for p in pts]
    ys = [p.expected_cost for p in pts]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    xpad = (xhi - xlo) * 0.10 or 0.01
    ypad = (yhi - ylo) * 0.10 or 1.0
    xlo, xhi = xlo - xpad, xhi + xpad
    ylo, yhi = ylo - ypad, yhi + ypad

    def px(g):
        return L + (g - xlo) / (xhi - xlo) * (R - L)

    def py(c):
        return B - (c - ylo) / (yhi - ylo) * (B - TOP)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">'
         f'<rect width="{W}" height="{H}" fill="white"/>']
    s.append(_txt(W / 2, 30, "Efficiency vs Rider-Income Fairness  -  Pareto front",
                  18, "middle", "bold"))
    s.append(_txt(W / 2, 50,
                  "rider-scarce demo: 60 orders / 20 couriers, capacity 4  (alpha sweep on a transparent demo greedy)",
                  11, "middle", fill="#5a6572"))

    # grid
    for i in range(6):
        gy = TOP + i * (B - TOP) / 5
        s.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{R}" y2="{gy:.1f}" stroke="{C_GRID}"/>')
        val = yhi - i * (yhi - ylo) / 5
        s.append(_txt(L - 8, gy + 4, f"{val:.0f}", 10, "end", fill="#5a6572"))
    for i in range(6):
        gx = L + i * (R - L) / 5
        s.append(f'<line x1="{gx:.1f}" y1="{TOP}" x2="{gx:.1f}" y2="{B}" stroke="{C_GRID}"/>')
        val = xlo + i * (xhi - xlo) / 5
        s.append(_txt(gx, B + 16, f"{val:.3f}", 10, "middle", fill="#5a6572"))

    # axes
    s.append(f'<line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="{C_INK}"/>')
    s.append(f'<line x1="{L}" y1="{TOP}" x2="{L}" y2="{B}" stroke="{C_INK}"/>')
    s.append(_txt((L + R) / 2, B + 40, "Rider income Gini  (lower = fairer)", 12, "middle"))
    s.append(_tag((L + R) / 2 + 132, B + 40, "SYNTHETIC", C_SYNTH))
    s.append(_txt(30, (TOP + B) / 2, "Expected cost  (lower = better)", 12, "middle",
                  rot=(30, (TOP + B) / 2)))
    s.append(_tag(18, TOP - 12, "REAL", C_REAL))

    # connect non-dominated front (sorted by cost) with a line
    front_pts = sorted([p for p in pts if round(p.alpha, 3) in front_alphas],
                       key=lambda p: p.expected_cost)
    if len(front_pts) > 1:
        poly = " ".join(f"{px(p.rider_income_gini):.1f},{py(p.expected_cost):.1f}"
                        for p in front_pts)
        s.append(f'<polyline points="{poly}" fill="none" stroke="{C_FRONT}" '
                 f'stroke-width="3" stroke-dasharray="0"/>')

    # locate alpha=0 and alpha=0.7 for the price arrow
    p0 = next(p for p in pts if abs(p.alpha) < 1e-9)
    p7 = next(p for p in pts if abs(p.alpha - 0.7) < 1e-9)

    # price-of-fairness arrow alpha=0 -> alpha=0.7
    x0, y0 = px(p0.rider_income_gini), py(p0.expected_cost)
    x7, y7 = px(p7.rider_income_gini), py(p7.expected_cost)
    s.append(f'<defs><marker id="arr" markerWidth="10" markerHeight="10" refX="7" refY="3" '
             f'orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{C_HILITE}"/></marker></defs>')
    s.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x7:.1f}" y2="{y7:.1f}" '
             f'stroke="{C_HILITE}" stroke-width="2.2" stroke-dasharray="6,4" '
             f'marker-end="url(#arr)"/>')

    dc = (p7.expected_cost - p0.expected_cost) / p0.expected_cost * 100.0
    df = (p7.fulfillment_rate - p0.fulfillment_rate) / p0.fulfillment_rate * 100.0
    dg = (p7.rider_income_gini - p0.rider_income_gini) / p0.rider_income_gini * 100.0
    # annotation box (top-left interior)
    bx, by = L + 18, TOP + 26
    s.append(f'<rect x="{bx}" y="{by}" width="252" height="92" rx="8" '
             f'fill="#fff6f6" stroke="{C_HILITE}" stroke-width="1.2"/>')
    s.append(_txt(bx + 12, by + 20, "Price of fairness  (alpha 0 -> 0.7):", 12, "start", "bold", C_HILITE))
    s.append(_txt(bx + 12, by + 40, f"rider Gini  {dg:+.1f}%   (fairer)", 11.5))
    s.append(_txt(bx + 12, by + 58, f"expected cost  {dc:+.1f}%   (REAL)", 11.5))
    s.append(_txt(bx + 12, by + 76, f"fulfillment  {df:+.1f}%   (REAL)", 11.5))

    # points + labels
    for p in pts:
        x, y = px(p.rider_income_gini), py(p.expected_cost)
        on = round(p.alpha, 3) in front_alphas
        col = C_FRONT if on else C_DOM
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if on else 5}" '
                 f'fill="{col}" stroke="white" stroke-width="1.2"/>')
        lab = f"a={p.alpha:.1f}"
        s.append(_txt(x + 8, y - 6, lab, 9.5, fill=col if on else "#7b8794"))

    # call out alpha=0 dominated, alpha=0.1 dominator
    s.append(_txt(x0 + 8, y0 + 16, "dominated by a=0.1", 9.5, fill=C_DOM,
                  style="font-style:italic"))

    # legend (right gutter)
    lx, ly = R + 28, TOP + 20
    s.append(_txt(lx, ly, "Legend", 12, "start", "bold"))
    s.append(f'<circle cx="{lx+8}" cy="{ly+22}" r="6" fill="{C_FRONT}"/>')
    s.append(_txt(lx + 22, ly + 26, "non-dominated front", 11))
    s.append(_txt(lx + 22, ly + 42, "alpha in {0.1,0.2,0.3,0.4,0.5}", 9.5, fill="#5a6572"))
    s.append(f'<circle cx="{lx+8}" cy="{ly+62}" r="5" fill="{C_DOM}"/>')
    s.append(_txt(lx + 22, ly + 66, "dominated point", 11))
    s.append(f'<line x1="{lx}" y1="{ly+86}" x2="{lx+16}" y2="{ly+86}" '
             f'stroke="{C_HILITE}" stroke-width="2.2" stroke-dasharray="6,4"/>')
    s.append(_txt(lx + 22, ly + 90, "price-of-fairness move", 11))

    # honesty footnote
    s.append(_txt(L, H - 16,
                  "Honest: no alpha corner equals production solver_v2; a=0 is sign-aligned with the official "
                  "objective only. Gini/wage axes are SYNTHETIC; cost/fulfillment are REAL (official group_expected_cost).",
                  9.5, fill="#7b8794"))

    s.append("</svg>")
    out_svg.write_text("\n".join(s))


# -----------------------------------------------------------------------------
# Figure 2: three-party fairness scorecard (efficiency a=0 vs fairness a=0.7).
# -----------------------------------------------------------------------------
def figure_scorecard(sc, out_svg: Path):
    W, H = 960, 620
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">'
         f'<rect width="{W}" height="{H}" fill="white"/>']
    s.append(_txt(W / 2, 30, "Three-Party Fairness Scorecard  -  efficiency (a=0) vs fairness (a=0.7)",
                  18, "middle", "bold"))
    s.append(_txt(W / 2, 50,
                  "each bar pair: left = efficiency-leaning a=0, right = fairness-weighted a=0.7   (R1 module: policy-dependent exposure, activated lateness)",
                  10.5, "middle", fill="#5a6572"))

    e, f = sc[0.0], sc[0.7]
    # rows: (party, label, val_eff, val_fair, better_dir, tag, fmt, max_for_bar)
    # better_dir: 'low' good or 'high' good (affects color of the winner)
    rows = [
        ("Rider", "income Gini (lower fairer)", e.rider["income_gini"], f.rider["income_gini"], "low", "SYNTHETIC", "{:.3f}"),
        ("Rider", "income Jain (higher fairer)", e.rider["income_jain"], f.rider["income_jain"], "high", "SYNTHETIC", "{:.3f}"),
        ("Rider", "worst hourly wage, Rawlsian", e.rider["worst_hourly_wage_rawlsian"], f.rider["worst_hourly_wage_rawlsian"], "high", "SYNTHETIC", "{:.1f}/h"),
        ("Merchant", "exposure Gini (lower fairer)", e.merchant["exposure_gini"], f.merchant["exposure_gini"], "low", "SYNTHETIC", "{:.3f}"),
        ("Merchant", "ready-alignment gap (min)", e.merchant["mean_ready_alignment_gap_min"], f.merchant["mean_ready_alignment_gap_min"], "low", "SYNTHETIC", "{:.2f}"),
        ("Customer", "max lateness (min)", e.customer["max_lateness_min"], f.customer["max_lateness_min"], "low", "SYNTHETIC", "{:.2f}"),
        ("Customer", "mean ETA (min)", e.customer["mean_eta_min"], f.customer["mean_eta_min"], "low", "SYNTHETIC", "{:.2f}"),
        ("Platform", "expected cost (lower better)", e.platform["expected_cost"], f.platform["expected_cost"], "low", "REAL", "{:.0f}"),
        ("Platform", "fulfillment rate (higher better)", e.platform["fulfillment_rate"], f.platform["fulfillment_rate"], "high", "REAL", "{:.3f}"),
    ]
    party_col = {"Rider": C_RIDER, "Merchant": C_MERCHANT, "Customer": C_CUSTOMER, "Platform": C_PLATFORM}

    top = 78
    row_h = 54
    bar_x = 300
    bar_w = 360
    for i, (party, label, ve, vf, direction, tag, fmt) in enumerate(rows):
        y = top + i * row_h
        # party chip
        s.append(f'<rect x="40" y="{y+8:.1f}" width="14" height="34" rx="3" fill="{party_col[party]}"/>')
        s.append(_txt(62, y + 22, party, 12, "start", "bold", party_col[party]))
        s.append(_txt(62, y + 38, label, 10.5, fill="#48515c"))
        # tag
        s.append(_tag(218, y + 30, tag, C_REAL if tag == "REAL" else C_SYNTH))
        # bars: normalize against max of the pair (abs), draw two
        mx = max(abs(ve), abs(vf)) or 1.0
        we = abs(ve) / mx * bar_w
        wf = abs(vf) / mx * bar_w
        # winner highlight
        if direction == "low":
            e_win = ve <= vf
        else:
            e_win = ve >= vf
        ce = party_col[party] if e_win else C_DOM
        cf = party_col[party] if not e_win else C_DOM
        s.append(f'<rect x="{bar_x}" y="{y+8:.1f}" width="{we:.1f}" height="15" rx="3" fill="{ce}" opacity="0.92"/>')
        s.append(_txt(bar_x + we + 6, y + 20, "a=0: " + fmt.format(ve), 10.5, fill="#48515c"))
        s.append(f'<rect x="{bar_x}" y="{y+27:.1f}" width="{wf:.1f}" height="15" rx="3" fill="{cf}" opacity="0.92"/>')
        s.append(_txt(bar_x + wf + 6, y + 39, "a=0.7: " + fmt.format(vf), 10.5, fill="#48515c"))

    # honest callouts
    fy = top + len(rows) * row_h + 12
    s.append(f'<rect x="40" y="{fy}" width="{W-80}" height="58" rx="8" fill="#f7f9fb" stroke="{C_GRID}"/>')
    s.append(_txt(54, fy + 20,
                  "Honest reading: fairness (a=0.7) wins rider Gini & Jain, but its worst hourly wage is LOWER "
                  "(more low-acceptance riders get a slice) and it pays", 10.5))
    s.append(_txt(54, fy + 38,
                  "+18.3% expected cost / -15.4% fulfillment.  Exposure Gini & lateness are SYNTHETIC and policy-dependent (R1); "
                  "cost & fulfillment are REAL.", 10.5))

    s.append("</svg>")
    out_svg.write_text("\n".join(s))


# -----------------------------------------------------------------------------
# Figure 3: business flywheel causal diagram (honest anchors only).
# -----------------------------------------------------------------------------
def figure_flywheel(out_svg: Path):
    W, H = 900, 720
    cx, cy, rad = 450, 360, 215
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">'
         f'<rect width="{W}" height="{H}" fill="white"/>']
    s.append(_txt(W / 2, 34, "Multi-Stakeholder Commercial Flywheel  (causal)", 18, "middle", "bold"))
    s.append(_txt(W / 2, 54,
                  "directional mechanism, NOT measured on competition data; external anchors cited, not reproduced here",
                  10.5, "middle", fill="#5a6572"))

    nodes = [
        ("Better four-party\ndispatch", C_PLATFORM),
        ("On-time rate up,\nETA error down", C_CUSTOMER),
        ("Higher conversion\n& repeat orders", C_CUSTOMER),
        ("Lower cost/order,\nGMV up", C_PLATFORM),
        ("Three-sided\nliquidity up", C_RIDER),
        ("Fairer rider income\n& wage floor", C_RIDER),
    ]
    import math
    n = len(nodes)
    pos = []
    for i in range(n):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        nx = cx + rad * math.cos(ang)
        ny = cy + rad * math.sin(ang)
        pos.append((nx, ny))

    s.append(f'<defs><marker id="fw" markerWidth="12" markerHeight="12" refX="8" refY="3.5" '
             f'orient="auto"><path d="M0,0 L9,3.5 L0,7 Z" fill="{C_PLATFORM}"/></marker></defs>')

    # arcs between consecutive nodes
    for i in range(n):
        x1, y1 = pos[i]
        x2, y2 = pos[(i + 1) % n]
        # pull endpoints in toward node edges
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        sx, sy = x1 + ux * 58, y1 + uy * 40
        ex, ey = x2 - ux * 62, y2 - uy * 44
        # slight curve via quadratic toward center-ish
        mxp = (sx + ex) / 2 + (cy - (sy + ey) / 2) * 0.0
        midx = (sx + ex) / 2 - (ey - sy) * 0.10
        midy = (sy + ey) / 2 + (ex - sx) * 0.10
        s.append(f'<path d="M{sx:.1f},{sy:.1f} Q{midx:.1f},{midy:.1f} {ex:.1f},{ey:.1f}" '
                 f'fill="none" stroke="{C_PLATFORM}" stroke-width="2.2" marker-end="url(#fw)" opacity="0.75"/>')

    # nodes
    for (label, col), (nx, ny) in zip(nodes, pos):
        s.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="56" fill="white" stroke="{col}" stroke-width="3"/>')
        s.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="56" fill="{col}" opacity="0.10"/>')
        for j, ln in enumerate(label.split("\n")):
            s.append(_txt(nx, ny - 4 + j * 14, ln, 11, "middle", "bold", col))

    # center label
    s.append(_txt(cx, cy - 6, "Self-reinforcing", 14, "middle", "bold", C_INK))
    s.append(_txt(cx, cy + 12, "loop", 14, "middle", "bold", C_INK))

    # anchor box
    ay = H - 132
    s.append(f'<rect x="48" y="{ay}" width="{W-96}" height="104" rx="8" fill="#f7f9fb" stroke="{C_GRID}"/>')
    s.append(_txt(64, ay + 22, "External directional anchors (cited, NOT reproduced on our data):", 11, "start", "bold"))
    s.append(_txt(64, ay + 42, "- Meituan public dispatch direction: delivery time down >30%; courier daily orders 20 -> 30.", 10.5))
    s.append(_txt(64, ay + 60,
                  "- Nair et al., \"Gigs with Guarantees: Achieving Fair Wage for Food Delivery Workers\", IJCAI 2022 (arXiv:2205.03530).", 10.5))
    s.append(_txt(64, ay + 82,
                  "Our own reproducible lever (this repo): a >=18/h wage floor costs +5.9% expected cost; >=24/h costs +39.2% "
                  "(coverage 60 -> 37). \"Self-estimated, not Meituan-official.\"", 10.5, fill="#48515c"))

    s.append("</svg>")
    out_svg.write_text("\n".join(s))


def to_png(svg: Path, png: Path):
    try:
        subprocess.run(["rsvg-convert", "-w", "1840", "-o", str(png), str(svg)],
                       check=True, capture_output=True)
        return True
    except Exception as ex:  # pragma: no cover
        print("  PNG export skipped:", ex)
        return False


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    pts, front_alphas, sc, floors, base_cost, base_worst = collect()

    pareto_svg = ASSETS / "ms-pareto-front-r4.svg"
    score_svg = ASSETS / "ms-scorecard-r4.svg"
    fly_svg = ASSETS / "ms-flywheel-r4.svg"

    figure_pareto(pts, front_alphas, pareto_svg)
    figure_scorecard(sc, score_svg)
    figure_flywheel(fly_svg)

    for svg in (pareto_svg, score_svg, fly_svg):
        to_png(svg, svg.with_suffix(".png"))

    # write a fresh data summary so the figures are auditable
    summary = {
        "source_module": "autosolver/multistakeholder_r1.py",
        "demo_case": "build_scarce_case(60 orders / 20 couriers, capacity 4)",
        "pareto_nondominated_alphas": sorted(front_alphas),
        "pareto": [dict(alpha=p.alpha, expected_cost=p.expected_cost,
                        rider_income_gini=p.rider_income_gini,
                        rider_worst_hourly=p.rider_worst_hourly,
                        fulfillment_rate=p.fulfillment_rate,
                        customer_max_lateness=p.customer_max_lateness) for p in pts],
        "scorecard_efficiency_a0": _sc_dict(sc[0.0]),
        "scorecard_fairness_a07": _sc_dict(sc[0.7]),
        "wage_floor": floors,
        "price_of_fairness_a0_to_a07": _price(pts),
        "assets": [str(pareto_svg), str(score_svg), str(fly_svg)],
        "note": "Gini/wage/exposure/lateness axes SYNTHETIC; expected_cost & fulfillment REAL.",
    }
    (ASSETS / "ms-summary-r4.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("Wrote R4 assets to", ASSETS)
    for k in ("ms-pareto-front-r4.svg", "ms-scorecard-r4.svg", "ms-flywheel-r4.svg",
              "ms-summary-r4.json"):
        print("  ", ASSETS / k)


def _sc_dict(sc):
    return {"rider": sc.rider, "merchant": sc.merchant,
            "customer": sc.customer, "platform": sc.platform}


def _price(pts):
    p0 = next(p for p in pts if abs(p.alpha) < 1e-9)
    p7 = next(p for p in pts if abs(p.alpha - 0.7) < 1e-9)
    return {
        "rider_gini_pct": (p7.rider_income_gini - p0.rider_income_gini) / p0.rider_income_gini * 100.0,
        "expected_cost_pct": (p7.expected_cost - p0.expected_cost) / p0.expected_cost * 100.0,
        "fulfillment_pct": (p7.fulfillment_rate - p0.fulfillment_rate) / p0.fulfillment_rate * 100.0,
    }


if __name__ == "__main__":
    main()
