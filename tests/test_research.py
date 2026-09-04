import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from test_indicators import _make_dummy_ohlcv

from ashquant.data.store import INDEX_KEY, BarStore


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_create_research_snapshot_success(tmp_path: Path):
    data_dir = tmp_path / "source_data"
    store = BarStore(data_dir)

    df_stock1 = _make_dummy_ohlcv(50)
    df_stock2 = _make_dummy_ohlcv(50)
    df_bench = _make_dummy_ohlcv(50)

    store.save_bars("600519", df_stock1)
    store.save_bars("000001", df_stock2)
    store.save_bars(INDEX_KEY, df_bench)

    # Add cached flow for 600519 only
    flow_df = pd.DataFrame(
        {
            "super_large_net_inflow": [100.0] * 50,
            "large_net_inflow": [50.0] * 50,
            "northbound_net_shares": [10.0] * 50,
            "northbound_hold_ratio": [2.0] * 50,
            "margin_balance": [1000.0] * 50,
        },
        index=df_stock1.index.strftime("%Y-%m-%d"),
    )
    flow_df.index.name = "date"
    flow_file = store.alt_dir / "600519_flow.parquet"
    flow_df.to_parquet(flow_file)

    dest = tmp_path / "snapshot"
    manifest = store.create_research_snapshot(["600519", "000001"], dest)

    assert dest.exists()
    assert (dest / "manifest.json").exists()

    assert manifest["schema_version"] == "1.0"
    assert manifest["symbols"] == ["000001", "600519"]
    assert "bars/600519.parquet" in manifest["files"]
    assert "bars/000001.parquet" in manifest["files"]
    assert f"bars/{INDEX_KEY}.parquet" in manifest["files"]
    assert "alternative/600519_flow.parquet" in manifest["files"]
    assert manifest["absent_flow_symbols"] == ["000001"]

    # Verify actual hashes match files in snapshot
    for rel_path, expected_hash in manifest["files"].items():
        assert _sha256(dest / rel_path) == expected_hash


def test_create_research_snapshot_missing_stock_or_benchmark(tmp_path: Path):
    data_dir = tmp_path / "source_data"
    store = BarStore(data_dir)

    df_stock = _make_dummy_ohlcv(50)
    store.save_bars("600519", df_stock)
    # Missing INDEX000300 and 000001
    dest = tmp_path / "snapshot"

    with pytest.raises((ValueError, FileNotFoundError), match="000001"):
        store.create_research_snapshot(["600519", "000001"], dest)

    # Now save 000001, but benchmark is still missing
    store.save_bars("000001", df_stock)
    with pytest.raises((ValueError, FileNotFoundError), match=INDEX_KEY):
        store.create_research_snapshot(["600519", "000001"], dest)


def test_create_research_snapshot_dest_exists(tmp_path: Path):
    data_dir = tmp_path / "source_data"
    store = BarStore(data_dir)
    df = _make_dummy_ohlcv(50)
    store.save_bars("600519", df)
    store.save_bars(INDEX_KEY, df)

    dest = tmp_path / "snapshot"
    dest.mkdir(parents=True, exist_ok=True)

    with pytest.raises((ValueError, FileExistsError)):
        store.create_research_snapshot(["600519"], dest)


def test_load_cached_capital_flow_no_cache(tmp_path: Path):
    data_dir = tmp_path / "source_data"
    store = BarStore(data_dir)

    # Without any flow file created, load_cached_capital_flow must return None
    # and strictly not invoke any online fetch or synthetic flow generation
    result = store.load_cached_capital_flow("600519")
    assert result is None

    # When flow exists, it loads it
    flow_df = pd.DataFrame(
        {"super_large_net_inflow": [10.0]},
        index=pd.Index(["2023-01-03"], name="date"),
    )
    flow_file = store.alt_dir / "600519_flow.parquet"
    flow_df.to_parquet(flow_file)
    cached = store.load_cached_capital_flow("600519")
    assert cached is not None
    assert len(cached) == 1


def test_analyze_stock_flow_loader_injection(monkeypatch):
    import ashquant.strategy as strat
    from ashquant.strategy import analyze_stock

    df = _make_dummy_ohlcv(100)

    # If fetch_capital_flow is called, raise an error
    def _boom(sym):
        raise AssertionError("fetch_capital_flow was called!")

    monkeypatch.setattr(strat, "fetch_capital_flow", _boom)

    # When flow_loader is provided (e.g. returning None), fetch_capital_flow must not be called
    analysis = analyze_stock("600519", df, flow_loader=lambda _: None)
    assert analysis is not None
    assert analysis.symbol == "600519"


