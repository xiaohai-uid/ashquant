# 11. Alternative Data & High-Confidence Signal Fusion for A-Share Quant

## 1. A-Share Alternative Data Landscape & Predictive Validity

### 1.1 Capital Flow Signals (资金流向 - High Information Ratio)
1. **北向资金 (Northbound Smart Money)**:
   - **Mechanism**: Foreign institutional holdings and daily net inflows via Shanghai/Shenzhen-Hong Kong Stock Connect.
   - **Empirical Edge**: High persistence in multi-day accumulation; strong positive alpha on 3-day to 10-day holding horizons during trending regimes.
   - **API Source**: `akshare.stock_em_hsgt_north_net_flow_in()`, `akshare.stock_hsgt_hold_stock_em()`.

2. **融资融券 (Margin Trading & Short Selling - Retail Leverage Proxy)**:
   - **Mechanism**: Financing balance expansion indicates retail extreme bullishness; rapid deleveraging triggers liquidity cascades.
   - **Empirical Edge**: Serves as a contrarian indicator at extreme historical percentiles (>95th percentile often precedes local market tops).
   - **API Source**: `akshare.stock_margin_detail_sse()`, `akshare.stock_margin_detail_szse()`.

3. **主力大单资金 (Institutional Block & Tick-Level Flow)**:
   - **Mechanism**: Tick volume partitioned into Super-Large (>1M RMB), Large, Medium, Small orders.
   - **Empirical Edge**: High Super-Large net inflow alongside low price change signals institutional accumulation without slippage impact.
   - **API Source**: `akshare.stock_individual_fund_flow()`.

---

## 2. A-Share Market Microstructure Nuances

1. **T+1 & Asymmetric Liquidity**:
   - Buy intraday cannot sell until T+1. Over-optimistic intraday entries cannot be hedged quickly by retail participants.
   - Predictions must forecast **Close-to-Close (T to T+1)** or **Open(T+1) to Close(T+1)**, not unexecutable intraday ticks.

2. **Price Limits (涨跌停) & Magnet Effect**:
   - 10% (Main Board), 20% (ChiNext/STAR), 30% (BSE).
   - Once locked at limit-up, buy execution probability drops to near zero; limit-down prevents liquidating positions.

3. **Policy & Retail Sentiment Reflexivity (政策与情绪共振)**:
   - A-share retail turnover exceeds 60-70% in high-volume regimes. Herding behavior (羊群效应) creates pronounced short-term momentum and long-term mean reversion.

---

## 3. High-Confidence Multi-Signal Fusion Architecture

### 3.1 Why Single Models Fail (The "99% Illusion" vs Robust Bayesian Probability)
- In financial time series, Signal-to-Noise Ratio (SNR) is typically < 0.05.
- Claiming "100% deterministic prediction" on a random walk is mathematically invalid (Fama EMH).
- **The True Objective**: Filter out 90% of ambiguous setups, and only trigger high-conviction trades when **all orthogonal signals agree** (Confluence / 共振), achieving a statistically verified 65-75% directional hit rate with asymmetric payoff (Win/Loss ratio > 2.0).

### 3.2 The 4-Layer Orthogonal Signal Stack:
1. **Trend / Momentum Layer** (Livermore / Druckenmiller): Causal Moving Averages, Donchian Channels, Volume Surge.
2. **Value / Mean-Reversion Layer** (Graham / Munger): RSI Extreme, Bollinger Band Distance, Historical Valuation Bands.
3. **Smart Money & Flow Layer** (Northbound / Margin / Block Trades): Institutional footprint alignment.
4. **LLM Master Debate & Risk Governance Layer** (Buffett / Soros / LangGraph Bull-Bear Debate): Contextual qualitative analysis, policy sentiment evaluation, risk veto.

### 3.3 Bayesian Confluence Scoring Formula:
$$P(\text{Up}) = \sigma\left(w_1 \cdot S_{\text{Trend}} + w_2 \cdot S_{\text{Reversion}} + w_3 \cdot S_{\text{Flow}} + w_4 \cdot S_{\text{Debate}}\right)$$
Trades are only executed when calibrated $P(\text{Up}) \ge 0.70$ and Risk Manager does not issue a veto.
