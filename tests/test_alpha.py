import numpy as np
import pandas as pd

from ashquant.alpha import add_alpha_factors, extract_alpha_factors_at


def test_add_alpha_factors_causality():
    # 生成合成日线数据
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100.0 + np.cumsum(np.random.randn(n))
    high = close + 1.0
    low = close - 1.0
    open_p = close - 0.2
    volume = np.random.uniform(1e5, 5e5, size=n)

    df = pd.DataFrame(
        {
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )

    alpha_df = add_alpha_factors(df)

    assert "alpha_vol_surge" in alpha_df.columns
    assert "alpha_pv_divergence" in alpha_df.columns
    assert "alpha_squeeze_breakout" in alpha_df.columns
    assert "alpha_smart_money_acc" in alpha_df.columns
    assert "composite_alpha" in alpha_df.columns

    # 验证复合因子范围
    assert alpha_df["composite_alpha"].max() <= 1.0
    assert alpha_df["composite_alpha"].min() >= -1.0

    # 提取最后切片
    factors = extract_alpha_factors_at(alpha_df, -1)
    assert isinstance(factors.composite_alpha, float)


def test_squeeze_breakout_not_dead_code():
    from ashquant.indicators import add_indicators

    # 生成包含指标的真实数据
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    close = np.linspace(10, 20, 60)
    high = close + 0.5
    low = close - 0.5
    open_p = close
    volume = np.full(60, 1e5)
    df = pd.DataFrame({"open": open_p, "high": high, "low": low, "close": close, "volume": volume}, index=dates)

    ind_df = add_indicators(df)
    assert "atr14" in ind_df.columns
    assert "boll_low" in ind_df.columns

    alpha_df = add_alpha_factors(ind_df)
    # 验证 squeeze_breakout 因子被真实计算，而不是全部为 0 死代码
    squeeze_vals = alpha_df["alpha_squeeze_breakout"].dropna()
    assert (squeeze_vals != 0.0).any()

