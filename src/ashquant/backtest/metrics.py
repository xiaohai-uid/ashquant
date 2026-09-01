"""回测绩效与预测诚实指标（命中率/覆盖率/校准度）。"""

from __future__ import annotations

import math

import pandas as pd

RF_ANNUAL = 0.015  # 无风险利率（年化），Sharpe 用


def performance(equity: pd.Series, initial_cash: float) -> dict:
    n = len(equity)
    total = float(equity.iloc[-1]) / initial_cash - 1.0
    annual = (1.0 + total) ** (252.0 / max(n, 1)) - 1.0 if n > 0 else 0.0
    rets = equity.pct_change().dropna()
    peak = equity.cummax()
    dd = (equity - peak) / peak
    mdd = float(dd.min()) if len(dd) else 0.0
    sharpe = 0.0
    if len(rets) > 20 and rets.std(ddof=0) > 0:
        rf_d = RF_ANNUAL / 252.0
        sharpe = float((rets.mean() - rf_d) / rets.std(ddof=0) * math.sqrt(252.0))
    return {
        "n_days": n,
        "total_return": round(total, 6),
        "annual_return": round(annual, 6),
        "max_drawdown": round(mdd, 6),
        "sharpe": round(sharpe, 4),
    }


def win_rate(trades: list[dict]) -> float | None:
    pnls = [t["pnl"] for t in trades if t.get("side") == "SELL" and t.get("pnl") is not None]
    if not pnls:
        return None
    return round(sum(1 for p in pnls if p > 0) / len(pnls), 4)


def prediction_stats(pred_df: pd.DataFrame) -> dict:
    """方向命中率 / 覆盖率 / 分置信度校准。NEUTRAL 不计命中率、计入覆盖率分母之外。"""
    if pred_df is None or pred_df.empty:
        return {"pred_total": 0, "directional": 0, "hit_rate": None,
                "up_hit": None, "down_hit": None, "coverage": None, "calibration": []}
    df = pred_df.dropna(subset=["hit"])
    directional = df[df["direction"].isin(["UP", "DOWN"])]
    all_rows = len(pred_df)
    out = {
        "pred_total": all_rows,
        "directional": len(directional),
        "hit_rate": None,
        "up_hit": None,
        "down_hit": None,
        "coverage": round(len(directional) / all_rows, 4) if all_rows else None,
        "calibration": [],
    }
    if len(directional):
        out["hit_rate"] = round(float(directional["hit"].mean()), 4)
        for d in ("UP", "DOWN"):
            sub = directional[directional["direction"] == d]
            if len(sub):
                out[f"{d.lower()}_hit"] = round(float(sub["hit"].mean()), 4)
        # 校准：把方向折算成“看涨概率” p_pos，与实际上涨频率比对
        p_pos = directional["prob_up"].where(directional["direction"] == "UP",
                                             1.0 - directional["prob_up"])
        actual_pos = (directional["actual_ret"] > 0).astype(float)
        edges = [0.5, 0.55, 0.65, 0.75, 1.01]
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (p_pos >= lo) & (p_pos < hi)
            if mask.sum() >= 10:
                out["calibration"].append({
                    "bucket": f"[{lo:.2f},{hi:.2f})", "n": int(mask.sum()),
                    "avg_prob": round(float(p_pos[mask].mean()), 4),
                    "actual_up_rate": round(float(actual_pos[mask].mean()), 4),
                })
    return out
