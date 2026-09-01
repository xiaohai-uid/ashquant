"""巴菲特：情绪逆向 —— 深度恐惧（超卖）后止跌企稳介入；过度贪婪回避。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def buffett(df: pd.DataFrame) -> pd.Series:
    rsi = df["rsi14"]
    c, o = df["close"], df["open"]
    fearful = rsi < 28
    greedy = rsi > 75
    stabilizing = (c > o) & (c > c.shift(1))
    score = np.where(
        fearful & stabilizing, 0.9,
        np.where(greedy, -0.7, np.where(fearful, 0.3, 0.0)),
    )
    s = pd.Series(score, index=df.index, dtype=float)
    s.iloc[:20] = 0.0
    return s
