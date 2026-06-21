/* 即时履约智能调度指挥舱 · 前端逻辑 (iteration-1)
 * 接真数据：SSE 五环 / Baseline 真值 / 6KPI / 证书 r1 / 地图真实 solution 连线。 */
'use strict';
const $ = id => document.getElementById(id);
const safe = t => String(t ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const NS = 'http://www.w3.org/2000/svg';
const el = (n, attrs = {}) => { const e = document.createElementNS(NS, n); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

/* ---------- 静态：业务场景 5 样例（iteration-1：第2项 active，切换为占位） ---------- */
const SCENES = [
  {id:'peak',   ico:'📈', t:'午高峰爆单',   d:'订单量激增 156%'},
  {id:'rain',   ico:'🌧️', t:'雨天低接单意愿', d:'骑手接单意愿下降'},
  {id:'scarce', ico:'🧍', t:'骑手稀缺商圈', d:'可用骑手紧张'},
  {id:'bundle', ico:'🗂️', t:'合单机会密集', d:'多订单同向集中'},
  {id:'newshop',ico:'🏪', t:'新店突发订单', d:'新店订单突然增加'},
];
function renderScenes(activeRegime){
  $('scenelist').innerHTML = SCENES.map((s,i)=>{
    const act = (activeRegime==='bundle-heavy' && s.id==='bundle') || (!activeRegime && i===3);
    return `<div class="scene ${act?'active':''}" data-id="${s.id}">
      <div class="si">${s.ico}</div>
      <div><div class="st">${i+1} ${safe(s.t)}</div><div class="sd">${safe(s.d)}</div></div>
    </div>`;
  }).join('');
}

/* ---------- 五环 ---------- */
const RINGS = [
  ['perception','感知','识别订单/骑手/意愿'],
  ['planner','规划','策略链镜像解读'],
  ['critic','执行/评估','solver_v4 求解+证书'],
  ['controller','评估','择优/预算守护'],
  ['memory','记忆','输出最优解'],
];
function renderRings(){
  const parts = [];
  RINGS.forEach((r,i)=>{
    parts.push(`<div class="ring wait" data-r="${r[0]}"><div class="rc">${i+1}</div><div class="rt">${safe(r[1])}</div><div class="rs" id="rs-${r[0]}">${safe(r[2])}</div></div>`);
    if(i<RINGS.length-1) parts.push('<div class="ring-arrow">→</div>');
  });
  $('rings').innerHTML = parts.join('');
}
function setRing(id, state, sub){
  document.querySelectorAll('.ring').forEach(n=>{
    if(n.dataset.r===id){
      n.classList.remove('wait','run','done');
      n.classList.add(state);
    }
  });
  if(sub){ const e=$('rs-'+id); if(e) e.textContent=sub; }
}

/* ---------- count-up ---------- */
function countUp(node, target, unit, decimals){
  if(target==null || isNaN(target)){ node.innerHTML = '—'; return; }
  const dur=700, t0=performance.now();
  const ease = x => 1-Math.pow(1-x,3);
  function frame(t){
    const p=Math.min(1,(t-t0)/dur), v=target*ease(p);
    node.innerHTML = (decimals?v.toFixed(decimals):Math.round(v).toLocaleString()) + (unit?`<span class="unit">${safe(unit)}</span>`:'');
    if(p<1) requestAnimationFrame(frame);
  }
  node.setAttribute('data-counting','1');
  requestAnimationFrame(frame);
  setTimeout(()=>node.removeAttribute('data-counting'), dur+50);
}

/* ---------- KPI ---------- */
function renderKpis(kpis){
  $('kpis').innerHTML = kpis.map(k=>{
    const arrow = k.good==='up'?'↑':(k.good==='down'?'↓':'·');
    const acls = k.good==='up'?'arrow-up':(k.good==='down'?'arrow-down-good':'arrow-neutral');
    const tag = k.is_demo?'<span class="demo-tag">演示</span>':'<span class="real-dot"></span>';
    const dec = (k.unit==='%'||k.key==='cost_index')?1:0;
    return `<div class="panel kpi skeleton">
      <div class="klbl">${tag}${safe(k.label)}</div>
      <div class="kval" data-key="${k.key}" data-val="${k.value??''}" data-unit="${safe(k.unit)}" data-dec="${dec}">—</div>
      <div class="ksub">${safe(k.sub||'')}</div>
      <div class="karrow ${acls}">${arrow}</div>
      <svg class="spark" viewBox="0 0 100 22" preserveAspectRatio="none">${sparkPath(k.key)}</svg>
    </div>`;
  }).join('');
  document.querySelectorAll('.kval').forEach(n=>{
    const v=parseFloat(n.dataset.val);
    countUp(n, isNaN(v)?null:v, n.dataset.unit, parseInt(n.dataset.dec));
  });
}
function sparkPath(key){
  // 确定性伪 sparkline（演示视觉）
  let seed=0; for(const c of key) seed=(seed*31+c.charCodeAt(0))&0xffff;
  const pts=[]; for(let i=0;i<10;i++){ seed=(seed*1103515245+12345)&0x7fffffff; pts.push(4+(seed%14)); }
  const d=pts.map((y,i)=>`${i*11},${22-y}`).join(' ');
  return `<polyline points="${d}" fill="none" stroke="rgba(63,210,224,.5)" stroke-width="1.4"/>`;
}

/* ---------- chips ---------- */
function renderChips(chips){
  if(!chips||!chips.length) return;
  $('chips').innerHTML = chips.map(c=>`<div class="chip skeleton">
    <span class="ci">${safe(c.icon)}</span>
    <div><div class="ct">${safe(c.title)}</div><div class="cv">${safe(c.value)}</div><div class="cd">${safe(c.delta)}</div></div>
  </div>`).join('');
}

/* ---------- verdict / scenes ---------- */
function renderVerdict(v){
  if(!v) return;
  $('verdict-name').textContent = 'AI 判定：' + (v.regime||'—');
  $('verdict-rule').innerHTML = (v.rules||[]).map(safe).join('<br>') || '—';
  renderScenes(v.regime);
}

/* ---------- risk ---------- */
function renderRisk(risk){
  if(!risk||!risk.length){ $('risk').innerHTML='<div class="empty-ph">无数据</div>'; return; }
  $('risk').innerHTML = risk.map(r=>{
    const lv = r.level==='high'?'高风险':(r.level==='mid'?'中风险':'低风险');
    return `<div class="risk-row"><div><div class="rn">${safe(r.name)}</div><div class="rb">${safe(r.basis)}</div></div>
      <span class="risk-badge lv-${safe(r.level)}">${lv}</span></div>`;
  }).join('');
}

/* ---------- strategy ---------- */
function renderStrategy(s){
  if(!s){ return; }
  const steps = (s.steps&&s.steps.length)?s.steps:[s.chain||'—'];
  $('strategy').innerHTML = steps.map((st,i)=>`<div class="strat-step"><div class="sn">${i+1}</div><div class="stx">${safe(st)}</div></div>`).join('')
    + (s.why?`<div class="tiny muted" style="margin-top:6px;line-height:1.5">WHY: ${safe(s.why)}</div>`:'');
}

/* ---------- certificate (r1) ---------- */
function renderCert(c){
  if(!c){ $('cert').innerHTML='<div class="empty-ph">无证书</div>'; return; }
  const applicable = c.applicable!==false;
  const gap = (applicable && c.gap_pct!=null)? Number(c.gap_pct).toFixed(2)+'%':'N/A';
  const badge = !applicable?'<span class="risk-badge lv-mid">N/A 不适用</span>'
    :(c.certified_optimal?'<span class="risk-badge lv-low">CERTIFIED OPTIMAL</span>':'<span class="risk-badge lv-mid">近最优</span>');
  $('cert').innerHTML = `<div style="font-size:12.5px;line-height:1.5;margin-bottom:8px"><span class="real-dot"></span>${safe(c.headline)} ${badge}</div>
    <div class="dec-grid">
      <span class="dk">optimality gap</span><span class="dv">${gap}</span>
      <span class="dk">下界 (proven)</span><span class="dv">${applicable&&c.lower_bound!=null?Number(c.lower_bound).toFixed(2):'—'}</span>
      <span class="dk">上界 (本解)</span><span class="dv">${applicable&&c.upper_bound!=null?Number(c.upper_bound).toFixed(2):'—'}</span>
      <span class="dk">binding</span><span class="dv">${applicable?safe(c.binding_bound):'—'}</span>
    </div>`;
}

/* ---------- candidates ABC ---------- */
function stars(n){ n=Math.max(0,Math.min(5,Math.round(n||0))); return '★'.repeat(n)+'☆'.repeat(5-n); }
function renderCandidates(cands){
  if(!cands||!cands.length){ return; }
  // 星级按相对成本映射（演示）
  const costs = cands.map(c=>c.cost).filter(x=>x!=null);
  const cmin=Math.min(...costs), cmax=Math.max(...costs);
  $('candidates').innerHTML = cands.map(c=>{
    let star=3;
    if(c.cost!=null && cmax>cmin) star = 1+Math.round((cmax-c.cost)/(cmax-cmin)*4);
    if(c.picked) star=5;
    return `<div class="cand ${c.picked?'picked':''}">
      <div class="ch"><div class="cl">${safe(c.label)}</div><span class="tag ${c.picked?'win':'out'}">${safe(c.tag)}</span></div>
      <div class="cm"><span>完成率</span><span>${c.completion!=null?c.completion+'%':'—'}</span></div>
      <div class="cm"><span>期望成本</span><span>${c.cost!=null?c.cost:'—'}</span></div>
      <div class="cm"><span>骑手使用</span><span>${c.used_couriers!=null?c.used_couriers:'—'}</span></div>
      <div class="cm"><span>综合评分</span><span class="stars">${stars(star)}</span></div>
      <div class="creason">${safe(c.reason)}</div>
    </div>`;
  }).join('');
}

/* ---------- baseline 表 ---------- */
function renderBaseline(bl){
  if(!bl){ return; }
  const g=bl.greedy||{}, a=bl.autosolver||{}, imp=bl.improvement||{};
  const compl=(o)=> (o.covered!=null&&o.total)? (o.covered/o.total*100).toFixed(1)+'%':'—';
  const costIdx=(o,base)=> (o.expected_cost!=null&&base)? (o.expected_cost/base*100).toFixed(1):'—';
  const gCost=g.expected_cost;
  const rows = [
    ['预计完成率', compl(g), compl(a), imp.coverage_delta!=null?(imp.coverage_delta>=0?'+':'')+imp.coverage_delta+' 覆盖':'持平'],
    ['期望成本', g.expected_cost??'—', `<span class="winner">${a.expected_cost??'—'}</span>`, imp.cost_pct!=null?`-${imp.cost_pct}%`:'—'],
    ['履约成本指数', '100.0', costIdx(a,gCost), imp.cost_pct!=null?`-${imp.cost_pct}%`:'—'],
    ['骑手占用<span class="tiny muted">(仅记录)</span>', g.used_couriers??'—', a.used_couriers??'—', '中性·非优势项'],
    ['调度耗时', (g.solve_time_s!=null?g.solve_time_s+'s':'—'), (a.solve_time_s!=null?a.solve_time_s+'s':'—'), '—'],
  ];
  const sb = imp.strictly_better;
  $('baseline').innerHTML = `<table class="btable">
    <thead><tr><th>对比指标</th><th>传统贪心基线</th><th>AutoSolver</th><th>改善</th></tr></thead>
    <tbody>${rows.map(r=>`<tr><td>${r[0]}</td><td class="val">${r[1]}</td><td class="val good">${r[2]}</td><td>${safe(r[3])}</td></tr>`).join('')}</tbody>
  </table>
  <div class="tiny" style="margin-top:7px;color:${sb?'var(--green)':'var(--red)'};font-weight:800">
    ${sb?'✓ 严格优于（成本口径：期望成本更低 + 覆盖不更差）':'未达严格优于'} ·
    <span class="muted">基线=纯贪心真实运行；不宣称省骑手</span></div>`;
}

/* ---------- decision ---------- */
function renderDecision(d){
  if(!d||!d.available){ $('decision').innerHTML='<div class="empty-ph">无合单组</div>'; return; }
  const riders = (d.riders||[]).map(r=>`<div class="rider">
    <div class="av">${safe((r.id||'R').slice(-2))}</div>
    <div><div class="rid">${safe(r.id)}</div>
      <div class="rm">接单意愿 ${r.willingness!=null?(r.willingness*100).toFixed(0)+'%':'—'} · 距离 ${r.distance_km}km<span class="demo-tag">演示距离</span></div></div>
  </div>`).join('');
  const modeLabel = d.is_bundle?'合单·高价值':(d.is_multi_courier?'多骑手兜底':'单派');
  $('decision').innerHTML = `
    <div class="dec-head"><div class="dg">任务组 ${safe(d.group_id)}</div>
      <span class="risk-badge lv-high">${modeLabel}</span></div>
    <div class="dec-grid">
      <span class="dk">订单数</span><span class="dv">${d.n_tasks}单${d.is_bundle?'(合单)':''}</span>
      <span class="dk">兜底骑手</span><span class="dv">${d.n_couriers||1}人</span>
      <span class="dk">预计送达<span class="demo-tag">演示</span></span><span class="dv">${d.eta_min}分钟</span>
      <span class="dk">商圈<span class="demo-tag">演示</span></span><span class="dv">${safe(d.district||'—')}</span>
      <span class="dk">距离<span class="demo-tag">演示</span></span><span class="dv">${d.distance_km}km</span>
    </div>
    <div class="tiny muted" style="margin:4px 0 6px"><span class="real-dot"></span>选择的骑手（派单/意愿/分数=真值）</div>
    ${riders}
    <div class="tiny muted" style="margin:8px 0 4px">决策原因</div>
    ${(d.reasons||[]).map(r=>`<div class="reason">${safe(r)}</div>`).join('')}
    ${d.use_bundle?`<div class="tiny" style="margin-top:6px;color:var(--green)">✓ 使用合单：合单后预计送达更短、单位成本更低<span class="demo-tag">演示换算</span></div>`
      :(d.is_multi_courier?`<div class="tiny" style="margin-top:6px;color:var(--green)">✓ 多骑手兜底：对冲低意愿拒单，提升完成率<span class="demo-tag">演示换算</span></div>`:'')}`;
}

/* ---------- 地图 ---------- */
let mapData=null, mapZoom=1, mapTx=0, mapTy=0;
function renderMap(m){
  mapData=m;
  const svg=$('mapsvg'); svg.innerHTML='';
  const W=m.canvas?.w||1000, H=m.canvas?.h||640;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);

  // 暗色路网底纹
  const defs=el('defs');
  defs.innerHTML=`<radialGradient id="mgrad" cx="50%" cy="48%" r="70%">
    <stop offset="0%" stop-color="#0d1b2c"/><stop offset="100%" stop-color="#070d14"/></radialGradient>`;
  svg.appendChild(defs);
  svg.appendChild(el('rect',{x:0,y:0,width:W,height:H,fill:'url(#mgrad)'}));
  // 网格
  const grid=el('g',{opacity:'0.13'});
  for(let x=0;x<=W;x+=62) grid.appendChild(el('line',{x1:x,y1:0,x2:x,y2:H,stroke:'#3fd2e0','stroke-width':'0.5'}));
  for(let y=0;y<=H;y+=62) grid.appendChild(el('line',{x1:0,y1:y,x2:W,y2:y,stroke:'#3fd2e0','stroke-width':'0.5'}));
  svg.appendChild(grid);

  const root=el('g',{id:'maproot'});
  svg.appendChild(root);

  // 商圈区块（柔光）
  (m.districts||[]).forEach(d=>{
    root.appendChild(el('circle',{cx:d.x,cy:d.y,r:78,fill:'rgba(63,210,224,.05)',stroke:'none'}));
  });

  // 圈：真合单组 + 多骑手兜底组（真值）。限量渲染避免满屏；优先显合单组。
  const bsorted=(m.bundles||[]).slice().sort((a,b)=> (a.kind==='task_bundle'?-1:0)-(b.kind==='task_bundle'?-1:0));
  bsorted.slice(0,10).forEach(b=>{
    root.appendChild(el('circle',{cx:b.cx,cy:b.cy,r:b.r,class:'bundle-ring'}));
    const t=el('text',{x:b.cx,y:b.cy-b.r-4,fill:'#37e0a0','font-size':'11','font-weight':'800','text-anchor':'middle'});
    t.textContent=b.label; root.appendChild(t);
  });

  // 候选虚线（先画，底层）
  const candG=el('g',{id:'candedges'});
  (m.candidate_edges||[]).forEach(e=>{
    candG.appendChild(el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,class:'cand-edge'}));
  });
  root.appendChild(candG);

  // 采纳实线（默认隐藏，收敛动画点亮）
  const accG=el('g',{id:'accedges'});
  (m.accepted_edges||[]).forEach(e=>{
    accG.appendChild(el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,class:'acc-edge'}));
  });
  root.appendChild(accG);

  // 商圈节点（方块代表商家中心）
  (m.districts||[]).forEach(d=>{
    const g=el('g',{class:'node-hit','data-district':d.id});
    g.appendChild(el('rect',{x:d.x-8,y:d.y-8,width:16,height:16,rx:3,class:'district-node'}));
    const t=el('text',{x:d.x,y:d.y+22,fill:'#8aa0b8','font-size':'9.5','text-anchor':'middle'});
    t.textContent=d.name; g.appendChild(t);
    g.addEventListener('click',()=>focusDistrict(d));
    root.appendChild(g);
  });

  // 骑手
  (m.couriers||[]).forEach(c=>{
    const node=el('circle',{cx:c.x,cy:c.y,r:c.active?5.5:4,
      class:c.active?'courier-node node-hit':'courier-idle node-hit','data-courier':c.id});
    node.addEventListener('mouseenter',ev=>showTip(ev,`骑手 ${c.id}\n${c.active?'已采纳派单(真)':'未采纳'}`));
    node.addEventListener('mouseleave',hideTip);
    root.appendChild(node);
  });

  // 订单（任务）节点
  (m.tasks||[]).forEach(t=>{
    const cls=t.risk==='high'?'task-high':(t.risk==='mid'?'task-mid':'task-low');
    const node=el('circle',{cx:t.x,cy:t.y,r:6,class:cls+' node-hit '+(t.risk==='high'?'pulse':''),'data-task':t.id});
    node.addEventListener('mouseenter',ev=>showTip(ev,`订单 ${t.id}\n意愿派生 ${t.willingness_repr} · 风险 ${t.risk}`));
    node.addEventListener('mouseleave',hideTip);
    root.appendChild(node);
  });

  applyMapTransform();
}
function applyMapTransform(){
  const root=$('maproot'); if(!root) return;
  root.setAttribute('transform',`translate(${mapTx},${mapTy}) scale(${mapZoom})`);
}
function convergeEdges(){
  // 候选虚线渐隐 + 采纳实线点亮（收敛感）
  const cand=$('candedges'); if(cand) cand.style.transition='opacity 1s', cand.style.opacity='0.18';
  const accs=document.querySelectorAll('.acc-edge');
  accs.forEach((e,i)=> setTimeout(()=>e.classList.add('on'), 40*i));
}
let tipEl=null;
function showTip(ev,text){
  hideTip();
  tipEl=document.createElement('div');
  tipEl.style.cssText='position:fixed;z-index:99;background:rgba(10,19,30,.95);border:1px solid var(--cyan);border-radius:8px;padding:6px 9px;font-size:11px;white-space:pre;pointer-events:none;color:#e6f0fb';
  tipEl.textContent=text;
  document.body.appendChild(tipEl);
  tipEl.style.left=(ev.clientX+12)+'px'; tipEl.style.top=(ev.clientY+12)+'px';
}
function hideTip(){ if(tipEl){ tipEl.remove(); tipEl=null; } }
function focusDistrict(d){
  // 聚焦缓动：放大该商圈
  const W=mapData.canvas?.w||1000, H=mapData.canvas?.h||640;
  mapZoom=1.8; mapTx=W/2 - d.x*mapZoom; mapTy=H/2 - d.y*mapZoom;
  const root=$('maproot'); if(root) root.style.transition='transform .35s cubic-bezier(.4,0,.2,1)';
  applyMapTransform();
  const fc=$('focuscard');
  fc.innerHTML=`<div class="fh">商圈 ${safe(d.name)}</div>
    <div class="fl"><span>商圈 ID</span><span>${safe(d.id)}</span></div>
    <div class="fl"><span>含订单</span><span>${(d.tasks||[]).length}单</span></div>
    <div class="fl"><span>坐标</span><span class="demo-tag">演示</span></div>`;
  fc.style.left='50%'; fc.style.top='44%'; fc.style.transform='translate(-50%,-50%)';
  fc.classList.add('show');
  setTimeout(()=>fc.classList.remove('show'),2600);
}
$('zoomin').onclick=()=>{ mapZoom=Math.min(3,mapZoom*1.25); applyMapTransform(); };
$('zoomout').onclick=()=>{ mapZoom=Math.max(.6,mapZoom/1.25); applyMapTransform(); };
$('zoomreset').onclick=()=>{ mapZoom=1; mapTx=0; mapTy=0;
  const root=$('maproot'); if(root) root.style.transition='transform .3s'; applyMapTransform(); };

