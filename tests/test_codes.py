import pytest

from ashquant.codes import (
    BSE,
    GEM,
    MAIN,
    STAR,
    board_of,
    is_st_name,
    limit_pct,
    limit_prices,
    normalize_symbol,
)


def test_normalize_symbol():
    assert normalize_symbol("600519") == "600519"
    assert normalize_symbol("sh600519") == "600519"
    assert normalize_symbol("600519.SH") == "600519"
    assert normalize_symbol("sz000001") == "000001"
    assert normalize_symbol("300750.SZ") == "300750"
    with pytest.raises(ValueError):
        normalize_symbol("invalid")


def test_board_classification():
    assert board_of("600519") == MAIN
    assert board_of("000001") == MAIN
    assert board_of("300750") == GEM
    assert board_of("688981") == STAR
    assert board_of("830001") == BSE
    assert board_of("920001") == BSE


def test_limit_pct_and_st_switch_date():
    # 创业板/科创板固定 20%
    assert limit_pct("300750") == 0.20
    assert limit_pct("688981") == 0.20
    assert limit_pct("830001") == 0.30

    # 主板非 ST 固定 10%
    assert limit_pct("600519", is_st=False) == 0.10

    # 主板 ST：2026-07-06 规则切换（5% -> 10%）
    assert limit_pct("600519", is_st=True, on="2026-07-05") == 0.05
    assert limit_pct("600519", is_st=True, on="2026-07-06") == 0.10
    assert limit_pct("600519", is_st=True, on="2026-08-01") == 0.10


def test_limit_prices_rounding():
    # 10.00 元的 10% 涨跌停
    up, down = limit_prices(10.00, 0.10)
    assert up == 11.00
    assert down == 9.00

    # 10.55 元的 10% 涨跌停（四舍五入到分）
    up, down = limit_prices(10.55, 0.10)
    assert up == 11.61
    assert down == 9.50


def test_is_st_name():
    assert is_st_name("*ST贵人") is True
    assert is_st_name("ST美芝") is True
    assert is_st_name("贵州茅台") is False
