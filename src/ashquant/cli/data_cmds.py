"""CLI 数据与股票池命令子模块。"""

from __future__ import annotations

import json
from datetime import date
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ashquant import codes
from ashquant import config as cfg_mod
from ashquant.data import BarStore, resolve_pool

data_app = typer.Typer(help="行情数据拉取与股票池管理")
console = Console()
err_console = Console(stderr=True)


def _store(data_dir: str | None) -> BarStore:
    cfg = cfg_mod.get_config(data_dir)
    return BarStore(cfg.data_dir)


def _emit_json(data):
    def default(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if hasattr(o, "to_dict"):
            return o.to_dict()
        if hasattr(o, "item"):
            return o.item()
        raise TypeError(f"无法序列化: {type(o)}")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=default))


@data_app.command("pool")
def pool(
    name: Annotated[str, typer.Option("--name", "-n", help="股票池: sample20 / csi300")] = "sample20",
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """列出股票池成分。"""
    try:
        syms = resolve_pool(name, None)
    except Exception as e:
        err_console.print(f"[red]获取股票池失败:[/red] {e}")
        raise typer.Exit(2)
    if json_out:
        _emit_json({"pool": name, "count": len(syms), "symbols": syms})
        return
    t = Table(title=f"股票池: {name}（共 {len(syms)} 只）", box=box.SIMPLE_HEAVY)
    t.add_column("#", justify="right", style="dim")
    t.add_column("代码", style="cyan")
    t.add_column("板块", style="yellow")
    for i, s in enumerate(syms, 1):
        t.add_row(str(i), s, codes.board_of(s))
    console.print(t)


@data_app.command("fetch")
def fetch(
    symbols: Annotated[str | None, typer.Option("--symbols", "-s", help="逗号分隔股票代码")] = None,
    pool_name: Annotated[str, typer.Option("--pool", "-p", help="股票池: sample20 / csi300")] = "sample20",
    years: Annotated[int, typer.Option("--years", "-y", help="回溯年数（默认 3 年）")] = 3,
    start: Annotated[str | None, typer.Option("--start", help="起日 YYYYMMDD")] = None,
    end: Annotated[str | None, typer.Option("--end", help="止日 YYYYMMDD")] = None,
    force: Annotated[bool, typer.Option("--force", help="强制覆盖已有缓存")] = False,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """抓取日线数据并落地本地 parquet 缓存（断点续抓）。"""
    sym_list = [s.strip() for s in symbols.split(",")] if symbols else resolve_pool(pool_name, None)
    st = _store(data_dir)
    end_s = end or date.today().strftime("%Y%m%d")
    if not start:
        start_d = date.today().replace(year=date.today().year - years)
        start_s = start_d.strftime("%Y%m%d")
    else:
        start_s = start

    if not json_out:
        console.print(f"开始抓取 {len(sym_list)} 只标的日线（{start_s} ~ {end_s}，跳过已有={not force}）...")

    def on_prog(s, status):
        if not json_out:
            color = "green" if status == "ok" else ("yellow" if status == "cached" else "red")
            console.print(f"  [{color}]{s:6s}[/{color}] -> {status}")

    results = st.refresh_bars(sym_list, start=start_s, end=end_s, skip_existing=not force, on_progress=on_prog)

    try:
        st.ensure_index("000300", start=start_s)
        results["000300(沪深300)"] = "ok"
    except Exception as e:
        results["000300(沪深300)"] = f"error: {e}"

    ok_n = sum(1 for v in results.values() if v in ("ok", "cached"))
    err_n = len(results) - ok_n

    if json_out:
        _emit_json({"total": len(results), "success": ok_n, "failed": err_n, "results": results})
    else:
        console.print(f"\n[bold green]抓取完成:[/bold green] 成功/已有 {ok_n}，失败 {err_n}")
    if err_n > 0 and ok_n == 0:
        raise typer.Exit(2)
