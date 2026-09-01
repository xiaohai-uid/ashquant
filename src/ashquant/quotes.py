"""实时快照（watch 自选股）：免费公开源，秒~分钟级延迟（A2 假设）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from ashquant.data import aksource


@dataclass(frozen=True)
class SpotQuote:
    symbol: str
    name: str | None
    price: float | None
    pct_chg: float | None
    change: float | None
    prev_close: float | None
    fetched_at: str
    market_state: str


def market_state(now: datetime | None = None) -> str:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return "周末休市（显示最后快照）"
    t = now.time()
    if time(9, 15) <= t < time(9, 25):
        return "集合竞价"
    if time(9, 30) <= t <= time(11, 30) or time(13, 0) <= t <= time(15, 0):
        return "交易中"
    if time(11, 30) < t < time(13, 0):
        return "午间休市"
    return "已收盘（显示最后快照）"


def snapshot(symbols: list[str]) -> list[SpotQuote]:
    df = aksource.fetch_spot(symbols)
    fetched = df.attrs.get("fetched_at", datetime.now().isoformat(timespec="seconds"))
    state = market_state()
    out = []
    for _, r in df.iterrows():
        price = r.get("price")
        if price is None or (isinstance(price, float) and price != price):  # NaN
            note_symbol = "快照缺失（可能停牌或代码错误）"
        else:
            note_symbol = None
        out.append(
            SpotQuote(
                symbol=str(r["symbol"]), name=r.get("name"), price=price,
                pct_chg=r.get("pct_chg"), change=r.get("change"),
                prev_close=r.get("prev_close"), fetched_at=fetched,
                market_state=note_symbol or state,
            )
        )
    return out
