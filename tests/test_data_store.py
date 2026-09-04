from pathlib import Path

import numpy as np
import pandas as pd

from ashquant.data.store import BarStore, compute_dynamic_qfq


def test_compute_dynamic_qfq():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    # Day 1, 2: 100元，累积复权因子 1.0
    # Day 3: 10送10除权，不复权收盘 50元，累积复权因子 2.0
    # Day 4: 不复权收盘 52元，累积复权因子 2.0
    df = pd.DataFrame(
        {
            "open": [99.0, 100.0, 49.0, 50.0],
            "high": [101.0, 102.0, 51.0, 53.0],
            "low": [98.0, 99.0, 48.0, 49.0],
            "close": [100.0, 100.0, 50.0, 52.0],
            "volume": [10000.0, 10000.0, 20000.0, 20000.0],
            "amount": [1e6, 1e6, 1e6, 1.04e6],
            "adj_factor": [1.0, 1.0, 2.0, 2.0],
        },
        index=dates,
    )

    # 1. 以最新日 (Day 4) 为基准的前复权：Day 1, 2 价格折半 (100 * 1.0 / 2.0 = 50.0)
    qfq_latest = compute_dynamic_qfq(df)
    assert qfq_latest["close"].iloc[0] == 50.0
    assert qfq_latest["close"].iloc[1] == 50.0
    assert qfq_latest["close"].iloc[2] == 50.0
    assert qfq_latest["close"].iloc[3] == 52.0
    # 成交量反向调整：Day 1, 2 成交量折算 (10000 / (1.0 / 2.0) = 20000.0)
    assert qfq_latest["volume"].iloc[0] == 20000.0

    # 2. 历史截面回测：以 Day 2 为截面计算前复权（防未来函数，此时除权尚未发生）
    qfq_as_of_d2 = compute_dynamic_qfq(df, as_of="2024-01-02")
    # 在 Day 2 截面视角下，Day 1 和 Day 2 的价格基准因子为 1.0，价格为原始 100.0
    assert qfq_as_of_d2.loc[: "2024-01-02", "close"].iloc[0] == 100.0
    assert qfq_as_of_d2.loc[: "2024-01-02", "close"].iloc[1] == 100.0

    # 3. 若无 adj_factor 列，应安全原样返回
    df_no_adj = df.drop(columns=["adj_factor"])
    res_no_adj = compute_dynamic_qfq(df_no_adj)
    assert (res_no_adj["close"] == df_no_adj["close"]).all()


def test_bar_store_load_bars_with_adjust(tmp_path: Path):
    store = BarStore(tmp_path)
    dates = pd.date_range("2024-01-01", periods=2, freq="B")
    df = pd.DataFrame(
        {
            "open": [100.0, 50.0],
            "high": [101.0, 51.0],
            "low": [99.0, 49.0],
            "close": [100.0, 50.0],
            "volume": [1000.0, 2000.0],
            "amount": [1e5, 1e5],
            "adj_factor": [1.0, 2.0],
        },
        index=dates,
    )
    store.save_bars("600519", df)

    # 默认加载 qfq
    df_qfq = store.load_bars("600519")
    assert df_qfq is not None
    assert df_qfq["close"].iloc[0] == 50.0

    # 显式加载 raw
    df_raw = store.load_bars("600519", adjust="raw")
    assert df_raw is not None
    assert df_raw["close"].iloc[0] == 100.0


def test_analyze_stock_prevents_double_qfq():
    from ashquant.strategy import analyze_stock

    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    # 模拟包含 adj_factor 的日线
    close = np.linspace(100, 200, 60)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(60, 10000.0),
            "adj_factor": np.full(60, 2.0),
        },
        index=dates,
    )

    # analyze_stock 传入带有 adj_factor 的 bars 时，指标计算应只执行一次 QFQ，不可二次折算
    analysis = analyze_stock("600519", df, flow_loader=lambda _: None)
    assert analysis is not None
    # 最终 close 序列应保持原始或单次换算一致性，绝不应发生 (ratio)^2 错误
    assert np.isclose(analysis.close.iloc[-1], 200.0)

