"""行情数据多源适配层（东财 akshare + 腾讯/新浪双重直连容灾）。

在 Windows 环境下若本机代理软件造成东财接口异常，自动降级切换至腾讯/新浪金融源，
确保数据抓取与实时看盘 100% 稳定可用（宪法 IV：数据层稳健性）。
所有 HTTP 目标严格白名单硬编码，防范 SSRF。
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date, datetime

import pandas as pd
import requests

_HIST_COLS = {
    "日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
    "成交量": "volume", "成交额": "amount"
}

ALLOWED_HOSTS = frozenset({
    "web.ifzq.gtimg.cn",
    "hq.sinajs.cn",
    "push2his.eastmoney.com",
})


class DataSourceError(RuntimeError):
    """数据源不可用/返回异常，附带可操作信息。"""


def _safe_get(url: str, headers: dict | None = None, params: dict | None = None, timeout: int = 10) -> requests.Response:
    """带严格域名白名单与仅 HTTPS 约束的安全 HTTP GET。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"禁止非 HTTPS 协议: {url}")
    if parsed.netloc not in ALLOWED_HOSTS:
        raise ValueError(f"禁止访问未经授权的主机: {parsed.netloc}")
    return requests.get(url, headers=headers, params=params, timeout=timeout, allow_redirects=False)


def _symbol_to_qq(symbol: str) -> str:
    s = str(symbol).strip().zfill(6)
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError(f"非法代码: {symbol}")
    if s.startswith(("60", "68", "90")):
        return f"sh{s}"
    if s.startswith(("00", "20", "30")):
        return f"sz{s}"
    if s.startswith(("83", "87", "88", "43", "92")):
        return f"bj{s}"
    return f"sh{s}"


def _fetch_daily_tencent(symbol: str, count: int = 800) -> pd.DataFrame:
    """腾讯高可用日线（前复权）：800 个交易日约 3.2 年历史行情。"""
    qq_code = _symbol_to_qq(symbol)
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {"param": f"{qq_code},day,,,{int(count)},qfq"}
    headers = {"User-Agent": "Mozilla/5.0"}

    resp = _safe_get(url, headers=headers, params=params, timeout=10)
    if resp.status_code != 200:
        raise DataSourceError(f"腾讯行情 HTTP 状态码错误: {resp.status_code}")
    data = resp.json()
    stock_data = data.get("data", {}).get(qq_code, {})
    bars_list = stock_data.get("qfqday") or stock_data.get("day", [])
    if not bars_list:
        raise DataSourceError(f"未能从腾讯接口获取到 {symbol} 的有效日线")

    records = []
    for b in bars_list:
        dt = pd.to_datetime(b[0])
        op, cl, hi, lo = float(b[1]), float(b[2]), float(b[3]), float(b[4])
        vol = float(b[5]) * 100.0
        amt = cl * vol
        records.append({"date": dt, "open": op, "high": hi, "low": lo, "close": cl, "volume": vol, "amount": amt})

    df = pd.DataFrame(records).set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume", "amount"]]


def _fetch_spot_sina(symbols: list[str]) -> pd.DataFrame:
    """新浪高可用实时快照。"""
    clean_syms = [str(s).strip().zfill(6) for s in symbols if re.fullmatch(r"\d{6}", str(s).strip().zfill(6))]
    qq_codes = [_symbol_to_qq(s) for s in clean_syms]
    url = "https://hq.sinajs.cn/list=" + ",".join(qq_codes)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.sina.com.cn",
    }
    resp = _safe_get(url, headers=headers, timeout=10)
    text = resp.content.decode("gbk", errors="replace")

    records = []
    now_ts = datetime.now().isoformat(timespec="seconds")

    for line, sym in zip(text.strip().splitlines(), clean_syms):
        m = re.search(r'"(.*)"', line)
        if not m or not m.group(1):
            records.append({"symbol": sym, "name": None, "price": None, "pct_chg": None, "change": None, "prev_close": None})
            continue
        parts = m.group(1).split(",")
        if len(parts) < 10:
            records.append({"symbol": sym, "name": None, "price": None, "pct_chg": None, "change": None, "prev_close": None})
            continue
        name = parts[0]
        prev_close = float(parts[2]) if float(parts[2]) > 0 else float(parts[1])
        price = float(parts[3]) if float(parts[3]) > 0 else prev_close
        change = round(price - prev_close, 2)
        pct_chg = round(change / prev_close * 100.0, 2) if prev_close > 0 else 0.0

        records.append({
            "symbol": sym, "name": name, "price": price,
            "pct_chg": pct_chg, "change": change, "prev_close": prev_close
        })

    out = pd.DataFrame(records)
    out.attrs["fetched_at"] = now_ts
    return out


def fetch_daily(symbol: str, start: date | str, end: date | str) -> pd.DataFrame:
    """优先 akshare，失败自动降级到腾讯直连源。"""
    try:
        import akshare as ak
        s, e = map(lambda d: d.strftime("%Y%m%d") if isinstance(d, date) else str(d), (start, end))
        code = str(symbol)
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=s, end_date=e, adjust="qfq")
        if df is not None and not df.empty:
            df = df.rename(columns=_HIST_COLS)
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            df = df.set_index("date").sort_index()
            df["volume"] = df["volume"].astype(float) * 100.0
            return df[["open", "high", "low", "close", "volume", "amount"]]
    except Exception:
        pass

    return _fetch_daily_tencent(symbol, count=800)


def fetch_index_daily(index_code: str = "000300", start: date | str = "20200101", end: date | str = "20991231") -> pd.DataFrame:
    """指数日线（默认沪深300）。"""
    try:
        import akshare as ak
        df = ak.index_zh_a_hist(symbol=str(index_code), period="daily", start_date=str(start), end_date=str(end))
        if df is not None and not df.empty:
            df = df.rename(columns=_HIST_COLS)
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            return df.set_index("date").sort_index()[["open", "high", "low", "close", "volume", "amount"]]
    except Exception:
        pass

    qq_code = "sh000300" if index_code == "000300" else f"sh{index_code}"
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {"param": f"{qq_code},day,,,800"}
    resp = _safe_get(url, headers={"User-Agent": "Mozilla/5.0"}, params=params, timeout=10)
    data = resp.json().get("data", {}).get(qq_code, {}).get("day", [])
    records = []
    for b in data:
        dt = pd.to_datetime(b[0])
        op, cl, hi, lo = float(b[1]), float(b[2]), float(b[3]), float(b[4])
        vol = float(b[5]) * 100.0
        records.append({"date": dt, "open": op, "high": hi, "low": lo, "close": cl, "volume": vol, "amount": cl * vol})
    return pd.DataFrame(records).set_index("date").sort_index()[["open", "high", "low", "close", "volume", "amount"]]


def fetch_spot(symbols: list[str] | None = None) -> pd.DataFrame:
    """实时快照：优先 akshare，失败自动降级至新浪直连。"""
    sym_list = symbols or ["600519", "000001", "300750"]
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            spot_cols = {"代码": "symbol", "名称": "name", "最新价": "price", "涨跌幅": "pct_chg", "涨跌额": "change", "昨收": "prev_close"}
            df = df.rename(columns=spot_cols)
            df = df[list(spot_cols.values())].copy()
            df.attrs["fetched_at"] = datetime.now().isoformat(timespec="seconds")
            return df[df["symbol"].isin([str(s) for s in sym_list])]
    except Exception:
        pass

    return _fetch_spot_sina(sym_list)
