#!/usr/bin/env python3
"""可复现研究闸门端到端验收 Smoke 脚本 (scripts/smoke_research.py)。

遵循项目 D8 架构准则（specs/001-quant-platform/research.md:66）：
- 全流程离线闭环，不触碰任何外部网络
- 验证 snapshot -> evaluate 完整生命周期
- 验证双次执行严格确定性（byte-for-byte 完全一致）
- 验证篡改阻断门禁
- 验收产物落盘至 results/ 目录（作为真实验收证据）
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ashquant.backtest import BacktestConfig
from ashquant.data.store import INDEX_KEY, BarStore
from ashquant.research import (
    ResearchIntegrityError,
    ResearchWindow,
    evaluate_snapshot,
    write_research_report,
)


def _make_realistic_ohlcv(n: int = 350, seed: int = 42) -> pd.DataFrame:
    """生成具备真实特征的时序日线行情（严格无未来函数）。"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    ret = rng.normal(0.0006, 0.018, n)
    c = 100.0 * np.cumprod(1 + ret)
    h = c * (1 + np.abs(rng.normal(0, 0.01, n)))
    l = c * (1 - np.abs(rng.normal(0, 0.01, n)))
    o = l + (h - l) * rng.uniform(0.2, 0.8, n)
    v = rng.uniform(1e5, 1e6, n)
    amt = c * v
    return pd.DataFrame(
        {"open": o, "high": h, "low": l, "close": c, "volume": v, "amount": amt},
        index=dates,
    )


def run_smoke() -> dict:
    # 1. 离线门禁：断开网络套接字，确保全流程零网络请求
    orig_connect = socket.socket.connect

    def _fail_on_network(*args, **kwargs):
        raise RuntimeError("Smoke 验收严重告警：检测到网络连接尝试！")

    socket.socket.connect = _fail_on_network

    repo_root = Path(__file__).resolve().parent.parent
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    smoke_workspace = results_dir / ".smoke_workspace"
    if smoke_workspace.exists():
        shutil.rmtree(smoke_workspace)
    smoke_workspace.mkdir(parents=True, exist_ok=True)

    try:
        print("[Smoke] 1. 准备本地基准与个股行情数据...")
        data_dir = smoke_workspace / "data"
        store = BarStore(data_dir)

        df_600519 = _make_realistic_ohlcv(350, seed=100)
        df_000001 = _make_realistic_ohlcv(350, seed=200)
        df_bench = _make_realistic_ohlcv(350, seed=300)

        store.save_bars("600519", df_600519)
        store.save_bars("000001", df_000001)
        store.save_bars(INDEX_KEY, df_bench)

        # 为 600519 注入本地资金流缓存
        flow_df = pd.DataFrame(
            {
                "super_large_net_inflow": np.linspace(1e5, 5e5, 350),
                "large_net_inflow": np.linspace(5e4, 2e5, 350),
                "northbound_net_shares": np.linspace(1e4, 5e4, 350),
                "northbound_hold_ratio": np.linspace(2.0, 5.0, 350),
                "margin_balance": np.linspace(1e7, 2e7, 350),
            },
            index=df_600519.index.strftime("%Y-%m-%d"),
        )
        flow_df.index.name = "date"
        flow_file = store.alt_dir / "600519_flow.parquet"
        flow_df.to_parquet(flow_file)

        print("[Smoke] 2. 创建冻结研究快照...")
        snap_dir = smoke_workspace / "snapshot"
        manifest = store.create_research_snapshot(["600519", "000001"], snap_dir)
        assert (snap_dir / "manifest.json").exists()
        assert len(manifest["files"]) >= 5
        print(f"  快照清单文件数: {len(manifest['files'])}, 包含标的: {manifest['symbols']}")

        print("[Smoke] 3. 执行三阶段确定性研究评估...")
        windows = [
            ResearchWindow("train", "2023-01-01", "2023-05-31"),
            ResearchWindow("validation", "2023-06-01", "2023-09-30"),
            ResearchWindow("test", "2023-10-01", "2024-03-31"),
        ]
        # 启用 A 股微观流动性冲击滑点与成交量上限（对标 Qlib / RQAlpha）
        bcfg = BacktestConfig(
            topk=2,
            rebalance_days=5,
            fee_enabled=True,
            volume_limit_ratio=0.20,
            impact_coef=0.02,
            initial_cash=1000000.0,
        )

        import subprocess
        git_res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        commit_id = git_res.stdout.strip()

        report1 = evaluate_snapshot(snap_dir, windows, bcfg, commit_id)
        report2 = evaluate_snapshot(snap_dir, windows, bcfg, commit_id)

        print("[Smoke] 4. 严格确定性核验 (两次评估输出必须 100% 一致)...")
        assert report1 == report2, "确定性失败：相同快照与参数产生不同报告！"
        assert report1["research_status"] == "EVALUATED_NOT_APPROVED"
        assert report1["git_commit"] == commit_id
        print(f"  状态: {report1['research_status']}")
        print(f"  Git 提交号: {report1['git_commit']}")
        print(f"  快照摘要: {report1['snapshot_manifest_digest']}")

        print("[Smoke] 5. 写入报告产物至 results/...")
        final_report_path = results_dir / "research_report.json"
        if final_report_path.exists():
            final_report_path.unlink()
        write_research_report(report1, final_report_path)
        assert final_report_path.exists()

        # 验证并发 no-clobber：目标存在时必须抛出 FileExistsError
        try:
            write_research_report(report1, final_report_path)
            raise AssertionError("未抛出 FileExistsError：no-clobber 防覆盖失效！")
        except FileExistsError:
            print("  [OK] 并发与重复写入保护生效：成功拒绝覆盖已有报告文件。")

        print("[Smoke] 6. 验证篡改检测门禁...")
        tamper_target = snap_dir / "bars" / "000001.parquet"
        orig_bytes = tamper_target.read_bytes()
        tamper_target.write_bytes(orig_bytes + b"\xff\xfe")
        try:
            evaluate_snapshot(snap_dir, windows, bcfg, commit_id)
            raise AssertionError("篡改数据未被检出：完整性门禁失效！")
        except ResearchIntegrityError as e:
            print(f"  [OK] 篡改被成功阻断: {e}")
        finally:
            tamper_target.write_bytes(orig_bytes)

        summary = {
            "smoke_status": "PASSED",
            "git_commit": commit_id,
            "research_status": report1["research_status"],
            "snapshot_manifest_digest": report1["snapshot_manifest_digest"],
            "windows": {k: {"benchmark_total_return": v["benchmark_total_return"], "trades_count": v["trades_count"]} for k, v in report1["windows"].items()},
            "artifacts": [
                final_report_path.relative_to(repo_root).as_posix(),
            ],
        }

        summary_path = results_dir / "smoke_summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Smoke] 验收成功，生成真实验收报告: {final_report_path} 及汇总: {summary_path}")
        return summary

    finally:
        socket.socket.connect = orig_connect
        if smoke_workspace.exists():
            shutil.rmtree(smoke_workspace, ignore_errors=True)


if __name__ == "__main__":
    try:
        res = run_smoke()
        print("\n=== SMOKE ACCEPTANCE PASSED ===")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Smoke ERROR] 验收失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
