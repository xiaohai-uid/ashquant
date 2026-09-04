"""Qlib 风格量化 Alpha 因子库（Alpha Factor Zoo）。

纯向量化数学变换，遵守 point-in-time 因果纪律（无未来函数）。
包含：
1. 动量与量能爆发因子 (Vol Surge)
2. 量价顶底背离因子 (PV Divergence)
3. 布林带通道压缩与突破因子 (Squeeze Breakout)
4. 聪明钱与主力资金累积因子 (Smart Money Acc - 自适应成交额归一化)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashquant.domain import AlphaFactors


def add_alpha_factors(df: pd.DataFrame, flow_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """计算完整的 Qlib 风格 Alpha 因子，并附加到指标 DataFrame 中。"""
    res = df.copy()
    close = res["close"]
    volume = res["volume"]

    # 1. 动量与量能爆发因子 (Vol Surge)
    vol_ma5 = volume.rolling(5, min_periods=3).mean()
    vol_ma20 = volume.rolling(20, min_periods=10).mean()
    vol_ratio = vol_ma5 / (vol_ma20 + 1e-6)
    res["alpha_vol_surge"] = np.clip((vol_ratio - 1.0) * np.where(close >= res["open"], 1.0, -0.8), -1.0, 1.0)

    # 2. 量价背离因子 (Price-Volume Divergence)
    price_pct = close.pct_change(5)
    vol_pct = volume.pct_change(5)
    pv_div = np.where((price_pct > 0.03) & (vol_pct < -0.2), -0.7, 0.0)
    pv_div = np.where((price_pct < -0.03) & (vol_pct < -0.3), 0.5, pv_div)
    res["alpha_pv_divergence"] = pv_div

    # 3. 布林带与波动率挤压突破 (Squeeze Breakout)
    if "boll_mid" in res.columns and ("atr14" in res.columns or "atr" in res.columns):
        boll_dn_col = "boll_low" if "boll_low" in res.columns else "boll_dn"
        bb_width = (res["boll_up"] - res[boll_dn_col]) / (res["boll_mid"] + 1e-6)
        is_breakout = (close > res["boll_up"]).astype(float)
        res["alpha_squeeze_breakout"] = np.clip(is_breakout * 0.8 - (bb_width > 0.15).astype(float) * 0.2, -1.0, 1.0)
    else:
        res["alpha_squeeze_breakout"] = 0.0

    # 4. 聪明钱与主力资金流因子 (Smart Money Acc)
    # 自适应归一化：使用滚动日均成交金额作为分母基准，避免大盘股/小盘股失真
    rolling_turnover = (close * volume).rolling(20, min_periods=5).mean().fillna(1e7)
    if flow_df is not None and not flow_df.empty:
        joined = res.join(flow_df, how="left").fillna(0.0)
        net_inflow = joined["super_large_net_inflow"] + joined["large_net_inflow"]
        flow_acc = net_inflow.rolling(3, min_periods=1).sum()
        # 归一化为相对成交额比率
        res["alpha_smart_money_acc"] = np.tanh(flow_acc / (rolling_turnover + 1e-6))
    else:
        res["alpha_smart_money_acc"] = np.clip(close.pct_change(3) * 5.0, -1.0, 1.0)

    # 5. 综合 Alpha 因子分 (Composite Alpha Score)
    res["composite_alpha"] = (
        0.35 * res["alpha_vol_surge"]
        + 0.25 * res["alpha_pv_divergence"]
        + 0.20 * res["alpha_squeeze_breakout"]
        + 0.20 * res["alpha_smart_money_acc"]
    ).clip(-1.0, 1.0)

    return res


def extract_alpha_factors_at(df: pd.DataFrame, idx: int = -1) -> AlphaFactors:
    """提取特定时点的 Alpha 因子对象。"""
    row = df.iloc[idx]
    return AlphaFactors(
        vol_surge=float(row.get("alpha_vol_surge", 0.0)),
        pv_divergence=float(row.get("alpha_pv_divergence", 0.0)),
        squeeze_breakout=float(row.get("alpha_squeeze_breakout", 0.0)),
        smart_money_acc=float(row.get("alpha_smart_money_acc", 0.0)),
        composite_alpha=float(row.get("composite_alpha", 0.0)),
    )
