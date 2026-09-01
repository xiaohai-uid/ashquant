"""Web 后端（FastAPI）：REST API + 单文件控制台（CDN lightweight-charts）。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ashquant import codes
from ashquant import config as cfg_mod
from ashquant.data import BarStore
from ashquant.indicators import add_indicators
from ashquant.paper import PaperBroker, PaperError
from ashquant.predict import InsufficientDataError, predict_next_day
from ashquant.quotes import snapshot

STATIC_DIR = Path(__file__).parent / "static"


class PaperOrderReq(BaseModel):
    symbol: str
    qty: int = 100
    price: float | None = None


def create_app(data_dir: str | None = None) -> FastAPI:
    cfg = cfg_mod.get_config(data_dir)
    store = BarStore(cfg.data_dir)
    paper = PaperBroker(cfg)

    api = FastAPI(title="ashquant Web Console", version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/", response_class=HTMLResponse)
    def index():
        html_file = STATIC_DIR / "index.html"
        if not html_file.exists():
            return "<h3>index.html not found</h3>"
        return html_file.read_text(encoding="utf-8")

    @api.get("/api/spot")
    def api_spot(symbols: str = "600519,000001,300750"):
        syms = [codes.normalize_symbol(s) for s in symbols.split(",") if s.strip()]
        try:
            quotes = snapshot(syms)
            return {"quotes": [q.__dict__ for q in quotes]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api.get("/api/kline/{symbol}")
    def api_kline(symbol: str, limit: int = 800):
        sym = codes.normalize_symbol(symbol)
        bars = store.load_bars(sym)
        if bars is None or bars.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {sym} 历史日线，请先运行 fetch 抓取")
        ind = add_indicators(bars)
        sub = ind.tail(limit)

        records = []
        for d, r in sub.iterrows():
            records.append({
                "time": str(d.date()),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
                "ma5": float(r["ma5"]) if "ma5" in r and r["ma5"] == r["ma5"] else None,
                "ma20": float(r["ma20"]) if "ma20" in r and r["ma20"] == r["ma20"] else None,
                "ma60": float(r["ma60"]) if "ma60" in r and r["ma60"] == r["ma60"] else None,
            })
        return {"symbol": sym, "bars": records}

    @api.get("/api/predict/{symbol}")
    def api_predict(symbol: str):
        sym = codes.normalize_symbol(symbol)
        try:
            return predict_next_day(store, sym, cfg=cfg, log=True)
        except InsufficientDataError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api.get("/api/paper")
    def api_paper():
        try:
            raw_st = paper._load()
            syms = list(raw_st.get("positions", {}).keys())
            prices = {}
            if syms:
                try:
                    quotes = snapshot(syms)
                    prices = {q.symbol: {"price": q.price, "name": q.name} for q in quotes}
                except Exception:
                    pass
            return paper.show(prices)
        except PaperError:
            # 自动初始化一个默认账户
            paper.init()
            return paper.show()

    @api.post("/api/paper/buy")
    def api_paper_buy(req: PaperOrderReq):
        sym = codes.normalize_symbol(req.symbol)
        px = req.price
        pc = None
        name = ""
        if px is None:
            q = snapshot([sym])[0]
            px = q.price
            pc = q.prev_close
            name = q.name or ""
        if px is None:
            raise HTTPException(status_code=400, detail="无法获取有效报价")
        try:
            res = paper.buy(sym, req.qty, px, name=name, prev_close=pc)
            return {"ok": True, "result": res}
        except PaperError as e:
            return {"ok": False, "reason": str(e)}

    @api.post("/api/paper/sell")
    def api_paper_sell(req: PaperOrderReq):
        sym = codes.normalize_symbol(req.symbol)
        px = req.price
        pc = None
        name = ""
        if px is None:
            q = snapshot([sym])[0]
            px = q.price
            pc = q.prev_close
            name = q.name or ""
        if px is None:
            raise HTTPException(status_code=400, detail="无法获取有效报价")
        try:
            res = paper.sell(sym, req.qty, px, name=name, prev_close=pc)
            return {"ok": True, "result": res}
        except PaperError as e:
            return {"ok": False, "reason": str(e)}

    return api
