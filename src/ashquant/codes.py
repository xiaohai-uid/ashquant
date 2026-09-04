"""代码规范化与 A股板块/涨跌停规则（宪法 II：市场规则保真）。"""

from __future__ import annotations

import re
from datetime import date

from ashquant.config import ST_MAIN_SWITCH_DATE

_ST_SWITCH = date.fromisoformat(ST_MAIN_SWITCH_DATE)

MAIN = "MAIN"  # 沪深主板
GEM = "GEM"  # 创业板
STAR = "STAR"  # 科创板
BSE = "BSE"  # 北交所


class SymbolError(ValueError):
    pass


def normalize_symbol(raw: str) -> str:
    """600519 / sh600519 / 600519.SH / 600519.SZ -> "600519"。"""
    s = str(raw).strip().lower()
    s = re.sub(r"^(sh|sz|bj)", "", s)
    s = re.sub(r"\.(sh|sz|bj)$", "", s)
    if not re.fullmatch(r"\d{6}", s):
        raise SymbolError(f"无法识别的股票代码: {raw!r}（示例: 600519 / sz000001 / 300750.SZ）")
    return s


def board_of(symbol: str) -> str:
    s = normalize_symbol(symbol)
    if s.startswith("68"):
        return STAR
    if s.startswith("30"):
        return GEM
    if s.startswith(("83", "87", "88", "43", "92", "920")):
        return BSE
    return MAIN


def limit_pct(symbol: str, is_st: bool = False, on: date | str | None = None) -> float:
    """该标的在指定日期的涨跌幅限制（小数）。

    主板 ST：2026-07-06 前 5%，之后 10%（沪深交易所 2026 修订交易规则）。
    创业板/科创板 20%；北交所 30%；主板非 ST 10%。
    """
    d = date.fromisoformat(on) if isinstance(on, str) else (on or date.today())
    b = board_of(symbol)
    if b == STAR or b == GEM:
        return 0.20
    if b == BSE:
        return 0.30
    if is_st:
        return 0.05 if d < _ST_SWITCH else 0.10
    return 0.10


def limit_prices(prev_close: float, pct: float) -> tuple[float, float]:
    """涨停价/跌停价（四舍五入到分，交易所规则）。"""
    up = round(prev_close * (1 + pct) + 1e-9, 2)
    down = round(prev_close * (1 - pct) + 1e-9, 2)
    return up, down


def is_trading_day(d: date | str) -> bool:
    """粗判是否为交易日（排除周末）。"""
    dt = date.fromisoformat(d) if isinstance(d, str) else d
    return dt.weekday() < 5


def next_trading_day(d: date | str) -> date:
    """获取下一个交易日（跳过周末）。"""
    dt = date.fromisoformat(d) if isinstance(d, str) else d
    cur = dt
    while True:
        cur = date.fromordinal(cur.toordinal() + 1)
        if cur.weekday() < 5:
            return cur


def is_st_name(name: str) -> bool:
    """按名称粗判 ST（回测的历史 ST 状态不可得时的保守开关；见 plan 局限说明）。"""
    n = (name or "").upper().replace(" ", "")
    return "ST" in n or "*ST" in n
