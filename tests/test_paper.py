from pathlib import Path

import pytest

from ashquant import config as cfg_mod
from ashquant.paper import PaperBroker, PaperError


def test_paper_broker_lifecycle(tmp_path: Path):
    cfg = cfg_mod.Config(data_dir=tmp_path)
    broker = PaperBroker(cfg)

    # 1. 初始化
    st = broker.init(100_000.0)
    assert st["cash"] == 100_000.0

    # 2. 买入 100 股 @ 10.00 元 (货款 1000 + 最低佣金 5 + 过户 0.01 = 1005.01)
    res_buy = broker.buy("600519", 100, 10.00)
    assert res_buy["cash_left"] == 98994.99

    # 3. T+1 当日不可卖出
    with pytest.raises(PaperError) as exc:
        broker.sell("600519", 100, 10.50)
    assert "T1_LOCK" in str(exc.value)

    # 4. 模拟跨日解冻
    raw = broker._load()
    raw["last_date"] = "2023-01-01"
    broker._save(raw)

    # 5. 次日卖出 @ 11.00 元 (货款 1100 - 佣金5 - 印花0.55 - 过户0.01 = 净收入 1094.44)
    res_sell = broker.sell("600519", 100, 11.00)
    assert res_sell["pnl"] == round(1094.44 - 1005.01, 2)
    assert res_sell["cash"] == round(98994.99 + 1094.44, 2)

    # 6. 对账单导出
    csv_file = tmp_path / "trades.csv"
    out = broker.export(csv_file)
    assert out.exists()
    assert len(out.read_text(encoding="utf-8-sig").splitlines()) == 3  # 表头 + 1买 + 1卖


def test_paper_broker_limit_up_rejected(tmp_path: Path):
    cfg = cfg_mod.Config(data_dir=tmp_path)
    broker = PaperBroker(cfg)
    broker.init(100_000.0)

    # 昨收 10.00，现价 11.00（涨停） -> 应当拒绝买入
    with pytest.raises(PaperError) as exc:
        broker.buy("600519", 100, price=11.00, prev_close=10.00)
    assert "LIMIT_UP" in str(exc.value)


def test_paper_broker_t1_trading_day_lock(tmp_path: Path):
    cfg = cfg_mod.Config(data_dir=tmp_path)
    broker = PaperBroker(cfg)
    broker.init(100_000.0)

    # 1. 模拟周五买入 (2024-01-05 是周五)
    st = broker._load()
    st["last_date"] = "2024-01-05"
    st["positions"]["600519"] = {
        "shares": 100,
        "cost_total": 1000.0,
        "cost_price": 10.0,
        "locked": 100,
        "opened": "2024-01-05",
    }
    broker._save(st)

    # 2. 周六尝试卖出 (2024-01-06 周六)：未达到交易日，严禁解锁
    broker._rollover_date(st, "2024-01-06")
    assert st["positions"]["600519"]["locked"] == 100

    # 3. 周日尝试卖出 (2024-01-07 周日)：依然锁定
    broker._rollover_date(st, "2024-01-07")
    assert st["positions"]["600519"]["locked"] == 100

    # 4. 下周一 (2024-01-08 周一)：交易日达到，成功解锁 T+1
    broker._rollover_date(st, "2024-01-08")
    assert st["positions"]["600519"]["locked"] == 0

