import numpy as np
import pandas as pd

from ashquant.indicators import add_indicators, assert_causal


def _make_dummy_ohlcv(n: int = 100) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    ret = np.random.normal(0.0005, 0.02, n)
    c = 100.0 * np.cumprod(1 + ret)
    h = c * (1 + np.abs(np.random.normal(0, 0.01, n)))
    l = c * (1 - np.abs(np.random.normal(0, 0.01, n)))
    o = l + (h - l) * np.random.uniform(0.2, 0.8, n)
    v = np.random.uniform(1e5, 1e6, n)
    amt = c * v
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v, "amount": amt}, index=dates)


def test_indicators_columns_and_values():
    df = _make_dummy_ohlcv(100)
    ind = add_indicators(df)
    for col in ["ma5", "ma20", "ma60", "macd_hist", "rsi14", "boll_mid", "atr14", "vol_ratio", "vol20"]:
        assert col in ind.columns
        assert not ind[col].iloc[-10:].isna().any()

    # RSI 范围断言 [0, 100]
    valid_rsi = ind["rsi14"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_causal_no_future_leak():
    """严禁未来函数断言（前缀不变性测试）。"""
    df = _make_dummy_ohlcv(150)
    assert_causal(df)
