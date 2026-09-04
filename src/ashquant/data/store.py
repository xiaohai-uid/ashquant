"""行情与特色资金流统一本地存储（MarketDataStore / BarStore）。

遵循 codebase-design 深度模块设计：
- 统一聚合日线（Bars）、基准指数（Index）、主力资金流（CapitalFlow）与元数据
- 隔离底层文件存储路径与序列化细节，支持跨环境目录注入与纯内存/离线测试。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ashquant.data.aksource import DataSourceError, fetch_daily, fetch_index_daily

logger = logging.getLogger(__name__)

BAR_COLS = ["open", "high", "low", "close", "volume", "amount"]
INDEX_KEY = "INDEX000300"  # 基准指数在 store 中的特殊键

# 默认样本池：覆盖主板/创业板/科创板的高流动性标的（演示与测试用）
SAMPLE20 = [
    "600519", "000001", "300750", "688981", "601318", "000858", "600036", "601899",
    "000333", "600900", "002594", "601012", "600030", "000651", "601166", "002415",
    "600276", "603288", "688111", "601398",
]


class BarStore:
    """统一市场数据仓储（包含日线行情与主力资金流）。"""

    def __init__(self, data_dir: Path | str):
        self.root = Path(data_dir)
        self.bars_dir = self.root / "bars"
        self.alt_dir = self.root / "alternative"
        self.bars_dir.mkdir(parents=True, exist_ok=True)
        self.alt_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 日线基本读写 ----------

    def _path(self, symbol: str) -> Path:
        return self.bars_dir / f"{symbol}.parquet"

    def _meta_path(self, symbol: str) -> Path:
        return self.bars_dir / f"{symbol}.meta.json"

    def save_bars(self, symbol: str, df: pd.DataFrame, source: str = "akshare") -> None:
        """原子写入：临时文件 + rename；整段替换，不与旧数据拼接（防复权口径错位）。"""
        symbol = str(symbol)
        tmp = self._path(symbol).with_suffix(".parquet.tmp")
        df.to_parquet(tmp, engine="pyarrow")
        os.replace(tmp, self._path(symbol))
        meta = {
            "symbol": symbol,
            "source": source,
            "adjust": "qfq",
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "rows": int(len(df)),
            "start": str(df.index.min().date()) if len(df) else None,
            "end": str(df.index.max().date()) if len(df) else None,
        }
        (self._meta_path(symbol)).write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def load_bars(self, symbol: str) -> pd.DataFrame | None:
        p = self._path(str(symbol))
        if not p.exists():
            return None
        return pd.read_parquet(p, engine="pyarrow")

    def meta(self, symbol: str) -> dict | None:
        p = self._meta_path(str(symbol))
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def has(self, symbol: str) -> bool:
        return self._path(str(symbol)).exists()

    def list_symbols(self) -> list[str]:
        return sorted(p.stem for p in self.bars_dir.glob("*.parquet"))

    def missing_symbols(self, symbols: list[str]) -> list[str]:
        return [s for s in symbols if not self.has(s)]

    # ---------- 主力资金流与特色数据 ----------

    def _alt_path(self, symbol: str) -> Path:
        clean_sym = symbol.split(".")[0]
        return self.alt_dir / f"{clean_sym}_flow.parquet"

    def load_capital_flow(self, symbol: str, use_cache: bool = True) -> pd.DataFrame:
        """获取个股历史资金流向数据（北向、融资融券、超大单）。"""
        p = self._alt_path(symbol)
        if use_cache and p.exists():
            try:
                return pd.read_parquet(p)
            except Exception as e:
                logger.warning("读取资金流缓存失败 %s: %s", p, e)

        # 尝试在线抓取
        clean_sym = symbol.split(".")[0]
        df = self._fetch_from_akshare(clean_sym)
        if df is not None and not df.empty:
            try:
                df.to_parquet(p, index=True)
                return df
            except Exception as e:
                logger.warning("缓存资金流失败 %s: %s", p, e)
                return df

        # 离线/测试合成兜底
        return self._generate_synthetic_flow(clean_sym)

    def load_cached_capital_flow(self, symbol: str) -> pd.DataFrame | None:
        """仅从本地缓存加载资金流。若缓存不存在则返回 None，绝不触网或生成合成数据。"""
        p = self._alt_path(symbol)
        if p.exists():
            try:
                return pd.read_parquet(p)
            except Exception as e:
                logger.warning("读取资金流缓存失败 %s: %s", p, e)
                return None
        return None

    def create_research_snapshot(self, symbols: list[str], destination: Path | str) -> dict:
        """冻结研究输入：复制指定标的日线、基准指数日线、元数据及已缓存资金流，并生成 manifest.json。"""
        dest = Path(destination)
        if dest.exists():
            raise FileExistsError(f"Snapshot destination directory already exists: {dest}")

        sorted_symbols = sorted(set(symbols))

        # 检查标的日线与基准指数必须存在
        missing_stocks = [s for s in sorted_symbols if not self.has(s)]
        if missing_stocks:
            raise FileNotFoundError(f"Missing stock bar parquets for symbols: {missing_stocks}")
        if not self.has(INDEX_KEY):
            raise FileNotFoundError(f"Missing benchmark bar parquet: {INDEX_KEY}")

        dest_bars = dest / "bars"
        dest_alt = dest / "alternative"
        dest_bars.mkdir(parents=True, exist_ok=False)
        dest_alt.mkdir(parents=True, exist_ok=False)

        files_hash: dict[str, str] = {}
        absent_flow_symbols: list[str] = []

        def _copy_and_hash(src_path: Path, dst_path: Path, rel_path: str):
            shutil.copy2(src_path, dst_path)
            h = hashlib.sha256(dst_path.read_bytes()).hexdigest()
            files_hash[rel_path] = h

        for s in sorted_symbols:
            src_bar = self._path(s)
            dst_bar = dest_bars / f"{s}.parquet"
            _copy_and_hash(src_bar, dst_bar, f"bars/{s}.parquet")

            src_meta = self._meta_path(s)
            if src_meta.exists():
                dst_meta = dest_bars / f"{s}.meta.json"
                _copy_and_hash(src_meta, dst_meta, f"bars/{s}.meta.json")

            src_flow = self._alt_path(s)
            if src_flow.exists():
                clean_sym = s.split(".")[0]
                dst_flow = dest_alt / f"{clean_sym}_flow.parquet"
                _copy_and_hash(src_flow, dst_flow, f"alternative/{clean_sym}_flow.parquet")
            else:
                absent_flow_symbols.append(s)

        # 复制基准指数
        src_bench = self._path(INDEX_KEY)
        dst_bench = dest_bars / f"{INDEX_KEY}.parquet"
        _copy_and_hash(src_bench, dst_bench, f"bars/{INDEX_KEY}.parquet")

        src_bench_meta = self._meta_path(INDEX_KEY)
        if src_bench_meta.exists():
            dst_bench_meta = dest_bars / f"{INDEX_KEY}.meta.json"
            _copy_and_hash(src_bench_meta, dst_bench_meta, f"bars/{INDEX_KEY}.meta.json")

        manifest = {
            "schema_version": "1.0",
            "symbols": sorted_symbols,
            "files": {k: files_hash[k] for k in sorted(files_hash.keys())},
            "absent_flow_symbols": sorted(absent_flow_symbols),
        }

        manifest_path = dest / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def _fetch_from_akshare(self, clean_sym: str) -> pd.DataFrame | None:
        try:
            import akshare as ak
            df_flow = ak.stock_individual_fund_flow(stock=clean_sym, market="sh" if clean_sym.startswith("6") else "sz")
            if df_flow is not None and not df_flow.empty:
                df_res = pd.DataFrame()
                df_res["date"] = pd.to_datetime(df_flow["日期"]).dt.strftime("%Y-%m-%d")
                if "超大单净流入-净额" in df_flow.columns:
                    df_res["super_large_net_inflow"] = pd.to_numeric(df_flow["超大单净流入-净额"], errors="coerce").fillna(0.0) * 10000.0
                else:
                    df_res["super_large_net_inflow"] = 0.0
                if "大单净流入-净额" in df_flow.columns:
                    df_res["large_net_inflow"] = pd.to_numeric(df_flow["大单净流入-净额"], errors="coerce").fillna(0.0) * 10000.0
                else:
                    df_res["large_net_inflow"] = 0.0
                df_res["northbound_net_shares"] = 0.0
                df_res["northbound_hold_ratio"] = 0.0
                df_res["margin_balance"] = 0.0
                return df_res.set_index("date").sort_index()
        except Exception as e:
            logger.debug("Akshare 资金流抓取跳过 %s: %s", clean_sym, e)
        return None

    def _generate_synthetic_flow(self, clean_sym: str, n_days: int = 250) -> pd.DataFrame:
        dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="B").strftime("%Y-%m-%d")
        seed = sum(ord(c) for c in clean_sym)
        rng = np.random.default_rng(seed)

        super_large = rng.normal(loc=1e6, scale=5e6, size=n_days)
        large = rng.normal(loc=5e5, scale=3e6, size=n_days)
        northbound_shares = rng.normal(loc=5e4, scale=2e5, size=n_days)
        northbound_ratio = np.clip(np.cumsum(rng.normal(loc=0.01, scale=0.05, size=n_days)) + 3.0, 0.5, 15.0)

        return pd.DataFrame(
            {
                "date": dates,
                "super_large_net_inflow": super_large,
                "large_net_inflow": large,
                "northbound_net_shares": northbound_shares,
                "northbound_hold_ratio": northbound_ratio,
                "margin_balance": 1e8 + np.cumsum(rng.normal(0, 1e6, size=n_days)),
            }
        ).set_index("date")

    # ---------- 抓取编排 ----------

    def refresh_bars(
        self,
        symbols: list[str],
        start: date | str = "20230101",
        end: date | str = date.today().strftime("%Y%m%d"),
        skip_existing: bool = True,
        on_progress=None,
    ) -> dict[str, str]:
        """批量抓取，断点续抓；返回 {symbol: "ok"|"cached"|"error: ..."}。"""
        results: dict[str, str] = {}
        for s in symbols:
            if skip_existing and self.has(s):
                results[s] = "cached"
                continue
            try:
                df = fetch_daily(s, start, end)
                if df is None or df.empty:
                    results[s] = "error: 空数据"
                    continue
                self.save_bars(s, df)
                results[s] = "ok"
            except Exception as e:  # noqa: BLE001
                results[s] = f"error: {e}"
            if on_progress:
                on_progress(s, results[s])
        return results

    def ensure_index(self, index_code: str = "000300",
                     start: date | str = "20200101") -> pd.DataFrame:
        """确保基准指数日线可用（缺失则抓取）。"""
        df = self.load_bars(INDEX_KEY)
        if df is None or (start and str(df.index.min().date()).replace("-", "") > str(start)):
            df = fetch_index_daily(index_code, start, "20991231")
            self.save_bars(INDEX_KEY, df, source=f"index_zh_a_hist({index_code})")
        return df


def resolve_pool(pool: str | None, symbols: list[str] | None) -> list[str]:
    """股票池解析：显式 symbols > sample20/csi300 池名。"""
    from ashquant.codes import normalize_symbol

    if symbols:
        return [normalize_symbol(s) for s in symbols]
    if pool == "csi300":
        return csi300_constituents()
    return list(SAMPLE20)


def csi300_constituents() -> list[str]:
    """沪深300 成分（akshare 新浪源；失败时给出可操作错误）。"""
    import akshare as ak
    try:
        df = ak.index_stock_cons(symbol="000300")
    except Exception as e:  # noqa: BLE001
        raise DataSourceError(
            f"获取沪深300成分失败: {e}；可改用 --symbols 显式指定或先用 --pool sample20"
        ) from e
    col = next(c for c in df.columns if "代码" in c)
    return sorted({str(c).zfill(6) for c in df[col].astype(str)})
