"""芒格：反过来想 —— 低波平静市场加分，异常高波（愚蠢边缘）减分。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def munger(df: pd.DataFrame) -> pd.Series:
    vol = df["vol20"]
    baseline = vol.rolling(250, min_periods=60).mean()
    ratio = vol / baseline
    score = np.where(
        ratio < 0.8, 0.4,
        np.where(ratio > 1.5, -0.6, 0.15 * (1.15 - ratio.fillna(1.0))),
    )
    s = pd.Series(score, index=df.index, dtype=float)
    s.iloc[:80] = 0.0  # 波动率基线预热
    return s
