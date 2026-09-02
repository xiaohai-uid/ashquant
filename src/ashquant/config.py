"""全局配置：路径、费用、策略参数。全部可通过构造参数覆盖（宪法 II/IV）。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 主板 ST 涨跌幅 5% -> 10% 的切换日（上交所 2026 年修订交易规则，见
# specs/research/02-ashare-data-and-brokers.md）
ST_MAIN_SWITCH_DATE = "2026-07-06"

# 默认全局数据目录常量
DATA_DIR = Path(os.environ.get("ASHQUANT_DATA_DIR", "data"))


@dataclass(frozen=True)
class FeesConfig:
    commission_ratio: float = 0.00025  # 佣金 万 2.5
    min_commission: float = 5.0  # 最低 5 元
    stamp_tax: float = 0.0005  # 印花税：卖出单边 0.05%（2023-08-28 起）
    transfer_fee: float = 0.00001  # 过户费：双边 0.001%


@dataclass(frozen=True)
class StrategyConfig:
    topk: int = 5
    rebalance_days: int = 5
    max_weight: float = 0.2
    neutral_band: float = 0.05  # |p-0.5| < 该值 -> NEUTRAL（弃权）
    min_history: int = 120  # 预测/入选最少交易日数
    calib_window: int = 250  # 逻辑回归校准窗口
    master_weights: dict = field(
        default_factory=lambda: {
            "trend": 1.0,
            "momentum": 1.0,
            "reversion": 0.8,
            "risk": 0.6,
            "sentiment": 0.8,
        }
    )


@dataclass(frozen=True)
class Config:
    data_dir: Path
    fees: FeesConfig = field(default_factory=FeesConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    initial_cash: float = 1_000_000.0


def resolve_data_dir(explicit: str | os.PathLike | None = None) -> Path:
    """数据目录解析：显式参数 > 环境变量 ASHQUANT_DATA_DIR > ./data。"""
    if explicit is not None:
        p = Path(explicit)
    elif (env := os.environ.get("ASHQUANT_DATA_DIR")):
        p = Path(env)
    else:
        p = Path("data")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config(
    data_dir: str | os.PathLike | None = None,
    fees: FeesConfig | None = None,
    strategy: StrategyConfig | None = None,
    initial_cash: float | None = None,
) -> Config:
    return Config(
        data_dir=resolve_data_dir(data_dir),
        fees=fees or FeesConfig(),
        strategy=strategy or StrategyConfig(),
        initial_cash=1_000_000.0 if initial_cash is None else initial_cash,
    )
