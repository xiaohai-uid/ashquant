"""格雷厄姆：安全边际代理 —— 深度超卖（布林下轨/RSI）给均值回归做多分。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def graham(df: pd.DataFrame) -> pd.Series:
    c, rsi = df["close"], df["rsi14"]
    below_band = c < df["boll_low"]
    deep = below_band | (rsi < 30)
    mild = rsi < 40
    over = rsi > 70
    score = np.where(
        deep, 0.8,
        np.where(mild, 0.3, np.where(over, -0.6, 0.1 * np.tanh((45 - rsi) / 15))),
    )
    s = pd.Series(score, index=df.index, dtype=float)
    s.iloc[:20] = 0.0
    return s
