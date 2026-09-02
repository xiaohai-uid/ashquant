"""ashquant 核心领域模型（Domain Models & Enums）。

遵循 codebase-design 深度模块设计：
- 消除 Primitive Obsession：用强类型枚举替代裸字符串（兼容 str）
- 消除 Data Clumps：将反复同行的市场上下文封装为 MarketContext 值对象
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class OrderSide(StrEnum):
    """订单买卖方向。"""
    BUY = "BUY"
    SELL = "SELL"


class FillStatus(StrEnum):
    """撮合结果状态。"""
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class SignalDirection(StrEnum):
    """预测与信号方向。"""
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class RejectReason(StrEnum):
    """拒单原因码。"""
    LIMIT_UP = "LIMIT_UP"            # 涨停买不进
    LIMIT_DOWN = "LIMIT_DOWN"        # 跌停卖不出
    T1_LOCK = "T1_LOCK"              # 当日买入 T+1 锁定
    ODD_LOT = "ODD_LOT"              # 零股/非整手限制
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    NO_POSITION = "NO_POSITION"


@dataclass(frozen=True)
class MarketContext:
    """市场环境值对象：封装标的、日期、现价、昨收价与 ST 状态，消除方法参数团。"""
    symbol: str
    trade_date: date | str
    price: float
    prev_close: float
    is_st: bool = False

    @property
    def trade_date_obj(self) -> date:
        if isinstance(self.trade_date, str):
            return date.fromisoformat(self.trade_date)
        return self.trade_date
