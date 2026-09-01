"""利弗莫尔：趋势跟踪（多头排列 + 20 日新高突破；多空对称）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def livermore(df: pd.DataFrame) -> pd.Series:
    c, ma20, ma60 = df["close"], df["ma20"], df["ma60"]
    up = (c > ma20) & (ma20 > ma60) & (ma20 > ma20.shift(5))
    dn = (c < ma20) & (ma20 < ma60) & (ma20 < ma20.shift(5))
    base = np.where(
        up, 0.8,
        np.where(dn, -0.8, 0.5 * np.tanh(((c / ma20) - 1).clip(-0.3, 0.3) * 10)),
    )
    hi20 = c.rolling(20).max().shift(1)
    lo20 = c.rolling(20).min().shift(1)
    bonus = np.where(c >= hi20, 0.2, np.where(c <= lo20, -0.2, 0.0))
    score = np.clip(base + bonus, -1.0, 1.0)
    s = pd.Series(score, index=df.index, dtype=float)
    s.iloc[:60] = 0.0  # 预热期无信号
    return s
