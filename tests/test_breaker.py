from datetime import datetime, timedelta

from ashquant.backtest.breaker import MarketStats, RegimeBreaker
from ashquant.domain import MarketRegime


def test_regime_breaker_market_plunge():
    breaker = RegimeBreaker(index_drop_limit=-0.025, down_ratio_limit=0.80)

    # 常态行情
    normal_stats = MarketStats(up_count=2600, down_count=2400, index_return=0.005)
    assert breaker.evaluate_market(normal_stats) == MarketRegime.NORMAL

    # 指数暴跌熔断 (-3.0%)
    crash_stats = MarketStats(up_count=500, down_count=4500, index_return=-0.032)
    assert breaker.evaluate_market(crash_stats) == MarketRegime.PANIC_CIRCUIT_BROKEN

    # 千股跌停跌家数占比过高熔断 (85% 下跌)
    down_stats = MarketStats(up_count=700, down_count=4300, index_return=-0.018)
    assert breaker.evaluate_market(down_stats) == MarketRegime.PANIC_CIRCUIT_BROKEN


def test_regime_breaker_account_cooldown():
    breaker = RegimeBreaker(consecutive_loss_limit=3, cooldown_hours=24)
    now = datetime(2026, 9, 2, 10, 0, 0)

    assert not breaker.is_account_in_cooldown(now)

    # 连续两次亏损
    breaker.record_trade_result(is_win=False, current_time=now)
    breaker.record_trade_result(is_win=False, current_time=now)
    assert not breaker.is_account_in_cooldown(now)

    # 第三次亏损 -> 触发 24 小时熔断
    breaker.record_trade_result(is_win=False, current_time=now)
    assert breaker.is_account_in_cooldown(now)

    # 12 小时后仍处于冷静期
    assert breaker.is_account_in_cooldown(now + timedelta(hours=12))

    # 25 小时后冷静期解除
    assert not breaker.is_account_in_cooldown(now + timedelta(hours=25))
