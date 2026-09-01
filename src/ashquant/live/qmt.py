"""QMT/miniQMT（xtquant）可选实盘适配器（宪法 III：默认模拟盘，实盘需用户显式配置）。

本模块不随核心依赖安装：需要实盘的用户自装 miniQMT 客户端与 xtquant，并在环境变量
ASHQUANT_QMT_PATH 指定userdata_mini 路径。程序化交易须遵守证监会 2024 年 8 号公告
及沪深北交易所程序化交易细则（见 specs/research/02-ashare-data-and-brokers.md）；
本项目不提供高频能力。
"""

from __future__ import annotations

import os

MSG_SETUP = (
    "未配置 QMT 实盘通道。启用步骤：1) 在支持 miniQMT 的券商开通权限；"
    "2) 安装 miniQMT 客户端并登录；3) pip install xtquant；"
    "4) 设置环境变量 ASHQUANT_QMT_PATH 指向 userdata_mini 目录。"
    "未配置时请使用模拟盘（ashquant paper ...）。"
)


class QmtNotConfigured(RuntimeError):
    pass


class QmtAdapter:
    """极薄的订单桥：buy/sell 仅下单，不做策略判断。"""

    def __init__(self):
        self._api = None

    def connect(self):
        if os.environ.get("ASHQUANT_QMT_PATH") is None:
            raise QmtNotConfigured(MSG_SETUP)
        try:
            from xtquant import xttrader  # noqa: F401  延迟导入：可选依赖
        except ImportError as e:
            raise QmtNotConfigured(f"xtquant 未安装（pip install xtquant）: {e}") from e
        # 具体连接参数因券商 miniQMT 版本而异，由用户环境决定；此处保留显式断点，
        # 不做任何静默降级（宪法 III：实盘路径必须显式）。
        raise QmtNotConfigured(
            "QMT 适配器为接口占位：请在 live/qmt.py 中按你的 miniQMT 环境补全连接与下单代码"
            "（项目开源后欢迎提交 PR）。默认请使用模拟盘。"
        )

    def buy(self, symbol: str, qty: int) -> dict:
        self.connect()  # 未配置时在此抛出 QmtNotConfigured
        raise NotImplementedError

    def sell(self, symbol: str, qty: int) -> dict:
        self.connect()
        raise NotImplementedError
