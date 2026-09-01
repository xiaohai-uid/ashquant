from test_indicators import _make_dummy_ohlcv

from ashquant.indicators import add_indicators
from ashquant.masters import REGISTRY, compute_master_series, signal_at


def test_all_masters_output_range():
    df = _make_dummy_ohlcv(120)
    ind = add_indicators(df)
    mdf = compute_master_series(ind)

    assert len(mdf.columns) == 5
    for m in REGISTRY:
        assert m.name in mdf.columns
        s = mdf[m.name]
        assert (s >= -1.0 - 1e-9).all() and (s <= 1.0 + 1e-9).all()

    # 验证单点信号提取（带名言与出处）
    as_of = ind.index[-1]
    signals = signal_at(ind, mdf, as_of)
    assert len(signals) == 5
    for sig in signals:
        assert sig.master in [m.name for m in REGISTRY]
        assert sig.quote != ""
        assert sig.source.startswith("http")
