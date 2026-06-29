"""Read-only dep-arb dashboard HTML (Bot 1 arb-first workspace)."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="color-scheme" content="dark"/>
<title>BTC Pulse · Dep-Arb</title>
<style>
:root{
  --bg:#12141a;--bg2:#181b24;--card:#1c2029;--line:#2a3040;
  --text:#f0f4f8;--text2:#aeb8c8;--text3:#8f9aad;
  --green:#4ade80;--yellow:#facc15;--red:#f87171;--accent:#a8c8f0;
  --radius:12px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:26px/1.45 "Segoe UI",system-ui,sans-serif}
header{
  padding:14px 18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  border-bottom:1px solid var(--line);background:var(--bg2);
}
h1{font-size:34px;font-weight:600;margin:0}
.tag{font-size:22px;padding:5px 14px;border-radius:16px;background:var(--card);color:var(--text2)}
.tag.live{color:var(--green)}.tag.warn{color:var(--yellow)}.tag.off{color:var(--red)}
main{max-width:min(1680px,100%);margin:0 auto;padding:14px 20px 24px}
.cap-bar{
  display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 20px;
  background:linear-gradient(135deg,var(--card) 0%,#222836 100%);
  border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 20px;margin-bottom:12px;
}
.cap-main{font-size:40px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.cap-label{font-size:22px;color:var(--text2);margin-top:2px}
.cap-sub{font-size:22px;color:var(--text2)}
.cap-sub b{color:var(--text);font-weight:600}
.cap-sub .up{color:var(--green)}.cap-sub .dn{color:var(--red)}
.stats-bar{
  display:flex;flex-wrap:wrap;gap:12px 24px;margin-bottom:12px;
  padding:12px 18px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
}
.stat{font-size:24px;color:var(--text2)}
.stat b{color:var(--text);font-weight:700;font-variant-numeric:tabular-nums}
.stat .w{color:var(--green)}.stat .l{color:var(--red)}.stat .o{color:var(--yellow)}
.verdict{
  display:flex;align-items:center;gap:8px;font-size:26px;font-weight:600;
  padding:10px 16px;border-radius:var(--radius);background:var(--card);border:1px solid var(--line);
  margin-bottom:12px;
}
.content-split{
  display:grid;grid-template-columns:1fr 420px;gap:12px 24px;align-items:start;
}
.trades-head{
  margin:0 0 8px;font-size:20px;font-weight:600;color:var(--accent);
  text-transform:uppercase;letter-spacing:.06em;
}
.trade-line{
  display:flex;justify-content:space-between;align-items:center;gap:10px;
  padding:6px 0;font-size:22px;line-height:1.35;
  border-bottom:1px solid rgba(42,48,64,.45);
}
.trade-line:last-child{border-bottom:0}
.trade-info{min-width:0;color:var(--text2)}
.trade-side{font-weight:600;color:var(--accent)}
.trade-tag{font-size:19px;color:var(--text2);margin-left:4px}
.trade-tag.win{color:var(--green)}.trade-tag.loss{color:var(--red)}.trade-tag.open{color:var(--yellow)}
.trade-pnl{font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap;font-size:22px}
.trade-pnl.up{color:var(--green)}.trade-pnl.dn{color:var(--red)}.trade-pnl.neu{color:var(--text2)}
.trades-empty{color:var(--text2);font-size:22px}
.tl-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(456px,1fr));gap:8px;min-width:0;
}
.tl-row{
  display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:center;
  padding:8px 12px;background:var(--card);border:1px solid var(--line);border-radius:8px;
}
.tl-dot{width:17px;height:17px;border-radius:50%;flex-shrink:0}
.tl-green{background:var(--green);box-shadow:0 0 6px rgba(74,222,128,.55)}
.tl-yellow{background:var(--yellow);box-shadow:0 0 6px rgba(250,204,21,.45)}
.tl-red{background:var(--red);box-shadow:0 0 6px rgba(248,113,113,.55)}
.tl-name{font-size:24px;color:var(--text)}
.tl-val{font-size:22px;color:var(--text2);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tl-hint{
  grid-column:1/-1;font-size:20px;color:var(--text2);
  padding-top:6px;margin-top:2px;border-top:1px solid var(--line);
}
.tl-section{
  grid-column:1/-1;font-size:20px;font-weight:600;color:var(--accent);
  text-transform:uppercase;letter-spacing:.06em;padding:8px 2px 4px;
}
.foot{margin-top:14px;color:var(--text2);font-size:20px}
@media(max-width:960px){.content-split{grid-template-columns:1fr}}
@media(max-width:420px){.tl-grid{grid-template-columns:1fr}.cap-main{font-size:34px}}
</style>
</head>
<body>
<header>
  <h1>Dep-Arb Lab</h1>
  <span class="tag">Paper only</span>
  <span class="tag" id="health">Loading…</span>
  <span class="tag" id="meta" style="color:var(--text3)"></span>
</header>
<main>
  <div class="cap-bar" id="cap-bar"></div>
  <div class="stats-bar" id="stats-bar"></div>
  <div class="verdict" id="verdict"></div>
  <div class="content-split">
    <div class="tl-grid" id="tl-grid"></div>
    <aside class="trades-col">
      <div class="trades-head">Last 20 dep-arb trades</div>
      <div id="trades-list"></div>
    </aside>
  </div>
  <div class="foot">Refreshes every 1 min · dependency-arb lane only · outcome-settled P&L</div>
</main>
<script>
const $=(h)=>{const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstChild};
const f=(x,d=2)=>x==null||x===''?'—':(typeof x==='number'?x.toFixed(d):String(x));
const usd=(x)=>x==null?'—':'$'+Number(x).toFixed(2);
const pct=(x)=>x==null?'—':(x>=0?'+':'')+Number(x).toFixed(2)+'%';
const dot=(c)=>'<span class="tl-dot tl-'+c+'"></span>';

function fmtTsShort(ts){
  if(ts==null)return '—';
  try{
    const d=new Date(Number(ts)*1000);
    return d.toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  }catch(e){return '—';}
}
function fmtAge(sec){
  if(sec==null)return '—';
  const s=Math.round(Number(sec));
  if(!Number.isFinite(s)||s<0)return '—';
  if(s<60)return s+'s';
  if(s<3600)return Math.floor(s/60)+'m';
  return Math.floor(s/3600)+'h';
}
function tradeOutcome(x){
  const st=(x.status||'').toLowerCase();
  if(st==='open')return {label:'open',cls:'open',pnlCls:'neu',pnl:'—'};
  if(x.won===true)return {label:'win',cls:'win',pnlCls:'up',pnl:usd(x.pnl_usd)};
  if(x.won===false)return {label:'loss',cls:'loss',pnlCls:'dn',pnl:usd(x.pnl_usd)};
  return {label:st||'—',cls:'',pnlCls:'neu',pnl:x.pnl_usd==null?'—':usd(x.pnl_usd)};
}
function renderTrades(listEl,positions){
  listEl.innerHTML='';
  const pos=(positions||[]).slice(0,20);
  if(!pos.length){
    listEl.innerHTML='<div class="trades-empty">No dep-arb trades yet.</div>';
    return;
  }
  pos.forEach(x=>{
    const r=x.research||{};
    const oc=tradeOutcome(x);
    const settled=x.outcome_settled?' · settled':'';
    const row=$('<div class="trade-line"></div>');
    row.innerHTML=
      '<div class="trade-info"><span class="trade-side">'+(x.side||'P-UP')+'</span>'
      +'<span class="trade-tag '+oc.cls+'">'+oc.label+'</span>'
      +'<span class="trade-tag"> '+r.market_series+' @'+f(x.entry_price,3)+settled+'</span>'
      +'<br><span class="trade-tag">'+fmtTsShort(x.entry_ts)+'</span></div>'
      +'<div class="trade-pnl '+oc.pnlCls+'">'+oc.pnl+'</div>';
    listEl.appendChild(row);
  });
}
function renderStats(el,st){
  st=st||{};
  el.innerHTML=
    '<span class="stat">Total <b>'+f(st.total,0)+'</b></span>'
    +'<span class="stat">Wins <b class="w">'+f(st.wins,0)+'</b></span>'
    +'<span class="stat">Losses <b class="l">'+f(st.losses,0)+'</b></span>'
    +'<span class="stat">Open <b class="o">'+f(st.open,0)+'</b></span>'
    +'<span class="stat">Settled <b>'+f(st.settled,0)+'</b></span>';
}
function addRow(rows,name,val,hint,light){rows.push({name,val,hint,light});}
function addSection(rows,title){rows.push({section:title});}

function buildRows(s){
  const rows=[];
  const dep=s.dependency_arbitrage||{};
  const cal=dep.dependency_arb_calibration||{};
  const gate=dep.kelly_gate||{};
  const book=dep.booking||{};
  const loops=s.loops||{};
  const statusAge=(Date.now()/1000)-(Number(s.ts)||0);
  const pnl=dep.realized_profit_usd||0;
  const wr=dep.settled>0?((gate.warm_buckets||0)>0?'see calibration':'—'):'—';

  addSection(rows,'Dep-Arb P&L');
  addRow(rows,'Realized P&L',usd(pnl),
    'Outcome-settled when resolver available',
    pnl>0?'green':(pnl>=0?'yellow':'red'));
  addRow(rows,'Theoretical booked',usd(book.theoretical_settled_usd),
    'Capture ratio '+f(book.capture_ratio,2),
    (book.capture_ratio||0)>=0.4?'green':'yellow');
  addRow(rows,'Heuristic compare',book.settled_n?f(book.settled_n,0)+' settled':'—',
    'Legacy capped heuristic kept for comparison',
    'yellow');

  addSection(rows,'Activity');
  addRow(rows,'Executed',f(dep.executed,0)+' · settled '+f(dep.settled,0),
    'open '+f(dep.open,0)+' · scans '+f(dep.scans,0),
    (dep.executed||0)>0?'green':'yellow');
  addRow(rows,'Violations',f(dep.violations_detected,0)+' detected',
    f(dep.actionable_detected,0)+' actionable · '+f(dep.mid_only_violations,0)+' mid-only',
    (dep.actionable_detected||0)>0?'green':'yellow');
  addRow(rows,'Mode',dep.mode||'—',
    dep.enabled?'execute ON':'log only',
    dep.enabled?'green':'yellow');

  addSection(rows,'Kelly & calibration');
  addRow(rows,'Kelly active',dep.kelly_active?'YES':'no',
    'enabled '+!!gate.kelly_enabled+' · fraction '+f(gate.kelly_fraction,2),
    dep.kelly_active?'green':'yellow');
  addRow(rows,'Walk-forward',gate.walk_forward_passed?'passed':'blocked',
    (gate.walk_forward||{}).holdout?'holdout n='+f(((gate.walk_forward||{}).holdout||{}).n,0):'warming up',
    gate.walk_forward_passed?'green':'yellow');
  const buckets=cal.buckets||{};
  const bucketKeys=Object.keys(buckets);
  if(bucketKeys.length){
    bucketKeys.slice(0,4).forEach(k=>{
      const b=buckets[k]||{};
      addRow(rows,'Bucket '+k,f(b.win_rate!=null?(b.win_rate*100).toFixed(1)+'%':'—'),
        'n='+f(b.n,0)+' · PF '+f(b.profit_factor,2)+' · avg '+usd(b.avg_pnl),
        (b.profit_factor||0)>=1?'green':'yellow');
    });
  }else{
    addRow(rows,'Calibration','no buckets yet',
      'min samples '+f(cal.min_samples_kelly,0)+' for Kelly',
      'yellow');
  }

  addSection(rows,'Engine');
  addRow(rows,'Bot alive','ticks '+f(s.ticks,0)+' · age '+fmtAge(statusAge),
    s.paper_only?'paper mode OK':'CHECK MODE',
    statusAge<45&&s.ticks>5?'green':(statusAge<120?'yellow':'red'));
  addRow(rows,'Loops',loops.all_live?'all live':'check',
    f((loops.stalled||[]).length,0)+' stalled',
    (loops.stalled||[]).length===0?'green':'red');

  return rows;
}

function overallLight(s,rows){
  const dep=s.dependency_arbitrage||{};
  const pnl=dep.realized_profit_usd||0;
  if(!s.available)return {light:'red',text:'NO DATA'};
  if(s.live_trading_enabled)return {light:'red',text:'LIVE TRADING ON'};
  if((dep.executed||0)===0)return {light:'yellow',text:'WAITING FOR DEP-ARB TRADES'};
  if(pnl<0)return {light:'yellow',text:'DEP-ARB NEGATIVE P&L'};
  return {light:'green',text:'DEP-ARB ACTIVE'};
}

function renderRows(grid,rows){
  grid.innerHTML='';
  rows.forEach(r=>{
    if(r.section){
      grid.appendChild($('<div class="tl-section">'+r.section+'</div>'));
      return;
    }
    const el=$('<div class="tl-row"></div>');
    let html=dot(r.light)+'<span class="tl-name">'+r.name+'</span><span class="tl-val">'+r.val+'</span>';
    if(r.hint)html+='<div class="tl-hint">'+r.hint+'</div>';
    el.innerHTML=html;
    grid.appendChild(el);
  });
}

async function fetchJson(url,timeoutMs=20000){
  const ctrl=new AbortController();
  const t=setTimeout(()=>ctrl.abort(),timeoutMs);
  try{
    const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
    if(!r.ok)throw new Error('HTTP '+r.status);
    return await r.json();
  }finally{clearTimeout(t);}
}

function setTag(id,text,cls){
  const el=document.getElementById(id);
  el.textContent=text;
  el.className='tag'+(cls?' '+cls:'');
}

async function tick(){
  setTag('health','Loading…','');
  let s,l;
  try{
    [s,l]=await Promise.all([
      fetchJson('/api/polymarket/training/btc_pulse'),
      fetchJson('/api/polymarket/training/btc_pulse/ledger?summary=1'),
    ]);
  }catch(e){setTag('health',e&&e.name==='AbortError'?'Timed out':'Unreachable','off');return;}
  if(!s.available){setTag('health','No data','off');return;}
  setTag('health','Live','live');
  document.getElementById('meta').textContent=
    'tick · '+new Date().toLocaleTimeString();

  const dep=s.dependency_arbitrage||{};
  const pnl=dep.realized_profit_usd||0;
  const pnlCls=pnl>=0?'up':'dn';
  const st=(l&&l.dep_arb_stats)||{};
  document.getElementById('cap-bar').innerHTML=
    '<div><div class="cap-main '+pnlCls+'">'+usd(pnl)+'</div>'
    +'<div class="cap-label">dep-arb realized P&L (outcome-settled)</div></div>'
    +'<div class="cap-sub">Executed <b>'+f(dep.executed,0)+'</b></div>'
    +'<div class="cap-sub">Settled <b>'+f(dep.settled,0)+'</b></div>'
    +'<div class="cap-sub">Open <b class="o">'+f(dep.open,0)+'</b></div>'
    +'<div class="cap-sub">Kelly <b>'+(dep.kelly_active?'active':'off')+'</b></div>';

  renderStats(document.getElementById('stats-bar'),st);

  const rows=buildRows(s);
  const ov=overallLight(s,rows);
  const v=document.getElementById('verdict');
  v.innerHTML=dot(ov.light)+'<span>'+ov.text+'</span>';
  v.style.borderColor=ov.light==='green'?'rgba(74,222,128,.4)':(ov.light==='yellow'?'rgba(250,204,21,.4)':'rgba(248,113,113,.4)');
  renderRows(document.getElementById('tl-grid'),rows);
  renderTrades(document.getElementById('trades-list'),(l&&l.positions)||[]);
}
tick();setInterval(tick,60000);
</script>
</body>
</html>"""