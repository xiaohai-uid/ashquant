# Python API Contract（库形态，`from ashquant import ...`）

仅列 v1 承诺稳定的公开面；内部模块可自由重构（宪法 V）。

```python
from ashquant.data.store import BarStore
store = BarStore(data_dir=...)           # 或默认 ~/.ashquant 与 ./data 二级探测
store.save_bars(symbol, df, source="akshare")
df = store.load_bars(symbol)             # DataFrame[DateIndex, OHLCV]
store.missing_symbols(symbols)           # 断点续抓支持

from ashquant.quotes import snapshot     # snapshot(symbols) -> list[SpotQuote]
from ashquant.indicators import add_indicators  # df -> df 附 MA/EMA/MACD/RSI/BOLL/ATR/ROC/VOL_RATIO
from ashquant.masters import all_masters, compute_signals(df)  # -> list[MasterSignal]
from ashquant.strategy import ensemble_score, calibrate_prob, build_target_portfolio
from ashquant.backtest import run_backtest, BacktestConfig   # -> BacktestReport
from ashquant.backtest.rules import MarketRules, simulate_fill  # 规则引擎可独立复用
from ashquant.predict import predict_next_day, prediction_stats
from ashquant.paper import PaperBroker   # init/buy/sell/show/export
```

稳定性承诺：这些符号在 v1.x 不删除、不改签名（参数只加可选）；数据类字段只增不改名。
