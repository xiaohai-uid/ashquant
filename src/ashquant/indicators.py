"""技术指标库：全部因果计算（只用 ≤t 数据），可做前缀不变性检验（宪法 IV）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """输入 OHLCV 日线（Date 索引），附加指标列，返回新 DataFrame。

    附加列: ma5/ma20/ma60, ema12/ema26, macd_dif/macd_dea/macd_hist,
    rsi14, boll_mid/boll_up/boll_low, atr14, roc10, vol_ratio, vol20
    """
    out = df.copy()
    c, h, l, o, v = out["close"], out["high"], out["low"], out["open"], out["volume"]

    out["ma5"] = c.rolling(5).mean()
    out["ma20"] = c.rolling(20).mean()
    out["ma60"] = c.rolling(60).mean()
    out["ema12"] = c.ewm(span=12, adjust=False).mean()
    out["ema26"] = c.ewm(span=26, adjust=False).mean()

    dif = out["ema12"] - out["ema26"]
    dea = dif.ewm(span=9, adjust=False).mean()
    out["macd_dif"] = dif
    out["macd_dea"] = dea
    out["macd_hist"] = 2.0 * (dif - dea)  # A股软件惯例 MACD 柱 = 2*(DIF-DEA)

    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()  # Wilder 平滑
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out["rsi14"] = 100 - 100 / (1 + rs)
    out.loc[(avg_loss == 0) & (avg_gain > 0), "rsi14"] = 100.0
    out.loc[(avg_loss == 0) & (avg_gain == 0), "rsi14"] = 50.0

    mid = c.rolling(20).mean()
    std = c.rolling(20).std(ddof=0)
    out["boll_mid"] = mid
    out["boll_up"] = mid + 2 * std
    out["boll_low"] = mid - 2 * std

    prev_c = c.shift(1)
    tr = pd.concat(
        [h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1 / 14, adjust=False).mean()

    out["roc10"] = c.pct_change(10)
    out["vol_ratio"] = v / v.rolling(5).mean()  # 量比：当日量 / 5日均量
    out["vol20"] = c.pct_change().rolling(20).std(ddof=0)  # 20日日收益率波动
    out["open_"] = o
    return out


INDICATOR_COLS = [
    "ma5", "ma20", "ma60", "ema12", "ema26", "macd_dif", "macd_dea", "macd_hist",
    "rsi14", "boll_mid", "boll_up", "boll_low", "atr14", "roc10", "vol_ratio", "vol20",
]


def assert_causal(df: pd.DataFrame) -> None:
    """前缀不变性自检：任意指标在 t 行的值不依赖 t 之后的数据（测试与引擎调用）。"""
    full = add_indicators(df)
    half = add_indicators(df.iloc[: len(df) // 2])
    tail = full.loc[half.index]
    for col in INDICATOR_COLS:
        a, b = tail[col], half[col]
        mask = a.notna() & b.notna()
        if mask.any():
            diff = (a[mask] - b[mask]).abs().max()
            assert diff < 1e-9, f"指标 {col} 存在未来函数（前缀偏差 {diff}）"
