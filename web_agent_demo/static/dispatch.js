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
/* iteration-16 P1-5：每场景一行极小字「看点预告」——评委点击前即知该场景演示什么，
 * 点击后由现场合成脱敏样例真 solve 兑现（与 scene-matrix 真值一致，不写死输出）。 */
const SCENES = [
  {id:'peak',   ico:'📈', t:'午高峰爆单',   d:'订单量激增 156%',     hint:'大规模高负载·v4 显著压成本'},
  {id:'rain',   ico:'🌧️', t:'雨天低接单意愿', d:'骑手接单意愿下降',  hint:'低意愿·多骑手兜底防拒单'},
  {id:'scarce', ico:'🧍', t:'骑手稀缺商圈', d:'可用骑手紧张',        hint:'骑手瓶颈·贪心欠覆盖(18/30)→v4 全覆盖'},
  {id:'bundle', ico:'🗂️', t:'合单机会密集', d:'多订单同向集中',      hint:'合单密集·兜底择优降单位成本'},
  {id:'newshop',ico:'🏪', t:'新店突发订单', d:'新店订单突然增加',    hint:'高噪声不确定·稳健择优'},
];
/* iteration-15：当前选中的业务场景 id（用户点击场景后置位）。null=头牌默认态。
 * renderScenes 在每次感知/verdict 回填时会重绘场景列表——必须据此保住用户选中高亮，
 * 否则求解完成回填 regime 会把高亮错误地跳回 bundle。 */
