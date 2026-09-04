import pytest

from ashquant.live.qmt import QmtAdapter, QmtEventCallback, QmtNotConfigured
from ashquant.live.reconciliation import ReconciliationEngine


class DummyOrder:
    def __init__(self, order_id: int, symbol: str, status: str):
        self.order_id = order_id
        self.stock_code = symbol
        self.order_status = status


class DummyTrade:
    def __init__(self, trade_id: int, order_id: int, symbol: str, price: float, volume: int):
        self.traded_id = trade_id
        self.order_id = order_id
        self.stock_code = symbol
        self.traded_price = price
        self.traded_volume = volume


def test_qmt_event_callback_queue():
    # 验证 C++ 回调与 Python 消费线程解耦（对标 EasyXT SimpleCallback）
    cb = QmtEventCallback()
    assert not cb.connected

    cb.on_connected()
    assert cb.connected

    # 模拟推送成交事件
    trade = DummyTrade(1001, 501, "600519.SH", 1800.0, 100)
    cb.on_stock_trade(trade)

    # 验证事件被毫秒级推入内部线程安全队列，无阻断
    assert cb.event_queue.qsize() == 2
    evt1, data1 = cb.event_queue.get_nowait()
    assert evt1 == "connected"
    assert data1 is True

    evt2, data2 = cb.event_queue.get_nowait()
    assert evt2 == "trade"
    assert data2.traded_id == 1001


def test_qmt_adapter_unconfigured_protection():
    # 宪法 III：未配置时严禁静默降级或无提示尝试
    adapter = QmtAdapter()
    with pytest.raises(QmtNotConfigured):
        adapter.connect()


def test_reconciliation_engine_pass():
    # 模拟本地模拟盘账本
    class MockPaperBroker:
        def __init__(self):
            self.state = {
                "cash": 100000.0,
                "positions": {
                    "600519": {"shares": 200},
                    "000001": {"shares": 500},
                },
            }

    local_paper = MockPaperBroker()
    engine = ReconciliationEngine()

    # 柜台持仓与本地完全一致
    broker_positions = {"600519": 200, "000001": 500}
    broker_cash = 100000.0

    report = engine.reconcile(local_paper, broker_positions=broker_positions, broker_cash=broker_cash)
    assert report.is_consistent
    assert len(report.diffs) == 0
    # 无异常，允许开盘交易
    engine.assert_can_trade(report)


def test_reconciliation_engine_detects_mismatch():
    class MockPaperBroker:
        def __init__(self):
            self.state = {
                "cash": 100000.0,
                "positions": {
                    "600519": {"shares": 200},
                },
            }

    local_paper = MockPaperBroker()
    engine = ReconciliationEngine()

    # 柜台持仓出现偏差：600519 仅有 100 股，且多出一只柜台手工买入的 000001
    broker_positions = {"600519": 100, "000001": 300}
    broker_cash = 95000.0

    report = engine.reconcile(local_paper, broker_positions=broker_positions, broker_cash=broker_cash)
    assert not report.is_consistent
    assert len(report.diffs) >= 3  # 600519 shares mismatch, 000001 missing in local, cash mismatch

    # 触发盘前防御阻断
    with pytest.raises(RuntimeError, match="盘前对账失败"):
        engine.assert_can_trade(report)
