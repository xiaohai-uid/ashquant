"""可复现研究闸门评估核心模块（Research Integrity Gate）。

遵循 codebase-design 与 ponytail 准则：
- 严格校验研究快照签名与不变量（无泄漏、无未来函数、防篡改）
- 固定三窗口（train、validation、test）同配置回测，严禁参数搜索/调优
- 确定性评估输出，绝不掺入运行时间戳
- 固定标注 research_status = "EVALUATED_NOT_APPROVED"，作为独立可审计证据
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ashquant.backtest import BacktestConfig, run_backtest
from ashquant.data.store import INDEX_KEY, BarStore


class ResearchIntegrityError(ValueError):
    """研究快照完整性或评估规则冲突异常。"""


@dataclass(frozen=True)
class ResearchWindow:
    """研究评估时间窗口。"""

    name: str
    start: str
    end: str


def evaluate_snapshot(
    snapshot_dir: Path | str,
    windows: list[ResearchWindow],
    bcfg: BacktestConfig,
    git_commit: str,
) -> dict:
    """对冻结快照执行确定性三阶段（train/validation/test）回测评估。"""
    # 1. 校验 git_commit 为 40 位 hex
    if not (
        isinstance(git_commit, str)
        and len(git_commit) == 40
        and all(c in "0123456789abcdefABCDEF" for c in git_commit)
    ):
        raise ResearchIntegrityError(
            f"Invalid git_commit: '{git_commit}', must be a 40-character hex string"
        )

    # 2. 校验窗口：必须且仅能为 train, validation, test；按时间递增且互不重叠
    if len(windows) != 3:
        raise ResearchIntegrityError(
            f"Must provide exactly 3 research windows (train, validation, test), got {len(windows)}"
        )

    expected_names = ["train", "validation", "test"]
    actual_names = [w.name for w in windows]
    if actual_names != expected_names:
        raise ResearchIntegrityError(
            f"Windows must be exactly {expected_names} in order, got {actual_names}"
        )

    for w in windows:
        if pd.Timestamp(w.start) > pd.Timestamp(w.end):
            raise ResearchIntegrityError(
                f"Window {w.name} start ({w.start}) is after end ({w.end})"
            )

    if pd.Timestamp(windows[0].end) >= pd.Timestamp(windows[1].start):
        raise ResearchIntegrityError(
            f"train window end ({windows[0].end}) overlaps or touches validation window start ({windows[1].start})"
        )
    if pd.Timestamp(windows[1].end) >= pd.Timestamp(windows[2].start):
        raise ResearchIntegrityError(
            f"validation window end ({windows[1].end}) overlaps or touches test window start ({windows[2].start})"
        )

    # 3. 校验 manifest.json 及快照内全部文件 SHA-256 签名
    snap_path = Path(snapshot_dir)
    manifest_file = snap_path / "manifest.json"
    if not manifest_file.exists():
        raise ResearchIntegrityError(f"Missing manifest.json in snapshot directory: {snap_path}")

    manifest_bytes = manifest_file.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as e:
        raise ResearchIntegrityError(f"Failed to parse manifest.json: {e}") from e

    files_map = manifest.get("files")
    if not isinstance(files_map, dict) or not files_map:
        raise ResearchIntegrityError("manifest.json missing valid 'files' map")

    for rel_path, expected_hash in files_map.items():
        file_path = snap_path / rel_path
        if not file_path.exists():
            raise ResearchIntegrityError(f"File listed in manifest is missing from snapshot: {rel_path}")
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ResearchIntegrityError(
                f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
            )

    # 4. 从快照加载数据并运行三窗口回测
    store = BarStore(snap_path)
    symbols = [s for s in manifest.get("symbols", []) if s != INDEX_KEY]
    bench_df = store.load_bars(INDEX_KEY)
    if bench_df is None or bench_df.empty:
        raise ResearchIntegrityError(f"Benchmark data {INDEX_KEY} missing or empty in snapshot")

    window_results: dict[str, dict] = {}
    for win in windows:
        win_bcfg = dataclasses.replace(bcfg, start=win.start, end=win.end)
        rpt = run_backtest(
            symbols=symbols,
            loader=store.load_bars,
            bcfg=win_bcfg,
            benchmark_df=bench_df,
            flow_loader=store.load_cached_capital_flow,
        )

        bench_ret = 0.0
        if rpt.benchmark_curve is not None and len(rpt.benchmark_curve) >= 2:
            bench_ret = round(
                float(rpt.benchmark_curve.iloc[-1] / rpt.benchmark_curve.iloc[0] - 1.0), 6
            )

        window_results[win.name] = {
            "window": win.name,
            "start": str(win.start),
            "end": str(win.end),
            "metrics": rpt.metrics,
            "benchmark_total_return": bench_ret,
            "trades_count": len(rpt.trades),
            "prediction_log_rows": len(rpt.prediction_log),
            "symbols_used": sorted(rpt.symbols_used),
        }

    cfg_dict = dataclasses.asdict(bcfg)
    for k, v in cfg_dict.items():
        if isinstance(v, (date, datetime)):
            cfg_dict[k] = str(v)

    return {
        "schema_version": "1.0",
        "research_status": "EVALUATED_NOT_APPROVED",
        "snapshot_manifest_digest": manifest_digest,
        "git_commit": git_commit.lower(),
        "config": cfg_dict,
        "windows": window_results,
    }


def write_research_report(report: dict, out: Path | str) -> Path:
    """原子写入研究评估报告；保证真正的 no-clobber 发布，若目标已存在立即抛出 FileExistsError。"""
    out_path = Path(out)
    if out_path.exists():
        raise FileExistsError(f"Output report file already exists: {out_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp_{uuid.uuid4().hex}")

    content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.write_text(content, encoding="utf-8")

    try:
        if os.name == "nt":
            # 在 Windows 上，os.rename 映射到 MoveFile，当目标已存在时强原子拒绝并抛出 FileExistsError
            os.rename(tmp_path, out_path)
        else:
            # 在 POSIX 上，os.link 创建硬链接为原子操作且在目标已存在时抛出 EEXIST/FileExistsError
            os.link(tmp_path, out_path)
            tmp_path.unlink()
    except FileExistsError:
        tmp_path.unlink(missing_ok=True)
        raise FileExistsError(f"Output report file already exists: {out_path}")
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise

    return out_path
