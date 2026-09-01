"""事件驱动回测引擎：t 收盘信号 -> t+1 开盘撮合；逐日预测日志（宪法 I/II）。

已知简化（v1 文档化局限）：
- 历史个股 ST 状态不可得，回测默认按非 ST 处理（可经 st_symbols 参数指定）；
- 已持仓且仍在目标中的标的不再加仓；
- 开盘涨停买单当日放弃（不追价），跌停卖单顺延至可卖日。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from ashquant import config as cfg_mod
from ashquant.backtest.metrics import performance, prediction_stats, win_rate
from ashquant.backtest.rules import DEFERRED, FILLED, MarketRules
from ashquant.indicators import add_indicators
from ashquant.masters import compute_master_series
from ashquant.strategy import (
    build_target_portfolio,
    calibrate_series,
    direction_of,
    ensemble_series,
)


@dataclass(frozen=True)
class BacktestConfig:
    start: date | str | None = None
    end: date | str | None = None
    topk: int = 5
    rebalance_days: int = 5
    max_weight: float = 0.2
    neutral_band: float = 0.05
    min_history: int = 120
    calib_window: int = 250
    initial_cash: float = 1_000_000.0
    fee_enabled: bool = True
    master_weights: dict = field(default_factory=lambda: cfg_mod.StrategyConfig().master_weights)


@dataclass
class Position:
    shares: int = 0
    cost_total: float = 0.0  # 累计买入成本（含费用）
    bought_date: date | None = None


@dataclass
class BacktestReport:
    config: BacktestConfig
    equity_curve: pd.Series
    benchmark_curve: pd.Series | None
    trades: list[dict]
    prediction_log: pd.DataFrame
    metrics: dict
    symbols_used: list[str]
    st_limitation: str = (
        "回测未建模历史个股 ST 状态切换（默认按非 ST 的板块涨跌幅处理）；模拟盘/实盘按当前名称实时判定。"
    )


def run_backtest(
    symbols: list[str],
    loader,  # Callable[[str], DataFrame|None]（BarStore.load_bars 或测试替身）
    bcfg: BacktestConfig | None = None,
    benchmark_df: pd.DataFrame | None = None,
    st_symbols: set[str] | None = None,
    compute_cost_sensitivity: bool = True,
) -> BacktestReport:
    bcfg = bcfg or BacktestConfig()
    syms = sorted(set(symbols))
    st_symbols = st_symbols or set()
    rules = MarketRules(fee_enabled=bcfg.fee_enabled)
    strat_w = bcfg.master_weights

    # ---- 预计算：指标 / 大师序列 / 综合分 / 概率（全部因果） ----
    frames: dict[str, dict] = {}
    for s in syms:
        bars = loader(s)
        if bars is None or len(bars) < 30:
            continue
        ind = add_indicators(bars)
        mdf = compute_master_series(ind)
        score = ensemble_series(mdf, strat_w)
        next_up = (bars["close"].shift(-1) > bars["close"]).astype(float)
        next_up.iloc[-1] = np.nan
        prob, method = calibrate_series(
            score, next_up, window=bcfg.calib_window,
            min_samples=max(60, bcfg.min_history // 2), refit_every=bcfg.rebalance_days,
        )
        frames[s] = {"ind": ind, "score": score, "prob": prob, "close": bars["close"],
                     "open": bars["open"], "prev_close": bars["close"].shift(1)}

    if not frames:
        raise ValueError("没有任何标的有足够数据（≥30 根日线）可回测")

    # ---- 日历 ----
    if benchmark_df is not None and len(benchmark_df):
        cal = benchmark_df.index
    else:
        cal = sorted(set().union(*[set(f["close"].index) for f in frames.values()]))
        cal = pd.DatetimeIndex(cal)
    start = pd.Timestamp(bcfg.start) if bcfg.start else cal[0]
    end = pd.Timestamp(bcfg.end) if bcfg.end else cal[-1]
    cal = cal[(cal >= start) & (cal <= end)]
    if len(cal) < 10:
        raise ValueError(f"回测区间过短（{len(cal)} 个交易日）")

    closes = {s: f["close"].reindex(cal).ffill() for s, f in frames.items()}

    # ---- 状态 ----
    cash = bcfg.initial_cash
    positions: dict[str, Position] = {}
    trades: list[dict] = []
    equity_pts: list[float] = []
    pred_rows: list[dict] = []
    pending_sells: dict[str, int] = {}
    pending_target: dict[str, float] | None = None
    pending_target_day: pd.Timestamp | None = None
    last_rebalance = -10**9

    def market_value(d) -> float:
        v = 0.0
        for s, p in positions.items():
            px = closes[s].loc[d]
            if pd.notna(px):
                v += p.shares * float(px)
        return v

    def do_sell(s: str, d: pd.Timestamp, qty: int) -> None:
        nonlocal cash
        fr = frames[s]
        if d not in fr["open"].index:
            return  # 停牌：顺延
        op, pc = float(fr["open"].loc[d]), fr["prev_close"].loc[d]
        pos = positions.get(s)
        if pos is None or pos.shares <= 0:
            pending_sells.pop(s, None)
            return
        sellable = pos.shares if (pos.bought_date is None or pos.bought_date < d.date()) else 0
        res = rules.sell(s, s in st_symbols, d.date(), op,
                         float(pc) if pd.notna(pc) else op, qty, pos.shares, sellable)
        if res.status == FILLED:
            amount = round(res.price * res.qty, 2)
            fee = sum(res.fees.values())
            cash_local_delta = round(amount - fee, 2)
            pnl = cash_local_delta - pos.cost_total
            cash += cash_local_delta
            trades.append({"date": str(d.date()), "symbol": s, "side": "SELL",
                           "qty": res.qty, "price": res.price, "fees": res.fees,
                           "note": "ok", "pnl": round(pnl, 2)})
            positions.pop(s, None)
            pending_sells.pop(s, None)
        elif res.status == DEFERRED:
            pending_sells[s] = qty  # 跌停，次日再试
            trades.append({"date": str(d.date()), "symbol": s, "side": "SELL",
                           "qty": qty, "price": None, "fees": {}, "note": "DEFERRED:" + res.note,
                           "pnl": None})

    # ---- 主循环 ----
    for j, d in enumerate(cal):
        # 1) 执行前一日信号产生的调仓（先卖后买，T+1 天然满足）
        if pending_target is not None and pending_target_day is not None and d > pending_target_day:
            targets = pending_target
            for s in [x for x in list(positions) if x not in targets]:
                do_sell(s, d, positions[s].shares)
            for s, w in sorted(targets.items(), key=lambda kv: -kv[1]):
                if s in positions or s not in frames:
                    continue
                fr = frames[s]
                if d not in fr["open"].index:
                    continue
                op, pc = float(fr["open"].loc[d]), fr["prev_close"].loc[d]
                equity_est = cash + market_value(d)
                qty = int((equity_est * w) / op / 100) * 100
                if qty <= 0:
                    continue
                res = rules.buy(s, s in st_symbols, d.date(), op,
                                float(pc) if pd.notna(pc) else op, qty, cash)
                if res.status == FILLED:
                    amount = round(res.price * res.qty, 2)
                    fee = sum(res.fees.values())
                    cash -= round(amount + fee, 2)
                    positions[s] = Position(shares=res.qty, cost_total=round(amount + fee, 2),
                                            bought_date=d.date())
                    trades.append({"date": str(d.date()), "symbol": s, "side": "BUY",
                                   "qty": res.qty, "price": res.price, "fees": res.fees,
                                   "note": "ok", "pnl": None})
            pending_target = None
            pending_target_day = None

        # 2) 补执行此前被跌停/停牌顺延的卖单
        for s in list(pending_sells):
            if s in positions:
                do_sell(s, d, pending_sells[s])

        # 3) 调仓信号日（收盘后）：打分 + 记录预测日志 + 生成次日目标
        if j - last_rebalance >= bcfg.rebalance_days:
            probs: dict[str, float] = {}
            for s, fr in frames.items():
                hist = int((fr["close"].index <= d).sum())
                if hist < bcfg.min_history or d not in fr["prob"].index:
                    continue
                p = float(fr["prob"].loc[d])
                if np.isnan(p):
                    continue
                probs[s] = p
                pred_rows.append({"as_of": str(d.date()), "symbol": s,
                                  "direction": direction_of(p, bcfg.neutral_band),
                                  "prob_up": round(p, 4)})
            if probs:
                last_rebalance = j
                pending_target = build_target_portfolio(
                    probs, bcfg.topk, bcfg.max_weight, bcfg.neutral_band
                )
                pending_target_day = d
                for s in list(pending_sells):
                    if s in pending_target:
                        pending_sells.pop(s)  # 新目标重新纳入，撤销旧卖单

        # 4) 收盘估值
        equity_pts.append(round(cash + market_value(d), 4))

    # ---- 预测日志对账（close-to-close，FR-012 口径） ----
    for row in pred_rows:
        s, as_of = row["symbol"], pd.Timestamp(row["as_of"])
        c = frames[s]["close"]
        pos = c.index.searchsorted(as_of, side="right")
        if pos < len(c.index) and as_of in c.index:
            ret = float(c.iloc[pos]) / float(c.loc[as_of]) - 1.0
            row["actual_ret"] = round(ret, 6)
            if row["direction"] == "UP":
                row["hit"] = bool(ret > 0)
            elif row["direction"] == "DOWN":
                row["hit"] = bool(ret < 0)
            else:
                row["hit"] = None
        else:
            row["actual_ret"], row["hit"] = None, None

    equity = pd.Series(equity_pts, index=cal, name="equity")
    bench = None
    if benchmark_df is not None and len(benchmark_df):
        bclose = benchmark_df["close"].reindex(cal).ffill().dropna()
        if len(bclose):
            bench = bclose / float(bclose.iloc[0]) * bcfg.initial_cash

    pred_df = pd.DataFrame(pred_rows)
    m = performance(equity, bcfg.initial_cash)
    m.update(prediction_stats(pred_df))
    m["win_rate"] = win_rate(trades)

    if compute_cost_sensitivity and bcfg.fee_enabled:
        bcfg_nofee = dataclasses.replace(bcfg, fee_enabled=False)
        rpt_nofee = run_backtest(
            symbols=symbols, loader=loader, bcfg=bcfg_nofee,
            benchmark_df=benchmark_df, st_symbols=st_symbols,
            compute_cost_sensitivity=False,
        )
        zero_fee_ret = rpt_nofee.metrics["total_return"]
        with_fee_ret = m["total_return"]
        m["cost_sensitivity"] = {
            "with_fee_total_ret": with_fee_ret,
            "zero_fee_total_ret": zero_fee_ret,
            "fee_drag": round(zero_fee_ret - with_fee_ret, 6),
        }
    else:
        m["cost_sensitivity"] = {"fee_enabled": bcfg.fee_enabled}

    return BacktestReport(
        config=bcfg, equity_curve=equity, benchmark_curve=bench, trades=trades,
        prediction_log=pred_df, metrics=m, symbols_used=list(frames.keys()),
    )
