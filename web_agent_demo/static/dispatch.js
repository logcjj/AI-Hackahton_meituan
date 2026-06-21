/* 即时履约智能调度指挥舱 · 前端逻辑 (iteration-1)
 * 接真数据：SSE 五环 / Baseline 真值 / 6KPI / 证书 r1 / 地图真实 solution 连线。 */
'use strict';
const $ = id => document.getElementById(id);
const safe = t => String(t ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const NS = 'http://www.w3.org/2000/svg';
const el = (n, attrs = {}) => { const e = document.createElementNS(NS, n); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

/* P1-5：骑手首字母彩色 avatar（确定性渐变底 + 首字母），贴近目标稿头像观感 */
const AV_PALETTES=[['#46f0a8','#1c9b6c'],['#43d5ff','#1f6fb0'],['#f4b14a','#d0731c'],
  ['#9a7cf0','#5e44c0'],['#ff8aa0','#c0445a'],['#5ad6c8','#1e8a82']];
function avatarHtml(id){
  const s=String(id||'R');
  let h=0; for(const c of s) h=(h*131+c.charCodeAt(0))>>>0;
  const pal=AV_PALETTES[h%AV_PALETTES.length];
  // 首字母：取最后一段数字前的字母，没有就取首字符（R-102 → R）
  const letter=(s.match(/[A-Za-z]/)||[s[0]||'R'])[0].toUpperCase();
  return `<div class="av" style="background:linear-gradient(135deg,${pal[0]},${pal[1]})">${safe(letter)}</div>`;
}

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

/* ---------- KPI 骨架（P0-3：idle 首屏灰显 + 「待推理」角标，避免空白） ---------- */
const KPI_SKEL=[
  {label:'预计完成率',unit:'%'},{label:'预计无人接单数',unit:'单'},
  {label:'履约成本指数',unit:''},{label:'骑手占用数',unit:'人'},
  {label:'相对省心基线改善',unit:'%'},{label:'预计商业收益',unit:'¥/日'},
];
function renderKpiSkeleton(){
  $('kpis').innerHTML=KPI_SKEL.map(k=>`<div class="panel kpi kpi-skel">
    <div class="klbl">${safe(k.label)}</div>
    <div class="kval kval-skel">—<span class="unit">${safe(k.unit)}</span></div>
    <div class="ksub"><span class="skel-bar"></span></div>
    <div class="karrow"><span class="pend-badge">待推理</span></div>
    <span class="skel-shimmer"></span>
  </div>`).join('');
}
function skeletonPanel(txt){ return `<div class="empty-ph skel-ph"><span class="pend-badge">待推理</span> ${safe(txt||'加载即自动现场求解…')}</div>`; }

/* ---------- KPI ---------- */
function renderKpis(kpis){
  $('kpis').innerHTML = kpis.map(k=>{
    const arrow = k.good==='up'?'↑':(k.good==='down'?'↓':'·');
    const acls = k.good==='up'?'arrow-up':(k.good==='down'?'arrow-down-good':'arrow-neutral');
    const tag = k.is_demo?'<span class="demo-tag">演示</span>':'<span class="real-dot"></span>';
    const dec = (k.unit==='%'||k.key==='cost_index')?1:0;
    const col = k.good==='neutral'?'rgba(127,165,151,.55)':(k.good==='up'||k.good==='down'?'rgba(70,240,168,.6)':'rgba(67,213,255,.55)');
    return `<div class="panel kpi skeleton">
      <div class="klbl">${tag}${safe(k.label)}</div>
      <div class="kval" data-key="${k.key}" data-val="${k.value??''}" data-unit="${safe(k.unit)}" data-dec="${dec}">—</div>
      <div class="ksub">${safe(k.sub||'')}</div>
      <div class="karrow ${acls}"><span class="ad">${arrow}</span></div>
      <svg class="spark" viewBox="0 0 100 24" preserveAspectRatio="none">${sparkPath(k.key,col)}</svg>
    </div>`;
  }).join('');
  document.querySelectorAll('.kval').forEach(n=>{
    const v=parseFloat(n.dataset.val);
    countUp(n, isNaN(v)?null:v, n.dataset.unit, parseInt(n.dataset.dec));
  });
}
function sparkPath(key,col){
  // 确定性伪 sparkline（演示视觉，颜色随 KPI 语义）
  col = col || 'rgba(67,213,255,.55)';
  let seed=0; for(const c of key) seed=(seed*31+c.charCodeAt(0))&0xffff;
  const pts=[]; for(let i=0;i<11;i++){ seed=(seed*1103515245+12345)&0x7fffffff; pts.push(4+(seed%15)); }
  const d=pts.map((y,i)=>`${i*10},${24-y}`).join(' ');
  const fill=`0,24 ${d} 100,24`;
  const fc=col.replace(/[\d.]+\)$/,'.10)');
  return `<polygon points="${fill}" fill="${fc}" stroke="none"/><polyline points="${d}" fill="none" stroke="${col}" stroke-width="1.5"/>`;
}

/* ---------- chips ---------- */
function renderChips(chips){
  if(!chips||!chips.length) return;
  const cls=t=>/意愿/.test(t)?'c-will':(/供给|骑手/.test(t)?'c-supply':(/合单|兜底/.test(t)?'c-bundle':''));
  $('chips').innerHTML = chips.map(c=>`<div class="chip skeleton ${cls(c.title)}">
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
  const pct = imp.cost_pct;   // 真值 68.6744
  // 双柱：贪心成本 vs v4 成本（v4 相对贪心的比例 → 柱长）
  const gC=g.expected_cost, aC=a.expected_cost;
  const ratio = (gC&&aC!=null)? Math.max(4, aC/gC*100) : 100;
  const heroHtml = (pct!=null && gC && aC!=null) ? `
    <div class="bl-hero">
      <div class="big">−${Number(pct).toFixed(2)}<span class="pc">%</span></div>
      <div class="hl">
        <div class="ht">期望履约成本（成本口径，纯贪心真跑 vs AutoSolver v4）</div>
        <div class="hsub">贪心基线 <b>${gC.toLocaleString()}</b> → AutoSolver <b>${aC.toLocaleString()}</b>，
          降本 <b>${(gC-aC).toLocaleString()}</b>（全场最硬真值）</div>
      </div>
      ${sb?`<div class="bl-stamp">严格优于<br>(成本口径)</div>`:''}
    </div>
    <div class="bl-bars">
      <div class="bl-bar greedy"><span class="bn">贪心基线</span>
        <span class="track"><span class="fill" style="width:0%" data-w="100"></span></span>
        <span class="bv">${gC.toLocaleString()}</span></div>
      <div class="bl-bar v4"><span class="bn">AutoSolver</span>
        <span class="track"><span class="fill" style="width:0%" data-w="${ratio.toFixed(1)}"></span></span>
        <span class="bv">${aC.toLocaleString()}</span></div>
    </div>` : '';

  $('baseline').innerHTML = heroHtml + `<table class="btable">
    <thead><tr><th>对比指标</th><th>传统贪心基线</th><th>AutoSolver</th><th>改善</th></tr></thead>
    <tbody>${rows.map(r=>`<tr><td>${r[0]}</td><td class="val">${r[1]}</td><td class="val good">${r[2]}</td><td>${safe(r[3])}</td></tr>`).join('')}</tbody>
  </table>
  <div class="tiny" style="margin-top:7px;color:${sb?'var(--green2)':'var(--red)'};font-weight:800">
    ${sb?'✓ 严格优于（成本口径：期望成本更低 + 覆盖不更差）':'未达严格优于'} ·
    <span class="muted">基线=纯贪心真实运行；不宣称省骑手</span></div>`;
  // 柱长入场动画
  requestAnimationFrame(()=>setTimeout(()=>{
    document.querySelectorAll('.bl-bar .fill').forEach(f=>{ f.style.width=f.dataset.w+'%'; });
  },60));
}

/* ---------- decision ---------- */
function renderDecision(d){
  if(!d||!d.available){ $('decision').innerHTML='<div class="empty-ph">无合单组</div>'; return; }
  const riders = (d.riders||[]).map(r=>`<div class="rider">
    ${avatarHtml(r.id)}
    <div><div class="rid">${safe(r.id)}</div>
      <div class="rm"><span style="color:var(--green2);font-weight:800">接单意愿 ${r.willingness!=null?(r.willingness*100).toFixed(0)+'%':'—'}</span>${r.score!=null?` · 分数 <span style="color:var(--green2);font-weight:800">${Number(r.score).toFixed(2)}</span>`:''}<span class="real-dot" style="margin-left:4px"></span> · <span style="color:var(--muted2)">距离 ${r.distance_km}km<span class="demo-tag">演示</span></span></div></div>
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

/* 确定性伪随机（seed=20260620）—— mulberry32，保证每次刷新路网完全一致 */
function mulberry32(seed){
  let a=seed>>>0;
  return function(){
    a|=0; a=(a+0x6D2B79F5)|0;
    let t=Math.imul(a^(a>>>15),1|a);
    t=(t+Math.imul(t^(t>>>7),61|t))^t;
    return ((t^(t>>>14))>>>0)/4294967296;
  };
}

/* P0-1（iter-04）：程序化生成「暗色城市街道地图」SVG 底图（确定性 seed=20260620）。
 * 目标：对标高德/Google 暗色地图——中性灰底 + 细密不规则路网 + 大小不一街区瓦片 +
 * 去饱和暖灰主干道（轻微贝塞尔弯曲）+ 河流。底图本身近乎中性灰，彩色只留给上层
 * 节点/连线/聚合圈/河流，使「绿色权重」显著下降。纯演示沙盘，不接外部地图 API、不宣称 GPS。*/
function buildStreetTiles(W,H){
  const R=mulberry32(20260620);
  const f=(n)=>(+n).toFixed(1);
  const parts=[];

  // —— 底：中性暗底（#07100e 系，去青绿）——
  parts.push(`<rect x="0" y="0" width="${W}" height="${H}" fill="url(#mgBase)"/>`);

  // —— 街区瓦片（block fills）：递归切分网格 -> 大小不一、随机留白、提亮到可见。
  //    用中性深蓝灰(#141d24~#1b2730)，营造真实瓦片质感（非格纸）。——
  let blocks='';
  // 把画布切成不等宽的列带 / 行带（间距不等），再在每个单元里随机决定是否填街区。
  const colEdges=[0]; { let x=0; while(x<W-18){ x+=W*(0.045+R()*0.055); colEdges.push(Math.min(W,x)); } if(colEdges[colEdges.length-1]<W) colEdges.push(W); }
  const rowEdges=[0]; { let y=0; while(y<H-16){ y+=H*(0.05+R()*0.06); rowEdges.push(Math.min(H,y)); } if(rowEdges[rowEdges.length-1]<H) rowEdges.push(H); }
  const blockTones=['#121b22','#16212a','#19262f','#1b2a33','#0f181e'];
  for(let i=0;i<colEdges.length-1;i++) for(let j=0;j<rowEdges.length-1;j++){
    const r=R(); if(r<0.20) continue;                   // 部分留空（空地/广场/水域）
    const x0=colEdges[i], x1=colEdges[i+1], y0=rowEdges[j], y1=rowEdges[j+1];
    const pad=1.5+R()*3.5;
    let bx=x0+pad+(R()-0.5)*3, by=y0+pad+(R()-0.5)*3;
    let bw=(x1-x0)-pad*2-(R()*6), bh=(y1-y0)-pad*2-(R()*6);
    if(bw<5||bh<5) continue;
    // 偶尔把相邻两格并成一个大街区，制造大小不一
    if(R()<0.16 && i<colEdges.length-2){ bw += (colEdges[i+2]-x1); }
    if(R()<0.13 && j<rowEdges.length-2){ bh += (rowEdges[j+2]-y1); }
    const tone=blockTones[(R()*blockTones.length)|0];
    const op=(0.55+R()*0.42).toFixed(2);
    const rx=(0.5+R()*2).toFixed(1);
    blocks+=`<rect x="${f(bx)}" y="${f(by)}" width="${f(bw)}" height="${f(bh)}" rx="${rx}" fill="${tone}" opacity="${op}"/>`;
  }
  parts.push(`<g class="map-blocks">${blocks}</g>`);

  // —— 水系（iter-5：主河 + 一条次级支流/水道，非对称走向，逼近目标底图的水系）——
  let water='';
  // 主河：横向贯穿、弯曲
  {
    const y0=H*(0.18+R()*0.14);
    let d=`M ${-20} ${f(y0)}`;
    let x=-20,y=y0;
    while(x<W+20){
      x+=W/7; y+=(R()-0.42)*H*0.17;
      y=Math.max(40,Math.min(H-40,y));
      d+=` Q ${f(x-W/14)} ${f(y+(R()-0.5)*32)} ${f(x)} ${f(y)}`;
    }
    water+=`<path d="${d}" fill="none" stroke="url(#mgRiver)" stroke-width="${(12+R()*7).toFixed(1)}" stroke-linecap="round" opacity="0.42"/>`;
    water+=`<path d="${d}" fill="none" stroke="#2b6f86" stroke-width="1.0" opacity="0.4"/>`;
  }
  // 支流/水道：斜向、较细，从右下汇入，打破对称
  {
    let x=W*(0.58+R()*0.18), y=H+18;
    let d=`M ${f(x)} ${f(y)}`;
    while(y>H*0.22){
      x+=(R()-0.62)*W*0.12; y-=H*(0.13+R()*0.06);
      x=Math.max(20,Math.min(W-20,x));
      d+=` Q ${f(x+(R()-0.5)*40)} ${f(y+H*0.05)} ${f(x)} ${f(y)}`;
    }
    water+=`<path d="${d}" fill="none" stroke="url(#mgRiver)" stroke-width="${(6+R()*5).toFixed(1)}" stroke-linecap="round" opacity="0.34"/>`;
    water+=`<path d="${d}" fill="none" stroke="#2b6f86" stroke-width="0.9" opacity="0.34"/>`;
  }
  parts.push(`<g class="map-water">${water}</g>`);

  // —— 次级街道 / 巷道：密度 ~2.5x，中性灰，间距不等 + 断头路/丁字路口，避免方格纸 ——
  let minor='';
  const STREET='#3a4956', STREET2='#303c45';   // 中性灰（非青绿，略提亮增强城市纹理）
  // 竖向次级街道：间距不等（iter-5：再加密一档，间距缩小）
  { let bx=0; while(bx<W){
      bx += W*(0.020+R()*0.030);            // 不等间距，密度再提升
      if(bx>=W) break;
      // 部分街道为「断头路」：只画到画面中段随机位置
      const stub=R()<0.22;
      const yEnd=stub ? H*(0.25+R()*0.55) : H+4;
      const yStart=stub&&R()<0.5 ? H*(R()*0.4) : -4;
      let d=`M ${f(bx)} ${f(yStart)}`; let yy=yStart;
      while(yy<yEnd){ yy+=H*(0.055+R()*0.04); const jx=bx+(R()-0.5)*9; d+=` L ${f(jx)} ${f(Math.min(yEnd,yy))}`; }
      const op=(0.42+R()*0.28).toFixed(2);
      minor+=`<path d="${d}" fill="none" stroke="${R()<0.5?STREET:STREET2}" stroke-width="${(0.7+R()*0.6).toFixed(1)}" opacity="${op}"/>`;
  }}
  // 横向次级街道：间距不等（iter-5：再加密一档）
  { let by=0; while(by<H){
      by += H*(0.026+R()*0.038);
      if(by>=H) break;
      const stub=R()<0.22;
      const xEnd=stub ? W*(0.25+R()*0.55) : W+4;
      const xStart=stub&&R()<0.5 ? W*(R()*0.4) : -4;
      let d=`M ${f(xStart)} ${f(by)}`; let xx=xStart;
      while(xx<xEnd){ xx+=W*(0.045+R()*0.035); const jy=by+(R()-0.5)*9; d+=` L ${f(Math.min(xEnd,xx))} ${f(jy)}`; }
      const op=(0.42+R()*0.28).toFixed(2);
      minor+=`<path d="${d}" fill="none" stroke="${R()<0.5?STREET:STREET2}" stroke-width="${(0.7+R()*0.6).toFixed(1)}" opacity="${op}"/>`;
  }}
  // 斜向次级街巷（iter-5）：少量倾斜短街，制造非正交交叉点、打破方格纸感
  for(let k=0;k<26;k++){
    const ox=R()*W, oy=R()*H;
    const ang=(R()<0.5? 0.32:-0.32)+(R()-0.5)*0.5;   // ~±18° 倾斜
    const seg=3+((R()*3)|0);
    let d=`M ${f(ox)} ${f(oy)}`, px=ox, py=oy;
    for(let s=0;s<seg;s++){
      const ln=18+R()*40;
      px+=Math.cos(ang)*ln+(R()-0.5)*8; py+=Math.sin(ang)*ln+(R()-0.5)*8;
      d+=` L ${f(px)} ${f(py)}`;
    }
    minor+=`<path d="${d}" fill="none" stroke="${R()<0.5?STREET:STREET2}" stroke-width="${(0.6+R()*0.6).toFixed(1)}" opacity="${(0.32+R()*0.26).toFixed(2)}"/>`;
  }
  // 散布的短巷/丁字小路（iter-5：数量加倍，局部加密、随机朝向），强化高密度瓦片纹理
  for(let k=0;k<88;k++){
    const ox=R()*W, oy=R()*H, len=12+R()*44, horiz=R()<0.5;
    const ex=horiz?ox+len*(R()<0.5?1:-1):ox, ey=horiz?oy:oy+len*(R()<0.5?1:-1);
    minor+=`<line x1="${f(ox)}" y1="${f(oy)}" x2="${f(ex)}" y2="${f(ey)}" stroke="${STREET2}" stroke-width="${(0.6+R()*0.5).toFixed(1)}" opacity="${(0.3+R()*0.25).toFixed(2)}"/>`;
  }
  parts.push(`<g class="map-minor">${minor}</g>`);

  // —— 主干道（去饱和暖灰、略亮略宽、轻微贝塞尔弯曲）——
  let major='';
  const MAJ='#4a5560', MAJ2='#5a6470';   // 去饱和暖灰
  // 用平滑曲线画一条主干道（沿主轴轻微蛇形）
  const drawArtery=(pts,wMain,wHi)=>{
    if(pts.length<2) return '';
    let d=`M ${f(pts[0][0])} ${f(pts[0][1])}`;
    for(let i=1;i<pts.length;i++){
      const p0=pts[i-1], p1=pts[i];
      const mx=(p0[0]+p1[0])/2, my=(p0[1]+p1[1])/2;
      d+=` Q ${f(p0[0])} ${f(p0[1])} ${f(mx)} ${f(my)}`;
    }
    d+=` L ${f(pts[pts.length-1][0])} ${f(pts[pts.length-1][1])}`;
    let s=`<path d="${d}" fill="none" stroke="${MAJ}" stroke-width="${wMain}" stroke-linecap="round" opacity="0.78"/>`;
    s+=`<path d="${d}" fill="none" stroke="${MAJ2}" stroke-width="${wHi}" stroke-linecap="round" opacity="0.5"/>`;
    return s;
  };
  // 2 条竖主干（iter-5：非对称走向——基线随机偏移 + 沿途单向漂移，非镜像对称）
  [W*0.26,W*0.62].forEach((bx0)=>{
    const pts=[]; let yy=-12, bx=bx0+(R()-0.5)*60, drift=(R()-0.5)*0.06;
    while(yy<H+12){ bx+=drift*H*0.16; pts.push([bx+(R()-0.5)*44, yy]); yy+=H*0.15; }
    major+=drawArtery(pts,2.6,0.9);
  });
  // 2 条横主干（非对称走向）
  [H*0.30,H*0.70].forEach((by0)=>{
    const pts=[]; let xx=-12, by=by0+(R()-0.5)*54, drift=(R()-0.5)*0.05;
    while(xx<W+12){ by+=drift*W*0.14; pts.push([xx, by+(R()-0.5)*42]); xx+=W*0.13; }
    major+=drawArtery(pts,2.6,0.9);
  });
  // 2 条对角主轴（iter-5：增加一条反向对角，制造更多主干交叉点、破对称）
  {
    const pts=[]; let x=-12,y=H*0.86;
    while(x<W+12){ pts.push([x, y+(R()-0.5)*46]); x+=W*0.11; y-=H*0.86*0.11; }
    major+=drawArtery(pts,2.4,0.8);
  }
  {
    const pts=[]; let x=-12,y=H*0.10;
    while(x<W+12){ pts.push([x, y+(R()-0.5)*44]); x+=W*0.12; y+=H*0.80*0.12; }
    major+=drawArtery(pts,2.2,0.75);
  }
  parts.push(`<g class="map-major">${major}</g>`);
  return parts.join('');
}

function renderMap(m){
  mapData=m;
  const svg=$('mapsvg'); svg.innerHTML='';
  const W=m.canvas?.w||1000, H=m.canvas?.h||640;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);

  // 暗色城市路网底图（程序化生成·seed20260620）渐变/滤镜定义
  const defs=el('defs');
  defs.innerHTML=`
    <radialGradient id="mgBase" cx="50%" cy="46%" r="78%">
      <stop offset="0%" stop-color="#0c151a"/><stop offset="58%" stop-color="#0a1115"/>
      <stop offset="100%" stop-color="#07100e"/></radialGradient>
    <linearGradient id="mgRiver" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#15414f"/><stop offset="50%" stop-color="#1c5e74"/>
      <stop offset="100%" stop-color="#15414f"/></linearGradient>
    <filter id="nodeGlow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge>
      <feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
  svg.appendChild(defs);

  // 路网底图（一次性 innerHTML 注入，确定性）
  const base=el('g',{class:'map-tiles'});
  base.innerHTML=buildStreetTiles(W,H);
  svg.appendChild(base);
  // 暗角(vignette)叠层 — 让边缘下沉，中心更聚焦，贴近暗色地图瓦片观感
  svg.appendChild(el('rect',{x:0,y:0,width:W,height:H,fill:'url(#mgVignette)',class:'map-vignette'}));
  // vignette 渐变需在 defs；补一个
  defs.innerHTML+=`<radialGradient id="mgVignette" cx="50%" cy="48%" r="70%">
      <stop offset="55%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#040a0d" stop-opacity="0.55"/></radialGradient>`;

  const root=el('g',{id:'maproot'});
  svg.appendChild(root);

  // 商圈区块（柔光）—— 簇收紧后半径收小，作为该商圈的「光晕底座」叠在路网上
  // P1-6：底图中性化后压低商圈柔光，避免整体绿色权重过高
  (m.districts||[]).forEach(d=>{
    root.appendChild(el('circle',{cx:d.x,cy:d.y,r:52,fill:'rgba(70,240,168,.028)',stroke:'none'}));
  });

  // 圈：真合单组(亮绿实线) + 多骑手兜底组(青虚线)。语义区分(P0-3)，限量避免满屏。
  // 优先显任务合单圈；兜底圈在 large_seed301 上占多数，与「兜底」叙事自洽。
  const bsorted=(m.bundles||[]).slice().sort((a,b)=> (a.kind==='task_bundle'?-1:0)-(b.kind==='task_bundle'?-1:0));
  bsorted.slice(0,14).forEach(b=>{
    const kind=b.kind==='task_bundle'?'task_bundle':'multi_courier';
    root.appendChild(el('circle',{cx:b.cx,cy:b.cy,r:b.r,class:'bundle-ring '+kind}));
    const t=el('text',{x:b.cx,y:b.cy-b.r-4,
      fill:kind==='task_bundle'?'#46f0a8':'#43d5ff','font-size':'11','font-weight':'800','text-anchor':'middle'});
    t.textContent=b.label; root.appendChild(t);
  });

  // 候选虚线（先画，底层）。P0-4：限量降噪——只「点亮」焦点商圈/featured 组附近的候选
  // 虚线（强调收敛感），其余候选极淡甚至隐藏，消除满图交叉噪声、突出焦点簇整洁。
  const candG=el('g',{id:'candedges'});
  const fg=m.featured_group;
  const allCand=(m.candidate_edges||[]);
  // 每条候选线到 featured 组中心的距离（用线段中点近似）
  const FG_R = fg ? (fg.r + 120) : 9999;   // featured 圈附近的影响半径
  const NEAR_CAP = 18;                      // 焦点附近最多点亮多少条，避免过密
  let nearCount=0;
  allCand.forEach(e=>{
    const mx=(e.x1+e.x2)/2, my=(e.y1+e.y2)/2;
    let near=false;
    if(fg){
      const d=Math.hypot(mx-fg.cx, my-fg.cy);
      // 端点也算进焦点圈内则视为「焦点候选」
      const d1=Math.hypot(e.x1-fg.cx,e.y1-fg.cy), d2=Math.hypot(e.x2-fg.cx,e.y2-fg.cy);
      near = (Math.min(d,d1,d2) < FG_R) && (nearCount < NEAR_CAP);
    }
    const ln=el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,
      class:'cand-edge'+(near?' cand-focus':' cand-dim')});
    if(near) nearCount++;
    candG.appendChild(ln);
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

  // 骑手（发光叠在路网上；hover 放大）
  (m.couriers||[]).forEach(c=>{
    const r0=c.active?5.5:4;
    const node=el('circle',{cx:c.x,cy:c.y,r:r0,'data-r':r0,
      class:c.active?'courier-node node-hit glow-node':'courier-idle node-hit','data-courier':c.id});
    node.addEventListener('mouseenter',ev=>{ showTip(ev,`骑手 ${c.id}\n${c.active?'已采纳派单(真)':'未采纳'}`); node.setAttribute('r',(r0*1.7).toFixed(1)); });
    node.addEventListener('mouseleave',()=>{ hideTip(); node.setAttribute('r',r0); });
    root.appendChild(node);
  });

  // 订单（任务）节点 —— 点击联动右侧决策解释聚焦(P1-6)；发光 + hover 放大
  (m.tasks||[]).forEach(t=>{
    const cls=t.risk==='high'?'task-high':(t.risk==='mid'?'task-mid':'task-low');
    const node=el('circle',{cx:t.x,cy:t.y,r:6,'data-r':'6',class:cls+' node-hit glow-node '+(t.risk==='high'?'pulse':''),'data-task':t.id});
    node.addEventListener('mouseenter',ev=>{ showTip(ev,`订单 ${t.id}\n意愿派生 ${t.willingness_repr} · 风险 ${t.risk}`); node.setAttribute('r','9.5'); });
    node.addEventListener('mouseleave',()=>{ hideTip(); node.setAttribute('r','6'); });
    node.addEventListener('click',()=>focusTaskDecision(t.id, node));
    root.appendChild(node);
  });

  // P0-2：代表性任务组 G-XXX 风格浮卡（默认显示，叠在路网/聚合圈旁，贴近目标稿）
  renderFeaturedGroup(m.featured_group, root, W, H);

  applyMapTransform();
}

/* P0-2：地图内的 G-028 风格浮卡（SVG foreignObject 锚定到代表组坐标） */
function renderFeaturedGroup(fg, root, W, H){
  if(!fg) return;
  // 高亮聚合圈（更亮的发光环）
  root.appendChild(el('circle',{cx:fg.cx,cy:fg.cy,r:(fg.r+4),class:'fg-ring'}));
  // 卡片放在圈右侧（若靠右则放左侧），用 foreignObject 承载 HTML
  const cardW=176, cardH=fg.is_bundle?108:98;
  let fx=fg.cx+fg.r+12, fy=fg.cy-cardH/2;
  if(fx+cardW>W-8) fx=fg.cx-fg.r-12-cardW;
  fy=Math.max(8,Math.min(H-cardH-8,fy));
  const modeLabel=fg.is_bundle?`${fg.n_tasks}单合单`:`${fg.n_couriers}骑手兜底`;
  const riskCls=fg.risk_text==='中高'?'rk-high':(fg.risk_text==='中'?'rk-mid':'rk-low');
  const fo=el('foreignObject',{x:fx.toFixed(1),y:fy.toFixed(1),width:cardW,height:cardH,class:'fg-fo'});
  fo.innerHTML=`<div xmlns="http://www.w3.org/1999/xhtml" class="fg-card">
    <div class="fg-h">订单组 ${safe(fg.group_id)} <span class="fg-mode">${modeLabel}</span></div>
    <div class="fg-row"><span>预计送达</span><span class="fg-v">${fg.eta_min}分钟<i class="demo-tag">演示</i></span></div>
    <div class="fg-row"><span>无人接单风险</span><span class="fg-v ${riskCls}">${safe(fg.risk_text)}</span></div>
    <div class="fg-row"><span>候选方案数</span><span class="fg-v">${fg.n_candidates}个</span></div>
  </div>`;
  root.appendChild(fo);
  // 连接圈与卡的细引导线
  root.appendChild(el('line',{x1:fg.cx,y1:fg.cy,x2:(fx<fg.cx?fx+cardW:fx).toFixed(1),y2:(fy+18).toFixed(1),
    stroke:'rgba(67,213,255,.5)','stroke-width':'1','stroke-dasharray':'3 3'}));
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
function focusTaskDecision(taskId, node){
  // 高亮选中节点
  document.querySelectorAll('.node-hit.sel').forEach(n=>n.classList.remove('sel'));
  if(node) node.classList.add('sel');
  // 找到包含该任务的采纳组（真值 solution），客户端据 map 真值即时构建决策卡聚焦它
  const story=LAST_STORY;
  let built=null;
  if(story && story.map){
    const edges=(story.map.accepted_edges||[]).filter(e=>(e.tasks||[]).includes(taskId));
    if(edges.length){
      const tk=edges[0].task_key, tids=edges[0].tasks||[];
      const b=(story.map.bundles||[]).find(bb=>bb.task_key===tk);
      const couriers=[...new Set(edges.map(e=>e.courier))];
      const isBundle=tids.length>1, isMulti=couriers.length>1;
      built={
        available:true,
        group_id:'G-'+taskId.replace(/[^0-9A-Za-z]/g,'').slice(-4).toUpperCase(),
        n_tasks:tids.length, n_couriers:couriers.length,
        is_bundle:isBundle, is_multi_courier:isMulti, use_bundle:isBundle,
        district:(story.map.districts||[{}])[0]?.name,
        eta_min:isBundle?12:(isMulti?18:22),
        distance_km:(2+(taskId.length%30)/10).toFixed(1),
        riders:edges.map(e=>({id:e.courier,willingness:e.willingness,score:e.score,distance_km:(0.8+(e.courier.length%30)/10).toFixed(1)})),
        reasons:[
          `订单 ${taskId} 接单意愿派生自真实 willingness，选择`+(isBundle?'合单优先':(isMulti?'多骑手兜底':'单骑手'))+'策略',
          isMulti?'多骑手分摊兜底，对冲低意愿拒单风险':(isBundle?'合单后单位履约成本下降':'单骑手直派，路径最短'),
          'AutoSolver 期望成本口径下为该组最优派单',
        ],
      };
    }
  }
  if(built){ renderDecision(built); }
  // 滚动到决策面板
  const dec=$('decision'); if(dec){ dec.closest('.panel').scrollIntoView({behavior:'smooth',block:'nearest'}); }
  $('phase').textContent=`已聚焦订单 ${taskId} 所在派单组（决策解释联动·真值意愿/分数高亮·演示 ETA/距离灰显）`;
}
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

/* ---------- 自进化（iter-2：真值透传，删假占位 #18-21） ---------- */
function renderEvo(evo){
  const body=$('evobody');
  if(!evo){ return; }
  const card=evo.promoted_card;     // 真值或 null
  const reg=evo.registry_summary;   // 真值或 null
  const causal=evo.causal_demo;     // 真值或 null

  // 若整段真值都拿不到 → 只保留机制流程图 + 诚实声明（绝不补假数据）
  if(!card && !reg && !causal){
    body.innerHTML=`<div class="evo-honesty">本次未取到 report.evolution 真值（机制可独立验证，但
      <b>对最终派单成绩零贡献·stub 无 live LLM</b>）。仅展示上方 5 步机制流程图。</div>`;
    return;
  }

  // ① 真·promoted 策略卡
  let promotedHtml='';
  if(card){
    const delta = card.improvement_vs_baseline;
    const ho = card.heldout_mean, bh = card.baseline_heldout_mean;
    promotedHtml=`<div class="evo-card promoted">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span class="evo-pid">${safe(card.strategy_id||'—')}</span>
        <span class="risk-badge lv-low">${safe(card.status||'—')}</span>
      </div>
      <div class="evo-kv">
        <span class="k">operator/代</span><span class="v">${safe(card.operator||'—')} · gen ${safe(card.generation??'—')}</span>
        <span class="k">parent</span><span class="v">${safe(card.parent||'—')}</span>
        <span class="k">ReEvo directive</span><span class="v">${safe(card.directive||'none')}</span>
        <span class="k">安全门</span><span class="v">${card.safety_passed?'✓ passed':safe(card.safety_reason||'—')}</span>
        <span class="k">质量门决策</span><span class="v">${safe(card.last_decision||'—')}</span>
        <span class="k">held-out 均值</span><span class="v">${ho!=null?Number(ho).toFixed(2):'—'} vs ${bh!=null?Number(bh).toFixed(2):'—'}</span>
      </div>
      ${delta!=null?`<div class="evo-delta">改进量 Δ = ${Number(delta).toFixed(2)}
        <span class="corner">机制内部指标·非派单成绩</span></div>`:''}
    </div>`;
  }

  // ② 注册表真实条数 + directive 直方图（真值）
  let regHtml='';
  if(reg){
    const hist=reg.directive_histogram||{};
    const keys=Object.keys(hist);
    const mx=Math.max(1,...keys.map(k=>hist[k]));
    const bars=keys.sort((a,b)=>hist[b]-hist[a]).map(k=>
      `<div class="dh-row"><span class="dn">${safe(k)}</span>
       <span class="dt"><span class="df" style="width:${(hist[k]/mx*100).toFixed(0)}%"></span></span>
       <span class="dc">${hist[k]}</span></div>`).join('');
    regHtml=`<div class="evo-card">
      <div class="evo-kv">
        <span class="k">注册表策略总数</span><span class="v">${reg.total_strategies??'—'} 条</span>
        <span class="k">accepted/候选</span><span class="v">${reg.n_accepted??'—'} 条</span>
        <span class="k">promoted</span><span class="v">${(reg.promoted||[]).join(', ')||'—'}</span>
        <span class="k">来源</span><span class="v">${safe(reg.source||'—')}</span>
      </div>
      ${keys.length?`<div class="evo-sub" style="margin-top:8px">ReEvo directive 直方图（真实计数）</div>${bars}`:''}
    </div>`;
  }

  // ③ 因果证据：同 parent + 不同 directive → 不同 rank 代码（真值，live runnable probe）
  let causalHtml='';
  if(causal && causal.variants && causal.variants.length){
    const rows=causal.variants.map(v=>`<div class="causal-item">
      <span class="cd-dir">&lt;${safe(v.directive)}&gt;</span>
      <code class="cd-code">${safe(v.final_key_line)}</code></div>`).join('');
    causalHtml=`<div class="evo-sub" style="margin-top:10px">因果探针：同一 parent (${safe(causal.parent||'—')}) + 不同 ReEvo lesson →
      生成不同 rank 代码 · ${causal.distinct_final_lines} 种不同代码 · ${causal.causal_proven?'<span style="color:var(--green2)">causal_proven=True</span>':'未证'}</div>
      <div class="causal-list">${rows}</div>`;
  }

  body.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px">
      <span class="shield"><span class="si">🛡️</span>当前正式求解器 AutoSolver v4 (solver_v4.py) · 稳定运行中</span>
      <span class="tiny muted">实验策略只有过安全门+质量门才进候选池，不污染正式求解器</span>
    </div>
    <div class="evo-grid2">
      <div><div class="evo-sub">① 已晋级策略（promoted · 真值）</div>${promotedHtml||'<div class="empty-ph">无 promoted（N/A）</div>'}${causalHtml}</div>
      <div><div class="evo-sub">② 策略注册表（真实条数 + directive 直方图）</div>${regHtml||'<div class="empty-ph">注册表不可读</div>'}</div>
    </div>
    <div class="evo-honesty">${safe(evo.honesty||'')}
      <b>机制可验证 · 对最终派单成绩零贡献 · stub 无 live LLM。</b></div>`;
}

/* ---------- ROI（P1-5：可追溯换算链） ---------- */
let costImprovePct = 18;       // 默认；推理后绑真实成本改善
let costImproveIsReal = false; // 是否已绑定真实 68.67%
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
  // 追溯链：把每一步带数字显式写出，「演示假设」从口号变公式
  const anchor = costImproveIsReal
    ? `<span class="anchor">${costImprovePct.toFixed(2)}%（真实成本改善·成本口径·纯贪心 2097.658→657.104）</span>`
    : `<span class="anchor">${costImprovePct.toFixed(2)}%（默认假设，推理后绑真实成本改善）</span>`;
  $('roi-chain').innerHTML=`
    <div>换算链（每步可追溯）：</div>
    <div class="cl-line">减少损失/日 = 日单量 × 无人接单下降比例 × 单均亏损 × 商圈覆盖率</div>
    <div class="cl-line">= ${orders.toLocaleString()} × ${anchor} × ¥${loss} × ${(coverage*100).toFixed(0)}%（${districts}/100 商圈）</div>
    <div class="cl-line">= <b>¥${daily.toLocaleString()}/日</b> → 月 <b>¥${(daily*30).toLocaleString()}</b></div>
    <div style="margin-top:4px">注：下降比例锚定<b>真实成本改善 68.67%</b>（非派单成绩夸大）；单均亏损/覆盖率为演示假设，可在上方输入框调参重算。</div>`;
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
  if(p.bundle_fraction!=null) chips.push({icon:'🗂️',title:'合单/兜底潜力',value:`潜力占比 ${(p.bundle_fraction*100).toFixed(1)}%`,delta:p.bundle_fraction>=0.35?'合单/兜底机会密集':'机会一般'});
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
    const pct=d.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(80,pct); costImproveIsReal=true; recomputeRoi(); } }
  else if(type==='result'){ applyStory(d.story); }
  else if(type==='error'){ $('phase').textContent='出错：'+(d.message||''); }
}
let LAST_STORY=null;
function applyStory(s){
  if(!s) return;
  LAST_STORY=s;
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
  if(s.evolution) renderEvo(s.evolution);   // iter-2：真值自进化
  if(s.solver_used) $('solverused').textContent=s.solver_used;
  // 收敛动画
  setTimeout(convergeEdges, 300);
  // ROI 系数绑真实成本改善
  const pct=s.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(80,pct); costImproveIsReal=true; }
  recomputeRoi();
}
function finishRun(){
  $('runbtn').disabled=false;
  $('runlight').classList.add('idle'); $('runtext').textContent='完成';
  stopTimer();
  $('phase').textContent='推理完成 · 全量真值已回填（约 10 秒内 SSE 逐事件）';
}

