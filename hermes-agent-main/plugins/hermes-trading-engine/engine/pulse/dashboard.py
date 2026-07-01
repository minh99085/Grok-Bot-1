"""Read-only dep-arb dashboard HTML (Bot 1 arb-first workspace)."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="color-scheme" content="dark"/>
<title>BTC Pulse · Bot 1 Dashboard</title>
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
  display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 24px;
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
.trades-col{margin-bottom:12px}
.trades-toggle{
  width:100%;text-align:left;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:12px 14px;margin:0 0 8px;
  font-size:24px;font-weight:600;color:var(--accent);
  background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  color:var(--text);
}
.trades-toggle:hover{border-color:var(--accent)}
.trades-toggle .chev{font-size:22px;color:var(--accent);transition:transform .2s}
.trades-toggle.open .chev{transform:rotate(90deg)}
.trades-toggle-sub{font-size:20px;font-weight:400;color:var(--text2)}
.trades-panel{
  max-height:0;overflow:hidden;transition:max-height .35s ease;
  border:1px solid transparent;border-radius:var(--radius);
}
.trades-panel.open{
  max-height:min(70vh,1200px);overflow-y:auto;
  border-color:var(--line);background:var(--card);padding:8px 12px;
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
.trades-empty{color:var(--text2);font-size:22px;padding:8px 4px}
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
@media(max-width:420px){.tl-grid{grid-template-columns:1fr}.cap-main{font-size:34px}}
</style>
</head>
<body>
<header>
  <h1>Bot 1 · Paper Trading</h1>
  <span class="tag">Practice money only</span>
  <span class="tag" id="health">Loading…</span>
  <span class="tag" id="meta" style="color:var(--text3)"></span>
</header>
<main>
  <div class="cap-bar" id="cap-bar"></div>
  <div class="stats-bar" id="stats-bar"></div>
  <div class="verdict" id="verdict"></div>
  <aside class="trades-col">
    <button type="button" class="trades-toggle" id="trades-toggle" aria-expanded="false">
      <span><span id="trades-toggle-title">Recent trades</span>
      <span class="trades-toggle-sub" id="trades-toggle-sub"></span></span>
      <span class="chev">▶</span>
    </button>
    <div class="trades-panel" id="trades-panel">
      <div id="trades-list"></div>
    </div>
  </aside>
  <div class="tl-grid" id="tl-grid"></div>
  <div class="foot">Updates every minute · directional (LLM council + best-EV) &amp; dependency-arbitrage lanes · no real money</div>
</main>
<script>
const TRADE_LIMIT=50;
const $=(h)=>{const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstChild};
const f=(x,d=2)=>x==null||x===''?'—':(typeof x==='number'?x.toFixed(d):String(x));
const usd=(x)=>x==null?'—':'$'+Number(x).toFixed(2);
const pct=(x)=>x==null?'—':(x>=0?'+':'')+Number(x).toFixed(2)+'%';
const dot=(c)=>'<span class="tl-dot tl-'+c+'"></span>';

let tradesOpen=false;

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
  if(s<60)return s+' seconds ago';
  if(s<3600)return Math.floor(s/60)+' min ago';
  return Math.floor(s/3600)+' hr ago';
}
function tradeOutcome(x){
  const st=(x.status||'').toLowerCase();
  if(st==='open')return {label:'still open',cls:'open',pnlCls:'neu',pnl:'—'};
  if(x.won===true)return {label:'won',cls:'win',pnlCls:'up',pnl:usd(x.pnl_usd)};
  if(x.won===false)return {label:'lost',cls:'loss',pnlCls:'dn',pnl:usd(x.pnl_usd)};
  return {label:st||'—',cls:'',pnlCls:'neu',pnl:x.pnl_usd==null?'—':usd(x.pnl_usd)};
}
function renderTrades(listEl,positions){
  listEl.innerHTML='';
  const pos=(positions||[]).slice(0,TRADE_LIMIT);
  if(!pos.length){
    listEl.innerHTML='<div class="trades-empty">No dependency-arbitrage trades yet.</div>';
    return;
  }
  pos.forEach(x=>{
    const r=x.research||{};
    const oc=tradeOutcome(x);
    const settled=x.outcome_settled?' · final result known':'';
    const row=$('<div class="trade-line"></div>');
    row.innerHTML=
      '<div class="trade-info"><span class="trade-side">'+(x.side||'Parent UP')+'</span>'
      +'<span class="trade-tag '+oc.cls+'">'+oc.label+'</span>'
      +'<span class="trade-tag"> '+r.market_series+' · entry '+f(x.entry_price,3)+settled+'</span>'
      +'<br><span class="trade-tag">'+fmtTsShort(x.entry_ts)+'</span></div>'
      +'<div class="trade-pnl '+oc.pnlCls+'">'+oc.pnl+'</div>';
    listEl.appendChild(row);
  });
}
function setupTradesToggle(count){
  const btn=document.getElementById('trades-toggle');
  const panel=document.getElementById('trades-panel');
  const sub=document.getElementById('trades-toggle-sub');
  const title=document.getElementById('trades-toggle-title');
  const shown=Math.min(count,TRADE_LIMIT);
  title.textContent='Recent trades (up to '+TRADE_LIMIT+')';
  sub.textContent=' — '+count+' total · click to '+(tradesOpen?'hide':'show')+' list';
  btn.classList.toggle('open',tradesOpen);
  panel.classList.toggle('open',tradesOpen);
  btn.setAttribute('aria-expanded',tradesOpen?'true':'false');
  if(!btn._wired){
    btn._wired=true;
    btn.addEventListener('click',()=>{
      tradesOpen=!tradesOpen;
      setupTradesToggle(count);
    });
  }
}
function renderStats(el,st,dep){
  st=st||{};
  dep=dep||{};
  el.innerHTML=
    '<span class="stat">All dep-arb trades <b>'+f(st.total,0)+'</b></span>'
    +'<span class="stat">Wins <b class="w">'+f(st.wins,0)+'</b></span>'
    +'<span class="stat">Losses <b class="l">'+f(st.losses,0)+'</b></span>'
    +'<span class="stat">Still open <b class="o">'+f(st.open,0)+'</b></span>'
    +'<span class="stat">Finished <b>'+f(st.settled,0)+'</b></span>'
    +'<span class="stat">Booked by bot <b>'+f(dep.executed,0)+'</b></span>';
}
function addRow(rows,name,val,hint,light){rows.push({name,val,hint,light});}
function addSection(rows,title){rows.push({section:title});}

function captureLight(ratio){
  if(ratio==null||ratio==='')return 'yellow';
  const r=Number(ratio);
  if(r<0)return 'red';
  if(r>=0.4)return 'green';
  if(r>=0.1)return 'yellow';
  return 'red';
}

function buildRows(s){
  const rows=[];
  const dep=s.dependency_arbitrage||{};
  const cal=dep.dependency_arb_calibration||{};
  const gate=dep.kelly_gate||{};
  const book=dep.booking||{};
  const loops=s.loops||{};
  const cap=s.capital||{};
  const statusAge=(Date.now()/1000)-(Number(s.ts)||0);
  const pnl=dep.realized_profit_usd||0;

  // ---- Directional / LLM council (the lane actively trading now) ----
  addSection(rows,'Directional · LLM council');
  const led=s.ledger||{};
  const dirPnl=cap.realized_pnl_usd;
  addRow(rows,'Directional trades',
    f(led.trades,0)+' settled'+(led.win_rate!=null?' · '+(led.win_rate*100).toFixed(0)+'% win':''),
    'P&amp;L '+usd(dirPnl)+' · '+f(cap.open_positions,0)+' open ($'+f(cap.open_exposure_usd,2)+' at risk)',
    (dirPnl==null)?'yellow':(dirPnl>=0?'green':'yellow'));
  const lc=s.llm_council||{};
  if(lc.enabled){
    addRow(rows,'LLM council',
      f(lc.trade_decisions,0)+' trade calls · '+f(lc.evaluations,0)+' windows judged',
      'Ensemble vote (quant + Grok + Claude + TV) with best-EV side pick; execution gate stays final',
      'green');
    const mem=lc.members||{};
    Object.keys(mem).sort().forEach(k=>{
      if(k.indexOf('tv')===0)return;          // TV members shown in their own section below
      const m=mem[k]||{};
      const st=(m.stance||'cold');
      const light=(st==='follow')?'green':(st==='fade'?'yellow':'yellow');
      addRow(rows,'· member '+k,
        st.toUpperCase()+(m.accuracy!=null?' · '+(m.accuracy*100).toFixed(0)+'% acc':'')+(m.n?' (n='+m.n+')':' (cold)'),
        'blend weight '+f(m.weight,2)+(m.faded?' · view INVERTED (fading a contrarian signal)':''),
        light);
    });
  }
  const mc=s.monte_carlo||{};
  if(mc.enabled){
    const fg=mc.flag_grading||{};
    addRow(rows,'Monte Carlo gate',mc.dep_arb_gate?'ON — vetoes negative-EV dep-arb':'observe only',
      'adverse-selection flag precision '+(fg.flag_precision!=null?(fg.flag_precision*100).toFixed(0)+'%':'—')+' · graded '+f(fg.graded,0),
      mc.dep_arb_gate?'green':'yellow');
  }
  const gd=s.grok_decider||{};
  const cd=s.claude_decider||{};
  addRow(rows,'LLM engines',
    'Grok '+(gd.mode||'—')+' · Claude '+(((cd.decided||0)>0)?'live':((cd.errors||0)>0?'erroring':'idle')),
    'Grok decided '+f(gd.decided,0)+' (err '+f(gd.errors,0)+') · Claude decided '+f(cd.decided,0)+' (err '+f(cd.errors,0)+')',
    (((cd.errors||0)>10)||((gd.errors||0)>80))?'yellow':'green');

  // ---- TradingView signals: each timeframe's live direction + how the council uses it ----
  addSection(rows,'TradingView signals (per timeframe)');
  const tvd=s.tradingview||{};
  const bytf=tvd.tradingview_latest_by_timeframe||{};
  const mem2=(s.llm_council||{}).members||{};
  const tfKeys=Object.keys(bytf).sort((a,b)=>{
    const na=parseInt((a.split('@')[1]||'0'),10), nb=parseInt((b.split('@')[1]||'0'),10);
    return na-nb;});
  if(tfKeys.length){
    tfKeys.forEach(k=>{
      const t=bytf[k]||{};
      const tfn=(k.split('@')[1]||'?');
      const cm=mem2['tv_'+tfn+'m']||{};
      const st=cm.stance||'cold';
      const dir=t.direction||'—';
      const light=(dir==='FLAT'||dir==='—')?'yellow':(st==='follow'?'green':(st==='fade'?'yellow':'yellow'));
      const stanceTxt=(st==='follow'?'FOLLOW':(st==='fade'?'FADE (inverted)':(st==='ignore'?'IGNORE':'learning')));
      addRow(rows,'TV '+tfn+'m',
        dir+(t.strength!=null?' · strength '+f(t.strength,2):'')+(t.signal_level?' ('+t.signal_level+')':''),
        'council: '+stanceTxt+(cm.accuracy!=null?' · '+(cm.accuracy*100).toFixed(0)+'% acc (n='+f(cm.n,0)+')':' — needs '+((s.llm_council||{}).min_samples||20)+' settled'),
        light);
    });
  }else{
    addRow(rows,'TV signals','No fresh alerts landing','check TradingView chart alerts + webhook','red');
  }
  addRow(rows,'TV alerts landing',
    f(tvd.tradingview_alerts_valid,0)+' valid / '+f(tvd.tradingview_alerts_received,0)+' received',
    'rejected '+f(tvd.tradingview_alerts_rejected,0)+' · observe-only (graded, followed/faded by the council)',
    (tvd.tradingview_alerts_valid||0)>0?'green':'red');

  addSection(rows,'Money — dependency arbitrage');
  addRow(rows,'Dep-arb profit/loss',usd(pnl),
    'Real money-style P&amp;L after each trade finishes (not guesses).',
    pnl>0?'green':(pnl>=0?'yellow':'red'));
  addRow(rows,'What we hoped to make',usd(book.theoretical_settled_usd),
    'Best-case if every gap paid off fully. Capture = what we actually kept: '+f(book.capture_ratio,2),
    captureLight(book.capture_ratio));
  addRow(rows,'Finished trades counted',book.settled_n?f(book.settled_n,0)+' settled':'—',
    'Older estimate kept for comparison only.',
    'yellow');

  addSection(rows,'Scanner activity');
  addRow(rows,'Trades placed',f(dep.executed,0)+' placed · '+f(dep.settled,0)+' finished',
    f(dep.open,0)+' still open · '+f(dep.scans,0)+' market scans',
    (dep.executed||0)>0?'green':'yellow');
  addRow(rows,'Price gaps found',f(dep.violations_detected,0)+' gaps spotted',
    f(dep.actionable_detected,0)+' looked tradable · '+f(dep.mid_only_violations,0)+' watch-only',
    (dep.actionable_detected||0)>0?'green':'yellow');
  addRow(rows,'Trading switch',dep.enabled?'ON — bot may place paper trades':'OFF — watch only',
    dep.mode==='paper_execute'?'Paper practice mode':'Log only',
    dep.enabled?'green':'yellow');

  addSection(rows,'Sizing rules (Kelly)');
  addRow(rows,'Smart sizing active?',dep.kelly_active?'Yes':'No',
    'Kelly only turns on when enough history exists. Fraction '+f(gate.kelly_fraction,2),
    dep.kelly_active?'green':'yellow');
  addRow(rows,'Out-of-sample test',gate.walk_forward_passed?'Passed':'Not yet',
    (gate.walk_forward||{}).holdout?'test sample size '+f(((gate.walk_forward||{}).holdout||{}).n,0):'still collecting data',
    gate.walk_forward_passed?'green':'yellow');
  const buckets=cal.buckets||{};
  const bucketKeys=Object.keys(buckets);
  if(bucketKeys.length){
    bucketKeys.slice(0,4).forEach(k=>{
      const b=buckets[k]||{};
      addRow(rows,'Entry price '+k,f(b.win_rate!=null?(b.win_rate*100).toFixed(1)+'% win rate':'—'),
        f(b.n,0)+' trades · profit factor '+f(b.profit_factor,2)+' · avg '+usd(b.avg_pnl),
        (b.profit_factor||0)>=1?'green':'yellow');
    });
  }else{
    addRow(rows,'Win rate by entry price','Not enough data yet',
      'Need '+f(cal.min_samples_kelly,0)+' finished trades before Kelly sizing',
      'yellow');
  }

  addSection(rows,'Bot health');
  addRow(rows,'Is the bot running?','Heartbeat '+f(s.ticks,0)+' · updated '+fmtAge(statusAge),
    s.paper_only?'Practice mode — safe':'WARNING: check live flag',
    statusAge<45&&s.ticks>5?'green':(statusAge<120?'yellow':'red'));
  addRow(rows,'Background jobs',loops.all_live?'All loops OK':'Some loops stalled',
    f((loops.stalled||[]).length,0)+' need attention',
    (loops.stalled||[]).length===0?'green':'red');
  if(cap.total_realized_pnl_usd!=null){
    addRow(rows,'Whole-bot P&amp;L (all strategies)',usd(cap.total_realized_pnl_usd),
      'Dep-arb + dutch-book arb + directional combined',
      cap.total_realized_pnl_usd>=0?'green':'yellow');
  }

  return rows;
}

function overallLight(s){
  const dep=s.dependency_arbitrage||{};
  const cap=s.capital||{};
  const pnl=dep.realized_profit_usd||0;
  const total=cap.total_on_hand_usd;
  if(!s.available)return {light:'red',text:'No data — bot may be stopped'};
  if(s.live_trading_enabled)return {light:'red',text:'WARNING: live trading is ON'};
  if((dep.executed||0)===0)return {light:'yellow',text:'Watching markets — no dep-arb trades placed yet'};
  if(pnl<0)return {light:'yellow',text:'Dep-arb is losing money so far — review capture and exits'};
  if(total!=null&&total<cap.starting_capital_usd)return {light:'yellow',text:'Total paper wallet is below starting capital'};
  return {light:'green',text:'Dep-arb is active and making paper trades'};
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
  }catch(e){setTag('health',e&&e.name==='AbortError'?'Timed out':'Cannot reach bot','off');return;}
  if(!s.available){setTag('health','No data','off');return;}
  setTag('health','Connected','live');
  document.getElementById('meta').textContent=
    'Last refresh · '+new Date().toLocaleTimeString();

  const dep=s.dependency_arbitrage||{};
  const cap=s.capital||{};
  const st=(l&&l.dep_arb_stats)||{};
  const totalCap=cap.total_on_hand_usd;
  const startCap=cap.starting_capital_usd;
  const totalRet=cap.total_return_pct;
  const depPnl=dep.realized_profit_usd||0;
  const capCls=(totalCap==null)?'':(totalCap>=startCap?'up':'dn');
  const depCls=depPnl>=0?'up':'dn';

  document.getElementById('cap-bar').innerHTML=
    '<div><div class="cap-main '+capCls+'">'+usd(totalCap)+'</div>'
    +'<div class="cap-label">Total paper capital (all strategies)</div>'
    +(startCap!=null?'<div class="cap-label">Started with '+usd(startCap)
      +(totalRet!=null?' · '+pct(totalRet)+' overall':'')+'</div>':'')+'</div>'
    +'<div><div class="cap-main" style="font-size:32px">'+f(st.total,0)+'</div>'
    +'<div class="cap-label">Total dep-arb trades</div></div>'
    +'<div class="cap-sub">Dep-arb P&amp;L <b class="'+depCls+'">'+usd(depPnl)+'</b></div>'
    +'<div class="cap-sub">Finished <b>'+f(dep.settled,0)+'</b></div>'
    +'<div class="cap-sub">Still open <b class="o">'+f(dep.open,0)+'</b></div>';

  renderStats(document.getElementById('stats-bar'),st,dep);

  const rows=buildRows(s);
  const ov=overallLight(s);
  const v=document.getElementById('verdict');
  v.innerHTML=dot(ov.light)+'<span>'+ov.text+'</span>';
  v.style.borderColor=ov.light==='green'?'rgba(74,222,128,.4)':(ov.light==='yellow'?'rgba(250,204,21,.4)':'rgba(248,113,113,.4)');
  renderRows(document.getElementById('tl-grid'),rows);
  renderTrades(document.getElementById('trades-list'),(l&&l.positions)||[]);
  setupTradesToggle(st.total||0);
}
tick();setInterval(tick,60000);
</script>
</body>
</html>"""