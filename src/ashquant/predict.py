"""实时预测：明日方向/概率/置信度/大师观点 + 可审计预测日志（close-to-close 口径）。

基于 strategy.analyze_stock 深层模块，消除与回测引擎的时序特征重复计算。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashquant import config as cfg_mod
from ashquant.domain import SignalDirection
from ashquant.masters import signal_at
from ashquant.strategy import (
    GOVERNANCE_NOTE,
    analyze_stock,
    confidence_tier,
    direction_of,
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

    # 接入 AnalysisPipeline 深层模块
    analysis = analyze_stock(
        symbol=symbol,
        bars=bars,
        master_weights=sc.master_weights,
        calib_window=sc.calib_window,
        min_samples=max(60, sc.min_history // 2),
        refit_every=5,
    )

    as_of = analysis.indicators.index[-1]
    p = float(analysis.prob_up.iloc[-1])
    direction = direction_of(p, sc.neutral_band)
    score_val = float(analysis.ensemble_score.iloc[-1])

    result = {
        "symbol": symbol,
        "as_of": str(as_of.date()),
        "direction": direction,
        "prob_up": round(p, 4),
        "confidence": confidence_tier(p, sc.neutral_band),
        "method": str(analysis.calib_method.iloc[-1]),
        "score": round(score_val, 4),
        "signals": [
            {"master": s.master, "category": s.category, "score": s.score,
             "reason": s.reason, "quote": s.quote, "source": s.source}
            for s in signal_at(analysis.indicators, analysis.master_scores, as_of)
        ],
        "note": GOVERNANCE_NOTE,
    }
    if direction == SignalDirection.NEUTRAL:
        result["abstain_reason"] = (
            f"|P(涨)-0.5| = {abs(p - 0.5):.3f} < 弃权阈值 {sc.neutral_band}，无把握，不给出方向"
        )
    if log:
        ind = analysis.indicators
        features_snapshot = {
            "close": round(float(bars["close"].iloc[-1]), 2),
            "rsi14": round(float(ind["rsi14"].iloc[-1]), 2) if pd.notna(ind["rsi14"].iloc[-1]) else None,
            "roc10": round(float(ind["roc10"].iloc[-1]), 4) if pd.notna(ind["roc10"].iloc[-1]) else None,
            "vol_ratio": round(float(ind["vol_ratio"].iloc[-1]), 2) if pd.notna(ind["vol_ratio"].iloc[-1]) else None,
            "score": result["score"],
        }
        signals_summary = {s["master"]: s["score"] for s in result["signals"]}

        entry = {
            "id": uuid.uuid4().hex[:12],
            "symbol": symbol,
            "as_of": result["as_of"],
            "direction": direction,
            "prob_up": result["prob_up"],
            "confidence": result["confidence"],
            "method": result["method"],
            "features_snapshot": features_snapshot,
            "signals_summary": signals_summary,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "actual_ret": None,
            "hit": None,
        }
        path = Path(cfg.data_dir) / "predictions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return result


def settle_expired(store, cfg: cfg_mod.Config | None = None) -> int:
    """对账：为已到期的预测回写 actual_ret/hit（统一使用 StockAnalysis.evaluate_hit）。"""
    cfg = cfg or cfg_mod.get_config()
    path = Path(cfg.data_dir) / "predictions.jsonl"
    if not path.exists():
        return 0
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n = 0
    # 缓存已加载的标的日线
    bars_cache = {}
    for e in entries:
        if e.get("hit") is not None or e.get("direction") == SignalDirection.NEUTRAL:
            continue
        sym = e["symbol"]
        if sym not in bars_cache:
            bars_cache[sym] = store.load_bars(sym)
        bars = bars_cache[sym]
        if bars is None:
            continue

        # 构造轻量 StockAnalysis 或复用其 evaluate_hit 逻辑
        analysis = analyze_stock(sym, bars)
        ret, hit = analysis.evaluate_hit(e["as_of"], e["direction"])
        if ret is not None:
            e["actual_ret"] = ret
            e["hit"] = hit
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
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
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