def test_run_backtest_flow_loader_fee_sensitivity():
    from ashquant.backtest import BacktestConfig, run_backtest

    df1 = _make_dummy_ohlcv(200)
    df2 = _make_dummy_ohlcv(200)
    data_map = {"600519": df1, "000001": df2}

    def loader(s):
        return data_map.get(s)

    call_log = []

    def tracking_flow_loader(s):
        call_log.append(s)
        return None

    bcfg = BacktestConfig(topk=2, rebalance_days=5, fee_enabled=True, initial_cash=100000.0)
    rpt = run_backtest(["600519", "000001"], loader=loader, bcfg=bcfg, flow_loader=tracking_flow_loader)

    # fee_enabled=True triggers cost sensitivity (2 backtests: fee-on and fee-off)
    # Each backtest analyzes 2 symbols, so tracking_flow_loader should be called 4 times
    assert len(call_log) == 4
    assert call_log == ["000001", "600519", "000001", "600519"]
    assert "cost_sensitivity" in rpt.metrics


def _prepare_snapshot_fixture(tmp_path: Path):
    source_dir = tmp_path / "src_data"
    store = BarStore(source_dir)
    # Generate 300 days of data starting from 2023-01-01
    df_stock = _make_dummy_ohlcv(300)
    df_bench = _make_dummy_ohlcv(300)
    store.save_bars("600519", df_stock)
    store.save_bars(INDEX_KEY, df_bench)

    snap_dir = tmp_path / "snap"
    store.create_research_snapshot(["600519"], snap_dir)
    return snap_dir, df_stock


def test_evaluate_snapshot_window_validation(tmp_path: Path):
    from ashquant.backtest import BacktestConfig
    from ashquant.research import ResearchIntegrityError, ResearchWindow, evaluate_snapshot

    snap_dir, _ = _prepare_snapshot_fixture(tmp_path)
    bcfg = BacktestConfig(topk=1, rebalance_days=5, fee_enabled=False, initial_cash=100000.0)
    git_commit = "a" * 40

    # Wrong window names (not train, validation, test)
    bad_windows = [
        ResearchWindow("w1", "2023-01-01", "2023-03-01"),
        ResearchWindow("w2", "2023-03-02", "2023-06-01"),
        ResearchWindow("w3", "2023-06-02", "2023-09-01"),
    ]
    with pytest.raises(ResearchIntegrityError, match="(?i)window"):
        evaluate_snapshot(snap_dir, bad_windows, bcfg, git_commit)

    # Overlapping windows
    overlap_windows = [
        ResearchWindow("train", "2023-01-01", "2023-04-01"),
        ResearchWindow("validation", "2023-03-15", "2023-06-01"),
        ResearchWindow("test", "2023-06-02", "2023-09-01"),
    ]
    with pytest.raises(ResearchIntegrityError, match="(?i)overlap"):
        evaluate_snapshot(snap_dir, overlap_windows, bcfg, git_commit)

    # Invalid git commit
    valid_windows = [
        ResearchWindow("train", "2023-01-01", "2023-04-01"),
        ResearchWindow("validation", "2023-04-02", "2023-07-01"),
        ResearchWindow("test", "2023-07-02", "2023-10-01"),
    ]
    with pytest.raises(ResearchIntegrityError, match="git_commit"):
        evaluate_snapshot(snap_dir, valid_windows, bcfg, "short_hash")


def test_evaluate_snapshot_hash_verification_and_tamper(tmp_path: Path):
    from ashquant.backtest import BacktestConfig
    from ashquant.research import ResearchIntegrityError, ResearchWindow, evaluate_snapshot

    snap_dir, _ = _prepare_snapshot_fixture(tmp_path)
    bcfg = BacktestConfig(topk=1, rebalance_days=5, fee_enabled=False, initial_cash=100000.0)
    git_commit = "b" * 40
    valid_windows = [
        ResearchWindow("train", "2023-01-01", "2023-04-01"),
        ResearchWindow("validation", "2023-04-02", "2023-07-01"),
        ResearchWindow("test", "2023-07-02", "2023-10-01"),
    ]

    # Tamper with bars/600519.parquet
    target_file = snap_dir / "bars" / "600519.parquet"
    target_file.write_bytes(target_file.read_bytes() + b"\x00")

    with pytest.raises(ResearchIntegrityError, match="[Hh]ash|mismatch"):
        evaluate_snapshot(snap_dir, valid_windows, bcfg, git_commit)


