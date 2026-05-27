# Technical Requirements Document: Autonomous Quantitative Research Desk

## 1. Project Overview

### Purpose
To develop an autonomous, serverless, multi‑agent trading research system that scans, analyzes, and optimizes trade strategies for the Indian equity market (NSE/BSE).

### Goal
Shift from manual scanning to a self‑optimizing "research desk" that learns from historical mock‑trade performance (P&L) and market regime changes, while remaining risk‑aware and observation‑first rather than live‑trading.

### Architecture
A hierarchical, event‑driven multi‑agent system hosted on Google Cloud Platform (GCP), using Cloud Functions, Firestore, BigQuery, and Gemini APIs. The system is stateless; all memory and configuration persist in Firestore.

---

## 2. Technical Stack

- **Backend:** Python 3.x (Cloud Functions)
- **Database / Memory:** Firestore (Real‑time synchronization for agent memory, state, and strategy registry)
- **Analytics:** BigQuery (SQL‑based technical indicators, historical data, and quant metrics)
- **AI Engine:** Google AI Studio (Gemini 2.5 Flash for high‑speed scanning; Gemini 2.5 Pro for deep analysis)
- **Frontend:** React + Vite + Tailwind CSS + shadcn/ui
- **Development Tooling:** Cursor AI (Constraints defined in .cursorrules)

---

## 3. The 7‑Agent Ecosystem (Roles & Responsibilities)

The system is composed of six distinct agents (with one logical "Meta‑Analyst" role spanning two modes). All agents must read configuration from the `strategy_registry` collection and write their state and outputs into Firestore.

### Agent Roles:
1. **Meta‑Analyst (Pre‑Market Screener)** – Filters NSE/BSE universe by liquidity and volatility
2. **Meta‑Analyst (Post‑Market Retrospective)** – Analyzes mock‑trade P&L and adjusts strategy parameters
3. **Sentinel** – Computes market regime (one of five categories)
4. **Specialist‑Pattern** – Technical analysis (moving averages, RSI, breakouts)
5. **Specialist‑Macro** – Macro headwinds (rate hikes, inflation, macro sentiment)
6. **Specialist‑News** – News sentiment ingestion and cross‑reference
7. **Supervisor** – Risk veto layer (exposure, max trades/day, regime filters)

---

## 4. Key Operational Workflow (Flowchart Logic)

```
Cloud Scheduler
    ↓
Meta-Analyst: Pre-Market Screener
    ↓
Firestore: Update Target Universe
    ↓
Sentinel: Regime Check
    ↓
Specialist Agents: Analyze Universe
    ↓
Cross-Reference: News/Macro API
    ↓
Supervisor: Risk Veto Layer
    ↓
Trade Approved? ──→ Yes ──→ Execute Mock Trade ──→ Store in Firestore
    ↓
    No ──→ Log Failure Thesis ──→ Store in Firestore
    ↓
Meta-Analyst: Post-Market Retrospective
    ↓
Update Global Strategy Registry
    ↓
(Loop continues next day)
```

### Notes on the flow:
- **Meta‑Analyst** runs at pre‑market, populates `target_universe` (e.g., top‑200–500 liquid/volatile stocks), and later revisits all trades from the cycle for retrospective analysis.
- **Sentinel** reads Nifty, India VIX, and ADR data, computes one of the five regimes, and writes `system_state/regime` to Firestore.
- **Specialist agents** cross‑reference news and macro APIs before producing their thesis JSON.
- **Supervisor** evaluates all inputs, enforces constraints (exposure, max trades/day, regime‑based filters), and either approves or vetoes.
- **Mock trades** are logged with full thesis JSON; no real capital is deployed.
- **Meta‑Analyst** later reads back the mock‑trade history, recomputes P&L and win‑rates, and updates the `strategy_registry` for the next cycle.

---

## 5. Functional Requirements

### 5.1 Screener (Pre‑Market)
Meta‑Analyst must filter NSE/BSE stocks into a `target_universe` collection in Firestore based on:
- **Liquidity:** Minimum average daily volume or turnover
- **Volatility:** 20‑day standard deviation of returns
- **Universe size:** Configurable (e.g., 200–500 tickers) and bounded to keep costs manageable on GCP

### 5.2 Cross‑Reference (News + Macro)
Each Specialist must:
- Ingest `news_sentiment` scores (−1 to +1) for each ticker
- Ingest macro‑headwind data (e.g., rate‑hike expectations, high‑inflation indicators)
- No trade thesis may be finalized until this cross‑reference is complete and stored in the thesis JSON

