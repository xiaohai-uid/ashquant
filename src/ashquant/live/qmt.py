"""QMT/miniQMT（xtquant）可选实盘适配器（宪法 III：默认模拟盘，实盘需用户显式配置）。

遵循工业级架构（对标 EasyXT / quant-king299）：
- 事件回调与核心业务逻辑异步队列解耦，防止 C++ 消息循环被本地阻塞
- 严密保持宪法 III 规定：未配置时绝不静默降级或带病上线
"""

from __future__ import annotations

import logging
import os
import queue
import threading
from typing import Any

logger = logging.getLogger(__name__)

MSG_SETUP = (
    "未配置 QMT 实盘通道。启用步骤：1) 在支持 miniQMT 的券商开通权限；"
    "2) 安装 miniQMT 客户端并登录；3) pip install xtquant；"
    "4) 设置环境变量 ASHQUANT_QMT_PATH 指向 userdata_mini 目录。"
    "未配置时请使用模拟盘（ashquant paper ...）。"
)


class QmtNotConfigured(RuntimeError):
    pass


class QmtEventCallback:
    """解耦的 QMT 交易事件监听器（对标 EasyXT SimpleCallback）。

    在 C++ 回调线程中仅做极速的内存队列推入与状态字典暂存，
    不执行任何耗时 IO、数据库写入或策略计算，杜绝卡死 XtQuant 消息循环。
    """

    def __init__(self):
        self.connected = False
        self.orders: dict[int, Any] = {}
        self.trades: dict[int, Any] = {}
        self.positions: dict[str, Any] = {}
        self.assets: dict[str, Any] = {}
        self.errors: list[Any] = []

        # 线程安全事件队列与同步事件
        self.event_queue: queue.Queue = queue.Queue()
        self.order_event = threading.Event()
        self.trade_event = threading.Event()

    def on_connected(self):
        self.connected = True
        logger.info("[QMT] 柜台交易连接成功")
        self.event_queue.put(("connected", True))

    def on_disconnected(self):
        self.connected = False
        logger.warning("[QMT] 柜台交易连接断开")
        self.event_queue.put(("disconnected", False))

    def on_stock_order(self, order: Any):
        order_id = getattr(order, "order_id", None)
        if order_id is not None:
            self.orders[order_id] = order
        self.event_queue.put(("order", order))
        self.order_event.set()

    def on_stock_trade(self, trade: Any):
        trade_id = getattr(trade, "traded_id", None)
        if trade_id is not None:
            self.trades[trade_id] = trade
        self.event_queue.put(("trade", trade))
        self.trade_event.set()

    def on_order_error(self, order_error: Any):
        self.errors.append(order_error)
        self.event_queue.put(("error", order_error))
        logger.error("[QMT] 委托回报错误: %s", order_error)


class QmtAdapter:
    """极薄的订单桥与事件队列守护：buy/sell 仅下单，不做策略判断。"""

    def __init__(self, callback: QmtEventCallback | None = None):
        self._api = None
        self.callback = callback or QmtEventCallback()

    def connect(self):
        if os.environ.get("ASHQUANT_QMT_PATH") is None:
            raise QmtNotConfigured(MSG_SETUP)
        try:
            from xtquant import xttrader  # noqa: F401
        except ImportError as e:
            raise QmtNotConfigured(f"xtquant 未安装（pip install xtquant）: {e}") from e

        raise QmtNotConfigured(
            "QMT 适配器为接口占位：请在 live/qmt.py 中按你的 miniQMT 环境补全连接与下单代码"
            "（项目开源后欢迎提交 PR）。默认请使用模拟盘。"
        )

    def buy(self, symbol: str, qty: int) -> dict:
        self.connect()
        raise NotImplementedError

    def sell(self, symbol: str, qty: int) -> dict:
        self.connect()
        raise NotImplementedError
