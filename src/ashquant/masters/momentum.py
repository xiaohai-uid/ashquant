"""德鲁肯米勒（谈索罗斯）：动量/反身性 —— 强动量 + 量能确认则顺势。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def druckenmiller(df: pd.DataFrame) -> pd.Series:
    roc = df["roc10"]
    vr = df["vol_ratio"]
    mom = 0.7 * np.tanh(roc.fillna(0.0) * 8)
    confirm = np.where(vr > 1.2, 1.15, np.where(vr < 0.8, 0.7, 1.0))
    score = np.clip(mom * confirm, -1.0, 1.0)
    s = pd.Series(score, index=df.index, dtype=float)
    s.iloc[:15] = 0.0
    return s
