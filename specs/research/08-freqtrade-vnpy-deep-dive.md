# 08. freqtrade & vn.py Deep Dive: Production Trading Frameworks & A-Share Gateways

## 1. freqtrade (53.9k Stars) - Strategy Lifecycle & FreqAI Machine Learning

### 1.1 Core Architecture Patterns
- **Standardized Strategy Interface (`IStrategy`)**:
  - `populate_indicators(dataframe, metadata)`: Vectorized indicator creation.
  - `populate_entry_trend(dataframe, metadata)`: Vectorized boolean mask for entry conditions.
  - `populate_exit_trend(dataframe, metadata)`: Vectorized boolean mask for exit conditions.
  - `custom_stoploss(...)` / `custom_stake_amount(...)`: Dynamic execution rules.
- **FreqAI (Automated Machine Learning Extension)**:
  - Continuously retrains models (LightGBM, XGBoost, CatBoost, PyTorch) on a rolling sliding window (e.g. past 30 days) to predict future price targets or directional classification.
  - Generates a **Distance-to-Target (DI) metric** / Dissimilarity Index: If current market features drift too far from the training distribution, FreqAI automatically sets the prediction confidence to zero and disables trading.
- **Dry-Run Mode & Protection Engines**:
  - `DryRunHandler`: Intercepts orders and simulates realistic slippage, fee deductions, and partial fills without sending funds.
  - `ProtectionManager`: Global circuits that halt trading across the entire account if a drawdown limit (e.g., -5% in 2 hours) or consecutive loss streak (e.g., 3 failed trades) is detected.

---

## 2. vn.py (45k Stars) - Institutional China Market Gateway & Event Engine

### 2.1 Core Architecture Patterns
- **`EventEngine`**:
  - High-throughput thread-safe queue (`Queue`) dispatching events (`EVENT_TICK`, `EVENT_BAR`, `EVENT_ORDER`, `EVENT_TRADE`, `EVENT_POSITION`) to handlers with sub-millisecond overhead.
- **A-Share Institutional Broker Gateways**:
  - `CtpGateway` (China Futures / Options).
  - `XtpGateway` (Zhongtai Securities institutional high-speed equity bus).
  - `QmtGateway` / `MiniQmt` (XtQuant - the most accessible programmatic trading bridge for Chinese individual investors through Guojin, Guosen, CITIC).
- **CTA Template (`CtaTemplate`)**:
  - Stateful bar-by-bar lifecycle callback:
    `on_init()` -> `on_start()` -> `on_tick()` -> `on_bar()` -> `on_order()` -> `on_trade()`.

---

## 3. Key Takeaways for ashquant v0.2.0

1. **Adopt FreqAI's Dissimilarity Index (DI / 数据漂移拒绝机制)**:
   - When market volatility or volume regime radically departs from historical training distributions (e.g., during market-wide extreme liquidity panics), `ashquant` should reject making predictions rather than outputting dangerous random guesses.
2. **Adopt Freqtrade's Protection Circuit Breakers (熔断保护机制)**:
   - In `ashquant.paper`, implement a global account circuit breaker: 3 consecutive stop-losses automatically pause paper trading for 24 hours to prevent revenge trading in adverse regimes.
3. **Formalize QMT / MiniQMT Gateway Interface**:
   - Keep paper trading as default, but provide a 1-to-1 matching `BrokerGateway` protocol so users with MiniQMT can switch execution seamlessly with zero strategy code changes.
