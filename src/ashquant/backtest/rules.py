"""A股微观规则引擎：费用 / 涨跌停 / 整手 / T+1（回测与模拟盘共用，宪法 II）。

遵循 codebase-design 原则：
- 核心规则统一在 MarketRules 内部内聚
- 支持传 MarketContext 对象（消除参数团）或位置参数（向前兼容）
- 支持使用 domain.py 领域枚举（消除 Primitive Obsession）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ashquant import codes
from ashquant.config import FeesConfig
from ashquant.domain import FillStatus, MarketContext, OrderSide, RejectReason

# 向上暴露领域状态常量（保持 100% 向前兼容）
FILLED = FillStatus.FILLED
REJECTED = FillStatus.REJECTED
DEFERRED = FillStatus.DEFERRED

LIMIT_UP = RejectReason.LIMIT_UP
LIMIT_DOWN = RejectReason.LIMIT_DOWN
T1_LOCK = RejectReason.T1_LOCK
ODD_LOT = RejectReason.ODD_LOT
INSUFFICIENT_CASH = RejectReason.INSUFFICIENT_CASH
NO_POSITION = RejectReason.NO_POSITION


@dataclass(frozen=True)
class FillResult:
    status: FillStatus | str
    price: float | None = None
    qty: int = 0
    fees: dict = field(default_factory=dict)
    note: str = ""


class MarketRules:
    def __init__(self, fees: FeesConfig | None = None, fee_enabled: bool = True):
        self.fees_cfg = fees or FeesConfig()
        self.fee_enabled = fee_enabled

    # ---------- 费用 ----------

    def fees(self, side: OrderSide | str, amount: float) -> dict:
        if not self.fee_enabled:
            return {"commission": 0.0, "stamp": 0.0, "transfer": 0.0}
        f = self.fees_cfg
        commission = round(max(amount * f.commission_ratio, f.min_commission), 2)
        stamp = round(amount * f.stamp_tax, 2) if str(side).upper() == "SELL" else 0.0
        transfer = round(amount * f.transfer_fee, 2)
        return {"commission": commission, "stamp": stamp, "transfer": transfer}

    def total_fees(self, side: OrderSide | str, amount: float) -> float:
        f = self.fees(side, amount)
        return round(f["commission"] + f["stamp"] + f["transfer"], 2)

    # ---------- 涨跌停 ----------

    def price_side(self, symbol: str, is_st: bool, on: date | str,
                   prev_close: float, price: float) -> str | None:
        """返回 "UP"/"DOWN"/None：该价格是否触及涨/跌停价。"""
        pct = codes.limit_pct(symbol, is_st, on)
        up, down = codes.limit_prices(prev_close, pct)
        if price >= up - 1e-9:
            return "UP"
        if price <= down + 1e-9:
            return "DOWN"
        return None

    # ---------- 撮合 ----------

    def buy_context(self, ctx: MarketContext, qty: int, cash: float) -> FillResult:
        """基于 MarketContext 值对象的标准下单接口（推荐深度用法）。"""
        return self.buy(
            symbol=ctx.symbol,
            is_st=ctx.is_st,
            trade_date=ctx.trade_date,
            open_price=ctx.price,
            prev_close=ctx.prev_close,
            qty=qty,
            cash=cash,
        )

    def buy(self, symbol: str, is_st: bool, trade_date: date | str,
            open_price: float, prev_close: float, qty: int, cash: float) -> FillResult:
        """经典位置参数下单接口（兼容现有回测/测试代码）。"""
        if qty is None or qty <= 0:
            return FillResult(REJECTED, note="数量非法")
        if qty % 100 != 0:
            return FillResult(REJECTED, note=ODD_LOT)
        side = self.price_side(symbol, is_st, trade_date, prev_close, open_price)
        if side == "UP":
            return FillResult(REJECTED, note=LIMIT_UP)
        amount = round(open_price * qty, 2)
        fee = self.total_fees(OrderSide.BUY, amount)
        if cash < amount + fee + 1e-9:
            return FillResult(REJECTED, note=INSUFFICIENT_CASH)
        return FillResult(FILLED, price=open_price, qty=qty,
                          fees=self.fees(OrderSide.BUY, amount), note="ok")

    def sell_context(self, ctx: MarketContext, qty: int,
                     held_shares: int, sellable_shares: int) -> FillResult:
        """基于 MarketContext 值对象的标准卖出接口（推荐深度用法）。"""
        return self.sell(
            symbol=ctx.symbol,
            is_st=ctx.is_st,
            trade_date=ctx.trade_date,
            open_price=ctx.price,
            prev_close=ctx.prev_close,
            qty=qty,
            held_shares=held_shares,
            sellable_shares=sellable_shares,
        )

    def sell(self, symbol: str, is_st: bool, trade_date: date | str,
             open_price: float, prev_close: float, qty: int,
             held_shares: int, sellable_shares: int) -> FillResult:
        """经典位置参数卖出接口（兼容现有回测/测试代码）。"""
        if qty is None or qty <= 0 or held_shares <= 0:
            return FillResult(REJECTED, note=NO_POSITION)
        if qty > sellable_shares:
            return FillResult(REJECTED, note=T1_LOCK)
        # 零股：仅允许一次性清仓卖出（A股规则）
        if qty % 100 != 0 and qty != held_shares:
            return FillResult(REJECTED, note=ODD_LOT)
        side = self.price_side(symbol, is_st, trade_date, prev_close, open_price)
        if side == "DOWN":
            return FillResult(DEFERRED, note=LIMIT_DOWN)
        amount = round(open_price * qty, 2)
        return FillResult(FILLED, price=open_price, qty=qty,
                          fees=self.fees(OrderSide.SELL, amount), note="ok")
