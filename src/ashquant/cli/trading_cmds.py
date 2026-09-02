"""CLI 模拟盘与实盘交易命令子模块。"""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ashquant import codes
from ashquant import config as cfg_mod
from ashquant.paper import PaperBroker, PaperError
from ashquant.quotes import snapshot

trading_app = typer.Typer(help="模拟盘交易与实时行情盯盘")
paper_app = typer.Typer(help="模拟盘持仓与订单管理")
trading_app.add_typer(paper_app, name="paper")

console = Console()
err_console = Console(stderr=True)


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


@trading_app.command("watch")
def watch(
    symbols: Annotated[str | None, typer.Option("--symbols", "-s", help="逗号分隔股票代码")] = "600519,000001,300750",
    interval: Annotated[int, typer.Option("--interval", "-i", help="刷新间隔秒数")] = 10,
    once: Annotated[bool, typer.Option("--once", help="单次快照后退出")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """查看自选股实时快照（涨跌幅着色）。"""
    import time
    sym_list = [codes.normalize_symbol(s) for s in symbols.split(",")]

    def render_once() -> list[dict]:
        quotes = snapshot(sym_list)
        if json_out:
            _emit_json({"quotes": [q.__dict__ for q in quotes]})
            return [q.__dict__ for q in quotes]
        t = Table(title=f"A股实时快照 ({quotes[0].fetched_at} · {quotes[0].market_state})", box=box.ROUNDED)
        t.add_column("代码", style="cyan")
        t.add_column("名称", style="bold")
        t.add_column("现价", justify="right")
        t.add_column("涨跌额", justify="right")
        t.add_column("涨跌幅", justify="right")
        t.add_column("昨收", justify="right", style="dim")
        t.add_column("状态", style="dim")
        for q in quotes:
            px = f"{q.price:.2f}" if q.price is not None else "n/a"
            chg = f"{q.change:+.2f}" if q.change is not None else "n/a"
            pct = f"{q.pct_chg:+.2f}%" if q.pct_chg is not None else "n/a"
            prev = f"{q.prev_close:.2f}" if q.prev_close is not None else "n/a"
            color = "red" if (q.pct_chg or 0) > 0 else ("green" if (q.pct_chg or 0) < 0 else "white")
            t.add_row(q.symbol, q.name or "-", px, f"[{color}]{chg}[/{color}]", f"[{color}]{pct}[/{color}]", prev, q.market_state)
        console.clear()
        console.print(t)
        return [q.__dict__ for q in quotes]

    try:
        if once or json_out:
            render_once()
            return
        console.print("[dim]按 Ctrl+C 退出刷新...[/dim]")
        while True:
            render_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        err_console.print(f"[red]快照获取失败:[/red] {e}")
        raise typer.Exit(2)


@paper_app.command("init")
def paper_init(
    cash: Annotated[float, typer.Option("--cash", "-c", help="初始虚拟资金")] = 1_000_000.0,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """初始化模拟账户资金。"""
    cfg = cfg_mod.get_config(data_dir)
    broker = PaperBroker(cfg)
    st = broker.init(cash)
    if json_out:
        _emit_json(st)
    else:
        console.print(f"[bold green]模拟账户已初始化:[/bold green] 资金 {st['cash']:,.2f} 元 (数据目录: {cfg.data_dir})")


@paper_app.command("show")
def paper_show(
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """查看模拟账户持仓、现金与总资产。"""
    cfg = cfg_mod.get_config(data_dir)
    broker = PaperBroker(cfg)
    try:
        raw_st = broker._load()
    except PaperError as e:
        err_console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(4)

    syms = list(raw_st.get("positions", {}).keys())
    prices = {}
    if syms:
        try:
            quotes = snapshot(syms)
            prices = {q.symbol: {"price": q.price, "name": q.name} for q in quotes}
        except Exception:
            pass

    st = broker.show(prices)
    if json_out:
        _emit_json(st)
        return

    console.print(f"[bold]总资产:[/bold] {st['equity']:,.2f} 元  |  [bold]可用资金:[/bold] {st['cash']:,.2f} 元  |  [bold]持股市值:[/bold] {st['market_value']:,.2f} 元")


@paper_app.command("buy")
def paper_buy(
    symbol: Annotated[str, typer.Argument(help="股票代码")],
    qty: Annotated[int, typer.Option("--qty", "-q", help="买入股数（必须为 100 的整数倍）")] = 100,
    price: Annotated[float | None, typer.Option("--price", "-p", help="指定成交价（缺省自动拉取当前快照价）")] = None,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """模拟买入股票（规则引擎严格校验整手/资金/涨停/熔断）。"""
    sym = codes.normalize_symbol(symbol)
    cfg = cfg_mod.get_config(data_dir)
    broker = PaperBroker(cfg)

    px = price
    pc = None
    name = ""
    if px is None:
        try:
            q = snapshot([sym])[0]
            px = q.price
            pc = q.prev_close
            name = q.name or ""
        except Exception as e:
            err_console.print(f"[red]获取 {sym} 实时价失败:[/red] {e}")
            raise typer.Exit(2)

    try:
        res = broker.buy(sym, qty, px, name=name, prev_close=pc)
    except PaperError as e:
        err_console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(4)

    if json_out:
        _emit_json(res)
    else:
        fees_total = sum(res["fees"].values())
        console.print(f"[bold green]买入成交:[/bold green] {sym} {res['qty']} 股 @ {res['price']:.2f} 元 (费用 {fees_total:.2f} 元)，剩余资金 {res['cash_left']:,.2f} 元")


@paper_app.command("sell")
def paper_sell(
    symbol: Annotated[str, typer.Argument(help="股票代码")],
    qty: Annotated[int, typer.Option("--qty", "-q", help="卖出股数")] = 100,
    price: Annotated[float | None, typer.Option("--price", "-p", help="指定成交价（缺省自动拉取当前快照价）")] = None,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """模拟卖出股票（T+1 校验：当日买入不可卖；跌停无法成交）。"""
    sym = codes.normalize_symbol(symbol)
    cfg = cfg_mod.get_config(data_dir)
    broker = PaperBroker(cfg)

    px = price
    pc = None
    name = ""
    if px is None:
        try:
            q = snapshot([sym])[0]
            px = q.price
            pc = q.prev_close
            name = q.name or ""
        except Exception as e:
            err_console.print(f"[red]获取 {sym} 实时价失败:[/red] {e}")
            raise typer.Exit(2)

    try:
        res = broker.sell(sym, qty, px, name=name, prev_close=pc)
    except PaperError as e:
        err_console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(4)

    if json_out:
        _emit_json(res)
    else:
        fees_total = sum(res["fees"].values())
        pnl_color = "red" if (res["pnl"] or 0) > 0 else "green"
        console.print(
            f"[bold green]卖出成交:[/bold green] {sym} {res['qty']} 股 @ {res['price']:.2f} 元 "
            f"(费用 {fees_total:.2f} 元)，盈亏 [{pnl_color}]{res['pnl']:+,.2f}[/{pnl_color}] 元，"
            f"账户现金 {res['cash']:,.2f} 元"
        )


@paper_app.command("export")
def paper_export(
    out: Annotated[str, typer.Option("--out", "-o", help="输出 CSV 路径")] = "results/paper_trades.csv",
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
):
    """导出模拟盘交易流水对账单。"""
    cfg = cfg_mod.get_config(data_dir)
    broker = PaperBroker(cfg)
    try:
        p = broker.export(out)
        console.print(f"[bold green]对账单已导出至:[/bold green] {p}")
    except PaperError as e:
        err_console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(4)
