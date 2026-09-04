"""CLI 研究闸门命令子模块 (ashquant research snapshot / evaluate)。"""

from __future__ import annotations

import subprocess
from typing import Annotated

import typer
from rich.console import Console

from ashquant import codes
from ashquant.backtest import BacktestConfig
from ashquant.data.store import BarStore
from ashquant.research import (
    ResearchWindow,
    evaluate_snapshot,
    write_research_report,
)

research_app = typer.Typer(help="可复现研究闸门：冻结输入快照与确定性三阶段评估")
console = Console()
err_console = Console(stderr=True)


@research_app.command("snapshot")
def snapshot_cmd(
    symbols: Annotated[str, typer.Option("--symbols", help="逗号分隔的股票代码列表")],
    data_dir: Annotated[str, typer.Option("--data-dir", help="本地市场数据目录")],
    out: Annotated[str, typer.Option("--out", help="快照输出目标目录")],
):
    """创建只读研究输入快照并生成 SHA-256 签名清单。"""
    sym_list = [codes.normalize_symbol(s.strip()) for s in symbols.split(",") if s.strip()]
    if not sym_list:
        err_console.print("[red]错误: 未指定任何有效股票代码[/red]")
        raise typer.Exit(1)

    store = BarStore(data_dir)
    try:
        manifest = store.create_research_snapshot(sym_list, out)
        console.print(f"[bold green]快照创建成功:[/bold green] {out}")
        console.print(f"包含标的: {manifest['symbols']}")
        console.print(f"签名文件数: {len(manifest['files'])}")
        if manifest["absent_flow_symbols"]:
            console.print(f"[yellow]未缓存资金流标的: {manifest['absent_flow_symbols']}[/yellow]")
    except Exception as e:
        err_console.print(f"[red]创建快照失败: {e}[/red]")
        raise typer.Exit(1)


@research_app.command("evaluate")
def evaluate_cmd(
    snapshot: Annotated[str, typer.Option("--snapshot", help="研究快照目录路径")],
    train_start: Annotated[str, typer.Option("--train-start", help="训练窗口起始日期 (YYYY-MM-DD)")],
    train_end: Annotated[str, typer.Option("--train-end", help="训练窗口结束日期 (YYYY-MM-DD)")],
    validation_start: Annotated[str, typer.Option("--validation-start", help="验证窗口起始日期 (YYYY-MM-DD)")],
    validation_end: Annotated[str, typer.Option("--validation-end", help="验证窗口结束日期 (YYYY-MM-DD)")],
    test_start: Annotated[str, typer.Option("--test-start", help="测试窗口起始日期 (YYYY-MM-DD)")],
    test_end: Annotated[str, typer.Option("--test-end", help="测试窗口结束日期 (YYYY-MM-DD)")],
    out: Annotated[str, typer.Option("--out", help="评估报告输出 JSON 文件路径")],
):
    """对冻结快照执行确定性三阶段回测评估，并生成签名报告。"""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_commit = res.stdout.strip()
    except Exception as e:
        err_console.print(f"[red]获取 Git 提交号失败 (git rev-parse HEAD): {e}[/red]")
        raise typer.Exit(1)

    if len(git_commit) != 40:
        err_console.print(f"[red]获取到的 Git 提交号不是 40 位: '{git_commit}'[/red]")
        raise typer.Exit(1)

    windows = [
        ResearchWindow("train", train_start, train_end),
        ResearchWindow("validation", validation_start, validation_end),
        ResearchWindow("test", test_start, test_end),
    ]

    bcfg = BacktestConfig()
    try:
        report = evaluate_snapshot(snapshot, windows, bcfg, git_commit)
        out_path = write_research_report(report, out)
        console.print(f"[bold green]研究评估完成:[/bold green] 报告已保存至 {out_path}")
        console.print(f"状态: {report['research_status']}")
        console.print(f"Git Commit: {report['git_commit']}")
        console.print(f"快照签名: {report['snapshot_manifest_digest']}")
    except Exception as e:
        err_console.print(f"[red]研究评估失败: {e}[/red]")
        raise typer.Exit(1)
