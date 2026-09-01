from pathlib import Path

import pytest
from test_indicators import _make_dummy_ohlcv

from ashquant import config as cfg_mod
from ashquant.data import BarStore
from ashquant.predict import InsufficientDataError, predict_next_day, prediction_stats


def test_predict_and_stats(tmp_path: Path):
    cfg = cfg_mod.Config(data_dir=tmp_path)
    store = BarStore(tmp_path)

    # 数据不足 (<120 根) 抛异常
    df_short = _make_dummy_ohlcv(50)
    store.save_bars("000001", df_short)
    with pytest.raises(InsufficientDataError):
        predict_next_day(store, "000001", cfg=cfg)

    # 数据充足 (150 根) 正常预测
    df_long = _make_dummy_ohlcv(150)
    store.save_bars("600519", df_long)
    res = predict_next_day(store, "600519", cfg=cfg, log=True)
    assert res["direction"] in ("UP", "DOWN", "NEUTRAL")
    assert 0.0 <= res["prob_up"] <= 1.0
    assert len(res["signals"]) == 5

    # 预测日志已落地并包含特征与信号快照
    log_file = tmp_path / "predictions.jsonl"
    assert log_file.exists()
    import json
    entries = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert "features_snapshot" in entries[0]
    assert "signals_summary" in entries[0]
    assert entries[0]["features_snapshot"]["close"] > 0
    assert len(entries[0]["signals_summary"]) == 5

    # 统计 (样本过少抛异常，体现诚实指标原则)
    with pytest.raises(InsufficientDataError):
        prediction_stats(min_count=5, cfg=cfg)
