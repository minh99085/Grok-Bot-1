# Grok-Bot-1

Blueprint for a **self-improving, loop-engineered AI hedge fund** on Polymarket — built to run alpha research, verify signals, and trade while you sleep.

This repo has no application code yet. It holds three reference documents that together define *what* to trade, *how* to run it autonomously, and *how not to fail quietly*.

**Author of source material:** [Roan @RohOnChain](https://x.com/RohOnChain) — backend developer focused on prediction-market quant systems and HFT-style execution.

---

## How the Three Files Fit Together

| File | Answers | Key insight |
|---|---|---|
| `Trading bot Loop Engine step by step.jpg` | **How do I wire this in practice?** | Four concrete steps from "stop prompting" to a live five-stage loop, plus four rules that keep it alive |
| `(5) …Loop Engineering… .pdf` | **What is loop engineering?** | You architect the loop; the agent runs inside it. Six pieces, five stages, maker-checker, self-improvement via `SKILL.md` |
| `(4) …Polymarket Math Roadmap… .pdf` | **What edge exists on Polymarket?** | ~$40M extracted via integer programming, Bregman projection, Frank-Wolfe, and non-atomic execution — not manual YES+NO checks |

```
┌─────────────────────────────────────────────────────────────┐
│  LOOP ENGINEERING (how the bot runs forever)                │
│  data → signal → verify → execute → monitor → memory → ↺  │
├─────────────────────────────────────────────────────────────┤
│  POLYMARKET MATH (what the bot hunts for)                   │
│  detect → project → optimize → execute → size → monitor     │
└─────────────────────────────────────────────────────────────┘
```

**Grok-Bot-1** is where these two layers meet: Grok (or any LLM) sits *inside* the loop as maker and checker — but the loop itself, the math, and the stop conditions are engineered in code and files that persist across runs.

---

## The Heartbeat

Every self-improving quant system runs the same cycle:

```
data → signal → verify → execute → monitor → memory → repeat
```

- The **agent forgets** between runs.
- The **loop does not** — because `STATE.md`, `SKILL.md`, and structured logs survive restarts.

Your job is not to prompt one trade at a time. Your job is to **write the loop** that prompts, verifies, decides, and repeats — even after the laptop is closed.

---

## Four Steps to Build It (from the step-by-step guide)

### 1. Stop prompting, start writing loops

Most builders still type → wait → read → type again. *They* are the loop.

Loop engineering inverts this: define a recursive goal, let the agent iterate against it, and keep running until a **real** stopping condition is met. The leverage point moved up one floor — you are no longer writing better prompts; you are writing the system that writes the prompts.

### 2. Wire up all six pieces

Miss one and the loop breaks **quietly** (no crash, just silent failure).

| Piece | File / mechanism | Purpose |
|---|---|---|
| **Automation** | cron, webhook, `/loop`, `/goal` | Heartbeat — fires without you typing |
| **Skill** | `SKILL.md` | Conventions, rules, lessons learned — intent compounds |
| **State** | `STATE.md` | Memory across runs — read at start, write at end |
| **Verifier** | separate agent / model | Grades the maker's work — never self-grades |
| **Worktrees** | isolated git directories | Parallel research, backtest, risk — no file collisions |
| **Connectors** | MCP | Brokers, APIs, databases, exchanges — hands in the real world |

**`/loop`** — reruns on cadence (e.g. pull data every hour).  
**`/goal`** — runs until a verifiable condition is true (e.g. backtest Sharpe > 1.5), graded by code — not the agent's claim.

### 3. Apply maker-checker (from real prop shops)

The signal generator is the **worst** judge of whether a signal is alpha or noise.

| Role | Who | Example |
|---|---|---|
| **Maker** | proposes signal / code / trade | Grok + alpha research skill |
| **Checker** | verifies independently | separate Grok prompt, or stronger model (Sonnet → Opus pattern) |

Citadel, Jane Street, Two Sigma all structure work this way: the researcher who builds the model does not validate it; the trader who proposes does not approve.

### 4. Build the five-stage trading loop

Each stage is its own sub-loop with its own skill, state, and verifier.

| Stage | Trigger | Action |
|---|---|---|
| **1. Data ingestion** | `@loop(interval=…)` | Pull market data on schedule → shared state |
| **2. Signal generation** | `@loop(trigger="data_updated")` | Alpha research skill proposes candidates — no self-grading |
| **3. Verification** | `@checker` | Independent agent applies hard rules; failures are killed |
| **4. Execution** | verified signals only | Broker MCP connector places orders; hands-off |
| **5. Risk monitoring** | `@loop(interval="1m")` in parallel worktree | Check positions every minute; kill switch on breach |

**Hard verification rules (examples):**

- Sharpe ratio > 1.5
- Max drawdown < 10%
- Newey-West t-statistic > 2.0
- Out-of-sample period ≥ 2 years

**Kill switch (example):** close all positions and log to `STATE.md` when drawdown exceeds 5%.

---

## Self-Improvement: Every Loss Writes a Rule

The skill file grows into institutional memory:

```markdown
## Lessons learned
- 2026-02-14: Lost 4.2% during earnings week.
  New rule: skip any signal 48 hours before earnings.
- 2026-03-08: Sector exposure breach caused 6% drawdown.
  New rule: cap sector exposure at 30%.
- 2026-04-22: Momentum signal blew up on FOMC day.
  New rule: kill all momentum signals on FOMC days.
```

After hundreds of trades, `SKILL.md` is a living rulebook the agent reads every cycle — closer to institutional knowledge than anything one human could hold in context.

### Stopping conditions must be checkable

Never accept the agent's "I'm done." Use numeric, code-verified gates:

- Sharpe above 1.5 over the last 30 trades
- Drawdown below 5%
- Test suite passes

Without this, the loop exits on a half-finished job and bad trades sit open.

---

## Four Rules to Keep the Loop Alive

1. **Log every loss** — date, loss %, root cause, new rule → `SKILL.md`
2. **Real stop conditions** — verifiable thresholds, not agent opinions
3. **Start small** — paper trade one asset, one signal, one cadence; iterate where it breaks
4. **Keep scope locked** — one working loop that compounds beats a universal system that converges to zero (Renaissance ran one loop for 30 years)

---

## Polymarket: What Edge Actually Looks Like

The math roadmap explains why retail "YES + NO = $1?" checks lose to production systems.

### Why simple math fails (Part I — Marginal Polytope)

Correlated markets create dependencies invisible to per-market sums. Valid prices live in the **marginal polytope** `M = conv(Z)`. Anything outside `M` is exploitable.

Brute force over `2^n` outcomes is impossible (`2^63` for a 63-game tournament). **Integer programming** replaces enumeration:

```
Z = { z ∈ {0,1}^I : A^T z ≥ b }
```

**Real data (Apr 2024 – Apr 2025):** 17,218 conditions examined; 41% showed single-market arbitrage; median mispricing $0.60 per dollar (40% off).

### How to compute the optimal trade (Part II — Bregman Projection)

Euclidean distance fails for LMSR markets. Use **Bregman divergence** (KL for LMSR). Maximum guaranteed profit = `D(μ*||θ)` where `μ*` projects current prices onto `M`. This gives positions, size, and expected profit accounting for order-book depth.

### How to make it tractable (Part III — Frank-Wolfe)

Direct projection is intractable. **Frank-Wolfe** builds `M` iteratively via linear programs + IP oracle (e.g. Gurobi). **Barrier Frank-Wolfe** handles boundary gradients. Typical: 50–150 iterations.

### Why math alone is not enough (Part IV — Non-Atomic Execution)

Polymarket CLOB is sequential — one leg can fill, the other fails. Production systems:

- Use **VWAP per Polygon block** (~2s), not quoted prices
- Cap profit by `min(volume across all required positions)`
- Submit all legs in ~30ms (same block); copy-trading fast wallets = exit liquidity
- Minimum ~$0.05 edge after gas and slippage

### Production stack (Part V)

| Layer | What it does |
|---|---|
| Data | WebSocket CLOB + Polygon node (OrderFilled, PositionSplit events) |
| Dependencies | LLM pair filtering (e.g. DeepSeek-R1) + manual verification |
| Optimization | LCMM → Frank-Wolfe IP → execution validation |
| Sizing | Modified Kelly with execution-risk discount; cap at 50% book depth |
| Monitoring | Opportunities/min, execution rate, drawdown, latency |

**Extracted Apr 2024 – Apr 2025:**

| Category | Amount |
|---|---|
| Single-condition arbitrage | $10.6M |
| Market rebalancing | $29.0M |
| Combinatorial arbitrage | $96K |
| **Total** | **~$39.7M** |

Top extractor: **$2.0M** from 4,049 trades (~$496/trade). Not luck — mathematical infrastructure executed systematically.

---

## External Resources

| Resource | Link |
|---|---|
| Arbitrage in prediction markets | [arXiv:2508.03474v1](https://arxiv.org/abs/2508.03474) |
| Combinatorial market making via IP | [arXiv:1606.02825v2](https://arxiv.org/abs/1606.02825) |
| IP solver | [Gurobi Optimizer](https://www.gurobi.com/) |
| On-chain data | Alchemy Polygon node API |
| Dependency detection LLM | DeepSeek-R1-Distill-Qwen-32B |

---

## Repository Status

| Included | Not included yet |
|---|---|
| Architecture blueprint (3 reference files) | Polymarket live data feeds |
| `loop/` — six pieces + five-stage driver | Frank-Wolfe / Gurobi optimization engine |
| `grok_bot/` — CLI, paper-only safety lock | Grok API wiring (maker/checker roles) |
| Skill files + verifier + state persistence | VPS deployment |

## Price feed stack (edge source)

Leading feeds move **before** Polymarket's Chainlink settlement oracle updates. The bot trades the lag.

```
Tier 1 — LEADING (fast)          Tier 2 — SETTLEMENT (slow)
─────────────────────────        ───────────────────────────
Binance BTCUSDT                  Chainlink BTC/USD on-chain
Coinbase BTC-USD        →edge→   (window open/end truth only)
TradingView BTCUSDT alerts
```

| Feed | Role | Used for |
|---|---|---|
| **Binance** | Leading CEX | Nowcast price, freshness |
| **Coinbase** | Leading CEX | Cross-venue confirmation |
| **TradingView** | Leading signal | Direction + price from alerts |
| **Chainlink** | Settlement truth | Window open/end — **not** the nowcast |

`p_up` and `edge_bps` are computed from leading stack vs window open. Chainlink is reconciliation only.

## LLM roles + signal feeds

| Role | Provider | Responsibility |
|---|---|---|
| **Maker** | Grok / xAI (`XAI_API_KEY`) | Alpha proposals, risk overlay bias/size hints |
| **Checker** | Claude / Anthropic (`ANTHROPIC_API_KEY`) | Independent signal review — never self-grades |
| **External feed** | TradingView webhook | BTCUSDT alert signals → `reports/tradingview_signals.jsonl` |

Numeric gates in `loop/verifier.py` always run first. Claude is a second checker layer; if Claude rejects, the signal is killed even when numeric checks pass.

### TradingView alert JSON (example)

```json
{
  "symbol": "BTCUSDT",
  "direction": "long",
  "strength": "strong",
  "indicator": "hermes_pulse",
  "price": 64000.0,
  "ttc_s": 120
}
```

Webhook URL: `http://<vps-host>:8799/tv/<TRADINGVIEW_WEBHOOK_SECRET>`

### Hermes Agent + profit discovery

```bash
git clone https://github.com/minh99085/Grok-Bot-1.git

bash scripts/setup_hermes.sh          # confirms hermes-agent/ vendored source
bash scripts/link_hermes_skills.sh    # link SKILL.md into ~/.hermes/skills
bash scripts/install_hermes_cron.sh   # register cron jobs (requires hermes CLI)
```

`hermes-agent/` is the **full Hermes Agent codebase** from [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent), vendored in this repo.

Bot starts in **`profit_discovery`** mode: paper-only, rungs `observe → shadow → armed | no_edge_found`.

### Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env   # set XAI_API_KEY, ANTHROPIC_API_KEY, TRADINGVIEW_WEBHOOK_SECRET
python -m grok_bot.main --verify
python -m grok_bot.main --tradingview-webhook   # receive BTCUSDT alerts
python -m grok_bot.main --discover-once          # one discovery window
python -m grok_bot.main --discover-loop          # bounded @goal discovery
python -m grok_bot.main --discovery-status      # reports/discovery_status.md
pytest
```

### Build order (remaining)

1. Wire Grok/xAI maker + checker with dual-verification guard
2. Add Polymarket CLOB + Chainlink read-only connectors
3. Paper discovery loop on `btc-updown-5m-*` windows
4. Layer integer-programming / Bregman stack from math roadmap