"""A股微观规则引擎：费用 / 涨跌停 / 整手 / T+1（回测与模拟盘共用，宪法 II）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ashquant import codes
from ashquant.config import FeesConfig

FILLED = "FILLED"
REJECTED = "REJECTED"
DEFERRED = "DEFERRED"

# 拒单原因码
LIMIT_UP = "LIMIT_UP"            # 开盘/现价涨停 -> 买不进
LIMIT_DOWN = "LIMIT_DOWN"        # 跌停 -> 卖不出（DEFERRED 顺延）
T1_LOCK = "T1_LOCK"              # 当日买入不可卖
ODD_LOT = "ODD_LOT"              # 非整手买入 / 非法零股卖出
INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
NO_POSITION = "NO_POSITION"


@dataclass(frozen=True)
class FillResult:
    status: str
    price: float | None = None
    qty: int = 0
    fees: dict = field(default_factory=dict)
    note: str = ""


class MarketRules:
    def __init__(self, fees: FeesConfig | None = None, fee_enabled: bool = True):
        self.fees_cfg = fees or FeesConfig()
        self.fee_enabled = fee_enabled

    # ---------- 费用 ----------

    def fees(self, side: str, amount: float) -> dict:
        if not self.fee_enabled:
            return {"commission": 0.0, "stamp": 0.0, "transfer": 0.0}
        f = self.fees_cfg
        commission = round(max(amount * f.commission_ratio, f.min_commission), 2)
        stamp = round(amount * f.stamp_tax, 2) if side == "SELL" else 0.0
        transfer = round(amount * f.transfer_fee, 2)
        return {"commission": commission, "stamp": stamp, "transfer": transfer}

    def total_fees(self, side: str, amount: float) -> float:
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

    def buy(self, symbol: str, is_st: bool, trade_date: date | str,
            open_price: float, prev_close: float, qty: int, cash: float) -> FillResult:
        if qty is None or qty <= 0:
            return FillResult(REJECTED, note="数量非法")
        if qty % 100 != 0:
            return FillResult(REJECTED, note=ODD_LOT)
        side = self.price_side(symbol, is_st, trade_date, prev_close, open_price)
        if side == "UP":
            return FillResult(REJECTED, note=LIMIT_UP)
        amount = round(open_price * qty, 2)
        fee = self.total_fees("BUY", amount)
        if cash < amount + fee + 1e-9:
            return FillResult(REJECTED, note=INSUFFICIENT_CASH)
        return FillResult(FILLED, price=open_price, qty=qty,
                          fees=self.fees("BUY", amount), note="ok")

    def sell(self, symbol: str, is_st: bool, trade_date: date | str,
             open_price: float, prev_close: float, qty: int,
             held_shares: int, sellable_shares: int) -> FillResult:
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
                          fees=self.fees("SELL", amount), note="ok")
