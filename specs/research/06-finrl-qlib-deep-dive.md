# 06. FinRL & Microsoft Qlib Deep Dive: Quantitative AI Architecture & Lessons for ashquant

## 1. Microsoft Qlib (48.2k+ Stars) - Industrial Alpha Factor & ML Pipeline

### 1.1 Core Architecture Patterns
- **Expression Engine (Qlib Alpha)**:
  - Declarative string expression engine for computing dynamic alphas across tens of thousands of instruments without loop overhead:
    - e.g., `Rank($close / Ref($close, 5))` or `Correlation($close, $volume, 10)`.
  - Avoids Python interpreter GIL bottlenecks by evaluating expressions in optimized Cython/C++ array operations.
- **Data Server & Fast Storage**:
  - Binary point-in-time flat files (similar to HDF5/Feather/Parquet) indexed by instrument and date.
  - Supports automated dividend adjustment (backward/forward split adjustment) dynamically without corrupting historical raw prices.
- **Model Zoo**:
  - Comprehensive benchmarks comparing GBDT (LightGBM, CatBoost, XGBoost) vs Deep Learning (LSTM, GRU, ALSTM, SFM, Transformer, TabNet).
  - **Empirical Takeaway**: In tabular financial time series, **LightGBM / CatBoost** consistently outperforms raw Transformers/LSTMs in out-of-sample information ratio (IC/ICIR) due to robustness against extreme noise, lower overfitting risk, and instant training speed.
- **Native China A-Share Heritage**:
  - Originally developed by Microsoft Research Asia specifically for Shanghai/Shenzhen A-shares (CSI 300 / CSI 500 / CSI 800 benchmarks).
  - Explicitly accounts for trading halts (`is_trading`), limit-up/limit-down conditions, and benchmark excess returns.

### 1.2 Applicability to ashquant
- `ashquant` already leverages clean vectorized pandas calculations (`ashquant.indicators`).
- **Takeaway for v0.2.0**:
  - Introduce an extensible **Alpha Factor Zoo** inspired by Qlib (e.g., Alpha101 / Alpha158 subsets suitable for A-shares: Volatility ratios, Momentum divergence, Volume-Price correlation).
  - Train an ensemble LightGBM/Ridge meta-model alongside the Master Agents to dynamically weight signals conditioned on market volatility regimes.

---

## 2. AI4Finance FinRL (10k+ Stars) - Deep Reinforcement Learning for Finance

### 2.1 Core Architectural Patterns
- **Gym-Style Market Environment (`StockTradingEnv`)**:
  - State Space: `[Current Cash, Current Holdings, Normalized Prices, Indicator Vector (MACD, RSI, CCI, ADX)]`.
  - Action Space: Continuous portfolio weights $\in [-1, 1]$ or discrete share orders $\in [-k, k]$.
  - Reward Function:
    $$R_t = \text{Portfolio Return}_t - \lambda \cdot \text{Variance}_t - \gamma \cdot \text{Transaction Cost}_t$$
  - Explicit transaction cost modeling ($0.1\%$ default in FinRL) prevents high-frequency churn.
- **DRL Algorithm Zoo**:
  - PPO (Proximal Policy Optimization), DDPG, A2C, SAC, TD3.
  - Ensemble strategy: Running multiple algorithms and picking the agent with the highest recent rolling Sharpe ratio.
- **Practical Limitations in Real Financial Markets**:
  - High non-stationarity leads to severe policy degradation in unseen market regimes (e.g., a policy trained during a bull run suffers catastrophic drawdown when a liquidity crunch occurs).
  - Requires continuous walk-forward retraining to prevent policy obsolescence.

### 2.2 Applicability to ashquant
- Rather than an opaque end-to-end RL agent that directly executes trades (which acts as a black box and can hallucinate catastrophic trades), `ashquant` should use **Reinforcement Learning from Financial Feedback (RLFF)** strictly at the **Meta-Allocator level**:
  - Let the Master Agents generate interpretable thesis/signals.
  - Let the meta-controller allocate portfolio capital weights dynamically across masters based on recent Sharpe/Calmar ratios.