/* ---------- 自进化 ---------- */
function renderEvo(evo){
  if(!evo){ return; }
  const card=evo.promoted_card||{};
  const reg=evo.registry_summary||{};
  const exps=[
    {id:'#21',state:'通过',ok:true,note:'可加入候选池'},
    {id:'#20',state:'通过',ok:true,note:'安全门+质量门通过'},
    {id:'#19',state:'失败',ok:false,note:'未过质量门'},
    {id:'#18',state:'失败',ok:false,note:'不稳定'},
  ];
  $('evobody').innerHTML=`
    <div class="tiny muted" style="margin-bottom:6px">当前正式求解器 <b style="color:var(--green)">AutoSolver v4 (solver_v4.py)</b> · 稳定运行中</div>
    <div class="evo-list">
      ${exps.map(e=>`<div class="evo-item"><span>实验策略 ${e.id} <span class="muted">${e.note}</span></span><span class="${e.ok?'evo-pass':'evo-fail'}">${e.state}</span></div>`).join('')}
    </div>
    <div class="tiny muted" style="margin-top:8px;line-height:1.5">
      promoted = ${safe(card.strategy_id||'—')} · directive ${safe(card.directive||'—')} · 注册表 ${reg.total_strategies||0} 条策略。
      实验策略不会直接污染正式求解器，只有通过质量门才进入候选池。
      <b>改进量 Δ 为机制内部 held-out 指标，非派单成绩；自进化对最终成绩零贡献。</b>
    </div>`;
}