/* ---------- 初始骨架（秒开）+ 自动推理（P0-1：加载即有数据，便于截图/答辩） ---------- */
async function loadSkeleton(){
  renderScenes(null); renderRings();
  RINGS.forEach(r=> setRing(r[0],'wait'));
  // P0-3：idle 首屏不留空白 —— KPI 灰显骨架 + 各面板「待推理」角标
  renderKpiSkeleton();
  $('risk').innerHTML=skeletonPanel('感知模块据尺寸解耦特征当场判风险');
  $('strategy').innerHTML=skeletonPanel('Planner 镜像解读策略链');
  $('decision').innerHTML=skeletonPanel('点击地图节点或推理后聚焦合单组');
  $('cert').innerHTML=skeletonPanel('solver_v4 求解后回填 gap·r1 证书');
  $('candidates').innerHTML=`<div style="grid-column:1/-1">${skeletonPanel('方案 A/B/C 自动评估')}</div>`;
  $('baseline').innerHTML=skeletonPanel('纯贪心真跑 vs AutoSolver 对比');
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
  // 加载即自动跑一次真实求解，使全部面板(KPI/Baseline/决策/候选/证书/自进化)无需点击即有真值。
  if(!AUTORUN_DONE){ AUTORUN_DONE=true; setTimeout(runStream, 350); }
}
let AUTORUN_DONE=false;