let SELECTED_SCENE=null;
function renderScenes(activeRegime){
  $('scenelist').innerHTML = SCENES.map((s,i)=>{
    // 优先：用户显式选中的场景；否则头牌默认态用 regime 推断（bundle-heavy→bundle，第4项）
    const act = SELECTED_SCENE!=null
      ? (s.id===SELECTED_SCENE)
      : ((activeRegime==='bundle-heavy' && s.id==='bundle') || (!activeRegime && i===3));
    return `<div class="scene ${act?'active':''}" data-id="${s.id}" title="${safe(s.hint||'')}">
      <div class="si">${s.ico}</div>
      <div class="scene-tx"><div class="st">${i+1} ${safe(s.t)}</div><div class="sd">${safe(s.d)}</div>
        ${s.hint?`<div class="shint"><span class="shint-dot"></span>${safe(s.hint)}</div>`:''}</div>
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
    <div class="klbl">${safe(k.label)}<span class="pend-badge" style="margin-left:auto">待推理</span></div>
    <div class="kval kval-skel">—<span class="unit">${safe(k.unit)}</span></div>
    <div class="kdelta"><span class="skel-bar"></span></div>
    <span class="skel-shimmer"></span>
  </div>`).join('');
}
function skeletonPanel(txt){ return `<div class="empty-ph skel-ph"><span class="pend-badge">待推理</span> ${safe(txt||'加载即自动现场求解…')}</div>`; }

/* ---------- KPI ---------- */
function renderKpis(kpis){
  $('kpis').innerHTML = kpis.map(k=>{
    const arrow = k.good==='up'?'↑':(k.good==='down'?'↓':'·');
    const acls = k.good==='up'?'arrow-up':(k.good==='down'?'arrow-down-good':'arrow-neutral');
    // 真值卡：绿点高亮；演示换算卡：标签前置「演示换算」+ 右上角醒目徽标 + 虚线半透卡（kpi-demo），
    // 让评委一眼分清「真实业务真值」与「演示换算指标」，绝不被误读为真实业务成本。
    const isDemo = !!k.is_demo;
    const tag = isDemo?'<span class="kpi-demo-lbl">演示换算</span>':'<span class="real-dot"></span>';
    const corner = isDemo?'<span class="kpi-demo-badge" title="演示换算指标：非真实业务成本/财务，由真值按公式派生">演示</span>':'';
    const dec = (k.unit==='%'||k.key==='cost_index')?1:0;
    const col = k.good==='neutral'?'rgba(127,165,151,.55)':(k.good==='up'||k.good==='down'?'rgba(70,240,168,.6)':'rgba(67,213,255,.55)');
    const subTxt = safe(k.sub||'');
    return `<div class="panel kpi skeleton${isDemo?' kpi-demo':''}">
      <div class="klbl">${tag}${safe(k.label)}</div>
      <div class="kval" data-key="${k.key}" data-val="${k.value??''}" data-unit="${safe(k.unit)}" data-dec="${dec}">—</div>
      <div class="kdelta"><span class="karrow ${acls}"><span class="ad">${arrow}</span></span>${subTxt?`<span class="ksub">${subTxt}</span>`:''}</div>
      ${corner}
      <svg class="spark" viewBox="0 0 100 27" preserveAspectRatio="none">${sparkPath(k.key,col)}</svg>
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
  const pts=[]; for(let i=0;i<13;i++){ seed=(seed*1103515245+12345)&0x7fffffff; pts.push(5+(seed%17)); }
  const d=pts.map((y,i)=>`${i*(100/12)},${27-y}`).join(' ');
  const fill=`0,27 ${d} 100,27`;
  const fc=col.replace(/[\d.]+\)$/,'.13)');
  return `<polygon points="${fill}" fill="${fc}" stroke="none"/><polyline points="${d}" fill="none" stroke="${col}" stroke-width="1.6" stroke-linejoin="round"/>`;
}

/* ---------- chips（iter-12：恢复 2 行——发光圆形图标 + 「场景名主标题行」+ 指标行）----------
   场景名(scene) 由 cockpit_story 按真实感知值派生(诚实，不与真值打架)；第 1 枚天气/云雨发光图标。*/
const CHIP_TONE_ICON={will:'🌧️', supply:'🛵', bundle:'🧩'};
function renderChips(chips){
  if(!chips||!chips.length) return;
  const tone=c=>c.tone || (/意愿/.test(c.title)?'will':(/供给|骑手|可用/.test(c.title)?'supply':(/合单|兜底|潜力/.test(c.title)?'bundle':'will')));
  $('chips').innerHTML = chips.map(c=>{
    const tn=tone(c);
    let pct=c.narr_pct;
    const hasPct=pct!=null&&!isNaN(pct);
    const sign=hasPct&&pct>=0?'+':'';
    const pctStr=hasPct?`${sign}${pct}%`:'';
    // 场景名主标题：优先真值派生的 scene，回退指标标签；图标按 tone 给发光圆形(意愿=云雨)
    const scene=c.scene||c.title;
    const ico=c.icon||CHIP_TONE_ICON[tn]||'•';
    return `<div class="chip skeleton c-${tn}" title="${safe(c.title)} · 真值 ${safe(c.value)} · ${safe(c.delta)}（叙事偏移%为演示派生）">
      <span class="ci">${safe(ico)}</span>
      <div class="chip-meta">
        <div class="ct chip-scene">${safe(scene)}</div>
        <div class="chip-metric"><span class="cml">${safe(c.title)}</span>${hasPct?`<span class="cp">${pctStr}<sup class="float-sup" title="叙事偏移%为演示派生，随场景真值浮动">~浮动</sup></span>`:`<span class="cv">${safe(c.value)}</span>`}</div>
      </div>
    </div>`;
  }).join('');
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
  }).join('')
  // P1-5：诚实注脚——风险等级由感知模块按当前场景真值即时判定，随场景真值浮动
  + `<div class="float-note"><span class="real-dot"></span>等级/依据据当前场景感知真值即时判定，<b>随场景真值浮动</b></div>`;
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
// iter-6：地图视图模式。默认「聚焦故事视图」(贴目标稿：稀疏聚焦、单订单组叙事)；
// 可切「全局运营网」(点亮全部采纳脉络)。默认必须 focus。
let mapView='focus';   // 'focus' | 'global'

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

  const fg=m.featured_group;
  const fgKey0 = fg ? fg.task_key : null;
  // 圈：真合单组(亮绿实线) + 多骑手兜底组(青虚线)。语义区分(P0-3)。
  // iter-6：聚焦视图大幅减少兜底圈杂讯——只保留合单圈 + 焦点组圈(其余隐藏)，贴目标稿稀疏感；
  // 全局运营网视图才显示全部(限 14)。焦点组的圈交给 fg-ring 高亮，这里不重复画。
  const bsorted=(m.bundles||[]).slice().sort((a,b)=> (a.kind==='task_bundle'?-1:0)-(b.kind==='task_bundle'?-1:0));
  // iter-12(P0-3)：聚焦视图也多标几组(焦点组及邻近若干组都标，不只焦点 hub)。
  const bcap = mapView==='global' ? 16 : 9;
  let bdrawn=0;
  // 发光环 + 醒目药丸标签("N单合单"/"N骑手兜底") —— 标签用 foreignObject 承载带背景的胶囊。
  const drawBundleLabel=(b,kind)=>{
    const isTB=kind==='task_bundle';
    const lw=Math.max(58, b.label.length*12+18), lh=20;
    const lx=(b.cx-lw/2).toFixed(1), ly=(b.cy-b.r-lh-2).toFixed(1);
    const fo=el('foreignObject',{x:lx,y:ly,width:lw,height:lh,class:'bundle-lbl-fo'});
    fo.innerHTML=`<div xmlns="http://www.w3.org/1999/xhtml" class="bundle-lbl ${isTB?'lbl-tb':'lbl-mc'}">${safe(b.label)}</div>`;
    root.appendChild(fo);
  };
  bsorted.forEach(b=>{
    const kind=b.kind==='task_bundle'?'task_bundle':'multi_courier';
    if(b.task_key===fgKey0) return;              // 焦点组改由发光环高亮，避免叠画
    // 聚焦视图：优先合单圈；兜底圈仅在配额内象征性保留少量
    if(mapView==='focus' && kind==='multi_courier' && bdrawn>=bcap) return;
    if(bdrawn>=16) return;
    root.appendChild(el('circle',{cx:b.cx,cy:b.cy,r:b.r,
      class:'bundle-ring '+kind+(mapView==='focus'?' bundle-dim':'')}));
    drawBundleLabel(b,kind);
    bdrawn++;
  });
  // iter-6 视觉层级：先算出「焦点订单组」相关的实体集合（焦点任务节点 / 焦点候选骑手），
  // 用于把焦点做大做亮、其余压暗压小，让画面读成「一个订单的派单决策故事」。
  const focusTaskKey = fg ? fg.task_key : null;
  const focusTids = new Set(fg ? (fg.task_key||'').split(',').filter(Boolean) : []);
  // 焦点组的候选骑手 = candidate_edges 里 task_key 命中焦点组的那几条的终点骑手（真值采样）
  const focusCouriers = new Set();
  (m.candidate_edges||[]).forEach(e=>{ if(e.task_key===focusTaskKey) focusCouriers.add(e.courier); });
  // 焦点组的采纳骑手也算焦点（实线锚点骑手），一并点亮
  (m.accepted_edges||[]).forEach(e=>{ if(e.task_key===focusTaskKey) focusCouriers.add(e.courier); });

  // ---- 采纳实线：iter-6 弱化为极淡背景「全局派单脉络」（绝不做成抢眼绿网）----
  // 聚焦视图下 80 条采纳线只作青灰暗背景(opacity~.14、1px、无强发光)；
  // 「全局运营网」视图下才略提亮，但仍是背景而非主角。
  const accG=el('g',{id:'accedges',class:mapView==='global'?'view-global':'view-focus'});
  (m.accepted_edges||[]).forEach(e=>{
    const isFocus=(e.task_key===focusTaskKey);
    accG.appendChild(el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,
      class:'acc-edge'+(isFocus?' acc-focus':'')}));
  });
  root.appendChild(accG);

  // ---- 候选虚线：iter-6 地图叙事主角 ----
  // 焦点订单组射向其候选骑手的几条「粗一档·高对比·流动」黄色虚线 = 主角(cand-feature)。
  // 其余候选线全部隐藏(聚焦视图)或极淡(全局视图)，让黄色射线不被淹没。
  const candG=el('g',{id:'candedges'});
  (m.candidate_edges||[]).forEach(e=>{
    const isFeature=(e.task_key===focusTaskKey);
    if(isFeature){
      candG.appendChild(el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,class:'cand-edge cand-feature'}));
    } else {
      // 非焦点候选：聚焦视图隐藏；全局视图保留极淡一层
      candG.appendChild(el('line',{x1:e.x1,y1:e.y1,x2:e.x2,y2:e.y2,
        class:'cand-edge cand-dim'+(mapView==='focus'?' cand-hidden':'')}));
    }
  });
  root.appendChild(candG);

  // 商圈节点（方块代表商家中心）
  (m.districts||[]).forEach(d=>{
    const g=el('g',{class:'node-hit','data-district':d.id});
    g.appendChild(el('rect',{x:d.x-8,y:d.y-8,width:16,height:16,rx:3,class:'district-node'}));
    const t=el('text',{x:d.x,y:d.y+22,fill:'#8aa0b8','font-size':'9.5','text-anchor':'middle'});
    t.textContent=d.name; g.appendChild(t);
    g.addEventListener('click',()=>focusDistrict(d));
    root.appendChild(g);
  });

  // 骑手（iter-6：整体放大一档；焦点候选骑手更大更亮，其余压暗压小，建立视觉层级）
  (m.couriers||[]).forEach(c=>{
    const isFocus=focusCouriers.has(c.id);
    // iter-12(P0-1)：放大骑手绿点(活跃 6.5/空闲 5)，让绿色骑手在图上明显可见、数量足
    const r0= isFocus ? 9 : (c.active?6.5:5);
    let cls = c.active?'courier-node node-hit glow-node':'courier-idle node-hit';
    if(isFocus) cls+=' courier-focus';
    else if(mapView==='focus') cls+=' node-muted';   // 非焦点压暗（仅聚焦视图）
    const node=el('circle',{cx:c.x,cy:c.y,r:r0,'data-r':r0,class:cls,'data-courier':c.id});
    node.addEventListener('mouseenter',ev=>{ showTip(ev,`骑手 ${c.id}\n${isFocus?'焦点组候选骑手(真)':(c.active?'已采纳派单(真)':'未采纳')}`); node.setAttribute('r',(r0*1.6).toFixed(1)); });
    node.addEventListener('mouseleave',()=>{ hideTip(); node.setAttribute('r',r0); });
    root.appendChild(node);
  });

  // 订单（任务）节点 —— iter-6：焦点组订单更大更亮，其余压暗；点击联动右侧决策解释聚焦
  (m.tasks||[]).forEach(t=>{
    const isFocus=focusTids.has(t.id);
    const cls=t.risk==='high'?'task-high':(t.risk==='mid'?'task-mid':'task-low');
    const r0= isFocus ? 9 : 6.5;
    let full=cls+' node-hit glow-node '+(t.risk==='high'?'pulse':'');
    if(isFocus) full+=' task-focus';
    else if(mapView==='focus') full+=' node-muted';
    const node=el('circle',{cx:t.x,cy:t.y,r:r0,'data-r':r0,class:full,'data-task':t.id});
    node.addEventListener('mouseenter',ev=>{ showTip(ev,`订单 ${t.id}\n意愿派生 ${t.willingness_repr} · 风险 ${t.risk}`); node.setAttribute('r',(r0+3.5).toFixed(1)); });
    node.addEventListener('mouseleave',()=>{ hideTip(); node.setAttribute('r',r0); });
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
  // iter-6 焦点订单组：橙/黄发光脉冲环（双环），作为画面唯一高亮焦点
  root.appendChild(el('circle',{cx:fg.cx,cy:fg.cy,r:(fg.r+14),class:'fg-ring-outer'}));
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
  // iter-6 收敛动画：采纳实线渐次点亮为「极淡背景脉络」（不再做成抢眼绿网）；
  // 焦点黄色候选射线(cand-feature)保持流动高亮，不参与渐隐——它是地图主角。
  const accs=document.querySelectorAll('.acc-edge');
  accs.forEach((e,i)=> setTimeout(()=>e.classList.add('on'), 22*i));
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

// iter-6 视图切换：默认「聚焦故事」(贴目标稿)，可切「全局运营网」(点亮全部采纳脉络)。
const _mvt=$('mapviewtoggle');
if(_mvt){
  _mvt.addEventListener('click',e=>{
    const b=e.target.closest('.mv-btn'); if(!b) return;
    const v=b.dataset.view; if(v===mapView) return;
    mapView=v;
    _mvt.querySelectorAll('.mv-btn').forEach(x=>x.classList.toggle('active',x.dataset.view===v));
    if(mapData){ renderMap(mapData); setTimeout(convergeEdges,200); }
  });
}

/* ---------- 自进化（iter-2：真值透传，删假占位 #18-21） ---------- */
function renderEvo(evo){
  const body=$('evobody');
  if(!evo){ return; }
  const card=evo.promoted_card;     // 真值或 null
  const reg=evo.registry_summary;   // 真值或 null
  const causal=evo.causal_demo;     // 真值或 null

  // iter-9：把首屏自进化角标的真值与 report.evolution 实时对齐（晋级 ID / 注册表条数）
  if(reg){
    const total=reg.total_strategies, acc=reg.n_accepted;
    if(total!=null && acc!=null){
      const ebR=$('eb-registry'); if(ebR) ebR.textContent=`${total} 条 / ${acc} 采纳`;
    }
    const promoted=(reg.promoted||[]);
    if(promoted.length){ const ebP=$('eb-promoted'); if(ebP) ebP.textContent=promoted[0]; }
  } else if(card && card.strategy_id){
    const ebP=$('eb-promoted'); if(ebP) ebP.textContent=card.strategy_id;
  }

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
      <b>机制可验证 · 对最终派单成绩零贡献 · stub 无 live LLM。</b>
      <a class="evo-mem-link" href="/memory" target="_blank" rel="noopener">🧬 打开记忆库：全部历史策略 / 谱系 / 搜索筛选 ↗</a></div>`;
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

/* ---------- iter-13 四方共赢 · 多方平衡（Keeta 健康生态） ----------
 * 全部接 report.stakeholders 真值：
 *   平台 expected_cost(657.104)/履约率 = REAL（官方成本口径，绿点·real）
 *   骑手 Gini/Jain/时薪、商家 gap/曝光、顾客 ETA/延误 = 演示合成层(seed=20260620)
 * Pareto 前沿用真实 pareto_front 点；α 滑块在已有 5 点间吸附最近点（不重算后端）。
 * 公平有真实代价：α↑ → Gini↓ 但 成本↑/履约↓，如实并列。 */
let STK=null;            // 缓存真值
let STK_ALPHA_IDX=0;     // 当前 α 选中点下标
let STK_FRONT=[];        // 缓存当前 pareto 点序（供塌缩判定）
function fmtPct(x){ return x==null?'—':(x>=0?'+':'')+x+'%'; }
function fmtNum(x,d){ return x==null?'—':(d!=null?Number(x).toFixed(d):x); }
function realDot(real){ return real?'<span class="real-dot" title="官方成本口径真值"></span>'
  :'<span class="stk-syn" title="演示合成层 seed=20260620，由真实 task/courier/score/willingness 单调派生">合成</span>'; }
function stkMetric(label,f,unit,fmt){
  const v=f&&f.value!=null?(fmt?fmt(f.value):f.value):null;
  return `<div class="stk-m"><span class="stk-ml">${safe(label)}${realDot(f&&f.real)}</span>
    <span class="stk-mv ${f&&f.real?'real':'syn'}">${v==null?'—':safe(v)}${v!=null&&unit?`<i>${safe(unit)}</i>`:''}</span></div>`;
}
function renderStakeholders(st){
  const body=$('stkbody'); if(!body) return;
  if(!st||st.available===false){ body.innerHTML='<div class="empty-ph">本次未取到 report.stakeholders 真值</div>'; return; }
  STK=st; const sc=st.scorecard||{};
  const front=(st.pareto_front||[]);
  // α 滑块默认吸附到「非支配 + α 最小」的高效点
  let defIdx=front.findIndex(p=>p.efficient); if(defIdx<0) defIdx=0; STK_ALPHA_IDX=defIdx;

  const r=sc.rider||{}, m=sc.merchant||{}, c=sc.customer||{}, p=sc.platform||{};
  const cards=`
    <div class="stk-card stk-rider"><div class="stk-h">${r.icon||'🛵'} 骑手 <i>公平 & 收入</i></div>
      ${stkMetric('收入 Gini',r.income_gini,'',v=>Number(v).toFixed(4))}
      ${stkMetric('Jain 公平指数',r.income_jain,'',v=>Number(v).toFixed(4))}
      ${stkMetric('最低时薪(Rawlsian)',r.worst_hourly,'¥/时',v=>Number(v).toFixed(2))}
      ${stkMetric('出场骑手数',r.n_riders,'人',v=>Math.round(v))}</div>
    <div class="stk-card stk-merch"><div class="stk-h">${m.icon||'🏪'} 商家 <i>出餐 & 曝光</i></div>
      ${stkMetric('出餐-到达 gap',m.ready_gap_min,'分',v=>Number(v).toFixed(2))}
      ${stkMetric('曝光 Gini',m.exposure_gini,'',v=>Number(v).toFixed(4))}</div>
    <div class="stk-card stk-cust"><div class="stk-h">${c.icon||'🙋'} 顾客 <i>时效 & 体验</i></div>
      ${stkMetric('平均 ETA',c.mean_eta_min,'分',v=>Number(v).toFixed(2))}
      ${stkMetric('最大延误',c.max_lateness_min,'分',v=>Number(v).toFixed(2))}</div>
    <div class="stk-card stk-plat"><div class="stk-h">${p.icon||'🏢'} 平台 <i>成本 & 履约</i></div>
      ${stkMetric('期望成本',p.expected_cost,'',v=>Number(v).toFixed(3))}
      ${stkMetric('履约率',p.fulfillment_rate,'',v=>(Number(v)*100).toFixed(2)+'%')}
      ${stkMetric('覆盖/总任务',{value:(p.covered_tasks&&p.total_tasks)?`${Math.round(p.covered_tasks.value??p.covered_tasks)}/${Math.round(p.total_tasks.value??p.total_tasks)}`:null,real:true},'',null)}</div>`;

  const tr=st.tradeoff||{};
  const trBar=tr.cost_pct!=null?`<div class="stk-tradeoff">
      <span class="stk-tt">α=${fmtNum(tr.alpha_from)}→${fmtNum(tr.alpha_to)} 真实 Pareto 口径（公平的真实代价）：</span>
      <span class="stk-chip cost">成本 ${fmtPct(tr.cost_pct)}</span>
      <span class="stk-chip gini">骑手 Gini ${fmtPct(tr.gini_pct)}</span>
      <span class="stk-chip ful">履约率 ${fmtPct(tr.fulfillment_pct)}</span>
      <span class="tiny muted">（成本/履约为官方真值口径；Gini 为合成层）</span></div>`:'';

  body.innerHTML=`
    <div class="stk-cards">${cards}</div>
    ${trBar}
    <div class="stk-pareto-wrap">
      <div class="stk-pareto-h">效率(期望成本↓，真值) × 公平(骑手收入 Gini↓，合成层) Pareto 前沿
        <span class="tiny muted">· 绿=非支配解 灰=被支配 · 拖动 α 在真实解间切换</span></div>
      <div class="stk-caliber">⚠️ 口径注：此处 α 折衷解基于<b>透明 demo greedy</b> 重算的四方 Pareto 前沿，与头条 <b>AutoSolver v4(期望成本 657.104)</b> 解口径不同，两者不可直接混读。</div>
      <div id="stk-pareto-svg"></div>
      <div class="stk-slider-row">
        <span class="stk-sl-lbl">公平权重 α</span>
        <input type="range" id="stk-alpha" min="0" max="${Math.max(0,front.length-1)}" step="1" value="${STK_ALPHA_IDX}">
        <span class="stk-sl-val" id="stk-alpha-val"></span>
      </div>
      <div class="stk-collapse-hint" id="stk-collapse-hint"></div>
      <div class="stk-pick" id="stk-pick"></div>
    </div>
    <div class="stk-honesty">${safe(st.honesty||'')}</div>`;

  const slider=$('stk-alpha');
  if(slider) slider.oninput=()=>{ STK_ALPHA_IDX=+slider.value; paintPareto(); };
  STK_FRONT=front;
  paintPareto();
}
function paintPareto(){
  if(!STK) return;
  const front=STK.pareto_front||[]; if(!front.length) return;
  const idx=Math.min(STK_ALPHA_IDX,front.length-1);
  const W=560,H=210,padL=58,padR=18,padT=14,padB=40;
  const xs=front.map(p=>p.expected_cost), ys=front.map(p=>p.rider_income_gini);
  const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  const xr=(xmax-xmin)||1, yr=(ymax-ymin)||1;
  const sx=v=>padL+(v-xmin)/xr*(W-padL-padR);
  const sy=v=>H-padB-(v-ymin)/yr*(H-padT-padB);  // Gini↓ 在上方更好
  // 连线（按成本排序）
  const ordered=[...front].sort((a,b)=>a.expected_cost-b.expected_cost);
  const path=ordered.map((p,i)=>`${i?'L':'M'}${sx(p.expected_cost).toFixed(1)},${sy(p.rider_income_gini).toFixed(1)}`).join(' ');
  const pts=front.map((p,i)=>{
    const cx=sx(p.expected_cost),cy=sy(p.rider_income_gini);
    const sel=i===idx;
    const col=p.efficient?'#46f0a8':'#5d8073';
    return `<g>
      ${sel?`<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="11" fill="none" stroke="#43d5ff" stroke-width="2"/>`:''}
      <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${sel?6:5}" fill="${col}" stroke="#0a1612" stroke-width="1.5"/>
      <text x="${cx.toFixed(1)}" y="${(cy-10).toFixed(1)}" fill="${sel?'#43d5ff':'#7fa597'}" font-size="10" text-anchor="middle" font-weight="${sel?800:600}">α=${fmtNum(p.alpha)}</text>
    </g>`;
  }).join('');
  const svg=`<svg viewBox="0 0 ${W} ${H}" class="stk-svg" preserveAspectRatio="xMidYMid meet">
    <line x1="${padL}" y1="${H-padB}" x2="${W-padR}" y2="${H-padB}" stroke="rgba(97,255,211,.25)"/>
    <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${H-padB}" stroke="rgba(97,255,211,.25)"/>
    <text x="${(padL+(W-padR))/2}" y="${H-8}" fill="#7fa597" font-size="10.5" text-anchor="middle">期望成本 →（↓更好，真值）</text>
    <text x="14" y="${(padT+(H-padB))/2}" fill="#7fa597" font-size="10.5" text-anchor="middle" transform="rotate(-90 14 ${(padT+(H-padB))/2})">骑手收入 Gini →（↓更好，合成层）</text>
    <text x="${padL-6}" y="${sy(ymax).toFixed(1)}" fill="#5d8073" font-size="9" text-anchor="end">${ymax.toFixed(3)}</text>
    <text x="${padL-6}" y="${sy(ymin).toFixed(1)}" fill="#5d8073" font-size="9" text-anchor="end">${ymin.toFixed(3)}</text>
    <path d="${path}" fill="none" stroke="rgba(70,240,168,.45)" stroke-width="1.6" stroke-dasharray="4 3"/>
    ${pts}
  </svg>`;
  const host=$('stk-pareto-svg'); if(host) host.innerHTML=svg;
  const sel=front[idx];
  // iter-14 P1-7：中段 α 塌缩（多个 α 落在同一解点）会让滑块「无响应」。
  // 用 (expected_cost, rider_income_gini) 量化键找出与选中点同坐标的 α 簇，
  // 显式提示「该区间解相同」，消除手感歧义（不改后端，纯前端去重提示）。
  const sameKey=p=>`${(p.expected_cost??0).toFixed(4)}|${(p.rider_income_gini??0).toFixed(6)}`;
  const selKey=sameKey(sel);
  const cluster=front.filter(p=>sameKey(p)===selKey);
  const collapsed=cluster.length>1;
  const av=$('stk-alpha-val');
  if(av) av.textContent=`α=${fmtNum(sel.alpha)} ${sel.efficient?'· 非支配解':'· 被支配'}`
    +(collapsed?` · 与 α∈{${cluster.map(p=>fmtNum(p.alpha)).join(',')}} 同解`:'');
  const hint=$('stk-collapse-hint');
  if(hint){
    hint.innerHTML=collapsed
      ? `<span class="stk-ch-dot"></span>该 α 区间 {${cluster.map(p=>fmtNum(p.alpha)).join(', ')}} <b>解相同</b>（坐标重合）——滑块在此段不变属真实塌缩，非卡顿。`
      : '';
    hint.style.display=collapsed?'block':'none';
  }
  const pick=$('stk-pick');
  if(pick) pick.innerHTML=`选中解 α=<b>${fmtNum(sel.alpha)}</b>：
    期望成本 <b class="real">${fmtNum(sel.expected_cost,3)}</b><span class="real-dot"></span> ·
    骑手 Gini <b class="syn">${fmtNum(sel.rider_income_gini,4)}</b><span class="stk-syn">合成</span> ·
    最低时薪 <b class="syn">${fmtNum(sel.rider_worst_hourly,2)}¥/时</b> ·
    履约率 <b class="real">${(Number(sel.fulfillment_rate)*100).toFixed(2)}%</b><span class="real-dot"></span> ·
    最大延误 <b class="syn">${fmtNum(sel.customer_max_lateness,2)}分</b>`;
}

/* ---------- 数据边界（iter-7：诚实边界数据化，真实 vs 演示分色 token 化） ---------- */
function renderBoundary(b){
  const strip=$('boundary-strip'); if(!strip||!b||typeof b!=='object') return;
  const real=(b.real_fields||[]).map(f=>`<span class="bt bt-real">${safe(f)}</span>`).join('');
  const demo=(b.demo_fields||[]).map(f=>`<span class="bt bt-demo">${safe(f)}</span>`).join('');
  strip.innerHTML=`<span class="bt-lbl"><span class="real-dot"></span>真实字段</span>${real}
    <span class="bt-sep">·</span><span class="bt-lbl bt-lbl-demo">演示合成层 seed=${safe(b.seed||'20260620')}·非GPS</span>${demo}`;
  const claim=$('boundary-claim');
  if(claim&&b.claim) claim.innerHTML=`<b>数据边界</b>：${safe(b.claim)}（${safe(b.note||'')}）`;
}

/* ---------- 计时器 ---------- */
let timerH=null, timerStart=0;
function fmtElapsed(ms){ const s=Math.floor(ms/1000);
  const hh=String(Math.floor(s/3600)).padStart(2,'0'), mm=String(Math.floor(s%3600/60)).padStart(2,'0'), ss=String(s%60).padStart(2,'0');
  return `${hh}:${mm}:${ss}`; }
function startTimer(){ timerStart=Date.now(); clearInterval(timerH);
  $('timer').textContent='00:00:00';
  timerH=setInterval(()=>{ $('timer').textContent=fmtElapsed(Date.now()-timerStart); },250);
}
/* stopTimer：定格总耗时（不归零），让终态留住"本次求解总耗时"真值感 */
function stopTimer(){ clearInterval(timerH); timerH=null;
  if(timerStart){ $('timer').textContent=fmtElapsed(Date.now()-timerStart); } }

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

/* iteration-15：当前求解上下文（头牌 large_seed301 或某业务场景脱敏样例）。
 * runStream 据此构造 POST body，并在 phase/状态条上显示「在解哪个场景」。 */
let CURRENT_CTX={kind:'headliner', body:{case:'large_seed301',memory_enabled:true}, label:'头牌官方案例 large_seed301（bundle-heavy）'};
const SCENE_LABELS={peak:'午高峰爆单',rain:'雨天低接单意愿',scarce:'骑手稀缺商圈',bundle:'合单机会密集',newshop:'新店突发订单'};

/* iteration-16 P0-2 并发保护：
 *  - RUN_BUSY：同步内存锁，runStream 入口立即置位（不依赖 runbtn.disabled 这种异步 DOM 态），
 *    杜绝「点击→setTimeout(runStream,220) 的 220ms 窗口里再点一次→两路并发 SSE 串数据」。
 *  - RUN_GEN：每次 run 递增的代号；reader 循环每次回调都核对自身 gen 是否仍是当前 gen，
 *    若已被新的 run 取代（理论上不该发生，但作为兜底）则丢弃该流的事件，绝不串面板。 */
let RUN_BUSY=false;
let RUN_PENDING=false;          // 已排程但尚未发起的求解（覆盖 setTimeout(runStream,…) 的窗口）
let RUN_GEN=0;
function isRunLocked(){ return RUN_BUSY||RUN_PENDING; }
/* 排程一次求解：同步置 RUN_PENDING（立刻封住并发窗口），delay 后真正发起。
 * 所有「切场景/回头牌/重新演示/点击开始」都经此排程，单一入口、单一锁。 */
function scheduleRun(delay){
  if(isRunLocked()) return false;
  RUN_PENDING=true;
  setTimeout(runStream, delay||0);
  return true;
}
function runStream(){
  RUN_PENDING=false;
  if(RUN_BUSY) return;          // 已有求解在跑：直接忽略（并发保护，不开第二路）
  RUN_BUSY=true;
  RUN_ERRORED=false;
  const myGen=++RUN_GEN;
  $('runbtn').disabled=true;
  // P0-1 运行中态：脉冲绿「● 调度运行中」+ 计时器走动（贴目标稿系统状态）
  const rl=$('runlight'); rl.classList.remove('idle','done'); rl.classList.add('running');
  $('runtext').textContent='调度运行中';
  const ctxLbl=CURRENT_CTX.label||'';
  $('phase').textContent=`现场求解中 · ${ctxLbl} …（run_blind_solve 全流程 + 贪心基线，约 7~10s 逐阶段点亮）`;
  renderRings();
  RINGS.forEach((r,i)=> setRing(r[0], i===0?'run':'wait'));
  startTimer();

  fetch('/api/cockpit/stream',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(CURRENT_CTX.body||{case:'large_seed301',memory_enabled:true})}).then(async resp=>{
    if(!resp.ok){ throw new Error('HTTP '+resp.status); }
    if(!resp.body){ throw new Error('无响应流'); }
    const reader=resp.body.getReader(), dec=new TextDecoder(); let buf='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      if(myGen!==RUN_GEN){ try{await reader.cancel();}catch(_){} return; }  // 已被新 run 取代→弃流
      buf+=dec.decode(value,{stream:true});
      let idx;
      while((idx=buf.indexOf('\n\n'))>=0){
        const chunk=buf.slice(0,idx); buf=buf.slice(idx+2);
        const ev=/event: (.*)/.exec(chunk), da=/data: ([\s\S]*)/.exec(chunk);
        if(ev&&da){
          let parsed; try{ parsed=JSON.parse(da[1]); }catch(_){ continue; }  // 半截/坏 JSON 不抛
          if(myGen===RUN_GEN) dispatchEvent2(ev[1].trim(), parsed);
        }
      }
    }
    if(myGen===RUN_GEN) finishRun();
  }).catch(e=>{ if(myGen===RUN_GEN){ $('phase').textContent='求解中断：'+(e&&e.message||e)+'（可点 ▶ 重新演示重试）'; finishRun(); } });
}
function dispatchEvent2(type,d){
  if(type==='meta'){ handleMeta(d); }
  else if(type==='trace'){ handleTrace(d); }
  else if(type==='baseline'){ renderBaseline(d.baseline);
    const pct=d.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(80,pct); costImproveIsReal=true; recomputeRoi(); } }
  else if(type==='result'){ applyStory(d.story); }
  else if(type==='error'){ RUN_ERRORED=true; handleSolveError(d&&d.message||''); }
}
/* iteration-16 P0-3：求解异常兜底——不白屏。把仍处「待推理」骨架的面板替换为
 * 明确的「本次求解未完成」提示（含重试指引），并标记 RUN_ERRORED 让 finishRun 不误报完成。 */
let RUN_ERRORED=false;
function handleSolveError(msg){
  const tip=`<div class="empty-ph err-ph"><b>本次求解未完成</b>${msg?(' · '+safe(msg)):''}<br>可点 <b>▶ 重新演示</b> 或切换其它场景重试（其余面板真值不受影响）。</div>`;
  ['risk','strategy','decision','cert','baseline','stkbody'].forEach(id=>{
    const n=$(id); if(n && /pend-badge|skel-ph|empty-ph/.test(n.innerHTML)) n.innerHTML=tip;
  });
  const cand=$('candidates');
  if(cand && /pend-badge|skel-ph|empty-ph/.test(cand.innerHTML)) cand.innerHTML=`<div style="grid-column:1/-1">${tip}</div>`;
  $('phase').textContent='求解异常：'+(msg||'内部错误')+'（已兜底，可重试，整舱未崩）';
}
/* iteration-15：meta 事件——服务端确认「正在求解哪个场景/案例」（脱敏标识/seed），
 * 立即更新状态条与场景角标，让加载态清晰可读。 */
function handleMeta(d){
  if(!d) return;
  const tag=$('case-tag');
  if(d.is_synthetic_sample && d.scene){
    const nm=SCENE_LABELS[d.scene]||d.scene;
    if(tag){ tag.style.display='inline-flex';
      tag.innerHTML=`<span class="ct-dot syn"></span>场景脱敏样例 · <b>${safe(nm)}</b> · regime=${safe(d.regime_key||'—')} · seed=${safe(d.seed)}<span class="demo-tag">现场合成·非记忆</span>`; }
    $('phase').textContent=`正在对「${nm}」脱敏样例跑完整真实求解（regime=${d.regime_key} seed=${d.seed}）…`;
  }else{
    if(tag){ tag.style.display='inline-flex';
      tag.innerHTML=`<span class="ct-dot real"></span>头牌官方案例 · <b>large_seed301</b>（bundle-heavy）`; }
  }
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
  if(s.stakeholders) renderStakeholders(s.stakeholders);  // iter-13：四方共赢
  if(s.solver_used) $('solverused').textContent=s.solver_used;
  // 收敛动画
  setTimeout(convergeEdges, 300);
  // ROI 系数绑真实成本改善
  const pct=s.baseline?.improvement?.cost_pct; if(pct!=null){ costImprovePct=Math.min(80,pct); costImproveIsReal=true; }
  recomputeRoi();
}
function finishRun(){
  RUN_BUSY=false;               // 释放并发锁（允许下一次求解/切场景）
  $('runbtn').disabled=false;
  stopTimer();
  const total=timerStart?fmtElapsed(Date.now()-timerStart):'';
  const ctxLbl=CURRENT_CTX.label||'';
  const rl=$('runlight'); rl.classList.remove('running','idle','done');
  if(RUN_ERRORED){
    // 异常终态：标灰「中断」而非误报「完成」（兜底已在 handleSolveError 铺好提示）
    rl.classList.add('idle'); $('runtext').textContent='已中断';
    const rb=$('replaybtn'); if(rb) rb.style.display='inline-flex';
    const hb=$('headlinerbtn'); if(hb) hb.style.display=(CURRENT_CTX.kind==='scene')?'inline-flex':'none';
    return;
  }
  // P0-1 终态：SSE 收敛后切「● 完成」（绿勾·停脉冲），计时器定格本次总耗时
  rl.classList.add('done');
  $('runtext').textContent='完成';
  $('phase').textContent=`求解完成 · ${ctxLbl} · 全量真值已回填${total?`（本次求解总耗时 ${total}）`:''}`;
  // 重新演示按钮：求解完成后可见，便于答辩反复演示整段动画
  const rb=$('replaybtn'); if(rb) rb.style.display='inline-flex';
  // iteration-15：在场景态下露出「回到头牌案例」按钮（头牌态隐藏）
  const hb=$('headlinerbtn'); if(hb) hb.style.display=(CURRENT_CTX.kind==='scene')?'inline-flex':'none';
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
  $('stkbody').innerHTML=skeletonPanel('求解后接入 report.stakeholders：平台成本真值 + 公平/体验合成层');
  try{
    const r=await(await fetch('/api/cockpit/case')).json();
    if(r.status==='ok'){
      if(r.chips) renderChips(r.chips);
      if(r.risk) renderRisk(r.risk);
      if(r.regime_verdict) renderVerdict(r.regime_verdict);
      if(r.map_skeleton) renderMap(r.map_skeleton);
      if(r.data_boundary) renderBoundary(r.data_boundary);
    }
  }catch(e){ /* 骨架失败不阻塞 */ }
  recomputeRoi();
  // 加载即自动跑一次真实求解，使全部面板(KPI/Baseline/决策/候选/证书/自进化)无需点击即有真值。
  if(!AUTORUN_DONE){ AUTORUN_DONE=true; scheduleRun(350); }
}
let AUTORUN_DONE=false;

/* ---------- 折叠 / 场景点击 ---------- */
$('evotoggle').onclick=()=> $('evopanel').classList.toggle('collapsed');

/* iter-9：首屏自进化常驻角标 → 平滑滚动到底部自进化全面板并展开（折叠态时先展开露出证据） */
(function(){
  const badge=$('evo-badge'); if(!badge) return;
  badge.addEventListener('click',()=>{
    const panel=$('evopanel');
    if(panel){
      panel.classList.remove('collapsed');                 // 确保展开后能看到全证据
      panel.scrollIntoView({behavior:'smooth',block:'center'});
    }
  });
})();
document.addEventListener('click',e=>{
  const sc=e.target.closest('.scene');
  if(sc){
    if(isRunLocked()){
      // 求解中（或已排程）：不切换高亮，避免误导（active 仍指向正在跑的场景）
      $('phase').textContent='当前正在求解，请等本次完成后再切换场景…';
      return;
    }
    document.querySelectorAll('.scene').forEach(n=>n.classList.toggle('active',n===sc));
    switchScene(sc.dataset.id);
  }
});
/* iteration-15 P0：点击场景 → 对该场景脱敏样例跑【完整真实求解】（run_blind_solve 全流程 + 贪心基线），
 * 所有面板（KPI/Baseline/决策/候选/地图/证书/四方/自进化）回填为该场景真值，带流式动画。
 * 不再只重判感知；不写死任何场景真值——由服务端现场合成 regime 脱敏样例并真跑。 */
function switchScene(sceneId){
  if(isRunLocked()){
    // 正在求解中（或已排程）：忽略点击，给提示（避免并发两路 SSE）
    $('phase').textContent='当前正在求解，请等本次完成后再切换场景…';
    return;
  }
  SELECTED_SCENE=sceneId;
  CURRENT_CTX={kind:'scene', body:{scene:sceneId, memory_enabled:true}, label:`${SCENE_LABELS[sceneId]||sceneId}（脱敏样例·现场合成）`};
  // 1) 面板回求解中骨架（「求解中」加载态清晰，避免误读上一场景真值为本场景）
  resetPanelsToSolving(`正在合成「${SCENE_LABELS[sceneId]||sceneId}」脱敏样例并完整真 solve…`);
  // 2) 启动完整 SSE 流式求解（与头牌同一条 runStream 链路，只是 body 指向该场景）。
  //    scheduleRun 同步置 RUN_PENDING，封住 220ms 排程窗口内的并发再点击。
  scheduleRun(220);
}

/* iteration-15：把全部面板重置为「求解中」骨架（与首屏 loadSkeleton/replay 同观感），
 * 让切换场景时有明确加载态，不残留上一场景真值。 */
function resetPanelsToSolving(phaseTxt){
  const rl=$('runlight'); rl.classList.remove('running','done'); rl.classList.add('idle');
  $('runtext').textContent='待机'; $('timer').textContent='00:00:00'; timerStart=0;
  $('solverused').textContent='—';
  renderRings(); RINGS.forEach(r=> setRing(r[0],'wait'));
  renderKpiSkeleton();
  $('risk').innerHTML=skeletonPanel('感知模块据该场景脱敏样例当场判风险');
  $('strategy').innerHTML=skeletonPanel('Planner 镜像解读该场景策略链');
  $('decision').innerHTML=skeletonPanel('该场景求解后聚焦代表派单组');
  $('cert').innerHTML=skeletonPanel('solver_v4 对该场景求解后回填 gap·r1 证书');
  $('candidates').innerHTML=`<div style="grid-column:1/-1">${skeletonPanel('该场景方案 A/B/C 自动评估')}</div>`;
  $('baseline').innerHTML=skeletonPanel('该场景：纯贪心真跑 vs AutoSolver 对比');
  $('stkbody').innerHTML=skeletonPanel('该场景求解后接入 report.stakeholders 真值');
  if(phaseTxt) $('phase').textContent=phaseTxt;
}

/* iteration-15：一键回到头牌官方案例（large_seed301）并重跑完整求解。 */
function backToHeadliner(){
  if(isRunLocked()) return;
  SELECTED_SCENE=null;
  CURRENT_CTX={kind:'headliner', body:{case:'large_seed301',memory_enabled:true}, label:'头牌官方案例 large_seed301（bundle-heavy）'};
  document.querySelectorAll('.scene').forEach(n=>n.classList.remove('active'));
  resetPanelsToSolving('回到头牌官方案例 large_seed301 · 重跑完整真实求解…');
  scheduleRun(220);
}
$('runbtn').onclick=()=>scheduleRun(0);

/* P0-2：「▶ 重新演示」——一键把整舱重置回骨架态，再完整重放一段"AI 自主求解"动画。
 * 便于答辩反复演示：五环逐格点亮、KPI count-up、地图候选→采纳收敛、Baseline/证书末态弹入。 */
function replayDemo(){
  if(isRunLocked()) return;            // 正在跑/已排程则忽略
  const rb=$('replaybtn'); rb.style.display='none';
  // 1) 系统状态回待机 + 计时器归零
  const rl=$('runlight'); rl.classList.remove('running','done'); rl.classList.add('idle');
  $('runtext').textContent='待机'; $('timer').textContent='00:00:00'; timerStart=0;
  $('solverused').textContent='—';
  // 2) 面板回骨架（与首屏 loadSkeleton 一致），制造"从零重新求解"观感
  renderRings(); RINGS.forEach(r=> setRing(r[0],'wait'));
  renderKpiSkeleton();
  $('risk').innerHTML=skeletonPanel('感知模块据尺寸解耦特征当场判风险');
  $('strategy').innerHTML=skeletonPanel('Planner 镜像解读策略链');
  $('decision').innerHTML=skeletonPanel('点击地图节点或推理后聚焦合单组');
  $('cert').innerHTML=skeletonPanel('solver_v4 求解后回填 gap·r1 证书');
  $('candidates').innerHTML=`<div style="grid-column:1/-1">${skeletonPanel('方案 A/B/C 自动评估')}</div>`;
  $('baseline').innerHTML=skeletonPanel('纯贪心真跑 vs AutoSolver 对比');
  $('stkbody').innerHTML=skeletonPanel('求解后接入 report.stakeholders：平台成本真值 + 公平/体验合成层');
  // 3) 短暂停顿后重放整段
  $('phase').textContent='重新演示 · 重置整舱并重放 AI 自主求解动画…';
  scheduleRun(320);
}
$('replaybtn').onclick=replayDemo;
{ const hb=$('headlinerbtn'); if(hb) hb.onclick=backToHeadliner; }

/* 键盘：空格开始推理 */
document.addEventListener('keydown',e=>{
  if(e.code==='Space' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)){ e.preventDefault(); if(!isRunLocked()) scheduleRun(0); }
});

loadSkeleton();
// iteration-2：自进化面板等待 SSE result.evolution 真值回填（不再注入假占位）。
$('evobody').innerHTML='<div class="empty-ph">点击「开始智能调度推理」后接入 report.evolution 真值（真·机制，stub 无 live LLM）</div>';
