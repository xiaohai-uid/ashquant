"""实时预测：明日方向/概率/置信度/大师观点 + 可审计预测日志（close-to-close 口径）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ashquant import config as cfg_mod
from ashquant.indicators import add_indicators
from ashquant.masters import compute_master_series, signal_at
from ashquant.strategy import (
    GOVERNANCE_NOTE,
    calibrate_series,
    confidence_tier,
    direction_of,
    ensemble_series,
)


class InsufficientDataError(ValueError):
    pass


def predict_next_day(store, symbol: str, cfg: cfg_mod.Config | None = None,
                     log: bool = True) -> dict:
    """对单一标的输出明日预测；数据 < min_history 拒绝（FR-011）。"""
    cfg = cfg or cfg_mod.get_config()
    sc = cfg.strategy
    bars = store.load_bars(symbol)
    if bars is None or len(bars) < sc.min_history:
        raise InsufficientDataError(
            f"{symbol} 数据不足（需 ≥{sc.min_history} 个交易日，"
            f"现有 {0 if bars is None else len(bars)}）；请先 ashquant fetch"
        )
    ind = add_indicators(bars)
    mdf = compute_master_series(ind)
    score = ensemble_series(mdf, sc.master_weights)
    next_up = (bars["close"].shift(-1) > bars["close"]).astype(float)
    next_up.iloc[-1] = np.nan
    prob, method = calibrate_series(
        score, next_up, window=sc.calib_window,
        min_samples=max(60, sc.min_history // 2), refit_every=5,
    )
    as_of = ind.index[-1]
    p = float(prob.iloc[-1])
    direction = direction_of(p, sc.neutral_band)
    result = {
        "symbol": symbol,
        "as_of": str(as_of.date()),
        "direction": direction,
        "prob_up": round(p, 4),
        "confidence": confidence_tier(p, sc.neutral_band),
        "method": str(method.iloc[-1]),
        "score": round(float(score.iloc[-1]), 4),
        "signals": [
            {"master": s.master, "category": s.category, "score": s.score,
             "reason": s.reason, "quote": s.quote, "source": s.source}
            for s in signal_at(ind, mdf, as_of)
        ],
        "note": GOVERNANCE_NOTE,
    }
    if direction == "NEUTRAL":
        result["abstain_reason"] = (
            f"|P(涨)-0.5| = {abs(p - 0.5):.3f} < 弃权阈值 {sc.neutral_band}，无把握，不给出方向"
        )
    if log:
        entry = {
            "id": uuid.uuid4().hex[:12],
            "symbol": symbol,
            "as_of": result["as_of"],
            "direction": direction,
            "prob_up": result["prob_up"],
            "confidence": result["confidence"],
            "method": result["method"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "actual_ret": None,
            "hit": None,
        }
        path = Path(cfg.data_dir) / "predictions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return result


def settle_expired(store, cfg: cfg_mod.Config | None = None) -> int:
    """对账：为已到期的预测回写 actual_ret/hit（close-to-close）。返回结算条数。"""
    cfg = cfg or cfg_mod.get_config()
    path = Path(cfg.data_dir) / "predictions.jsonl"
    if not path.exists():
        return 0
    entries = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for e in entries:
        if e.get("hit") is not None or e.get("direction") == "NEUTRAL":
            continue
        bars = store.load_bars(e["symbol"])
        if bars is None:
            continue
        c = bars["close"]
        as_of = pd.Timestamp(e["as_of"])
        if as_of not in c.index:
            continue
        pos = c.index.searchsorted(as_of, side="right")
        if pos >= len(c.index):
            continue
        ret = float(c.iloc[pos]) / float(c.loc[as_of]) - 1.0
        e["actual_ret"] = round(ret, 6)
        e["hit"] = bool(ret > 0) if e["direction"] == "UP" else bool(ret < 0)
        n += 1
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return n


def prediction_stats(min_count: int = 20, cfg: cfg_mod.Config | None = None) -> dict:
    """预测日志统计：命中率/覆盖率/按置信度分层（FR-012）。"""
    cfg = cfg or cfg_mod.get_config()
    path = Path(cfg.data_dir) / "predictions.jsonl"
    if not path.exists():
        raise FileNotFoundError("尚无预测日志；先运行 ashquant predict / backtest")
    entries = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(entries)
    settled = df[df["hit"].notna()] if "hit" in df else df.iloc[0:0]
    if len(settled) < min_count:
        raise InsufficientDataError(
            f"已到期预测仅 {len(settled)} 条（建议 ≥{min_count}），样本过少不足以计算可信命中率"
        )
    directional = settled[settled["direction"].isin(["UP", "DOWN"])]
    out = {
        "total": len(df), "settled": len(settled), "directional": len(directional),
        "hit_rate": round(float(directional["hit"].mean()), 4) if len(directional) else None,
        "coverage": round(len(directional) / max(len(settled), 1), 4),
        "by_confidence": [],
    }
    for tier in ("LOW", "MEDIUM", "HIGH"):
        sub = directional[directional["confidence"] == tier]
        if len(sub):
            out["by_confidence"].append({
                "tier": tier, "n": len(sub),
                "hit_rate": round(float(sub["hit"].mean()), 4),
            })
    return out
