"""
server_v2.py  --  FINALS "judge blind-test" enhanced demo (non-destructive).

Keeps the original web_agent_demo/server.py untouched and runnable. This is a
SEPARATE server (default port 8770) whose center-piece is:
  judges paste / generate a BRAND-NEW case -> the Agent solves it live -> the
  decision trajectory (Perception / Planner / Trials / Critic / Controller /
  Memory) is shown with a size-decoupled regime call, an optimality-gap
  certificate, a four-party scorecard + Pareto front, and the REAL promoted
  self-evolved strategy (gen01_M1_003).

Run:
    python3 web_agent_demo/server_v2.py
    # then open http://127.0.0.1:8770

Self-check (headless, no browser):
    python3 web_agent_demo/server_v2.py --selfcheck
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

from web_agent_demo import blind_test_orchestrator as orch


# --------------------------------------------------------------------------- #
# SSE helper                                                                   #
# --------------------------------------------------------------------------- #
def _sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


# --------------------------------------------------------------------------- #
# Page                                                                         #
# --------------------------------------------------------------------------- #
def render_index() -> str:
    return r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AutoSolver · 现场盲测 Live Blind-Test</title>
<style>
  :root{
    --ink:#16211e;--muted:#67746f;--leaf:#236a43;--leaf2:#123f2a;--gold:#d8b14a;
    --clay:#c9714a;--blue:#2e5f73;--paper:rgba(255,253,246,.86);
    --card:rgba(255,255,255,.74);--line:rgba(22,33,30,.14);
    --shadow:0 24px 80px rgba(31,46,38,.16);
    --mono:"SFMono-Regular","Cascadia Code",Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;color:var(--ink);font-family:"Avenir Next","PingFang SC","Hiragino Sans GB",sans-serif;
    background:
      radial-gradient(circle at 7% 10%,rgba(216,177,74,.30),transparent 22rem),
      radial-gradient(circle at 92% 4%,rgba(46,95,115,.22),transparent 26rem),
      radial-gradient(circle at 82% 94%,rgba(35,106,67,.20),transparent 24rem),
      linear-gradient(135deg,#f8efd9 0%,#eef0df 44%,#d9e8df 100%);
    min-height:100vh}
  main{width:min(1440px,calc(100vw - 32px));margin:0 auto;padding:24px 0 56px}
  .panel{background:var(--paper);border:1px solid var(--line);border-radius:24px;
    box-shadow:var(--shadow);backdrop-filter:blur(16px)}
  .hero{padding:26px 28px;margin-bottom:16px;position:relative;overflow:hidden}
  .eyebrow{color:var(--leaf);font-weight:900;letter-spacing:.16em;text-transform:uppercase;font-size:12px}
  h1{font-size:clamp(30px,4vw,52px);line-height:.98;margin:10px 0 12px;letter-spacing:-.05em}
  h2{margin:0 0 8px;font-size:20px;letter-spacing:-.03em}
  h3{margin:14px 0 8px;font-size:15px;letter-spacing:-.02em}
  .lead{color:var(--muted);font-size:16px;line-height:1.7;max-width:980px}
  .grid2{display:grid;grid-template-columns:1.05fr .95fr;gap:16px;align-items:start}
  .controls{padding:20px;display:grid;gap:12px}
  label{color:var(--muted);font-size:13px;font-weight:800;display:grid;gap:6px}
  select,input,textarea,button{width:100%;border:1px solid var(--line);border-radius:14px;
    padding:12px 13px;font-size:15px;background:rgba(255,255,255,.9);color:var(--ink)}
  textarea{font-family:var(--mono);font-size:12px;min-height:128px;resize:vertical;white-space:pre}
  button{cursor:pointer;border:none;color:#fff;font-weight:900;
    background:linear-gradient(135deg,var(--leaf),var(--leaf2));box-shadow:0 12px 28px rgba(35,106,67,.24)}
  button.sec{background:linear-gradient(135deg,var(--blue),#183247)}
  button.gold{background:linear-gradient(135deg,var(--gold),#b8922e);color:#241c00}
  button:disabled{cursor:wait;opacity:.6}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
  .switch{display:flex;align-items:center;gap:10px;padding:11px 13px;border:1px solid var(--line);
    border-radius:14px;background:rgba(255,255,255,.7);font-weight:900;font-size:13px;cursor:pointer;user-select:none}
  .switch .dot{width:34px;height:20px;border-radius:999px;background:rgba(22,33,30,.18);position:relative;transition:.2s}
  .switch .dot:after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;
    background:#fff;transition:.2s}
  .switch.off .dot{background:var(--clay)}
  .switch.off .dot:after{transform:translateX(0)}
  .switch.on .dot{background:var(--leaf)}
  .switch.on .dot:after{transform:translateX(14px)}
  .pill{display:inline-flex;align-items:center;gap:8px;width:fit-content;border-radius:999px;
    padding:7px 11px;background:rgba(255,255,255,.62);color:var(--muted);font-weight:800;font-size:12px}
  .pill:before{content:"";width:8px;height:8px;border-radius:50%;background:var(--gold)}
  .pill.run:before{background:var(--leaf);animation:pulse 1.1s infinite}
  @keyframes pulse{50%{transform:scale(1.4);opacity:.5}}
  .traj{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
  .stage{padding:14px;border-radius:18px;background:var(--card);border:1px solid var(--line);min-height:118px}
  .stage.active{border-color:rgba(35,106,67,.6);background:rgba(239,248,228,.85)}
  .stage.done{border-color:rgba(216,177,74,.5)}
  .stage .tag{display:inline-block;border-radius:999px;padding:3px 8px;margin-bottom:8px;font-size:11px;
    font-weight:900;letter-spacing:.05em;text-transform:uppercase;background:rgba(46,95,115,.12);color:var(--blue)}
  .stage b{display:block;margin-bottom:4px}
  .stage .body{color:var(--muted);font-size:13px;line-height:1.5}
  .stream{margin-top:16px;max-height:340px;overflow:auto;display:grid;gap:8px}
  .ev{display:grid;grid-template-columns:64px 1fr;gap:10px;padding:11px 12px;border-radius:14px;
    background:rgba(255,255,255,.72);border:1px solid var(--line)}
  .ev .t{font-family:var(--mono);font-size:11px;color:var(--muted)}
  .ev .ty{display:inline-block;border-radius:999px;padding:2px 7px;margin-bottom:4px;font-size:10px;
    font-weight:900;text-transform:uppercase;background:rgba(35,106,67,.12);color:var(--leaf)}
  .ev .msg{font-size:13px;line-height:1.5}
  .kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px;margin-top:6px}
  .kv .k{color:var(--muted);font-weight:800}
  .kv .v{font-family:var(--mono)}
  .cert{padding:16px;border-radius:18px;border:1px solid var(--line);
    background:rgba(255,250,235,.8);margin-top:14px}
  .cert b{color:var(--leaf2)}
  .scorecards{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:12px}
  .sc{padding:13px;border-radius:16px;background:rgba(255,255,255,.72);border:1px solid var(--line)}
  .sc .h{font-weight:900;margin-bottom:7px;font-size:13px}
  .sc .l{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:2px 0}
  .sc .l span:last-child{font-family:var(--mono);color:var(--ink)}
  .presetrow{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}
  .preset{border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.66);
    color:var(--muted);font-size:12px;font-weight:900;cursor:pointer}
  .preset.active{color:#fff;background:var(--blue);border-color:transparent}
  .pareto{margin-top:12px}
  svg{width:100%;height:auto;display:block}
  .evo{padding:16px;border-radius:18px;background:rgba(238,245,235,.8);border:1px solid var(--line);margin-top:12px}
  .evo .badge{display:inline-flex;border-radius:999px;padding:5px 10px;background:rgba(35,106,67,.14);
    color:var(--leaf);font-weight:900;font-size:12px;margin-bottom:8px}
  pre{margin:8px 0 0;padding:13px;border-radius:13px;background:#13241c;color:#d6e8d8;
    font-family:var(--mono);font-size:11.5px;line-height:1.55;overflow:auto;max-height:300px}
  .muted{color:var(--muted)}
  .empty{min-height:80px;display:grid;place-items:center;color:var(--muted);border:1px dashed var(--line);
    border-radius:14px;background:rgba(255,255,255,.4);text-align:center;line-height:1.6;font-size:13px;padding:14px}
  .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:12px}
  .metric{padding:12px;border-radius:14px;background:rgba(255,255,255,.7);border:1px solid var(--line)}
  .metric strong{display:block;font-size:19px;letter-spacing:-.03em}
  .metric span{color:var(--muted);font-size:10.5px;font-weight:900;text-transform:uppercase}
  @media(max-width:1080px){.grid2,.traj,.scorecards{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<main>
  <section class="hero panel">
    <div class="eyebrow">Live Blind-Test · 现场盲测</div>
    <h1>评委现场盲测全新 case</h1>
    <p class="lead">点「生成评委没见过的 case」或粘贴自定义 TSV，提交后对该<b>全新数据现场跑 Agent</b>。
    可<b>关闭 Memory/缓存</b>证明关掉后照样跑（求解链路 = solver_v3 实时搜索，solver_v2 去硬编码 + 已验证进化候选 argmin，绝不命中原始 solver.py 的 seed 硬编码）。
    决策轨迹用<b>尺寸解耦特征</b>（密度比 d=骑手/任务、willingness 分位数）判 regime，Critic 给<b>最优性 gap 证书</b>，
    并展示四方共赢面板与<b>真·自进化</b> promoted=gen01_M1_003。</p>
    <div class="metrics">
      <div class="metric"><strong id="m-regime">—</strong><span>Regime (尺寸解耦)</span></div>
      <div class="metric"><strong id="m-gap">—</strong><span>Optimality gap</span></div>
      <div class="metric"><strong id="m-cov">—</strong><span>Coverage</span></div>
      <div class="metric"><strong id="m-time">—</strong><span>Solve time</span></div>
    </div>
  </section>

  <div class="grid2">
    <section class="controls panel">
      <h2>① 现场盲测入口</h2>
      <div class="row">
        <label>Regime / 规模<select id="regime"></select></label>
        <label>种子(留空=实时随机)<input id="seed" type="text" placeholder="auto >=10000"></label>
      </div>
      <button id="gen" class="gold">⚡ 生成评委没见过的随机 case</button>
      <label>自定义输入（粘 TSV：task_id_list ⇥ courier_id ⇥ total_score ⇥ willingness）
        <textarea id="tsv" placeholder="task_id_list&#9;courier_id&#9;total_score&#9;willingness&#10;T0001&#9;C001&#9;42.5&#9;0.61&#10;..."></textarea>
      </label>
      <div class="row">
        <div class="switch on" id="memsw"><span class="dot"></span><span id="memlbl">Memory/缓存：开</span></div>
        <button id="run">▶ 现场对全新数据跑 Agent</button>
      </div>
      <div id="status" class="pill">等待盲测启动</div>
      <div id="caseinfo" class="muted" style="font-size:12px;line-height:1.5"></div>
    </section>

    <section class="panel" style="padding:20px">
      <h2>② 决策轨迹 Decision Trajectory</h2>
      <div class="traj" id="traj"></div>
      <div class="stream" id="stream"><div class="empty">启动后这里实时显示 Perception → Planner → Trials → Critic → Controller → Memory。</div></div>
    </section>
  </div>

  <section class="panel" style="padding:20px;margin-top:16px">
    <h2>③ Critic · 最优性证书</h2>
    <div id="cert"><div class="empty">求解后显示『本解 provably 在某个证明下界的 X% 以内』的 gap 证书 headline（调 autosolver.optimality_bound）。</div></div>
  </section>

  <section class="panel" style="padding:20px;margin-top:16px">
    <h2>④ 多方共赢面板 Four-Party Scorecard + Pareto</h2>
    <div class="presetrow" id="presets"></div>
    <div class="scorecards" id="scorecards"><div class="empty" style="grid-column:1/-1">求解后显示骑手/商家/顾客/平台四方 scorecard。</div></div>
    <div class="pareto" id="pareto"></div>
  </section>

  <section class="panel" style="padding:20px;margin-top:16px">
    <h2>⑤ 真·自进化面板 Self-Evolution (REAL)</h2>
    <div id="evo"><div class="empty">从 strategy_registry.json 读出真实 promoted 策略 (thought + code)。</div></div>
  </section>
</main>

<script>
const $=id=>document.getElementById(id);
const safe=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let memOn=true, preset='balanced', lastSolution=null, lastText=null, currentRun=null;
const STAGES=[
  ['perception','Perception','尺寸解耦特征判 regime'],
  ['planner','Planner / Trials','选策略链 + 实时求解'],
  ['critic','Critic','最优性 gap 证书'],
  ['controller','Controller','择优 / 预算守护'],
  ['memory','Memory','输出当前最优解'],
  ['final','Done','盲测完成'],
];
function paintTraj(active){
  $('traj').innerHTML=STAGES.map(([id,t,d])=>{
    const cls=id===active?'active':'';
    return `<div class="stage ${cls}" data-st="${id}"><span class="tag">${t}</span><b>${safe(d)}</b><span class="body" id="st-${id}">—</span></div>`;
  }).join('');
}
function setStage(id,text){
  document.querySelectorAll('.stage').forEach(n=>{
    if(n.dataset.st===id){n.classList.add('active','done');}
  });
  const el=$('st-'+id); if(el) el.textContent=text;
}
let evCount=0;
function addEv(ty,msg){
  evCount++;
  if(evCount===1) $('stream').innerHTML='';
  const now=(performance.now()/1000).toFixed(2);
  const div=document.createElement('div'); div.className='ev';
  div.innerHTML=`<div class="t">#${evCount}</div><div><span class="ty">${safe(ty)}</span><div class="msg">${safe(msg)}</div></div>`;
  $('stream').appendChild(div); $('stream').scrollTop=$('stream').scrollHeight;
}
async function loadRegimes(){
  const r=await(await fetch('/api/regimes')).json();
  $('regime').innerHTML=r.regimes.map(x=>`<option value="${safe(x.id)}">${safe(x.label)}</option>`).join('');
  $('presets').innerHTML=r.presets.map((p,i)=>`<div class="preset ${i===0?'active':''}" data-p="${safe(p)}">${safe(p)}</div>`).join('');
  document.querySelectorAll('.preset').forEach(n=>n.addEventListener('click',()=>{
    preset=n.dataset.p;
    document.querySelectorAll('.preset').forEach(m=>m.classList.toggle('active',m.dataset.p===preset));
    if(lastSolution) refreshStakeholders();
  }));
  loadEvolution();
}
async function loadEvolution(){
  const c=await(await fetch('/api/evolution')).json();
  const card=c.card;
  if(!card||!card.available){$('evo').innerHTML='<div class="empty">registry 未找到 promoted 策略。</div>';return;}
  $('evo').innerHTML=`
    <div class="badge">promoted = ${safe(card.strategy_id)} · status ${safe(card.status)} · operator ${safe(card.operator)} · gen ${safe(card.generation)}</div>
    <div class="kv">
      <div class="k">target regime</div><div class="v">${safe(card.target_regime)}</div>
      <div class="k">held-out mean</div><div class="v">${safe(card.heldout_mean)} (baseline ${safe(card.baseline_heldout_mean)})</div>
      <div class="k">改进量 Δ</div><div class="v">${safe(card.improvement_vs_baseline)} (越大越好)</div>
      <div class="k">safety gate</div><div class="v">${card.safety_passed?'通过':'未过'} · ${safe(card.safety_reason)}</div>
      <div class="k">last decision</div><div class="v">${safe(card.last_decision)} — ${safe(card.last_reason)}</div>
    </div>
    <h3>Thought（LLM 进化思路，真实记录）</h3>
    <div class="muted" style="font-size:13px;line-height:1.6">${safe(card.thought)}</div>
    <h3>Promoted code（${safe(card.file)}）</h3>
    <pre>${safe(card.code)}</pre>`;
}
$('gen').addEventListener('click',async()=>{
  $('gen').disabled=true; $('caseinfo').textContent='生成中…';
  try{
    const seed=$('seed').value.trim();
    const u='/api/generate?regime='+encodeURIComponent($('regime').value)+(seed?('&seed='+encodeURIComponent(seed)):'');
    const r=await(await fetch(u)).json();
    if(r.status!=='ok'){throw new Error(r.error||'gen failed');}
    $('tsv').value=r.case.text;
    $('caseinfo').innerHTML=`<b>已生成：</b>${safe(r.case.note)}<br>路径 ${safe(r.case.path)} · ${safe(r.case.rows)} 行 · ${safe(r.case.tasks)}任务/${safe(r.case.couriers)}骑手`;
  }catch(e){$('caseinfo').textContent='生成失败：'+e.message;}
  $('gen').disabled=false;
});
$('memsw').addEventListener('click',()=>{
  memOn=!memOn;
  $('memsw').classList.toggle('on',memOn); $('memsw').classList.toggle('off',!memOn);
  $('memlbl').textContent=memOn?'Memory/缓存：开':'Memory/缓存：关（强制实时搜索）';
});
function paintCert(c){
  if(!c){$('cert').innerHTML='<div class="empty">无证书</div>';return;}
  const opt=c.certified_optimal?' <b>[CERTIFIED OPTIMAL]</b>':'';
  $('cert').innerHTML=`<div class="cert"><b>Critic 证书：</b>${safe(c.headline)}${opt}
    <div class="kv">
      <div class="k">gap</div><div class="v">${c.gap_pct!=null?(Number(c.gap_pct).toFixed(3)+'%'):'—'}</div>
      <div class="k">lower bound (proven)</div><div class="v">${c.lower_bound!=null?Number(c.lower_bound).toFixed(2):'—'}</div>
      <div class="k">our upper bound</div><div class="v">${c.upper_bound!=null?Number(c.upper_bound).toFixed(2):'—'}</div>
      <div class="k">binding bound</div><div class="v">${safe(c.binding_bound)}</div>
    </div></div>`;
}
function scBlock(title,obj){
  const lines=Object.entries(obj).map(([k,v])=>`<div class="l"><span>${safe(k)}</span><span>${typeof v==='number'?(Number.isInteger(v)?v:Number(v).toFixed(3)):safe(v)}</span></div>`).join('');
  return `<div class="sc"><div class="h">${safe(title)}</div>${lines}</div>`;
}
function paintStakeholders(s){
  if(!s||s.error){$('scorecards').innerHTML='<div class="empty" style="grid-column:1/-1">'+(s&&s.error?safe(s.error):'无数据')+'</div>';$('pareto').innerHTML='';return;}
  const sc=s.scorecard;
  $('scorecards').innerHTML=
    scBlock('🛵 骑手 Rider',sc.rider)+scBlock('🏪 商家 Merchant',sc.merchant)+
    scBlock('🙋 顾客 Customer',sc.customer)+scBlock('🏢 平台 Platform',sc.platform);
  paintPareto(s.pareto_front);
}
function paintPareto(front){
  if(!front||!front.length){$('pareto').innerHTML='';return;}
  const W=560,H=200,pad=44;
  const xs=front.map(p=>p.expected_cost), ys=front.map(p=>p.rider_income_gini);
  const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  const sx=v=>pad+(xmax===xmin?0.5:(v-xmin)/(xmax-xmin))*(W-2*pad);
  const sy=v=>H-pad-(ymax===ymin?0.5:(v-ymin)/(ymax-ymin))*(H-2*pad);
  const pts=front.map(p=>`${sx(p.expected_cost).toFixed(1)},${sy(p.rider_income_gini).toFixed(1)}`).join(' ');
  const dots=front.map(p=>{
    const eff=p.pareto_efficient;
    return `<circle cx="${sx(p.expected_cost).toFixed(1)}" cy="${sy(p.rider_income_gini).toFixed(1)}" r="${eff?6:4}"
      fill="${eff?'#236a43':'#c9714a'}" stroke="#fff" stroke-width="1.5"></circle>
      <text x="${(sx(p.expected_cost)+8).toFixed(1)}" y="${(sy(p.rider_income_gini)-6).toFixed(1)}" font-size="10" fill="#67746f">α=${p.alpha}</text>`;
  }).join('');
  $('pareto').innerHTML=`<h3>效率(期望成本↓) × 公平(骑手收入 Gini↓) Pareto 前沿 — 绿点=非支配解</h3>
    <svg viewBox="0 0 ${W} ${H}">
      <line x1="${pad}" y1="${H-pad}" x2="${W-pad}" y2="${H-pad}" stroke="#16211e22"/>
      <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${H-pad}" stroke="#16211e22"/>
      <text x="${W/2}" y="${H-8}" font-size="11" fill="#67746f" text-anchor="middle">expected_cost →</text>
      <text x="14" y="${H/2}" font-size="11" fill="#67746f" transform="rotate(-90 14 ${H/2})" text-anchor="middle">rider Gini →</text>
      <polyline points="${pts}" fill="none" stroke="#2e5f7355" stroke-width="2"/>
      ${dots}
    </svg>`;
}
async function refreshStakeholders(){
  if(!lastSolution||!lastText) return;
  const r=await(await fetch('/api/stakeholders',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:lastText,solution:lastSolution,preset})})).json();
  if(r.status==='ok') paintStakeholders(r.panel);
}
$('run').addEventListener('click',()=>{
  const text=$('tsv').value;
  if(!text.trim()){$('status').textContent='请先生成或粘贴一个 case';return;}
  if(currentRun) currentRun.close();
  evCount=0; lastSolution=null; lastText=text;
  paintTraj(null);
  $('stream').innerHTML='<div class="empty">求解中…</div>';
  $('cert').innerHTML='<div class="empty">求解中…</div>';
  $('scorecards').innerHTML='<div class="empty" style="grid-column:1/-1">求解中…</div>';$('pareto').innerHTML='';
  ['m-regime','m-gap','m-cov','m-time'].forEach(i=>$(i).textContent='…');
  $('run').disabled=true; $('status').textContent='盲测求解中'; $('status').classList.add('run');
  runBlindStream(text);
});
function runBlindStream(text){
  // POST the case via a one-shot fetch + manual SSE parse (textarea may be large).
  fetch('/api/blind_stream',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text,memory_enabled:memOn,preset})}).then(async resp=>{
    const reader=resp.body.getReader(); const dec=new TextDecoder(); let buf='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      let idx;
      while((idx=buf.indexOf('\n\n'))>=0){
        const chunk=buf.slice(0,idx); buf=buf.slice(idx+2);
        const ev=/event: (.*)/.exec(chunk), da=/data: (.*)/.exec(chunk);
        if(ev&&da){ handleEvent(ev[1].trim(), JSON.parse(da[1])); }
      }
    }
    $('run').disabled=false; $('status').textContent='盲测完成'; $('status').classList.remove('run');
  }).catch(e=>{$('run').disabled=false; $('status').textContent='出错：'+e.message; $('status').classList.remove('run');});
}
function handleEvent(type,d){
  if(type==='trace'){
    const t=d.type;
    if(t==='perception'){
      const p=d.perception;
      setStage('perception',`regime=${p.regime} · d=${p.density_ratio} · p50=${p.willingness.p50} · bundle f=${p.bundle_fraction}`);
      $('m-regime').textContent=p.regime;
      addEv('Perception',`${d.message}\n规则: ${(p.rules||[]).join(' | ')}`);
    }else if(t==='memory_switch'){
      addEv('Memory Switch',d.message);
    }else if(t==='planner'){
      setStage('planner',`${d.chain}`);
      addEv('Planner',`${d.message}\nWHY: ${d.why}`);
    }else if(t==='trial_start'){
      addEv('Trials',d.message);
    }else if(t==='critic'){
      setStage('critic',`gap ${d.gap_pct!=null?Number(d.gap_pct).toFixed(2)+'%':'—'}`);
      $('m-gap').textContent=d.gap_pct!=null?Number(d.gap_pct).toFixed(2)+'%':'—';
      $('m-cov').textContent=d.coverage||'—';
      addEv('Critic',d.message);
    }else if(t==='controller'){
      setStage('controller',`${d.solve_time_s}s ${d.within_budget?'(预算内)':'(超时保护)'}`);
      $('m-time').textContent=(d.solve_time_s!=null?d.solve_time_s+'s':'—');
      addEv('Controller',d.message);
    }else if(t==='memory'){
      setStage('memory',d.covered+' covered');
      addEv('Memory',d.message);
    }else if(t==='final'){
      setStage('final','done');
      addEv('Done',d.message);
    }else{
      addEv(t,d.message||'');
    }
  }else if(type==='result'){
    const rep=d.report;
    lastSolution=rep.solution; lastText=$('tsv').value;
    paintCert(rep.certificate);
    paintStakeholders(rep.stakeholders);
  }
}
loadRegimes();
paintTraj(null);
</script>
</body>
</html>"""


