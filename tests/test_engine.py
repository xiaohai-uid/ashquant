from test_indicators import _make_dummy_ohlcv

from ashquant.backtest import BacktestConfig, run_backtest


def test_engine_determinism_and_metrics():
    # 构造两只虚拟标的的日线数据
    df1 = _make_dummy_ohlcv(200)
    df2 = _make_dummy_ohlcv(200)
    data_map = {"600519": df1, "000001": df2}

    def loader(s):
        return data_map.get(s)

    bcfg = BacktestConfig(topk=2, rebalance_days=5, fee_enabled=True, initial_cash=100000.0)

    rpt1 = run_backtest(["600519", "000001"], loader=loader, bcfg=bcfg)
    rpt2 = run_backtest(["600519", "000001"], loader=loader, bcfg=bcfg)

    # 确定性检验：两次回测权益曲线必须完全一致（SC-002）
    assert (rpt1.equity_curve == rpt2.equity_curve).all()

    # 绩效指标完整性
    m = rpt1.metrics
    assert "total_return" in m
    assert "annual_return" in m
    assert "max_drawdown" in m
    assert "sharpe" in m
    assert "pred_total" in m
    assert "cost_sensitivity" in m
    assert "fee_drag" in m["cost_sensitivity"]
    assert "zero_fee_total_ret" in m["cost_sensitivity"]

    # 预测日志对账存在
    assert len(rpt1.prediction_log) > 0
    assert "prob_up" in rpt1.prediction_log.columns
    assert "hit" in rpt1.prediction_log.columns


def test_run_backtest_custom_flow_loader():
    df1 = _make_dummy_ohlcv(200)
    data_map = {"600519": df1}

    def loader(s):
        return data_map.get(s)

    flows_loaded = []

    def dummy_flow(s):
        flows_loaded.append(s)
        return None

    bcfg = BacktestConfig(topk=1, rebalance_days=5, fee_enabled=False, initial_cash=100000.0)
    rpt = run_backtest(["600519"], loader=loader, bcfg=bcfg, flow_loader=dummy_flow)
    assert rpt is not None
    assert "600519" in flows_loaded