/* ---------- ROI ---------- */
let costImprovePct = 18; // 默认；推理后绑真实成本改善
function recomputeRoi(){
  const orders=parseFloat($('roi-orders').value)||0;
  const loss=parseFloat($('roi-loss').value)||0;
  const districts=parseFloat($('roi-districts').value)||0;
  const coverage=Math.min(1, districts/100);
  const pct=costImprovePct/100;
  const daily=Math.round(orders*pct*loss*coverage);
  $('roi-daily').textContent='¥'+daily.toLocaleString();
  $('roi-monthly').textContent='¥'+(daily*30).toLocaleString();
  $('roi-stab').textContent='+'+(costImprovePct*0.42).toFixed(1)+'%';
}
$('roi-calc').onclick=recomputeRoi;

/* ---------- 计时器 ---------- */
let timerH=null, timerStart=0;
function startTimer(){ timerStart=Date.now(); clearInterval(timerH);
  timerH=setInterval(()=>{ const s=Math.floor((Date.now()-timerStart)/1000);
    const hh=String(Math.floor(s/3600)).padStart(2,'0'), mm=String(Math.floor(s%3600/60)).padStart(2,'0'), ss=String(s%60).padStart(2,'0');
    $('timer').textContent=`${hh}:${mm}:${ss}`; },250);
}
function stopTimer(){ clearInterval(timerH); }