# --------------------------------------------------------------------------- #
# Request handler                                                              #
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _html(self, html):
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._html(render_index())
                return
            if parsed.path == "/api/regimes":
                self._json(
                    {
                        "status": "ok",
                        "regimes": orch.list_blind_regimes(),
                        "presets": list(orch.WEIGHT_PRESETS.keys()),
                    }
                )
                return
            if parsed.path == "/api/generate":
                qs = parse_qs(parsed.query)
                regime = qs.get("regime", ["scarce"])[0]
                seed_raw = qs.get("seed", [""])[0].strip()
                seed = int(seed_raw) if seed_raw else None
                case = orch.generate_blind_case(regime, seed=seed)
                self._json({"status": "ok", "case": case})
                return
            if parsed.path == "/api/evolution":
                self._json(
                    {
                        "status": "ok",
                        "card": orch.promoted_strategy_card(),
                        "summary": orch.evolution_registry_summary(),
                    }
                )
                return
            self._json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
            if parsed.path == "/api/stakeholders":
                text = body.get("text", "")
                solution = [(k, list(cs)) for k, cs in body.get("solution", [])]
                preset = body.get("preset", "balanced")
                panel = orch.stakeholder_panel(text, solution, preset=preset)
                self._json({"status": "ok", "panel": panel})
                return
            if parsed.path == "/api/blind_stream":
                text = body.get("text", "")
                memory_enabled = bool(body.get("memory_enabled", True))
                preset = body.get("preset", "balanced")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()

                def observer(event):
                    self.wfile.write(_sse("trace", event))
                    self.wfile.flush()

                report = orch.run_blind_solve(
                    text,
                    case_label="blind-paste",
                    memory_enabled=memory_enabled,
                    weight_preset=preset,
                    observer=observer,
                )
                self.wfile.write(_sse("result", {"report": report}))
                self.wfile.write(_sse("done", {"message": "complete"}))
                self.wfile.flush()
                self.close_connection = True
                return
            self._json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            try:
                self._json(
                    {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                    status=500,
                )
            except Exception:
                pass

    def log_message(self, fmt, *args):
        print(f"[blind-test] {self.address_string()} - {fmt % args}")


# --------------------------------------------------------------------------- #
# Headless self-check: boot the server, drive one full blind solve over HTTP    #
# --------------------------------------------------------------------------- #
def _selfcheck(host="127.0.0.1", port=8771) -> int:
    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{host}:{port}"
    ok = True
    try:
        print(f"[selfcheck] server booted at {base}")
        # 1) regimes
        regimes = json.loads(urllib.request.urlopen(base + "/api/regimes", timeout=10).read())
        print(f"[selfcheck] /api/regimes -> {len(regimes['regimes'])} regimes, presets={regimes['presets']}")
        # 2) generate a fresh judge-unseen case
        gen = json.loads(urllib.request.urlopen(base + "/api/generate?regime=scarce", timeout=20).read())
        case = gen["case"]
        print(f"[selfcheck] /api/generate -> seed={case['seed']} rows={case['rows']}")
        # 3) evolution card
        evo = json.loads(urllib.request.urlopen(base + "/api/evolution", timeout=10).read())
        card = evo["card"]
        print(f"[selfcheck] /api/evolution -> promoted={card['strategy_id']} status={card['status']}")
        # 4) blind stream (memory OFF) -> parse SSE
        payload = json.dumps({"text": case["text"], "memory_enabled": False, "preset": "balanced"}).encode()
        req = urllib.request.Request(
            base + "/api/blind_stream", data=payload, headers={"Content-Type": "application/json"}
        )
        raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        trace_types, result = [], None
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
            if ev == "result" and da:
                result = da["report"]
        print(f"[selfcheck] /api/blind_stream trace types = {trace_types}")
        if result is None:
            print("[selfcheck] FAIL: no result event"); ok = False
        else:
            print(f"[selfcheck]   solve_status = {result['solve_status']} time={result['solve_time_s']}s")
            print(f"[selfcheck]   regime       = {result['perception']['regime']} (d={result['perception']['density_ratio']})")
            print(f"[selfcheck]   coverage     = {result['solution_summary']['covered_tasks']}/{result['solution_summary']['total_tasks']}")
            print(f"[selfcheck]   gap          = {result['certificate']['gap_pct']}")
            print(f"[selfcheck]   pareto pts   = {len(result['stakeholders'].get('pareto_front', []))}")
            if result["solve_status"] not in {"ok", "ok-fallback-v2"}:
                print("[selfcheck] FAIL: solve not ok"); ok = False
            if "perception" not in trace_types or "critic" not in trace_types or "final" not in trace_types:
                print("[selfcheck] FAIL: missing trajectory stages"); ok = False
        # 5) stakeholders re-weight endpoint (rider_first)
        sk_payload = json.dumps(
            {"text": case["text"], "solution": result["solution"], "preset": "rider_first"}
        ).encode()
        sk_req = urllib.request.Request(
            base + "/api/stakeholders", data=sk_payload, headers={"Content-Type": "application/json"}
        )
        sk = json.loads(urllib.request.urlopen(sk_req, timeout=30).read())
        print(f"[selfcheck] /api/stakeholders(rider_first) U_total={sk['panel']['utilities']['U_weighted_total']}")
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
    parser = argparse.ArgumentParser(description="AutoSolver finals blind-test demo (non-destructive).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--selfcheck", action="store_true", help="boot + drive one blind solve, then exit")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"AutoSolver 现场盲测 Demo running at http://{args.host}:{args.port}")
    print("  (原版 demo 仍可用: python3 web_agent_demo/server.py)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
