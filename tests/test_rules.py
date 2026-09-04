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


def test_volume_limit_truncation():
    from ashquant.domain import MarketContext
    # 限制单笔/单日最多吸收 10% 流动性
    rules = MarketRules(volume_limit_ratio=0.1)

    # 1. 当日总成交量 1000 股，10% 对应 100 股。若委托 500 股，应截断为 100 股成交
    ctx = MarketContext(symbol="600519", trade_date="2024-01-02", price=10.0, prev_close=10.0, is_st=False, volume=1000)
    res_buy = rules.buy_context(ctx, qty=500, cash=50000.0)
    assert res_buy.status == FILLED
    assert res_buy.qty == 100

    # 2. 当日总成交量 500 股，10% 对应 50 股，不足整手（100股），应拒绝
    ctx_low = MarketContext(symbol="600519", trade_date="2024-01-02", price=10.0, prev_close=10.0, is_st=False, volume=500)
    res_low = rules.buy_context(ctx_low, qty=100, cash=50000.0)
    assert res_low.status == REJECTED
    assert res_low.qty == 0


def test_square_root_impact_slippage():
    from ashquant.domain import MarketContext
    # 启用平方根冲击滑点：impact_coef = 0.04
    rules = MarketRules(impact_coef=0.04)

    # volume = 10000, qty = 2500 -> sqrt(2500 / 10000) = 0.5
    # delta_p = 10.0 * 0.04 * 0.5 = 0.20
    ctx = MarketContext(symbol="600519", trade_date="2024-01-02", price=10.0, prev_close=10.0, is_st=False, volume=10000)

    # 买入：价格上浮 0.20，成交价 10.20
    res_buy = rules.buy_context(ctx, qty=2500, cash=50000.0)
    assert res_buy.status == FILLED
    assert round(res_buy.price, 4) == 10.20
    assert round(res_buy.slippage_cost, 2) == round(0.20 * 2500, 2)

    # 卖出：价格下浮 0.20，成交价 9.80
    res_sell = rules.sell_context(ctx, qty=2500, held_shares=2500, sellable_shares=2500)
    assert res_sell.status == FILLED
    assert round(res_sell.price, 4) == 9.80
    assert round(res_sell.slippage_cost, 2) == round(0.20 * 2500, 2)