/* ---------- SSE 主流程 ---------- */
function handleTrace(d){
  const t=d.type;
  if(t==='perception'){
    const p=d.perception;
    setRing('perception','done',`regime=${p.regime}`);
    renderVerdict({regime:p.regime,rules:p.rules});
    renderChips(/*from案: chips built server-side at result, but light up early*/ buildChipsFromPerc(p));
    renderRiskFromPerc(p);
  }else if(t==='planner'){
    setRing('planner','done', d.chain);
    renderStrategy({steps:(d.chain||'').split(/[+·]/).map(s=>s.trim()).filter(Boolean), chain:d.chain, why:d.why});
  }else if(t==='trial_start'){
    setRing('critic','run','solver_v4 求解中…');
  }else if(t==='progress'){
    setRing('critic','run',`求解中 ${d.elapsed_s}s`);
  }else if(t==='critic'){
    setRing('critic','done', d.gap_pct!=null?`gap ${Number(d.gap_pct).toFixed(2)}%`:'N/A');
    renderCert(d);
  }else if(t==='controller'){
    setRing('controller','done', `${d.solve_time_s}s`);
    if(d.solver_used) $('solverused').textContent=d.solver_used;
  }else if(t==='memory'){
    setRing('memory','done', d.covered+' covered');
  }else if(t==='final'){
    $('phase').textContent='盲测求解完成，回填全量真值…';
  }
}
function buildChipsFromPerc(p){
  const chips=[];
  if(p.willingness_mean!=null) chips.push({icon:'☔',title:'接单意愿',value:`w̄=${p.willingness_mean}`,delta:p.willingness_mean<0.45?'意愿偏低':'意愿正常'});
  if(p.density_ratio!=null) chips.push({icon:'🧍',title:'骑手供给',value:`d=${p.density_ratio}`,delta:p.density_ratio>=1.8?'骑手充裕':(p.density_ratio>1?'均衡':'骑手紧张')});
  if(p.bundle_fraction!=null) chips.push({icon:'🗂️',title:'合单潜力',value:`合单占比 ${(p.bundle_fraction*100).toFixed(1)}%`,delta:p.bundle_fraction>=0.35?'合单机会密集':'合单一般'});
  return chips;
}
function renderRiskFromPerc(p){
  const w=p.willingness_mean??0.4, d=p.density_ratio??1.5, bf=p.bundle_fraction??0;
  const q=p.willingness||{}, spread=(q.p90||0)-(q.p10||0);
  renderRisk([
    {name:'接单意愿低',level:w<0.3?'high':(w<0.5?'mid':'low'),basis:`w̄=${w}`},
    {name:'骑手供给不足',level:d<=1.0?'high':(d<1.6?'mid':'low'),basis:`d=${d}`},
    {name:'订单分布不均',level:spread>0.6?'high':(spread>0.4?'mid':'low'),basis:`p90-p10=${spread.toFixed(3)}`},
    {name:'合单机会密集',level:bf>=0.35?'low':'mid',basis:`合单占比=${bf}`},
  ]);
}

