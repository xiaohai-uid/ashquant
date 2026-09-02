"""A 股特色与主力资金流向数据（兼容代理层）。

将实际仓储操作委托给 BarStore（实现数据层统一契约，消除全局 DATA_DIR 泄漏）。
"""

from __future__ import annotations

import pandas as pd

from ashquant.config import DATA_DIR
from ashquant.data.store import BarStore


def fetch_capital_flow(symbol: str, use_cache: bool = True, data_dir: str | None = None) -> pd.DataFrame:
    """获取个股历史资金流向数据（统一路由至 BarStore 管理）。"""
    target_dir = data_dir or DATA_DIR
    store = BarStore(target_dir)
    return store.load_capital_flow(symbol, use_cache=use_cache)
