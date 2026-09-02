"""异常行情与宏观环境漂移熔断电路（RegimeBreaker）。

借鉴 FreqAI 的数据分布漂移检测与顶级量化风控：
1. 市场级熔断：
   - 当基准指数（沪深300/上证指数）当日暴跌超过阈值（如 -2.5%），或全市场下跌家数占比超过 80%（千股跌停），直接判定为 PANIC_CIRCUIT_BROKEN。
   - 在熔断状态下，系统强制拒止一切新的买入预测与模拟盘/实盘开仓挂单。
2. 账户级熔断：
   - 连续 3 笔交易触发止损后，进入 24 小时交易冷静期。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from ashquant.domain import MarketRegime

logger = logging.getLogger(__name__)


@dataclass
class MarketStats:
    """全市场截面统计数据。"""
    up_count: int = 2500
    down_count: int = 2500
    limit_up_count: int = 50
    limit_down_count: int = 10
    index_return: float = 0.002  # 基准指数当日涨跌幅


class RegimeBreaker:
    """市场与账户环境熔断器。"""

    def __init__(
        self,
        index_drop_limit: float = -0.025,       # 指数暴跌 -2.5% 触发熔断
        down_ratio_limit: float = 0.80,         # 全市场 80% 个股下跌触发熔断
        consecutive_loss_limit: int = 3,        # 连续亏损熔断笔数
        cooldown_hours: int = 24,               # 账户冷静期时长 (小时)
    ):
        self.index_drop_limit = index_drop_limit
        self.down_ratio_limit = down_ratio_limit
        self.consecutive_loss_limit = consecutive_loss_limit
        self.cooldown_hours = cooldown_hours

        self.consecutive_losses: int = 0
        self.cooldown_until: datetime | None = None

    def evaluate_market(self, stats: MarketStats) -> MarketRegime:
        """评估当前市场环境是否触发熔断。"""
        total = stats.up_count + stats.down_count
        down_ratio = (stats.down_count / total) if total > 0 else 0.5

        if stats.index_return <= self.index_drop_limit or down_ratio >= self.down_ratio_limit:
            logger.warning(
                "🚨 触发市场级异常行情熔断！指数涨跌: %.2f%%, 下跌占比: %.2f%%",
                stats.index_return * 100,
                down_ratio * 100,
            )
            return MarketRegime.PANIC_CIRCUIT_BROKEN

        if stats.index_return <= -0.015 or down_ratio >= 0.65:
            return MarketRegime.TURBULENT

        return MarketRegime.NORMAL

    def is_account_in_cooldown(self, current_time: datetime | None = None) -> bool:
        """检查账户是否处于连续亏损冷静期。"""
        now = current_time or datetime.now()
        if self.cooldown_until and now < self.cooldown_until:
            return True
        return False

    def record_trade_result(self, is_win: bool, current_time: datetime | None = None) -> None:
        """记录交易胜负，更新账户熔断状态。"""
        now = current_time or datetime.now()
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.consecutive_loss_limit:
                self.cooldown_until = now + timedelta(hours=self.cooldown_hours)
                logger.warning(
                    "🚨 账户已连续亏损 %d 笔，触发 %d 小时冷静期熔断（直至 %s）",
                    self.consecutive_losses,
                    self.cooldown_hours,
                    self.cooldown_until.isoformat(),
                )
