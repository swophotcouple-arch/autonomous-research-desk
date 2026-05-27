# Autonomous Research Desk

An autonomous, serverless, multi‑agent trading research system for the Indian equity market (NSE/BSE). This system scans, analyzes, and optimizes trade strategies using AI agents, learns from historical performance, and adapts to changing market regimes—all without deploying real capital.

## 🎯 Project Vision

**Goal:** Transform manual market scanning into a self‑optimizing research desk that:
- 🤖 Autonomously screens and analyzes thousands of stocks daily
- 📊 Learns from mock‑trade performance (P&L and win‑rates)
- 🔄 Adapts strategy parameters based on market regime changes
- 📈 Provides deep insights via interactive dashboards
- 💰 Operates within GCP free tier (budget‑capped)

## 📋 Quick Start

### Prerequisites
- Python 3.x
- Google Cloud Platform (GCP) account (free tier eligible)
- GitHub (this repo)

### Setup Steps (Coming Soon)
1. Clone this repository
2. Configure GCP credentials and Firestore
3. Deploy agents to Cloud Functions
4. Access the React dashboard

## 📁 Repository Structure

```
autonomous-research-desk/
├── TRD.md                          # Complete technical requirements document
├── README.md                       # This file
├── docs/
│   ├── ARCHITECTURE.md            # System design & data flows
│   ├── SETUP_GUIDE.md             # Detailed setup instructions
│   └── API_REFERENCE.md           # Agent API specs
├── backend/
│   ├── agents/                    # Cloud Functions for each agent
│   │   ├── meta_analyst.py        # Pre/post-market screener & retrospective
│   │   ├── sentinel.py            # Market regime calculator
│   │   ├── specialist_pattern.py  # Technical analysis
│   │   ├── specialist_macro.py    # Macro analysis
│   │   ├── specialist_news.py     # News sentiment
│   │   └── supervisor.py          # Risk veto layer
│   ├── config/
│   │   ├── firestore_schema.json  # Firestore collections schema
│   │   └── gcp_defaults.yaml      # GCP configuration
│   └── utils/
│       ├── market_regime.py       # Regime calculation logic
│       ├── backtest.py            # Backtesting engine (vectorbt)
│       └── data_fetch.py          # NSE/BSE data retrieval
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── pages/                 # Page layouts
│   │   ├── hooks/                 # Custom React hooks
│   │   └── App.jsx                # Main app
│   └── package.json               # Frontend dependencies
├── tests/
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── backtest/                  # Backtest validation
└── .cursorrules                   # Cursor AI constraints
```

## 🏗️ System Architecture

### High‑Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Cloud Scheduler (GCP)                   │
│                  (Triggers daily flows)                  │
└────────────┬────────────────────────────────────────────┘
             │
     ┌───────▼────────┐
     │  Meta-Analyst  │
     │ (Pre-Market)   │  ← Filters NSE/BSE by liquidity & volatility
     └───────┬────────┘
             │
     ┌───────▼──────────┐
     │ Firestore        │
     │ target_universe  │
     └───────┬──────────┘
             │
     ┌───────▼────────┐
     │   Sentinel     │  ← Detects market regime (Trending Bull, Panic, etc.)
     └───────┬────────┘
             │
     ┌───────▼──────────────────────────────────┐
     │  Specialist Agents (Parallel)            │
     ├──────────────────────────────────────────┤
     │ • Specialist-Pattern (Technical)         │
     │ • Specialist-Macro (Macro headwinds)     │
     │ • Specialist-News (News sentiment)       │
     └───────┬──────────────────────────────────┘
             │
     ┌───────▼────────┐
     │   Supervisor   │  ← Risk veto layer (exposure, max trades, filters)
     └───────┬────────┘
             │
     ┌───────▼───────────────┐
     │ Approved Trade?       │
     └───────┬───────┬───────┘
             │       │
        YES  │       │  NO
             │       │
     ┌───────▼──┐  ┌─▼──────────────┐
     │Mock Trade│  │Log Rejection   │
     └───────┬──┘  └─┬──────────────┘
             │       │
             └───┬───┘
                 │
         ┌───────▼──────────┐
         │ Firestore        │
         │ mock_trades      │
         └───────┬──────────┘
                 │
         ┌───────▼────────────────┐
         │  Meta-Analyst          │
         │ (Post-Market)          │  ← Analyzes P&L, updates strategy registry
         └───────┬────────────────┘
                 │
         ┌───────▼──────────────┐
         │ strategy_registry    │  ← Self-correction: tune parameters
         └──────────────────────┘