### 5.3 Global Strategy Registry
- **Registry location:** Firestore collection `strategy_registry`, with documents keyed by `strategy_id`
- **Schema:** See section 5.6 below for the full JSON schema
- **Rule:** All agents must fetch their logic parameters (e.g., `conviction_threshold`, `allowed_regimes`, `macro_requirements`, `news_sentiment_min`) from Firestore. Hard‑coded logic is prohibited.

### 5.4 Self‑Correction Logic
Meta‑Analyst shall:
- Aggregate mock‑trade P&L over a configurable window (e.g., 30 days) per strategy and regime
- Compute win‑rate and risk‑adjusted metrics
- If the sample size meets `min_sample_size` and the win‑rate falls below a threshold:
  - Adjust `conviction_threshold` by `score_delta_on_failure` (as defined in `self_correction_rules`), but not below a minimum value
  - Updated parameters must be written back into the corresponding `strategy_registry` document and picked up automatically in the next cycle

### 5.5 Market‑Regime Specification

#### Objective:
Define a simple, deterministic regime taxonomy for the Sentinel so all agents can treat the market consistently.

#### Core metrics:
- **Nifty 20‑day return** (simple moving average vs prior)
- **India VIX level** (normalized vs its own 252‑day rolling mean and std)
- **Advance‑Decline ratio (ADR):** (Advancing stocks / Declining stocks) × 100 on NSE‑wide

#### Regime categories:

| Regime | Nifty 20d Return | VIX Level | ADR | Characteristics |
|--------|-----------------|-----------|-----|-----------------|
| **Trending Bull** | > 0 & positive trend | < 1.0× rolling mean | > 70 | Strong uptrend, low volatility |
| **Recovery / Relief Rally** | > 0 but recent drawdown | < 1.5× rolling mean | 50–70 | Bounce from weakness |
| **Choppy / Neutral** | ≈ 0 (−1% to +1%) | ≈ rolling mean | 40–60 | No clear direction |
| **Stressed / Volatile** | Falling or choppy (< 0) | ≥ 1.5× rolling mean | < 40 | High uncertainty, not extreme |
| **Panic / Extreme Volatility** | ≤ −3% | ≥ 2.0× rolling mean | < 30 | Extreme market dislocation |

#### Spec language:
Sentinel shall compute one of the five regimes above once per day (or pre‑market) using Nifty close, India VIX, and ADR data. The result must be written to a Firestore document (e.g., `system_state/regime`), and all agents must consume this label as the current `market_regime`. The label must be a string exactly matching one of the above category names.

### 5.6 Strategy Registry Schema (Firestore)

**Top‑level collection:** `strategy_registry`  
**Document ID:** `strategy_id` (e.g., `crash_rebound_highconv`, `trending_bull_breakout`)

#### Sample strategy document (JSON):

```json
{
  "strategy_id": "crash_rebound_highconv",
  "name": "Crash‑Rebound, High Conviction",
  "description": "High‑conviction bounce trades after sharp corrections in stressed/volatile regimes.",
  "version": "1.0.0",
  "timestamp_updated": "2026‑05‑26T10:00:00Z",
  "status": "active",

  "allowed_agents": ["Meta‑Analyst", "Specialist‑Pattern", "Specialist‑Macro"],
  "allowed_regimes": ["Stressed / Volatile", "Panic / Extreme Volatility"],

  "conviction_threshold": 7,
  "min_conviction_for_trade": 6,
  "max_conviction_for_override": 9,

  "max_exposure_per_ticker_pct": 2,
  "max_exposure_per_sector_pct": 10,
  "max_trades_per_day": 10,

  "backtest_params": {
    "slippage_bps": 20,
    "commission_rate_bps": 50,
    "minimum_trade_volume_lakhs": 5.0
  },

  "macro_requirements": {
    "allow_during_rate_rise": false,
    "allow_during_high_inflation": false
  },
  "news_sentiment_min": 0.2,

  "enable_self_correction": true,
  "self_correction_rules": {
    "min_sample_size": 10,
    "window_days": 30,
    "score_delta_on_failure": -0.5
  }
}
```

#### Spec language:
- All agents must read their operational thresholds from `strategy_registry` documents. Hard‑coded numeric thresholds are prohibited.
- The Meta‑Analyst is responsible for updating these documents after each retrospective period, using a self‑correction rule that respects sample‑size and regime‑aware windows.
- Developers may add additional fields to the schema, but must not remove or rename the core fields above without explicit approval.

### 5.7 Thesis JSON and "Strategy Intelligence" Tab Inputs

