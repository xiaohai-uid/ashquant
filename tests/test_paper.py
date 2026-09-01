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