```

### Key Components

| Component | Role | Technology |
|-----------|------|-----------|
| **Meta‑Analyst** | Pre‑market screener & post‑market retrospective | Python Cloud Function |
| **Sentinel** | Market regime detector | Python Cloud Function |
| **Specialists** | Technical, macro, news analysis | Python Cloud Functions |
| **Supervisor** | Risk veto layer | Python Cloud Function |
| **Firestore** | State, config, mock trades | GCP Firestore |
| **BigQuery** | Historical data, technical indicators | GCP BigQuery |
| **Dashboard** | Strategy intelligence & drill‑down | React + Tailwind |

## 🤖 The 7‑Agent Ecosystem

1. **Meta‑Analyst (Pre‑Market)** – Filters NSE/BSE universe by liquidity & volatility; populates target_universe
2. **Meta‑Analyst (Post‑Market)** – Analyzes mock‑trade P&L; updates strategy_registry with self‑correction rules
3. **Sentinel** – Computes market regime (Trending Bull, Panic, etc.) from Nifty, VIX, ADR
4. **Specialist‑Pattern** – Technical analysis (MA, RSI, breakouts, volume)
5. **Specialist‑Macro** – Macro headwinds (rate hikes, inflation, macro sentiment)
6. **Specialist‑News** – News sentiment ingestion and cross‑reference
7. **Supervisor** – Risk veto layer (exposure caps, max trades/day, regime filters)

## 📊 Market Regimes

The Sentinel classifies market state into one of five regimes:

| Regime | Nifty 20d Return | VIX Level | ADR | Use Case |
|--------|-----------------|-----------|-----|----------|
| 🟢 **Trending Bull** | > 0, positive trend | < 1.0× mean | > 70 | Trend‑following strategies |
| 🟡 **Recovery / Relief** | > 0, recent drawdown | < 1.5× mean | 50–70 | Bounce trades |
| ⚪ **Choppy / Neutral** | ≈ 0 (−1% to +1%) | ≈ mean | 40–60 | Mean‑reversion |
| 🔴 **Stressed / Volatile** | < 0 | ≥ 1.5× mean | < 40 | High conviction only |
| 🔴🔴 **Panic / Extreme** | ≤ −3% | ≥ 2.0× mean | < 30 | Restricted (selective) |

## 📈 Mock Trading & P&L

- **No real capital deployed** – All trades are simulated
- **Full thesis tracking** – Each mock trade includes:
  - Conviction score (1–10)
  - News sentiment (−1 to +1)
  - Macro alignment (Boolean)
  - Technical setup (String)
  - Entry & exit plan
- **Performance metrics:**
  - Win rate (% of profitable trades)
  - Avg P&L per trade
  - Max drawdown
  - Regime‑aware statistics

## 🔧 Configuration

All agent parameters are stored in Firestore's `strategy_registry` collection. Example:

```json
{
  "strategy_id": "crash_rebound_highconv",
  "name": "Crash‑Rebound, High Conviction",
  "conviction_threshold": 7,
  "allowed_regimes": ["Stressed / Volatile", "Panic / Extreme Volatility"],
  "max_exposure_per_ticker_pct": 2,
  "news_sentiment_min": 0.2,
  "enable_self_correction": true
}
```

**Key principle:** Hard‑coded thresholds are prohibited. All logic is configurable via Firestore.

## 🧪 Backtesting

- **Engine:** vectorbt (fast, array‑based)
- **Realism:** Configurable slippage & commission rates
- **Minimum window:** 3 years of daily NSE/BSE data
- **Parameter grids:** Support ≥10 parameter combinations per strategy

## 💰 Budget & Cost Control

- **Design goal:** Operate within GCP **Always Free** tier
- **Free tier limits:**
  - Cloud Functions: 2M invocations/month, 400k GB-seconds
  - Firestore: 1 GB storage, 50k reads/day, 20k writes/day
  - BigQuery: 1 TB/month query processing
- **Throttling:** System logs warnings and reduces universe size if limits approached
- **Paid mode:** `allow_paid_services: true` enables scaled‑up usage

## 📊 Dashboard Features

### Strategy Intelligence Tab
- **Filters:** By regime, strategy_id, agent type
- **Metrics:**
  - Mock trade count
  - Win rate & P&L distribution
  - Conviction score vs actual returns
  - Failure patterns by regime
- **Drill‑down:** View top‑100 trades with full thesis JSON
- **Visualizations:**
  - Win rate heatmaps (conviction vs outcome)
  - Regime transition flows
  - P&L attribution charts

## 🚀 Development Roadmap

### Phase 1: Foundation (Weeks 1–3)
- ✅ Set up GCP infrastructure (Firestore, BigQuery)
- ✅ Deploy Sentinel & Meta‑Analyst agents
- ✅ Create strategy_registry in Firestore
- ✅ Build mock trade logger

### Phase 2: Specialists (Weeks 4–6)
- ✅ Deploy Specialist‑Pattern, Specialist‑Macro, Specialist‑News
- ✅ Integrate news & macro APIs
- ✅ Build Supervisor risk veto layer

### Phase 3: Dashboard & Observability (Weeks 7–9)
- ✅ Build React dashboard with Strategy Intelligence tab
- ✅ Implement drill‑down & visualization
- ✅ Create automated performance reports

### Phase 4: Self‑Correction (Weeks 10–12)
- ✅ Implement Meta‑Analyst P&L aggregation
- ✅ Build self‑correction tuning logic
- ✅ End‑to‑end system testing & validation

## 📖 Documentation

- **TRD.md** – Complete technical specification
- **ARCHITECTURE.md** – System design & data flows (coming soon)
- **SETUP_GUIDE.md** – Step‑by‑step deployment guide (coming soon)
- **API_REFERENCE.md** – Agent API specifications (coming soon)

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.x, Google Cloud Functions |
| **Database** | Firestore (document store) |
| **Analytics** | BigQuery (data warehouse) |
| **AI/LLM** | Google Gemini 2.5 (Flash & Pro) |
| **Frontend** | React, Vite, Tailwind CSS, shadcn/ui |
| **Backtesting** | vectorbt |
| **DevOps** | Google Cloud Scheduler, GitHub Actions |

## 📝 Contributing

This project is under active development. For contributions:
1. Check the GitHub Issues for open tasks
2. Follow the architecture and TRD specifications
3. All agents must read config from Firestore (no hard‑coded logic)
4. Each mock trade must include a complete thesis JSON

## 📄 License

(To be determined)

## 🤝 Support

For questions or issues:
- Review the TRD.md for detailed specifications
- Check the docs/ directory for guides
- Open a GitHub Issue

---

**Last Updated:** 2026‑05‑27  
**Status:** In Development  
**Current Phase:** Phase 1 (Foundation)