#### Thesis JSON example (Firestore):

```json
{
  "thesis": {
    "strategy_id": "crash_rebound_highconv",
    "market_regime": "Stressed / Volatile",
    "conviction_score": 7,
    "news_sentiment": 0.4,
    "macro_alignment": false,
    "technical_setup": "Price below 50‑day MA, 20‑day RSI < 30, volume spike > 2× average",
    "entry_reason": "Short‑term oversold bounce in stressed regime",
    "exit_plan": "2× ATR stop, 1.5× ATR target",
    "risk_notes": "Sector‑wide drag; macro headwinds indicate limited upside"
  }
}
```

#### "Strategy Intelligence" tab – data model spec

**Aggregation levels the dashboard must support:**
- Per `strategy_id`
- Per `market_regime`
- Per Specialist agent (e.g., Specialist‑Pattern, Specialist‑Macro)

**Minimum metrics to compute and expose:**
- Count of mock trades
- Win rate (positive P&L trades / total)
- Avg P&L per trade (in % of capital)
- Max drawdown within the strategy's holding window
- Distribution of `conviction_score` and `news_sentiment` for that strategy

**Frontend‑side queries:**
The dashboard shall allow:
- Filtering by `market_regime` and `strategy_id`
- Drill‑down into top‑100 trades (with full thesis JSON shown in a modal)
- Optionally, show a heatmap of `conviction_score` vs actual P&L for each strategy

**Spec language:**
The Strategy Intelligence tab must display aggregated performance metrics per strategy and regime, and allow the user to inspect the top‑100 recent mock trades with their full thesis JSON. Failure patterns shall be grouped and visualized by strategy, regime, and conviction/negative‑sentiment clusters. The thesis must be stored as a JSON‑serializable object in Firestore, preserving all keys specified above.

---

## 6. Non‑Functional Requirements

### Zero‑Cost / Budget‑Capped Compliance:
- The architecture must initially be designed to operate within the GCP "Always Free" tier constraints
- Where the prototype exceeds these limits:
  - The system must log an explicit warning in Firestore
  - It may throttle heavy components (e.g., limiting LLM calls per run or reducing the pre‑market universe size)
  - The developer may implement a configurable flag `allow_paid_services: bool` that, when set to `true`, enables scaled‑up usage of BigQuery, Cloud Functions concurrency, and LLM usage

### Statelessness:
- All agents are stateless Cloud Functions
- All state (universe, regime, trade history, strategy parameters) must persist in Firestore

### Observability:
- Every mock trade must include a `thesis` field (JSON) with at least:
  - `conviction_score`: 1–10
  - `news_sentiment`: −1 to +1
  - `macro_alignment`: Boolean
  - `technical_setup`: String
- Logs must distinguish between:
  - Approved mock trades
  - Rejected trades with a `failure_reason` (e.g., "regime mismatch", "news_sentiment too low", "Supervisor risk veto")

---

## 7. Backtesting Requirements

### Engine:
The backtesting engine must use **vectorbt** for parameter‑dense, fast array‑based simulations.

### Realism:
- All backtests must include configurable `slippage_bps` and `commission_rate_bps` variables (brokerage + STT)
- Hypothetical P&L calculations without these are invalid

### Constraints:
- Minimum backtest window: 3 years of daily NSE/BSE data
- Must support at least 10 different parameter grids per strategy (e.g., different conviction thresholds, regime windows, macro filters)

---

## 8. Acceptance Criteria

### Automated Tuning:
- The system must demonstrate successful adjustment of `conviction_thresholds` in the `strategy_registry` following a mock‑trade failure pattern (e.g., multiple consecutive losses in a specific regime)
- Tuning must respect the `min_sample_size` and `window_days` constraints

### Veto Logic:
- The Supervisor must correctly block trades when:
  - Sentinel broadcasts "Panic / Extreme Volatility" or "Stressed / Volatile" mode (as configured by the strategy)
  - News sentiment is below the `news_sentiment_min` threshold for the strategy
  - Blocked trades must be logged with `failure_reason = "veto"` and a human‑readable note

### Observability:
- The user must be able to:
  - View the Strategy Intelligence tab in the dashboard
  - Drill into top‑100 mock trades and see their full thesis JSON
- The Meta‑Analyst must generate automated performance reports (PDF or in‑dashboard) summarizing:
  - Win‑rates by strategy and regime
  - Impact of recent parameter‑tuning changes

---

## Document Metadata

- **Last Updated:** 2026‑05‑27
- **Status:** Active
- **Version:** 1.0.0
