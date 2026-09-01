"""CLI 入口（typer + rich）：fetch / watch / backtest / predict / stats / paper / web。"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ashquant import __version__, codes
from ashquant import config as cfg_mod
from ashquant.backtest import BacktestConfig, run_backtest
from ashquant.data import BarStore, resolve_pool
from ashquant.paper import PaperBroker, PaperError
from ashquant.predict import InsufficientDataError, predict_next_day, prediction_stats, settle_expired
from ashquant.quotes import snapshot

app = typer.Typer(
    name="ashquant",
    help="A股本地量化平台：行情查看 / 规则保真回测 / 次日概率预测 / 模拟盘（诚实指标，不构成投资建议）",
    no_args_is_help=True,
)
paper_app = typer.Typer(help="模拟盘交易与持仓管理（T+1/涨跌停/费用校验）")
app.add_typer(paper_app, name="paper")

console = Console()
err_console = Console(stderr=True)


def _store(data_dir: str | None) -> BarStore:
    cfg = cfg_mod.get_config(data_dir)
    return BarStore(cfg.data_dir)


def _emit_json(data):
    # 处理 DataFrame / Series / Timestamp 序列化
    def default(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if hasattr(o, "to_dict"):
            return o.to_dict()
        if hasattr(o, "item"):
            return o.item()
        raise TypeError(f"无法序列化: {type(o)}")

    print(json.dumps(data, ensure_ascii=False, indent=2, default=default))


# ============================================================================
# 基本命令
# ============================================================================


@app.command()
def version():
    """查看版本。"""
    console.print(f"[bold cyan]ashquant[/bold cyan] v{__version__}")


@app.command()
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


@app.command()
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

    # 抓取基准指数
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


@app.command()
def watch(
    symbols: Annotated[str | None, typer.Option("--symbols", "-s", help="逗号分隔股票代码")] = "600519,000001,300750",
    interval: Annotated[int, typer.Option("--interval", "-i", help="刷新间隔秒数")] = 10,
    once: Annotated[bool, typer.Option("--once", help="单次快照后退出")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """查看自选股实时快照（涨跌幅着色）。"""
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


# ============================================================================
# 回测
# ============================================================================


@app.command()
def backtest(
    symbols: Annotated[str | None, typer.Option("--symbols", "-s", help="逗号分隔股票代码")] = None,
    pool_name: Annotated[str, typer.Option("--pool", "-p", help="股票池")] = "sample20",
    start: Annotated[str | None, typer.Option("--start", help="起日 YYYY-MM-DD")] = None,
    end: Annotated[str | None, typer.Option("--end", help="止日 YYYY-MM-DD")] = None,
    topk: Annotated[int, typer.Option("--topk", "-k", help="持仓只数")] = 5,
    rebalance: Annotated[int, typer.Option("--rebalance", "-r", help="调仓周期（交易日）")] = 5,
    max_weight: Annotated[float, typer.Option("--max-weight", "-w", help="单票仓位上限（默认 0.2）")] = 0.2,
    fee: Annotated[bool, typer.Option("--fee/--no-fee", help="是否计入佣金/印花税/过户费")] = True,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    out: Annotated[str | None, typer.Option("--out", "-o", help="结果保存路径 (JSON)")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """运行三年 A股规则保真回测（T+1/涨跌停/费用/基准对照/可审计预测日志）。"""
    sym_list = [codes.normalize_symbol(s) for s in symbols.split(",")] if symbols else resolve_pool(pool_name, None)
    st = _store(data_dir)
    bench_df = st.load_bars("INDEX000300")

    bcfg = BacktestConfig(
        start=start, end=end, topk=topk, rebalance_days=rebalance,
        max_weight=max_weight, fee_enabled=fee,
    )

    try:
        rpt = run_backtest(sym_list, loader=st.load_bars, bcfg=bcfg, benchmark_df=bench_df)
    except Exception as e:
        err_console.print(f"[red]回测失败:[/red] {e}")
        raise typer.Exit(2)

    cost_diff = rpt.metrics.get("cost_sensitivity") if fee else None

    # 保存报告文件
    out_path = Path(out) if out else (Path("results") / f"backtest_{date.today().strftime('%Y%m%d_%H%M%S')}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = {
        "metrics": rpt.metrics,
        "symbols_used": rpt.symbols_used,
        "trades_count": len(rpt.trades),
        "prediction_log_rows": len(rpt.prediction_log),
        "equity_curve": [{"date": str(d.date()), "equity": round(float(v), 2)} for d, v in rpt.equity_curve.items()],
        "st_limitation": rpt.st_limitation,
    }
    out_path.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    if json_out:
        _emit_json(report_dict)
        return

    # 终端展示
    m = rpt.metrics
    t = Table(title=f"回测报告 ({m['n_days']} 个交易日 · {len(rpt.symbols_used)} 只标的)", box=box.ROUNDED)
    t.add_column("指标", style="cyan")
    t.add_column("策略表现", justify="right", style="bold")
    t.add_column("基准(沪深300)", justify="right", style="dim")

    bench_ret = "n/a"
    if rpt.benchmark_curve is not None and len(rpt.benchmark_curve):
        b_total = float(rpt.benchmark_curve.iloc[-1]) / float(rpt.benchmark_curve.iloc[0]) - 1.0
        bench_ret = f"{b_total:+.2%}"

    t.add_row("累计收益率", f"{m['total_return']:+.2%}", bench_ret)
    t.add_row("年化收益率", f"{m['annual_return']:+.2%}", "-")
    t.add_row("最大回撤 (MDD)", f"{m['max_drawdown']:.2%}", "-")
    t.add_row("夏普比率 (rf=1.5%)", f"{m['sharpe']:.2f}", "-")
    if m.get("win_rate") is not None:
        t.add_row("交易胜率 (平仓笔数)", f"{m['win_rate']:.2%} ({len([tr for tr in rpt.trades if tr.get('side')=='SELL'])} 笔)", "-")

    console.print(t)

    # 诚实预测指标
    pt = Table(title="次日预测可审计指标（逐日预测日志对账）", box=box.SIMPLE)
    pt.add_column("项目", style="yellow")
    pt.add_column("数值", justify="right")
    pt.add_row("总预测条数", str(m.get("pred_total", 0)))
    pt.add_row("有方向预测 (剔除观望)", str(m.get("directional", 0)))
    pt.add_row("方向覆盖率", f"{m.get('coverage', 0):.2%}" if m.get("coverage") else "n/a")
    pt.add_row("方向命中率 (全样本)", f"[bold]{m.get('hit_rate', 0):.2%}[/bold]" if m.get("hit_rate") else "n/a")
    if m.get("up_hit"):
        pt.add_row("  - 看多命中率", f"{m['up_hit']:.2%}")
    if m.get("down_hit"):
        pt.add_row("  - 看空命中率", f"{m['down_hit']:.2%}")
    console.print(pt)

    if cost_diff:
        console.print(f"[dim]费用敏感性: 零成本收益 {cost_diff['zero_fee_total_ret']:+.2%} vs 真实成本 {cost_diff['with_fee_total_ret']:+.2%} (摩擦磨损 {cost_diff['fee_drag']:.2%})[/dim]")
    console.print(f"[dim]详细报告已保存至: {out_path}[/dim]")
    console.print(f"[dim yellow]局限声明: {rpt.st_limitation}[/dim yellow]")


# ============================================================================
# 预测
# ============================================================================


@app.command()
def predict(
    symbols: Annotated[str, typer.Argument(help="股票代码（如 600519 或逗号分隔多个）")],
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """对指定标的输出明日走势预测与投资大师观点（诚实概率与置信度）。"""
    sym_list = [codes.normalize_symbol(s) for s in symbols.split(",")]
    st = _store(data_dir)
    cfg = cfg_mod.get_config(data_dir)

    results = []
    for s in sym_list:
        try:
            res = predict_next_day(st, s, cfg=cfg, log=True)
            results.append(res)
        except InsufficientDataError as e:
            err_console.print(f"[yellow]{s}:[/yellow] {e}")
        except Exception as e:
            err_console.print(f"[red]{s} 预测失败:[/red] {e}")

    if not results:
        raise typer.Exit(3)

    if json_out:
        _emit_json(results)
        return

    for r in results:
        dir_color = "red" if r["direction"] == "UP" else ("green" if r["direction"] == "DOWN" else "yellow")
        t = Table(title=f"明日预测: {r['symbol']} (基准日: {r['as_of']})", box=box.ROUNDED)
        t.add_column("项目", style="cyan")
        t.add_column("内容", style="bold")
        t.add_row("预测方向", f"[{dir_color}]{r['direction']}[/{dir_color}]")
        t.add_row("上涨概率 / 置信度", f"{r['prob_up']:.2%} ({r['confidence']})")
        t.add_row("大师综合评分", f"{r['score']:+.4f} (范围 [-1, +1])")
        if r.get("abstain_reason"):
            t.add_row("弃权说明", f"[yellow]{r['abstain_reason']}[/yellow]")
        console.print(t)

        st_table = Table(title=f"{r['symbol']} 大师独立观点", box=box.SIMPLE)
        st_table.add_column("大师", style="bold")
        st_table.add_column("哲学", style="dim")
        st_table.add_column("打分", justify="right")
        st_table.add_column("理由")
        st_table.add_column("出处名言", style="italic dim")
        for s in r["signals"]:
            sc_color = "red" if s["score"] > 0.15 else ("green" if s["score"] < -0.15 else "white")
            st_table.add_row(
                s["master"], s["category"], f"[{sc_color}]{s['score']:+.2f}[/{sc_color}]",
                s["reason"], f"“{s['quote']}”",
            )
        console.print(st_table)
        console.print(f"[dim]{r['note']}[/dim]\n")


@app.command()
def stats(
    min_count: Annotated[int, typer.Option("--min-count", "-m", help="最少已到期样本数")] = 1,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    settle: Annotated[bool, typer.Option("--settle/--no-settle", help="先对账已到期预测")] = True,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """统计历史实时预测的真实命中率与覆盖率（close-to-close 对账）。"""
    st = _store(data_dir)
    cfg = cfg_mod.get_config(data_dir)

    if settle:
        n = settle_expired(st, cfg)
        if n > 0 and not json_out:
            console.print(f"[dim]已对账结算 {n} 条新到期预测...[/dim]")

    try:
        s = prediction_stats(min_count=min_count, cfg=cfg)
    except Exception as e:
        err_console.print(f"[yellow]统计失败:[/yellow] {e}")
        raise typer.Exit(3)

    if json_out:
        _emit_json(s)
        return

    t = Table(title="实时预测历史命中统计 (可审计日志)", box=box.ROUNDED)
    t.add_column("指标", style="cyan")
    t.add_column("数值", justify="right", style="bold")
    t.add_row("总记录条数", str(s["total"]))
    t.add_row("已到期可对账条数", str(s["settled"]))
    t.add_row("有方向预测数", str(s["directional"]))
    t.add_row("方向覆盖率", f"{s['coverage']:.2%}" if s["coverage"] else "n/a")
    t.add_row("真实命中率", f"[bold green]{s['hit_rate']:.2%}[/bold green]" if s["hit_rate"] else "n/a")

    console.print(t)
    if s.get("by_confidence"):
        ct = Table(title="按置信度分层命中率", box=box.SIMPLE)
        ct.add_column("置信层级", style="cyan")
        ct.add_column("样本数", justify="right")
        ct.add_column("命中率", justify="right")
        for b in s["by_confidence"]:
            ct.add_row(b["tier"], str(b["n"]), f"{b['hit_rate']:.2%}")
        console.print(ct)


# ============================================================================
# 模拟盘子命令
# ============================================================================


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
    if not st["positions"]:
        console.print("[dim]当前无持仓[/dim]")
        return

    t = Table(title="当前持仓明细 (T+1 锁定状态)", box=box.ROUNDED)
    t.add_column("代码", style="cyan")
    t.add_column("总持股", justify="right")
    t.add_column("今日可卖", justify="right", style="green")
    t.add_column("成本价", justify="right")
    t.add_column("最新价", justify="right")
    t.add_column("持股市值", justify="right")
    t.add_column("浮动盈亏", justify="right")

    for p in st["positions"]:
        px = f"{p['last_price']:.2f}" if p["last_price"] else "-"
        pnl = f"{p['pnl']:+,.2f}" if p["pnl"] is not None else "-"
        color = "red" if (p["pnl"] or 0) > 0 else ("green" if (p["pnl"] or 0) < 0 else "white")
        t.add_row(
            p["symbol"], str(p["shares"]), str(p["sellable"]),
            f"{p['cost_price']:.2f}", px, f"{p['market_value']:,.2f}",
            f"[{color}]{pnl}[/{color}]",
        )
    console.print(t)


@paper_app.command("buy")
def paper_buy(
    symbol: Annotated[str, typer.Argument(help="股票代码")],
    qty: Annotated[int, typer.Option("--qty", "-q", help="买入股数（必须为 100 的整数倍）")] = 100,
    price: Annotated[float | None, typer.Option("--price", "-p", help="指定成交价（缺省自动拉取当前快照价）")] = None,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """模拟买入股票（规则引擎严格校验整手/资金/涨停）。"""
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

    if px is None:
        err_console.print(f"[red]无法获取 {sym} 有效行情[/red]")
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

    if px is None:
        err_console.print(f"[red]无法获取 {sym} 有效行情[/red]")
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


# ============================================================================
# Web 控制台
# ============================================================================


@app.command()
def web(
    host: Annotated[str, typer.Option("--host", "-h", help="监听地址")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="端口")] = 8000,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
):
    """启动本地 Web 可视化控制台。"""
    try:
        import uvicorn

        from ashquant.web.app import create_app
    except ImportError:
        err_console.print("[red]Web 依赖未安装，请执行: pip install -e '.[web]' 或 uv sync --extra web[/red]")
        raise typer.Exit(1)

    app_instance = create_app(data_dir=data_dir)
    console.print(f"[bold green]正在启动 Web 控制台:[/bold green] http://{host}:{port}")
    console.print("[dim]按 Ctrl+C 停止服务[/dim]")
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


def main():
    app()


if __name__ == "__main__":
    main()
