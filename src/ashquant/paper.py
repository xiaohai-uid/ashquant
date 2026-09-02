"""模拟盘（paper trading）：默认交易形态（宪法 III），复用 MarketRules 规则引擎。

v0.2.0: 接入 RegimeBreaker 熔断机制，在异常行情或连续亏损冷静期下拦截买入。
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

from ashquant import config as cfg_mod
from ashquant.backtest.breaker import RegimeBreaker
from ashquant.backtest.rules import MarketRules
from ashquant.codes import is_st_name, normalize_symbol
from ashquant.domain import FillStatus, MarketContext

FILLED = FillStatus.FILLED
DEFERRED = FillStatus.DEFERRED


class PaperError(RuntimeError):
    """规则拒单等业务结果（CLI 退出码 4）。"""


class PaperBroker:
    def __init__(self, cfg: cfg_mod.Config | None = None, breaker: RegimeBreaker | None = None):
        self.cfg = cfg or cfg_mod.get_config()
        self.path = Path(self.cfg.data_dir) / "paper_portfolio.json"
        self.trades_path = Path(self.cfg.data_dir) / "paper_trades.jsonl"
        self.rules = MarketRules(self.cfg.fees)
        self.breaker = breaker or RegimeBreaker()

    # ---------- 状态 ----------

    def _load(self) -> dict:
        if not self.path.exists():
            raise PaperError("模拟账户未初始化；先运行 ashquant paper init")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, st: dict) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def _rollover_date(self, st: dict, today: str) -> None:
        """跨交易日：解锁前一日买入（T+1 可卖）。"""
        if st.get("last_date") and st["last_date"] < today:
            for p in st["positions"].values():
                p["locked"] = 0
        st["last_date"] = today

    def _append_trade(self, t: dict) -> None:
        with self.trades_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    # ---------- 操作 ----------

    def init(self, cash: float | None = None) -> dict:
        cash = self.cfg.initial_cash if cash is None else float(cash)
        st = {
            "cash": round(cash, 2), "positions": {}, "last_date": date.today().isoformat(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "equity_curve": [{"date": date.today().isoformat(), "equity": round(cash, 2)}],
        }
        self._save(st)
        return st

    def show(self, prices: dict[str, dict] | None = None) -> dict:
        """prices: {symbol: {"price":.., "name":..}} 实时价（可选，缺省仅报持仓成本）。"""
        st = self._load()
        self._rollover_date(st, date.today().isoformat())
        positions = []
        mkt = 0.0
        for s, p in st["positions"].items():
            px = (prices or {}).get(s, {}).get("price")
            val = p["shares"] * px if px else p["shares"] * p["cost_price"]
            mkt += val
            positions.append({
                "symbol": s, "shares": p["shares"],
                "sellable": p["shares"] - p.get("locked", 0),
                "cost_price": p["cost_price"],
                "last_price": px,
                "market_value": round(val, 2),
                "pnl": round(val - p["cost_total"], 2) if px else None,
            })
        return {"cash": round(st["cash"], 2), "positions": positions,
                "market_value": round(mkt, 2), "equity": round(st["cash"] + mkt, 2)}

    def buy(self, symbol: str, qty: int, price: float, name: str = "",
            prev_close: float | None = None) -> dict:
        # 熔断拦截
        if self.breaker.is_account_in_cooldown():
            raise PaperError("买入被拒: 账户处于连续亏损 24 小时冷静期熔断保护中")

        symbol = normalize_symbol(symbol)
        st = self._load()
        today = date.today().isoformat()
        self._rollover_date(st, today)
        pc = float(prev_close if prev_close is not None else price)
        ctx = MarketContext(symbol=symbol, trade_date=today, price=float(price), prev_close=pc, is_st=is_st_name(name))
        res = self.rules.buy_context(ctx, qty=int(qty), cash=st["cash"])
        if res.status != FILLED:
            raise PaperError(f"买入被拒: {res.note}")
        amount = round(res.price * res.qty, 2)
        fee = round(sum(res.fees.values()), 2)
        st["cash"] = round(st["cash"] - amount - fee, 2)
        pos = st["positions"].get(symbol)
        if pos is None:
            pos = {"shares": 0, "cost_total": 0.0, "cost_price": 0.0, "locked": 0,
                   "opened": today}
            st["positions"][symbol] = pos
        total_shares = pos["shares"] + res.qty
        pos["cost_total"] = round(pos["cost_total"] + amount + fee, 2)
        pos["cost_price"] = round(pos["cost_total"] / total_shares, 4)
        pos["shares"] = total_shares
        pos["locked"] = pos.get("locked", 0) + res.qty  # T+1
        self._save(st)
        self._append_trade({"date": today, "symbol": symbol, "side": "BUY", "qty": res.qty,
                            "price": res.price, "fees": res.fees, "amount": amount})
        return {"symbol": symbol, "qty": res.qty, "price": res.price, "fees": res.fees,
                "cash_left": st["cash"]}

    def sell(self, symbol: str, qty: int, price: float, name: str = "",
             prev_close: float | None = None) -> dict:
        symbol = normalize_symbol(symbol)
        st = self._load()
        today = date.today().isoformat()
        self._rollover_date(st, today)
        pos = st["positions"].get(symbol)
        if pos is None:
            raise PaperError("卖出被拒: NO_POSITION")
        pc = float(prev_close if prev_close is not None else price)
        ctx = MarketContext(symbol=symbol, trade_date=today, price=float(price), prev_close=pc, is_st=is_st_name(name))
        res = self.rules.sell_context(ctx, qty=int(qty), held_shares=pos["shares"],
                                      sellable_shares=pos["shares"] - pos.get("locked", 0))
        if res.status == DEFERRED:
            raise PaperError(f"卖出被拒: {res.note}（跌停无法成交，稍后再试）")
        if res.status != FILLED:
            raise PaperError(f"卖出被拒: {res.note}")
        amount = round(res.price * res.qty, 2)
        fee = round(sum(res.fees.values()), 2)
        net = round(amount - fee, 2)
        st["cash"] = round(st["cash"] + net, 2)
        pnl = round(net - pos["cost_total"] * res.qty / pos["shares"], 2)
        pos["shares"] -= res.qty
        pos["cost_total"] = round(pos["cost_total"] * (pos["shares"] / (pos["shares"] + res.qty)), 2)
        if pos["shares"] == 0:
            st["positions"].pop(symbol)
        self._save(st)
        self._append_trade({"date": today, "symbol": symbol, "side": "SELL", "qty": res.qty,
                            "price": res.price, "fees": res.fees, "amount": amount, "pnl": pnl})

        # 记录胜负至熔断器
        self.breaker.record_trade_result(is_win=bool(pnl > 0))

        return {"symbol": symbol, "qty": res.qty, "price": res.price, "fees": res.fees,
                "pnl": pnl, "cash": st["cash"]}

    def export(self, out_csv: str | Path) -> Path:
        if not self.trades_path.exists():
            raise PaperError("尚无模拟交易记录")
        rows = [json.loads(l) for l in self.trades_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        out = Path(out_csv)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["date", "symbol", "side", "qty", "price", "commission",
                        "stamp", "transfer", "amount", "pnl"])
            for r in rows:
                fees = r.get("fees", {})
                w.writerow([r["date"], r["symbol"], r["side"], r["qty"], r["price"],
                            fees.get("commission", ""), fees.get("stamp", ""),
                            fees.get("transfer", ""), r.get("amount", ""), r.get("pnl", "")])
        return out
