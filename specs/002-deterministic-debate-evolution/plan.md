# Technical Implementation Plan: 002-deterministic-debate-evolution

**Feature**: `deterministic-debate-evolution` (ashquant v0.2.0)  
**Created Date**: 2026-09-02  
**Status**: Ready for Tasks  

---

## 1. System Architecture & Dependency Topology

To strictly enforce GitNexus **Zero Cycle Gate (`cycleCount: 0`)**, the module dependency hierarchy is strictly layered top-down:

```
                  ┌──────────────────────┐
                  │    cli / web (UI)    │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │     strategy.py      │
                  └──┬───────┬─────────┬─┘
                     │       │         │
       ┌─────────────┘       │         └──────────────┐
       ▼                     ▼                        ▼
┌──────────────┐    ┌─────────────────┐     ┌──────────────────┐
│ ashquant.    │    │ ashquant.       │     │ ashquant.        │
│ debate       │    │ alpha           │     │ masters          │
└──────┬───────┘    └────────┬────────┘     └─────────┬────────┘
       │                     │                        │
       │                     │                        │
       └─────────────┬───────┴────────────────────────┘
                     ▼
          ┌─────────────────────┐
          │ ashquant.indicators │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   ashquant.data     │ (store / aksource / alternative)
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   ashquant.domain   │
          └─────────────────────┘
```

**Dependency Invariants**:
- `domain.py`: Leaf module containing standard dataclasses (`Bar`, `SpotQuote`, `MasterSignal`, `DebateVerdict`, `ReflectionRecord`).
- `data/`: Reads raw APIs and local Parquet caches. Only imports `domain` and `config`.
- `indicators.py` & `alpha/`: Pure mathematical transformations over DataFrames. No imports from `masters` or `debate`.
- `masters/`: Quantitative rules scoring. Imports `indicators` and `domain`.
- `debate/`: Multi-agent state machine and reflection memory. Imports `domain` and `masters`.
- `backtest/`: Microstructure matching rules and circuit breaker.
- `strategy.py`: Pipeline orchestrator unifying `data` → `alpha` → `masters` → `debate` → `calibration`.

---

## 2. Detailed Technical Components

### 2.1 `ashquant.data.alternative` (A 股特色资金流)
- **`fetch_northbound_flow(symbol: str) -> pd.DataFrame`**:
  - Pulls Shanghai/Shenzhen-Hong Kong Stock Connect daily net holding changes.
  - Columns: `date`, `hold_shares`, `hold_ratio`, `net_buy_shares`.
- **`fetch_margin_detail(symbol: str) -> pd.DataFrame`**:
  - Pulls daily financing buy/repayment and margin balances.
- **`fetch_fund_flow(symbol: str) -> pd.DataFrame`**:
  - Pulls super-large, large, medium, small net inflow amounts and ratios.
- **Cache**: Cached to `data/alternative/{symbol}_flow.parquet`.

### 2.2 `ashquant.alpha` (Qlib 风格 Alpha 因子库)
- **`add_alpha_factors(df: pd.DataFrame) -> pd.DataFrame`**:
  - **`alpha_vol_surge`**: 5-day volume acceleration normalized by 20-day volume volatility.
  - **`alpha_pv_divergence`**: Price making higher highs while MACD / Volume momentum slopes downward (negative values = bearish divergence).
  - **`alpha_squeeze_breakout`**: Bollinger Bands narrowing inside Keltner Channels (ATR) followed by directional expansion.
  - **`alpha_smart_money_acc`**: Rolling 3-day Northbound accumulation strength.

### 2.3 `ashquant.debate` (TradingAgents 对抗辩论引擎)
- **`DebateRole`**:
  - `BULL_LIVERMORE`: Explores trend breakouts, volume expansion, resistance breakthroughs.
  - `BEAR_MUNGER`: Explores valuation risk, margin degradation, high-level distribution, T+1 liquidity trap, and historical reflection traps.
  - `CIO_ARBITRATOR`: Assesses debate transcripts, enforces VETO if bear reveals unmitigated fatal flaws.
- **`MasterDebateArena`**:
  - **Offline Quantitative Mode**: Evaluates multi-factor score balance and rule-based checks (e.g., if `alpha_pv_divergence < -0.6` or `overbought_rsi > 80`, Bear automatically triggers VETO).
  - **Online LLM Mode**: Uses OpenAI-compatible API (`ASHQUANT_LLM_API_KEY`) to orchestrate a 2-round LangGraph-style dialogue.
- **Outputs**:
  - `DebateTranscript`: Full text of Bull, Bear, and CIO speeches.
  - `DebateVerdict`: `decision` (`BULLISH_APPROVED`, `VETOED_ON_RISK`, `NEUTRAL`), `conviction_score` $\in [0, 1]$, `veto_reasons` (`list[str]`).

### 2.4 `ashquant.debate.memory` (ReflectionMemory 自进化反思飞轮)
- **File**: `data/reflection_memory.jsonl`
- **Schema**:
  ```json
  {
    "id": "refl_20260902_600519",
    "symbol": "600519",
    "timestamp": "2026-09-02T15:05:00",
    "forecast_direction": "UP",
    "actual_return": -0.034,
    "pattern_tags": ["high_volume_breakout", "rsi_overbought"],
    "fatal_blindspot": "Northbound heavy selling during morning session ignored by Bull",
    "rule_learned": "Never buy breakout when Northbound net outflow exceeds 300M"
  }
  ```
- **Engine**:
  - `record_post_mortem(prediction, actual_bar)`: Appends failed trade retrospectives.
  - `retrieve_relevant_rules(symbol, current_tags) -> list[str]`: Injects relevant historical warnings into Bear's debate context.

### 2.5 `ashquant.backtest.breaker` (RegimeBreaker 异常行情熔断)
- **`check_market_regime(index_bar, market_stats) -> RegimeStatus`**:
  - `NORMAL`: All trading permitted.
  - `TURBULENT`: Volatility elevated; reduce sizing by 50%.
  - `PANIC_CIRCUIT_BROKEN`: CSI 300 / Index down $\ge 2.5\%$ or $>80\%$ stocks falling; **ALL new buys prohibited**.
- **`AccountBreaker`**: 3 consecutive loss streaks trigger a 24-hour mandatory pause in paper trading.

---

## 3. Data Model & Contract Artifacts

### 3.1 `specs/002-deterministic-debate-evolution/data-model.md`
Will define `AlphaVector`, `DebateTranscript`, `DebateVerdict`, `ReflectionRecord`, `MarketRegime`.

### 3.2 `specs/002-deterministic-debate-evolution/contracts/`
Will define:
- `cli-commands.md`: Specification for `ashquant scan`, `ashquant debate`, `ashquant settle`, etc.
- `web-api.md`: Specification for `/api/debate/{symbol}`, `/api/reflections`, `/api/scan`.
