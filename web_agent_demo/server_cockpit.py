"""
server_cockpit.py  --  即时履约智能调度指挥舱 后端 (iteration-1)

非破坏性：只 import / 复用现有后端（blind_test_orchestrator_v3.run_blind_solve +
cockpit_baseline + cockpit_story），不改任何 solver / orchestrator 字节。

端口 8775（避让 server_v4 的 8774）。

路由：
  GET  /                       -> static/dispatch.html
  GET  /memory                 -> static/memory.html（记忆独立页·历史策略时间线）
  GET  /api/memory             -> 真实进化注册表快照 strategy_registry_r2_snapshot.json（24 条全量）
  GET  /static/<file>          -> 静态资源 (css/js/...)
  GET  /api/cockpit/case       -> 默认 large_seed301 解析 + 合成布局（不跑求解，秒开骨架）
  POST /api/cockpit/stream     -> SSE：run_blind_solve 逐事件推 + event:baseline + event:result(全量story)
  GET  /api/baseline?...       -> 独立刷新纯贪心 vs v4 对比（run_v4_if_missing）

自检：
  python3 web_agent_demo/server_cockpit.py --selfcheck
    启动 -> 对 large_seed301 跑一次 SSE -> 断言 baseline.improvement.strictly_better
    且各面板 payload 非空 -> 打印 [selfcheck] PASS/FAIL
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_agent_demo import blind_test_orchestrator_v3 as orch
from web_agent_demo import cockpit_baseline as cbase
from web_agent_demo import cockpit_story as cstory

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_CASE = ROOT / "data" / "official_cases" / "large_seed301.txt"
# iteration-14：记忆独立页接的真实进化注册表快照（确定性 R2、byte-reproducible、stub 无 live LLM）
REGISTRY_SNAPSHOT = (
    ROOT / "autosolver_agent" / "evolution_state" / "strategy_registry_r2_snapshot.json"
)


def _load_memory_registry() -> dict:
    """读真实进化注册表快照 → 前端 /memory 页直接渲染（不臆造字段，键名照搬）。

    返回 {status, meta, strategies[], overview, honesty}；
    任一字段拿不到则降级，绝不补假数据。
    """
    try:
        raw = json.loads(REGISTRY_SNAPSHOT.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error",
                "error": f"registry snapshot unavailable: {type(exc).__name__}: {exc}"}

    reg = raw.get("registry") or {}
    meta = raw.get("_meta") or {}
    counts = meta.get("counts") or {}

    strategies = []
    for sid, v in reg.items():
        ho = v.get("heldout_mean")
        base = v.get("baseline_heldout_mean")
        delta = None
        if isinstance(ho, (int, float)) and isinstance(base, (int, float)):
            delta = round(base - ho, 4)   # >0 = held-out 改进（成本↓）
        strategies.append({
            "strategy_id": sid,
            "status": v.get("status"),
            "operator": v.get("operator"),
            "generation": v.get("generation"),
            "parent": v.get("parent"),
            "directive": v.get("directive"),
            "target_regime": v.get("target_regime"),
            "heldout_mean": ho,
            "baseline_heldout_mean": base,
            "heldout_delta": delta,
            "train_mean": v.get("train_mean"),
            "last_decision": v.get("last_decision"),
            "last_reason": v.get("last_reason"),
            "safety_passed": v.get("safety_passed"),
            "safety_reason": v.get("safety_reason"),
            "attempts": v.get("attempts"),
            "rank_body": v.get("rank_body"),
            "thought": v.get("thought"),
            "source": v.get("source"),
        })
    # 谱系深度（generation）→ 时间线排序；同 gen 按 id 稳定
    strategies.sort(key=lambda s: (s.get("generation") or 0, s.get("strategy_id") or ""))

    promoted_ids = [s["strategy_id"] for s in strategies if s.get("status") == "promoted"]
    overview = {
        "total_strategies": counts.get("total_strategies", len(strategies)),
        "accepted_or_better": counts.get("accepted_or_better"),
        "promoted": counts.get("promoted"),
        "candidate": counts.get("candidate"),
        "rejected": counts.get("rejected"),
        "byte_identical_clone_pairs": counts.get("byte_identical_clone_pairs"),
        "distinct_rank_bodies": counts.get("distinct_rank_bodies"),
        "strategies_with_code": counts.get("strategies_with_code"),
        "directive_histogram": counts.get("directive_histogram") or {},
        "promoted_ids": promoted_ids,
    }
    return {
        "status": "ok",
        "generated_by": meta.get("generated_by"),
        "note": meta.get("note"),
        "overview": overview,
        "strategies": strategies,
        "honesty": (
            "机制可验证（lesson 真改代码 / 五算子 0 字节克隆 / SHA256 可复现）·"
            "对最终派单成绩零贡献 · stub 无 live LLM · 接真 LLM 一条命令。"
            "held-out 改进量 Δ 为机制内部留出集指标，非派单成绩；不宣称提分。"
        ),
    }

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class ClientGone(Exception):
    pass


def _sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def _read_case_text(case: str | None) -> str:
    if not case or case in {"large_seed301", "default"}:
        return DEFAULT_CASE.read_text(encoding="utf-8")
    p = (ROOT / "data" / "official_cases" / case)
    if p.exists():
        return p.read_text(encoding="utf-8")
    cand = Path(case)
    if cand.exists():
        return cand.read_text(encoding="utf-8")
    return DEFAULT_CASE.read_text(encoding="utf-8")


# 前端 5 场景 id → 压力测试 regime（脱敏样例参数）。只读复用，不改后端算法。
_SCENE_TO_REGIME = {
    "peak": "large",           # 午高峰爆单：大规模高负载
    "rain": "low_willing",     # 雨天低接单意愿
    "scarce": "scarce",        # 骑手稀缺商圈
    "bundle": "bundle_heavy",  # 合单机会密集
    "newshop": "high_noise",   # 新店突发订单：高噪声/不确定
}


def _generate_scene(scene: str, seed: int) -> dict:
    """合成一个全新脱敏样例 + 跑感知重判（真实判出 regime/chips/risk）。"""
    try:
        from tools.generalization_stress_test import REGIME_BANK, generate_case
    except Exception as exc:
        return {"status": "error", "error": f"generator unavailable: {type(exc).__name__}: {exc}",
                "fallback": True}
    regime_key = _SCENE_TO_REGIME.get(scene, "bundle_heavy")
    spec = REGIME_BANK.get(regime_key) or REGIME_BANK.get("medium")
    text = generate_case(spec, seed)
    candidates, all_tasks = cstory.parse_candidates(text)
    perc = orch.size_decoupled_perception(candidates, all_tasks)
    stub_report = {"perception": perc, "solution": [], "solution_summary": {
        "groups": 0, "used_couriers": 0, "covered_tasks": 0,
        "total_tasks": len(all_tasks), "valid": False}}
    return {
        "status": "ok",
        "scene": scene,
        "regime_key": regime_key,
        "is_synthetic_sample": True,   # 脱敏全新随机样例，非记忆/官方数据
        "n_tasks": len(all_tasks),
        "n_rows": len(candidates),
        "perception": perc,
        "regime_verdict": {"regime": perc.get("regime"), "rules": perc.get("rules", []),
                           "is_demo": False, "is_synthetic": True},
        "chips": cstory.synth_chips(stub_report),
        "risk": cstory.synth_risk(stub_report),
        "note": ("脱敏样例：用 generalization_stress_test.generate_case 现场合成全新随机实例"
                 "(seed 可变)，感知模块真实判出 regime；非官方数据、非记忆样例。"),
    }


class Handler(BaseHTTPRequestHandler):
    # ----- response helpers -----
    def _json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self._json({"status": "error", "error": "not found"}, status=404)
            return
        raw = path.read_bytes()
        ct = _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ----- routing -----
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._send_file(STATIC_DIR / "dispatch.html")
                return
            if parsed.path == "/memory":
                # iteration-14：记忆独立页（接真实进化注册表）
                self._send_file(STATIC_DIR / "memory.html")
                return
            if parsed.path == "/api/memory":
                # 直接读 strategy_registry_r2_snapshot.json 真值（24 条全量）
                self._json(_load_memory_registry())
                return
            if parsed.path.startswith("/static/"):
                rel = parsed.path[len("/static/"):]
                # prevent path traversal
                target = (STATIC_DIR / rel).resolve()
                if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
                    self._json({"status": "error", "error": "forbidden"}, status=403)
                    return
                self._send_file(target)
                return
            if parsed.path == "/api/cockpit/case":
                qs = parse_qs(parsed.query)
                case = qs.get("case", ["large_seed301"])[0]
                text = _read_case_text(case)
                # 不跑求解，只给感知 + 合成布局骨架（秒开）。用空 solution 的占位 report。
                candidates, all_tasks = cstory.parse_candidates(text)
                perc = orch.size_decoupled_perception(candidates, all_tasks)
                stub_report = {"perception": perc, "solution": [], "solution_summary": {
                    "groups": 0, "used_couriers": 0, "covered_tasks": 0,
                    "total_tasks": len(all_tasks), "valid": False}}
                layout = cstory.synth_layout(text, stub_report)
                self._json({
                    "status": "ok",
                    "case": case,
                    "perception": perc,
                    "chips": cstory.synth_chips(stub_report),
                    "risk": cstory.synth_risk(stub_report),
                    "regime_verdict": {"regime": perc.get("regime"), "rules": perc.get("rules", []), "is_demo": False},
                    "map_skeleton": layout,
                    "data_boundary": cstory.DATA_BOUNDARY,
                })
                return
            if parsed.path == "/api/generate":
                # iter-2(P1-7)：5 业务场景脱敏样例。用 generalization_stress_test 的
                # generate_case 现场合成一个**全新随机**实例（非记忆样例），跑感知重判，
                # 返回 regime/chips/risk，让前端切换场景时「感知真实判出」。只读、不改后端。
                qs = parse_qs(parsed.query)
                scene = qs.get("regime", ["bundle"])[0]
                seed = int(qs.get("seed", ["20260620"])[0])
                payload = _generate_scene(scene, seed)
                self._json(payload)
                return
            if parsed.path == "/api/baseline":
                qs = parse_qs(parsed.query)
                case = qs.get("case", ["large_seed301"])[0]
                run_v4 = qs.get("run_v4", ["1"])[0] not in {"0", "false", "no"}
                text = _read_case_text(case)
                bl = cbase.compute_baseline(text, run_v4_if_missing=run_v4)
                self._json({"status": "ok", "baseline": bl})
                return
            self._json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            print(f"[cockpit] GET {parsed.path} error: {traceback.format_exc()}", file=sys.stderr)
            self._json({"status": "error", "error": f"{type(exc).__name__}: {exc}"}, status=500)

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
            if parsed.path == "/api/cockpit/stream":
                self._handle_stream(body)
                return
            self._json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            print(f"[cockpit] POST {parsed.path} error: {traceback.format_exc()}", file=sys.stderr)
            try:
                self._json({"status": "error", "error": f"{type(exc).__name__}"}, status=500)
            except Exception:
                pass

    def _handle_stream(self, body: dict) -> None:
        """SSE：盲测逐事件 + baseline + 全量 story。

        客户端可传 {case: "large_seed301"} 或 {text: <TSV>}。
        """
        case = body.get("case", "large_seed301")
        text = body.get("text") or _read_case_text(case)
        memory_enabled = bool(body.get("memory_enabled", True))
        preset = body.get("preset", "balanced")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def observer(event):
            try:
                self.wfile.write(_sse("trace", event))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                raise ClientGone(str(exc))

        try:
            report = orch.run_blind_solve(
                text, case_label=f"cockpit:{case}", memory_enabled=memory_enabled,
                weight_preset=preset, observer=observer,
            )
            # 纯贪心基线（复用 SSE 已产出的 v4 解，不二次跑 v4）
            try:
                baseline = cbase.compute_baseline(
                    text,
                    autosolver_solution=report.get("solution"),
                    autosolver_solve_time_s=report.get("solve_time_s"),
                    autosolver_solver_used=report.get("solver_used", "solver_v4.py"),
                )
            except Exception:
                print(f"[cockpit] baseline error: {traceback.format_exc()}", file=sys.stderr)
                baseline = {"greedy": {}, "autosolver": {}, "improvement": {"strictly_better": False}}
            self.wfile.write(_sse("baseline", {"baseline": baseline}))
            self.wfile.flush()

            story = cstory.build_story(text, report, baseline)
            self.wfile.write(_sse("result", {"story": story}))
            self.wfile.write(_sse("done", {"message": "complete"}))
            self.wfile.flush()
        except ClientGone:
            print("[cockpit] SSE client disconnected; aborting.", file=sys.stderr)
        except Exception:
            print(f"[cockpit] SSE solve error: {traceback.format_exc()}", file=sys.stderr)
            try:
                self.wfile.write(_sse("error", {"message": "internal error (see server log)"}))
                self.wfile.flush()
            except Exception:
                pass
        finally:
            self.close_connection = True

    def log_message(self, fmt, *args):
        print(f"[cockpit] {self.address_string()} - {fmt % args}")


# --------------------------------------------------------------------------- #
# self-check                                                                  #
# --------------------------------------------------------------------------- #
def _selfcheck(host="127.0.0.1", port=8779) -> int:
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{host}:{port}"
    ok = True
    try:
        print(f"[selfcheck] cockpit server booted at {base}")

        # 1) /api/cockpit/case — 骨架秒开
        case = json.loads(urllib.request.urlopen(base + "/api/cockpit/case", timeout=30).read())
        assert case["status"] == "ok", "case endpoint not ok"
        print(f"[selfcheck] /api/cockpit/case regime={case['perception']['regime']} "
              f"chips={len(case['chips'])} map_tasks={len(case['map_skeleton']['tasks'])} "
              f"couriers={len(case['map_skeleton']['couriers'])}")
        if not case["chips"] or not case["map_skeleton"]["tasks"]:
            print("[selfcheck] FAIL: empty skeleton chips/tasks"); ok = False

        # 2) SSE stream — 全量 story + baseline strictly_better
        payload = json.dumps({"case": "large_seed301", "memory_enabled": True}).encode()
        req = urllib.request.Request(base + "/api/cockpit/stream", data=payload,
                                     headers={"Content-Type": "application/json"})
        raw = urllib.request.urlopen(req, timeout=120).read().decode("utf-8")
        trace_types, baseline, story = [], None, None
        for block in raw.split("\n\n"):
            if not block.strip():
                continue
            ev = da = None
            for line in block.splitlines():
                if line.startswith("event: "):
                    ev = line[7:].strip()
                if line.startswith("data: "):
                    da = json.loads(line[6:])
            if ev == "trace" and da:
                trace_types.append(da.get("type"))
            elif ev == "baseline" and da:
                baseline = da["baseline"]
            elif ev == "result" and da:
                story = da["story"]
        print(f"[selfcheck] SSE trace types = {trace_types}")

        # baseline gate (P0)
        if baseline is None:
            print("[selfcheck] FAIL: no baseline event"); ok = False
        else:
            imp = baseline.get("improvement", {})
            g = baseline.get("greedy", {}); a = baseline.get("autosolver", {})
            print(f"[selfcheck] baseline greedy_cost={g.get('expected_cost')} "
                  f"v4_cost={a.get('expected_cost')} cost_pct={imp.get('cost_pct')} "
                  f"strictly_better={imp.get('strictly_better')}")
            if not imp.get("strictly_better"):
                print("[selfcheck] FAIL: baseline not strictly_better (cost basis)"); ok = False
            for fld in ("expected_cost", "covered", "used_couriers"):
                if g.get(fld) is None or a.get(fld) is None:
                    print(f"[selfcheck] FAIL: baseline missing {fld}"); ok = False

        # story panels non-empty (P0)
        if story is None:
            print("[selfcheck] FAIL: no result/story event"); ok = False
        else:
            checks = {
                "chips": story.get("chips"),
                "kpis": story.get("kpis"),
                "risk": story.get("risk"),
                "strategy.steps": (story.get("strategy") or {}).get("steps"),
                "map.tasks": (story.get("map") or {}).get("tasks"),
                "map.couriers": (story.get("map") or {}).get("couriers"),
                "map.accepted_edges": (story.get("map") or {}).get("accepted_edges"),
                "candidates": story.get("candidates"),
                "certificate.headline": (story.get("certificate") or {}).get("headline"),
            }
            for name, v in checks.items():
                empty = (v is None) or (isinstance(v, (list, dict, str)) and len(v) == 0)
                status_s = "OK" if not empty else "EMPTY"
                if empty:
                    print(f"[selfcheck] FAIL: story.{name} empty"); ok = False
                else:
                    n = len(v) if isinstance(v, (list, dict, str)) else v
                    print(f"[selfcheck] story.{name} {status_s} (n={n})")
            kpis = story.get("kpis") or []
            real_kpis = [k for k in kpis if not k.get("is_demo")]
            print(f"[selfcheck] kpis total={len(kpis)} real={len(real_kpis)} "
                  f"bundles={len((story.get('map') or {}).get('bundles', []))}")
            if "perception" not in trace_types or "critic" not in trace_types:
                print("[selfcheck] FAIL: trajectory missing perception/critic"); ok = False

        # 3) static html exists & served
        try:
            html = urllib.request.urlopen(base + "/", timeout=10).read().decode("utf-8")
            if "<html" not in html.lower():
                print("[selfcheck] FAIL: / did not serve html"); ok = False
            else:
                print(f"[selfcheck] / served dispatch.html ({len(html)} bytes)")
        except Exception as exc:
            print(f"[selfcheck] WARN: static html not served ({exc})")

        # 4) iteration-14：/memory 页 + /api/memory 真实注册表（24 条全量）
        try:
            mem_html = urllib.request.urlopen(base + "/memory", timeout=10).read().decode("utf-8")
            if "<html" not in mem_html.lower():
                print("[selfcheck] FAIL: /memory did not serve html"); ok = False
            else:
                print(f"[selfcheck] /memory served memory.html ({len(mem_html)} bytes)")
            mem = json.loads(urllib.request.urlopen(base + "/api/memory", timeout=10).read())
            n_strat = len(mem.get("strategies") or [])
            ov = mem.get("overview") or {}
            promoted_ids = ov.get("promoted_ids") or []
            if mem.get("status") != "ok" or n_strat < 24:
                print(f"[selfcheck] FAIL: /api/memory strategies={n_strat} (<24)"); ok = False
            elif "gen01_M1_003" not in promoted_ids:
                print(f"[selfcheck] FAIL: promoted gen01_M1_003 missing ({promoted_ids})"); ok = False
            else:
                print(f"[selfcheck] /api/memory n_strategies={n_strat} "
                      f"promoted={promoted_ids} accepted={ov.get('accepted_or_better')} "
                      f"clones={ov.get('byte_identical_clone_pairs')}")
        except Exception as exc:
            print(f"[selfcheck] FAIL: /memory not served ({exc})"); ok = False

    except Exception as exc:
        print(f"[selfcheck] EXCEPTION: {exc}")
        print(traceback.format_exc())
        ok = False
    finally:
        server.shutdown()
        server.server_close()
    print(f"[selfcheck] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="即时履约智能调度指挥舱 后端 (iteration-1, 非破坏性).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8775)
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"即时履约智能调度指挥舱 running at http://{args.host}:{args.port}")
    print(f"  static dir: {STATIC_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
