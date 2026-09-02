"""CLI 策略分析、多空辩论与预测命令子模块。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ashquant import codes
from ashquant import config as cfg_mod
from ashquant.backtest import BacktestConfig, run_backtest
from ashquant.data import BarStore, resolve_pool
from ashquant.domain import VerdictDecision
from ashquant.predict import InsufficientDataError, predict_next_day, prediction_stats, settle_expired
from ashquant.strategy import analyze_stock

analysis_app = typer.Typer(help="量化策略回测、多空辩论与预测")
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


@analysis_app.command("backtest")
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

    pt = Table(title="次日预测可审计指标（逐日预测日志对账）", box=box.SIMPLE)
    pt.add_column("项目", style="yellow")
    pt.add_column("数值", justify="right")
    pt.add_row("总预测条数", str(m.get("pred_total", 0)))
    pt.add_row("有方向预测 (剔除观望)", str(m.get("directional", 0)))
    pt.add_row("方向覆盖率", f"{m.get('coverage', 0):.2%}" if m.get("coverage") else "n/a")
    pt.add_row("方向命中率 (全样本)", f"[bold]{m.get('hit_rate', 0):.2%}[/bold]" if m.get("hit_rate") else "n/a")
    console.print(pt)

    if cost_diff:
        console.print(f"[dim]费用敏感性: 零成本收益 {cost_diff['zero_fee_total_ret']:+.2%} vs 真实成本 {cost_diff['with_fee_total_ret']:+.2%} (摩擦磨损 {cost_diff['fee_drag']:.2%})[/dim]")
    console.print(f"[dim]详细报告已保存至: {out_path}[/dim]")


@analysis_app.command("debate")
def debate(
    symbol: Annotated[str, typer.Argument(help="股票代码（如 600519）")],
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """【v0.2.0 新增】触发 MasterDebateArena 多空大师对抗辩论与终审裁决。"""
    sym = codes.normalize_symbol(symbol)
    st = _store(data_dir)
    bars = st.load_bars(sym)
    if bars is None or len(bars) < 60:
        err_console.print(f"[red]{sym} 历史日线数据不足，请先执行 fetch[/red]")
        raise typer.Exit(2)

    analysis = analyze_stock(sym, bars, include_debate=True)
    v = analysis.latest_verdict

    if not v:
        err_console.print(f"[yellow]无法生成 {sym} 的辩论记录[/yellow]")
        raise typer.Exit(3)

    if json_out:
        _emit_json({
            "symbol": v.symbol,
            "as_of": v.as_of,
            "decision": v.decision,
            "conviction": v.conviction_score,
            "veto_reasons": v.veto_reasons,
            "transcript": v.transcript.__dict__,
        })
        return

    console.print("\n[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]")
    console.print(f"[bold cyan]🎯 MasterDebateArena 大师对抗辩论与终审裁决: {v.symbol} ({v.as_of})[/bold cyan]")
    console.print("[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]\n")

    console.print(f"[bold green]{v.transcript.bull_speech}[/bold green]\n")
    console.print(f"[bold red]{v.transcript.bear_speech}[/bold red]\n")
    console.print(f"[bold yellow]{v.transcript.bull_rebuttal}[/bold yellow]\n")

    dec_color = "bold green" if v.decision == VerdictDecision.BULLISH_APPROVED else ("bold red" if v.decision == VerdictDecision.VETOED_ON_RISK else "bold yellow")
    console.print(f"[{dec_color}]{v.transcript.cio_summary}[/{dec_color}]\n")
    console.print(f"[dim]裁决状态: {v.decision} | 置信度: {v.conviction_score:.2%}[/dim]\n")


@analysis_app.command("scan")
def scan(
    pool_name: Annotated[str, typer.Option("--pool", "-p", help="股票池: sample20 / csi300")] = "sample20",
    top: Annotated[int, typer.Option("--top", "-t", help="最多输出只数")] = 5,
    data_dir: Annotated[str | None, typer.Option("--data-dir", help="数据目录")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="以 JSON 输出")] = False,
):
    """【v0.2.0 新增】全市场多维度正交共振扫描（寻找 Grade AAA 高确定性决策）。"""
    st = _store(data_dir)
    syms = resolve_pool(pool_name, None)

    candidates = []
    for s in syms:
        bars = st.load_bars(s)
        if bars is None or len(bars) < 60:
            continue
        try:
            analysis = analyze_stock(s, bars, include_debate=True)
            v = analysis.latest_verdict
            if v and v.decision == VerdictDecision.BULLISH_APPROVED:
                candidates.append({
                    "symbol": s,
                    "prob_up": float(analysis.prob_up.iloc[-1]),
                    "conviction": v.conviction_score,
                    "vol_surge": analysis.latest_alpha.vol_surge if analysis.latest_alpha else 0.0,
                    "smart_money": analysis.latest_alpha.smart_money_acc if analysis.latest_alpha else 0.0,
                })
        except Exception:
            continue

    candidates.sort(key=lambda x: -x["conviction"])
    cands_top = candidates[:top]

    if json_out:
        _emit_json({"pool": pool_name, "total_scanned": len(syms), "grade_aaa_count": len(cands_top), "candidates": cands_top})
        return

    t = Table(title="全市场九子连珠正交共振扫描 (Grade AAA 高确定性机会)", box=box.ROUNDED)
    t.add_column("代码", style="cyan")
    t.add_column("上涨概率", justify="right")
    t.add_column("辩论裁决置信度", justify="right", style="bold green")
    t.add_column("量能爆发 (Vol Surge)", justify="right")
    t.add_column("聪明钱流向 (Smart Money)", justify="right")

    if not cands_top:
        console.print("[yellow]今日扫描全市场标的，未发现达成完全正交共振的 Grade AAA 机会，建议空仓观望。[/yellow]")
        return

    for c in cands_top:
        t.add_row(
            c["symbol"],
            f"{c['prob_up']:.2%}",
            f"{c['conviction']:.2%}",
            f"{c['vol_surge']:+.2f}",
            f"{c['smart_money']:+.2f}",
        )
    console.print(t)


@analysis_app.command("predict")
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


@analysis_app.command("stats")
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
