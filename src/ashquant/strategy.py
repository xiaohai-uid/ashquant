"""策略层：大师信号合成分 -> 概率校准（walk-forward 逻辑回归）-> 目标组合。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashquant.domain import SignalDirection

UP = SignalDirection.UP
DOWN = SignalDirection.DOWN
NEUTRAL = SignalDirection.NEUTRAL

# 治理锚点（specs/research/04-master-quotes.md）：输出界面固定附注
GOVERNANCE_NOTE = (
    "「我无法预测股市短期走势。一个月或一年后股票是高是低，我毫无头绪。」——巴菲特，"
    "《纽约时报》2008-10-16；「在这个行当里，如果你优秀，你十次能对六次。你永远不可能"
    "十次对九次。」——彼得·林奇，PBS《Betting on the Market》(1997)。本系统输出的是"
    "概率与可审计的命中率，不是确定性预言。"
)


def ensemble_series(master_df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """按哲学类别加权合成大师打分 -> 综合分 s∈[-1,1]。"""
    w = pd.Series({m: weights.get(cat, 1.0) for m, cat in _name_category().items()})
    vals = master_df.fillna(0.0) * w
    return (vals.sum(axis=1) / w.sum()).clip(-1.0, 1.0)


def _name_category() -> dict[str, str]:
    from ashquant.masters import REGISTRY

    return {m.name: m.category for m in REGISTRY}


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def logistic_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """一维特征逻辑回归（Newton，确定性实现；无 sklearn 依赖）。"""
    X = np.column_stack([np.ones_like(x), x]).astype(float)
    beta = np.zeros(2)
    for _ in range(12):
        p = _sigmoid(X @ beta)
        W = np.clip(p * (1 - p), 1e-6, None)
        H = X.T @ (X * W[:, None])
        g = X.T @ (y - p)
        try:
            step = np.linalg.solve(H + 1e-8 * np.eye(2), g)
        except np.linalg.LinAlgError:
            break
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return float(beta[0]), float(beta[1])


def calibrate_series(
    score: pd.Series, next_up: pd.Series, window: int = 250,
    min_samples: int = 60, refit_every: int = 5,
) -> tuple[pd.Series, pd.Series]:
    """walk-forward 概率校准：t 日概率只用 ≤t-1 的样本拟合；每 refit_every 日重估参数。

    样本不足时退化为启发式映射 p=0.5+0.2*s（method 标记 heuristic）。
    返回 (prob 系列, method 系列)。
    """
    n = len(score)
    prob = pd.Series(np.nan, index=score.index)
    method = pd.Series("none", index=score.index, dtype=object)
    a = b = 0.0
    fitted = False
    last_fit = -(10**9)
    for i in range(n):
        if i < min_samples:
            prob.iloc[i] = float(np.clip(0.5 + 0.2 * score.iloc[i], 0.05, 0.95))
            method.iloc[i] = "heuristic"
            continue
        if not fitted or (i - last_fit) >= refit_every:
            lo = max(0, i - window)
            x = score.iloc[lo:i].to_numpy(dtype=float)
            y = next_up.iloc[lo:i].to_numpy(dtype=float)
            mask = ~np.isnan(x) & ~np.isnan(y)
            if mask.sum() >= min_samples:
                a, b = logistic_fit(x[mask], y[mask])
                fitted = True
                last_fit = i
        if fitted:
            prob.iloc[i] = float(_sigmoid(a + b * score.iloc[i]))
            method.iloc[i] = "logistic"
        else:
            prob.iloc[i] = float(np.clip(0.5 + 0.2 * score.iloc[i], 0.05, 0.95))
            method.iloc[i] = "heuristic"
    return prob, method


def direction_of(prob: float, band: float = 0.05) -> str:
    if prob >= 0.5 + band:
        return UP
    if prob <= 0.5 - band:
        return DOWN
    return NEUTRAL


def confidence_tier(prob: float, band: float = 0.05) -> str:
    d = abs(prob - 0.5)
    if d < band:
        return "LOW"
    return "MEDIUM" if d < 0.15 else "HIGH"


def build_target_portfolio(
    probs: dict[str, float], topk: int, max_weight: float, band: float = 0.05
) -> dict[str, float]:
    """等权 Top-K（FR-019）：按 p 降序取通过弃权带的候选，权重=min(1/K, 上限)。"""
    cands = sorted(
        ((s, p) for s, p in probs.items() if p >= 0.5 + band), key=lambda kv: -kv[1]
    )[:topk]
    if not cands:
        return {}
    k = len(cands)
    w = min(1.0 / k, max_weight)
    return {s: w for s, _ in cands}