function runStream(){
  $('runbtn').disabled=true;
  $('runlight').classList.remove('idle'); $('runtext').textContent='调度运行中';
  $('phase').textContent='盲测求解中…（solver_v4：v3 base + 余量精修，约 10 秒内逐事件点亮）';
  renderRings();
  RINGS.forEach((r,i)=> setRing(r[0], i===0?'run':'wait'));
  startTimer();

  fetch('/api/cockpit/stream',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({case:'large_seed301',memory_enabled:true})}).then(async resp=>{
    const reader=resp.body.getReader(), dec=new TextDecoder(); let buf='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      let idx;
      while((idx=buf.indexOf('\n\n'))>=0){
        const chunk=buf.slice(0,idx); buf=buf.slice(idx+2);
        const ev=/event: (.*)/.exec(chunk), da=/data: ([\s\S]*)/.exec(chunk);
        if(ev&&da){ dispatchEvent2(ev[1].trim(), JSON.parse(da[1])); }
      }
    }
    finishRun();
  }).catch(e=>{ $('phase').textContent='出错：'+e.message; finishRun(); });
}
function dispatchEvent2(type,d){
  if(type==='trace'){ handleTrace(d); }
  else if(type==='baseline'){ renderBaseline(d.baseline);
    const pct=d.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(60,pct); } }
  else if(type==='result'){ applyStory(d.story); }
  else if(type==='error'){ $('phase').textContent='出错：'+(d.message||''); }
}
function applyStory(s){
  if(!s) return;
  if(s.chips) renderChips(s.chips);
  if(s.kpis) renderKpis(s.kpis);
  if(s.risk) renderRisk(s.risk);
  if(s.strategy) renderStrategy(s.strategy);
  if(s.regime_verdict) renderVerdict(s.regime_verdict);
  if(s.map) renderMap(s.map);
  if(s.decision) renderDecision(s.decision);
  if(s.candidates) renderCandidates(s.candidates);
  if(s.certificate) renderCert(s.certificate);
  if(s.baseline) renderBaseline(s.baseline);
  if(s.solver_used) $('solverused').textContent=s.solver_used;
  // 收敛动画
  setTimeout(convergeEdges, 300);
  // ROI 系数绑真实成本改善
  const pct=s.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(60,pct); }
  recomputeRoi();
}
function finishRun(){
  $('runbtn').disabled=false;
  $('runlight').classList.add('idle'); $('runtext').textContent='完成';
  stopTimer();
  $('phase').textContent='推理完成 · 全量真值已回填（约 10 秒内 SSE 逐事件）';
}

