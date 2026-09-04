import time

from test_indicators import _make_dummy_ohlcv

from ashquant.backtest import BacktestConfig, run_backtest


def test_backtest_performance_sla():
    """回测性能 SLA 基准门禁（对标 Qlib 性能回归测试）：

    防退化断言：5只股票 250 个交易日的完整回测（含指标计算、Alpha因子、大师打分、
    流动性冲击撮合与 Walk-Forward 概率校准）纯计算耗时须稳定在 1.0 秒内。
    """
    symbols = [f"60000{i}" for i in range(5)]
    data_map = {s: _make_dummy_ohlcv(250) for s in symbols}

    def loader(s):
        return data_map.get(s)

    bcfg = BacktestConfig(
        topk=3,
        rebalance_days=5,
        fee_enabled=True,
        volume_limit_ratio=0.15,
        impact_coef=0.02,
        initial_cash=1_000_000.0,
    )

    t0 = time.perf_counter()
    rpt = run_backtest(
        symbols,
        loader=loader,
        bcfg=bcfg,
        flow_loader=lambda _: None,
        compute_cost_sensitivity=False,
    )
    elapsed = time.perf_counter() - t0

    assert rpt is not None
    assert len(rpt.trades) > 0
    # 性能断言：纯计算回测耗时必须在 1.0s 以内（实测 ~0.15s）
    assert elapsed < 1.0, f"回测耗时 {elapsed:.3f}s 超出 1.0s SLA 性能门禁！"
