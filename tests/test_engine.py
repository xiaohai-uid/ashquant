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


def test_backtest_volume_limit_and_impact_slippage():
    df1 = _make_dummy_ohlcv(200)
    data_map = {"600519": df1}

    def loader(s):
        return data_map.get(s)

    # 1. 默认回测（0 滑点，无限制）
    bcfg_base = BacktestConfig(topk=1, rebalance_days=5, fee_enabled=True, initial_cash=100000.0)
    rpt_base = run_backtest(["600519"], loader=loader, bcfg=bcfg_base)

    # 2. 引入流动性冲击滑点与成交量上限
    bcfg_impact = BacktestConfig(
        topk=1, rebalance_days=5, fee_enabled=True, initial_cash=100000.0,
        volume_limit_ratio=0.10, impact_coef=0.03
    )
    rpt_impact = run_backtest(["600519"], loader=loader, bcfg=bcfg_impact)

    assert rpt_impact is not None
    assert len(rpt_impact.trades) > 0
    # 验证交易记录中存在 slippage 记录
    slippage_records = [t.get("slippage", 0.0) for t in rpt_impact.trades]
    assert any(s > 0 for s in slippage_records)
    # 相比理想 0 滑点，考虑微观冲击成本后的净值曲线应更贴近真实或收益受冲击消耗
    assert rpt_impact.metrics["total_return"] != rpt_base.metrics["total_return"]