/* ---------- 初始骨架（秒开，不跑求解） ---------- */
async function loadSkeleton(){
  renderScenes(null); renderRings();
  RINGS.forEach(r=> setRing(r[0],'wait'));
  try{
    const r=await(await fetch('/api/cockpit/case')).json();
    if(r.status==='ok'){
      if(r.chips) renderChips(r.chips);
      if(r.risk) renderRisk(r.risk);
      if(r.regime_verdict) renderVerdict(r.regime_verdict);
      if(r.map_skeleton) renderMap(r.map_skeleton);
    }
  }catch(e){ /* 骨架失败不阻塞 */ }
  recomputeRoi();
}

/* ---------- 折叠 / 场景点击 ---------- */
$('evotoggle').onclick=()=> $('evopanel').classList.toggle('collapsed');
document.addEventListener('click',e=>{
  const sc=e.target.closest('.scene');
  if(sc){
    document.querySelectorAll('.scene').forEach(n=>n.classList.toggle('active',n===sc));
    $('phase').textContent='场景样例切换（iteration-1：其余 4 样例为占位，下一轮接 /api/generate 脱敏样例）';
  }
});
$('runbtn').onclick=runStream;

/* 键盘：空格开始推理 */
document.addEventListener('keydown',e=>{
  if(e.code==='Space' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)){ e.preventDefault(); if(!$('runbtn').disabled) runStream(); }
});

loadSkeleton();
// 进化面板用静态骨架（iteration-1：接真值在 result.evolution，本轮先渲染结构）
renderEvo({promoted_card:{strategy_id:'gen01_M1_003',directive:'none'},registry_summary:{total_strategies:0}});