def test_evaluate_snapshot_success_and_determinism(tmp_path: Path):
    from ashquant.backtest import BacktestConfig
    from ashquant.research import (
        ResearchWindow,
        evaluate_snapshot,
        write_research_report,
    )

    snap_dir, _ = _prepare_snapshot_fixture(tmp_path)
    bcfg = BacktestConfig(topk=1, rebalance_days=5, fee_enabled=False, initial_cash=100000.0)
    git_commit = "c" * 40
    # Dates spanning 300 business days: 2023-01-01 to ~2024-02-23
    valid_windows = [
        ResearchWindow("train", "2023-01-01", "2023-05-31"),
        ResearchWindow("validation", "2023-06-01", "2023-09-30"),
        ResearchWindow("test", "2023-10-01", "2024-01-31"),
    ]

    rpt1 = evaluate_snapshot(snap_dir, valid_windows, bcfg, git_commit)
    rpt2 = evaluate_snapshot(snap_dir, valid_windows, bcfg, git_commit)

    assert rpt1 == rpt2
    assert rpt1["schema_version"] == "1.0"
    assert rpt1["research_status"] == "EVALUATED_NOT_APPROVED"
    assert rpt1["git_commit"] == git_commit
    assert "snapshot_manifest_digest" in rpt1
    assert "config" in rpt1
    assert "windows" in rpt1
    assert set(rpt1["windows"].keys()) == {"train", "validation", "test"}

    for name in ["train", "validation", "test"]:
        w = rpt1["windows"][name]
        assert "metrics" in w
        assert "benchmark_total_return" in w
        assert "trades_count" in w
        assert "prediction_log_rows" in w
        assert "symbols_used" in w

    # Test report writing
    out_file1 = tmp_path / "report1.json"
    written1 = write_research_report(rpt1, out_file1)
    assert written1 == out_file1
    assert out_file1.exists()

    # If destination exists, write_research_report must fail
    with pytest.raises(FileExistsError):
        write_research_report(rpt1, out_file1)

    out_file2 = tmp_path / "report2.json"
    write_research_report(rpt2, out_file2)

    assert out_file1.read_text(encoding="utf-8") == out_file2.read_text(encoding="utf-8")


def test_write_research_report_concurrency_race(tmp_path: Path):
    import concurrent.futures

    from ashquant.research import write_research_report

    out_file = tmp_path / "concurrent_report.json"
    results = []

    def _worker(idx):
        try:
            write_research_report({"worker_id": idx}, out_file)
            return ("success", idx)
        except FileExistsError:
            return ("exists_error", idx)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futs = [executor.submit(_worker, i) for i in range(20)]
        results = [f.result() for f in futs]

    successes = sum(1 for r, _ in results if r == "success")
    exists_errors = sum(1 for r, _ in results if r == "exists_error")

    assert successes == 1, f"Expected exactly 1 success, got {successes}"
    assert exists_errors == 19, f"Expected 19 FileExistsErrors, got {exists_errors}"

    # Verify winner content is valid and no temp files are leaked
    winner_content = json.loads(out_file.read_text(encoding="utf-8"))
    assert "worker_id" in winner_content
    temp_files = list(tmp_path.glob(".*.tmp_*"))
    assert len(temp_files) == 0, f"Found leaked temp files: {temp_files}"


def test_write_research_report_no_clobber_race_window(tmp_path: Path, monkeypatch):
    from ashquant.research import write_research_report

    out_file = tmp_path / "race_target.json"

    # Simulate race: right after the initial exists() check passes, another process creates out_file
    orig_path_exists = Path.exists

    def _first_time_false_then_create_and_true(path_obj):
        if path_obj == out_file:
            # First check says does not exist, but we sneakily create it right here
            if not orig_path_exists(path_obj):
                out_file.write_text("pre_existing_data", encoding="utf-8")
                return False
        return orig_path_exists(path_obj)

    monkeypatch.setattr(Path, "exists", _first_time_false_then_create_and_true)

    with pytest.raises(FileExistsError):
        write_research_report({"new_data": 123}, out_file)

    # Must NOT have overwritten pre_existing_data
    assert out_file.read_text(encoding="utf-8") == "pre_existing_data"


