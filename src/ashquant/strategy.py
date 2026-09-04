"""策略层：大师信号 + Alpha 因子 + 多空对抗辩论 -> 概率校准 -> 目标组合。

遵循 codebase-design 深度模块设计：
- 导出深层分析实体 StockAnalysis 与流水线函数 analyze_stock()
- v0.2.0 Deepening: StockAnalysis 直接封装预测快照生成 (to_prediction_record) 与命中结算 (evaluate_hit)
- 真正隐藏特征对齐、逻辑回归校准与对抗辩论状态机细节，对调用方提供极简高杠杆接口。
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from ashquant.alpha import add_alpha_factors, extract_alpha_factors_at
from ashquant.data.alternative import fetch_capital_flow
from ashquant.debate import MasterDebateArena
from ashquant.domain import (
    AlphaFactors,
    DebateVerdict,
    SignalDirection,
    VerdictDecision,
)
from ashquant.indicators import add_indicators
from ashquant.masters import compute_master_series, signal_at

UP = SignalDirection.UP
DOWN = SignalDirection.DOWN
NEUTRAL = SignalDirection.NEUTRAL

# 治理锚点（specs/research/04-master-quotes.md）：输出界面固定附注
GOVERNANCE_NOTE = (
    "「我无法预测股市短期走势。一个月或一年后股票是高是低，我毫无头绪。」——巴菲特，"
    "《纽约时报》2008-10-16；「在这个行当里，如果你优秀，你十次能对六次。你永远不可能"
    "十次对九次。」——彼得·林奇，PBS《Betting on the Market》(1997)。本系统输出的是"
    "多维度正交共振概率与对抗辩论审计报告，不是确定性预言。"
)


@dataclass(frozen=True)
class StockAnalysis:
    """个股全量时序分析结果（Deep Value Object）。"""
    symbol: str
    bars: pd.DataFrame
    indicators: pd.DataFrame
    master_scores: pd.DataFrame
    ensemble_score: pd.Series
    prob_up: pd.Series
    calib_method: pd.Series
    close: pd.Series
    open: pd.Series
    prev_close: pd.Series
    latest_alpha: AlphaFactors | None = None
    latest_verdict: DebateVerdict | None = None

    def evaluate_hit(self, as_of: str | pd.Timestamp, direction: SignalDirection | str) -> tuple[float | None, bool | None]:
        """计算指定预测日在次日（close-to-close）的实际涨跌与命中结果。

        口径：FR-012 close-to-close 涨跌。
        """
        as_of_ts = pd.Timestamp(as_of)
        c = self.close
        if as_of_ts not in c.index:
            return None, None
        pos = c.index.searchsorted(as_of_ts, side="right")
        if pos >= len(c.index):
            return None, None  # 尚未到期
        ret = float(c.iloc[pos]) / float(c.loc[as_of_ts]) - 1.0
        ret_round = round(ret, 6)

        if str(direction).upper() == SignalDirection.UP:
            hit = bool(ret > 0)
        elif str(direction).upper() == SignalDirection.DOWN:
            hit = bool(ret < 0)
        else:
            hit = None  # 观望不计命中
        return ret_round, hit

    def to_prediction_record(self, neutral_band: float = 0.05) -> dict:
        """【深度门面】一键将最新分析结果转换为可审计的预测日志记录与展示模型。"""
        as_of = self.indicators.index[-1]
        as_of_str = str(pd.Timestamp(as_of).date())
        p = float(self.prob_up.iloc[-1])
        direction = direction_of(p, neutral_band)
        score_val = float(self.ensemble_score.iloc[-1])
        conf = confidence_tier(p, neutral_band)

        signals_list = [
            {
                "master": s.master,
                "category": s.category,
                "score": s.score,
                "reason": s.reason,
                "quote": s.quote,
                "source": s.source,
            }
            for s in signal_at(self.indicators, self.master_scores, as_of)
        ]

        ind = self.indicators
        features_snapshot = {
            "close": round(float(self.bars["close"].iloc[-1]), 2),
            "rsi14": round(float(ind["rsi14"].iloc[-1]), 2) if "rsi14" in ind and pd.notna(ind["rsi14"].iloc[-1]) else None,
            "roc10": round(float(ind["roc10"].iloc[-1]), 4) if "roc10" in ind and pd.notna(ind["roc10"].iloc[-1]) else None,
            "vol_ratio": round(float(ind["vol_ratio"].iloc[-1]), 2) if "vol_ratio" in ind and pd.notna(ind["vol_ratio"].iloc[-1]) else None,
            "score": round(score_val, 4),
        }

        entry = {
            "id": uuid.uuid4().hex[:12],
            "symbol": self.symbol,
            "as_of": as_of_str,
            "direction": direction,
            "prob_up": round(p, 4),
            "confidence": conf,
            "method": str(self.calib_method.iloc[-1]),
            "score": round(score_val, 4),
            "signals": signals_list,
            "features_snapshot": features_snapshot,
            "signals_summary": {s["master"]: s["score"] for s in signals_list},
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "actual_ret": None,
            "hit": None,
            "note": GOVERNANCE_NOTE,
        }

        if direction == SignalDirection.NEUTRAL:
            entry["abstain_reason"] = f"|P(涨)-0.5| = {abs(p - 0.5):.3f} < 弃权阈值 {neutral_band}，无把握，不给出方向"

        return entry


def analyze_stock(
    symbol: str,
    bars: pd.DataFrame,
    master_weights: dict[str, float] | None = None,
    calib_window: int = 250,
    min_samples: int = 60,
    refit_every: int = 5,
    include_debate: bool = True,
    *,
    flow_loader: Callable[[str], pd.DataFrame | None] | None = None,
) -> StockAnalysis:
    """全量分析流水线（Deep Module 核心）。

    输入单张原始 OHLCV 日线表，封装指标计算、资金流对齐、Alpha 因子计算、大师打分、
    多空对抗辩论裁决与 Walk-forward 概率校准。
    """
    master_weights = master_weights or _default_weights()
    ind = add_indicators(bars)

    # 1. 对齐主力资金流并计算 Alpha 因子
    if flow_loader is not None:
        flow_df = flow_loader(symbol)
    else:
        flow_df = fetch_capital_flow(symbol)
    ind = add_alpha_factors(ind, flow_df)

    # 2. 计算 5 位大师打分
    mdf = compute_master_series(ind)

    # 3. 融合 Alpha 因子与大师综合分
    raw_ensemble = ensemble_series(mdf, master_weights)
    composite_alpha = ind["composite_alpha"] if "composite_alpha" in ind.columns else 0.0
    score = (0.7 * raw_ensemble + 0.3 * composite_alpha).clip(-1.0, 1.0)

    # 4. Walk-forward 概率校准
    next_up = (bars["close"].shift(-1) > bars["close"]).astype(float)
    next_up.iloc[-1] = np.nan

    prob, method = calibrate_series(
        score, next_up, window=calib_window,
        min_samples=min_samples, refit_every=refit_every,
    )

    # 5. 最新时点辩论裁决
    latest_alpha = extract_alpha_factors_at(ind, -1) if not ind.empty else None
    latest_verdict = None
    if include_debate and not ind.empty:
        last_row = ind.iloc[-1]
        as_of_str = str(ind.index[-1])[:10]
        arena = MasterDebateArena()
        latest_verdict = arena.run_debate(
            symbol=symbol,
            as_of=as_of_str,
            price=float(last_row["close"]),
            ma20=float(last_row.get("ma20", last_row["close"])),
            ma60=float(last_row.get("ma60", last_row["close"])),
            rsi=float(last_row.get("rsi", 50.0)),
            alpha=latest_alpha,
            ensemble_score=float(score.iloc[-1]),
        )

        # 若空头触发一票否决，直接将最新概率修正至中性保护
        if latest_verdict.decision == VerdictDecision.VETOED_ON_RISK:
            prob.iloc[-1] = 0.50

    return StockAnalysis(
        symbol=symbol,
        bars=bars,
        indicators=ind,
        master_scores=mdf,
        ensemble_score=score,
        prob_up=prob,
        calib_method=method,
        close=bars["close"],
        open=bars["open"],
        prev_close=bars["close"].shift(1),
        latest_alpha=latest_alpha,
        latest_verdict=latest_verdict,
    )


def ensemble_series(master_df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """按哲学类别加权合成大师打分 -> 综合分 s∈[-1,1]。"""
    w = pd.Series({m: weights.get(cat, 1.0) for m, cat in _name_category().items()})
    vals = master_df.fillna(0.0) * w
    return (vals.sum(axis=1) / w.sum()).clip(-1.0, 1.0)


def _name_category() -> dict[str, str]:
    from ashquant.masters import REGISTRY

    return {m.name: m.category for m in REGISTRY}


def _default_weights() -> dict[str, float]:
    return {"trend": 1.0, "momentum": 1.0, "reversion": 0.8, "risk": 0.6, "sentiment": 0.8}


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