/* ---------- 折叠 / 场景点击 ---------- */
$('evotoggle').onclick=()=> $('evopanel').classList.toggle('collapsed');
document.addEventListener('click',e=>{
  const sc=e.target.closest('.scene');
  if(sc){
    document.querySelectorAll('.scene').forEach(n=>n.classList.toggle('active',n===sc));
    switchScene(sc.dataset.id);
  }
});
/* P1-7：点击场景 → 拉 /api/generate 脱敏样例，感知真实重判 */
async function switchScene(sceneId){
  $('phase').textContent='切换场景 · 合成脱敏样例并重跑感知判定…';
  try{
    const r=await(await fetch('/api/generate?regime='+encodeURIComponent(sceneId))).json();
    if(r.status==='ok'){
      const verd={regime:r.regime_verdict.regime,rules:r.regime_verdict.rules};
      $('verdict-name').textContent='AI 判定：'+(verd.regime||'—')+'（脱敏样例·真实重判）';
      $('verdict-rule').innerHTML=(verd.rules||[]).map(safe).join('<br>')||'—';
      if(r.chips) renderChips(r.chips);
      if(r.risk) renderRisk(r.risk);
      $('phase').textContent=`脱敏样例 ${r.regime_key}（T=${r.n_tasks}, 行=${r.n_rows}）→ 感知真实判出 regime=${verd.regime}（非记忆样例）`;
    }else{
      $('phase').textContent='场景生成不可用，已保留当前判定（占位）：'+(r.error||'');
    }
  }catch(err){
    $('phase').textContent='场景切换失败（占位）：'+err.message;
  }
}
$('runbtn').onclick=runStream;

/* 键盘：空格开始推理 */
document.addEventListener('keydown',e=>{
  if(e.code==='Space' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)){ e.preventDefault(); if(!$('runbtn').disabled) runStream(); }
});

loadSkeleton();
// iteration-2：自进化面板等待 SSE result.evolution 真值回填（不再注入假占位）。
$('evobody').innerHTML='<div class="empty-ph">点击「开始智能调度推理」后接入 report.evolution 真值（真·机制，stub 无 live LLM）</div>';