def test_research_offline_end_to_end_blocked_socket(tmp_path: Path, monkeypatch):
    import socket

    from typer.testing import CliRunner

    from ashquant.cli import app

    # Globally block any network connection attempts
    def _blocked_connect(*args, **kwargs):
        raise RuntimeError("Network connection strictly forbidden during offline research!")

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)

    data_dir = tmp_path / "offline_data"
    store = BarStore(data_dir)
    df = _make_dummy_ohlcv(200)
    store.save_bars("600519", df)
    store.save_bars(INDEX_KEY, df)

    snap_dir = tmp_path / "offline_snap"
    report_file = tmp_path / "offline_report.json"

    runner = CliRunner()
    res_snap = runner.invoke(
        app,
        [
            "research",
            "snapshot",
            "--symbols",
            "600519",
            "--data-dir",
            str(data_dir),
            "--out",
            str(snap_dir),
        ],
    )
    assert res_snap.exit_code == 0
    assert (snap_dir / "manifest.json").exists()

    res_eval = runner.invoke(
        app,
        [
            "research",
            "evaluate",
            "--snapshot",
            str(snap_dir),
            "--train-start",
            "2023-01-01",
            "--train-end",
            "2023-04-30",
            "--validation-start",
            "2023-05-01",
            "--validation-end",
            "2023-07-31",
            "--test-start",
            "2023-08-01",
            "--test-end",
            "2023-09-30",
            "--out",
            str(report_file),
        ],
    )
    assert res_eval.exit_code == 0
    assert report_file.exists()
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["research_status"] == "EVALUATED_NOT_APPROVED"
    assert "snapshot_manifest_digest" in report



def test_research_cli_snapshot_and_evaluate(tmp_path: Path):
    from typer.testing import CliRunner

    from ashquant.cli import app

    runner = CliRunner()

    # Test --help for research sub-app
    res = runner.invoke(app, ["research", "--help"])
    assert res.exit_code == 0
    assert "snapshot" in res.output
    assert "evaluate" in res.output

    # Prepare data for snapshot
    data_dir = tmp_path / "cli_src"
    store = BarStore(data_dir)
    df = _make_dummy_ohlcv(300)
    store.save_bars("600519", df)
    store.save_bars(INDEX_KEY, df)

    snap_dir = tmp_path / "cli_snap"
    res_snap = runner.invoke(
        app,
        [
            "research",
            "snapshot",
            "--symbols",
            "600519",
            "--data-dir",
            str(data_dir),
            "--out",
            str(snap_dir),
        ],
    )
    assert res_snap.exit_code == 0
    assert (snap_dir / "manifest.json").exists()

    # Test evaluate CLI command
    report_out = tmp_path / "cli_report.json"
    res_eval = runner.invoke(
        app,
        [
            "research",
            "evaluate",
            "--snapshot",
            str(snap_dir),
            "--train-start",
            "2023-01-01",
            "--train-end",
            "2023-05-31",
            "--validation-start",
            "2023-06-01",
            "--validation-end",
            "2023-09-30",
            "--test-start",
            "2023-10-01",
            "--test-end",
            "2024-01-31",
            "--out",
            str(report_out),
        ],
    )
    assert res_eval.exit_code == 0
    assert report_out.exists()
    content = json.loads(report_out.read_text(encoding="utf-8"))
    assert content["research_status"] == "EVALUATED_NOT_APPROVED"
    assert len(content["git_commit"]) == 40


def test_research_cli_evaluate_fails_without_git_commit(tmp_path: Path, monkeypatch):
    import subprocess

    from typer.testing import CliRunner

    from ashquant.cli import app

    runner = CliRunner()

    snap_dir, _ = _prepare_snapshot_fixture(tmp_path)
    report_out = tmp_path / "fail_report.json"

    def _mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git", "rev-parse", "HEAD"])

    monkeypatch.setattr(subprocess, "run", _mock_run)

    res = runner.invoke(
        app,
        [
            "research",
            "evaluate",
            "--snapshot",
            str(snap_dir),
            "--train-start",
            "2023-01-01",
            "--train-end",
            "2023-05-31",
            "--validation-start",
            "2023-06-01",
            "--validation-end",
            "2023-09-30",
            "--test-start",
            "2023-10-01",
            "--test-end",
            "2024-01-31",
            "--out",
            str(report_out),
        ],
    )
    assert res.exit_code != 0
    assert not report_out.exists()




