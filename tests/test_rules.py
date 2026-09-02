from ashquant.backtest.rules import (
    DEFERRED,
    FILLED,
    INSUFFICIENT_CASH,
    LIMIT_DOWN,
    LIMIT_UP,
    ODD_LOT,
    REJECTED,
    T1_LOCK,
    MarketRules,
)


def test_fees_calculation():
    # 默认费用：佣金万2.5（最低5元）、印花税卖0.05%、过户费0.001%
    rules = MarketRules()

    # 买 1000 元：佣金应触底 5 元，无印花，过户 0.01 元
    b_fees = rules.fees("BUY", 1000.0)
    assert b_fees["commission"] == 5.0
    assert b_fees["stamp"] == 0.0
    assert b_fees["transfer"] == 0.01
    assert rules.total_fees("BUY", 1000.0) == 5.01

    # 卖 100000 元：佣金 25 元，印花 50 元，过户 1 元
    s_fees = rules.fees("SELL", 100000.0)
    assert s_fees["commission"] == 25.0
    assert s_fees["stamp"] == 50.0
    assert s_fees["transfer"] == 1.0
    assert rules.total_fees("SELL", 100000.0) == 76.0


def test_buy_limit_up_rejected():
    rules = MarketRules()
    # 昨收 10.0，开盘直接 11.00（主板 10% 涨停）-> 涨停买不进
    res = rules.buy("600519", False, "2024-01-02", 11.00, 10.00, 100, 10000.0)
    assert res.status == REJECTED
    assert res.note == LIMIT_UP


def test_buy_odd_lot_and_cash():
    rules = MarketRules()
    # 非 100 整数倍买单拒绝
    assert rules.buy("600519", False, "2024-01-02", 10.0, 10.0, 150, 10000.0).note == ODD_LOT
    # 资金不足拒绝
    assert rules.buy("600519", False, "2024-01-02", 100.0, 100.0, 100, 500.0).note == INSUFFICIENT_CASH


def test_sell_t1_and_limit_down():
    rules = MarketRules()
    # T+1 锁定（今日买入未解冻）-> 拒绝
    res = rules.sell("600519", False, "2024-01-02", 10.0, 10.0, 100, held_shares=100, sellable_shares=0)
    assert res.status == REJECTED
    assert res.note == T1_LOCK

    # 跌停开盘（昨收 10.0，开盘 9.0）-> 顺延 DEFERRED
    res_down = rules.sell("600519", False, "2024-01-02", 9.00, 10.00, 100, held_shares=100, sellable_shares=100)
    assert res_down.status == DEFERRED
    assert res_down.note == LIMIT_DOWN

    # 正常卖出
    res_ok = rules.sell("600519", False, "2024-01-02", 9.50, 10.00, 100, held_shares=100, sellable_shares=100)
    assert res_ok.status == FILLED
    assert res_ok.price == 9.50


def test_market_context_deep_interface():
    from ashquant.domain import MarketContext
    rules = MarketRules()

    # 使用 MarketContext 封装进行买卖撮合
    ctx = MarketContext(symbol="600519", trade_date="2024-01-02", price=10.0, prev_close=10.0, is_st=False)
    res_buy = rules.buy_context(ctx, qty=100, cash=5000.0)
    assert res_buy.status == FILLED

    res_sell = rules.sell_context(ctx, qty=100, held_shares=100, sellable_shares=100)
    assert res_sell.status == FILLED
