"""实时预测：明日方向/概率/置信度/大师观点 + 可审计预测日志（close-to-close 口径）。

基于 strategy.StockAnalysis 深层模块，预测与快照生成完全由实体自身契约负责。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ashquant import config as cfg_mod
from ashquant.debate.memory import ReflectionMemory
from ashquant.domain import SignalDirection
from ashquant.strategy import (
    StockAnalysis,
    analyze_stock,
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
    analysis: StockAnalysis = analyze_stock(
        symbol=symbol,
        bars=bars,
        master_weights=sc.master_weights,
        calib_window=sc.calib_window,
        min_samples=max(60, sc.min_history // 2),
        refit_every=5,
    )

    # 【深度调用】：由实体直接生成预测记录
    result = analysis.to_prediction_record(neutral_band=sc.neutral_band)

    if log:
        path = Path(cfg.data_dir) / "predictions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    return result


def settle_expired(store, cfg: cfg_mod.Config | None = None) -> int:
    """对账：为已到期的预测回写 actual_ret/hit，若失误自动触发 ReflectionMemory 沉淀反思规则。"""
    cfg = cfg or cfg_mod.get_config()
    path = Path(cfg.data_dir) / "predictions.jsonl"
    if not path.exists():
        return 0
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n = 0
    memory = ReflectionMemory(Path(cfg.data_dir) / "reflection_memory.jsonl")

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

        # 复用 StockAnalysis.evaluate_hit
        analysis = analyze_stock(sym, bars)
        ret, hit = analysis.evaluate_hit(e["as_of"], e["direction"])
        if ret is not None:
            e["actual_ret"] = ret
            e["hit"] = hit
            n += 1

            # 闭环学习飞轮：若看涨但下跌超 2% (或未命中且跌幅较大)，自动提炼经验规则
            if e["direction"] == SignalDirection.UP and ret <= -0.02:
                feat = e.get("features_snapshot", {})
                tags = []
                if (feat.get("vol_ratio") or 1.0) > 1.5:
                    tags.append("high_volume_breakout")
                if (feat.get("rsi14") or 50.0) > 70:
                    tags.append("rsi_overbought")

                blindspot = f"预测看多但在次日遭受 {ret:+.2%} 回撤，或遭主力盘中诱多派发"
                rule = f"严禁在无强资金支撑下盲目追涨 {sym}，防范假突破陷阱"

                try:
                    memory.record_post_mortem(
                        symbol=sym,
                        timestamp=str(pd.Timestamp.now()),
                        forecast_direction=SignalDirection.UP,
                        actual_return=ret,
                        pattern_tags=tags,
                        fatal_blindspot=blindspot,
                        rule_learned=rule,
                    )
                except Exception:
                    pass

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
