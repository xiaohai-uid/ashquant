"""CLI 主路由与分发入口（精简深层门面）。

遵循 codebase-design 深度模块设计：
- 将具体命令实现委托给子命令包 ashquant.cli.* (data_cmds, analysis_cmds, trading_cmds)
- 根模块仅保留版本与 Web 启动入口，彻底消除 Divergent Change 坏味道。
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from ashquant import __version__
from ashquant.cli.analysis_cmds import analysis_app
from ashquant.cli.data_cmds import data_app
from ashquant.cli.trading_cmds import paper_app, trading_app

app = typer.Typer(
    name="ashquant",
    help="A股本地量化平台：行情查看 / 规则保真回测 / 大师对抗辩论 / 概率预测 / 模拟盘（诚实指标，不构成投资建议）",
    no_args_is_help=True,
)

# 挂载子应用命令组
app.add_typer(data_app, name="data")
app.add_typer(analysis_app, name="analysis")
app.add_typer(trading_app, name="trade")
app.add_typer(paper_app, name="paper")

# 平铺快捷注册（保持原有 CLI 命令 100% 向后兼容）
app.command(name="fetch", help=data_app.registered_commands[1].help)(data_app.registered_commands[1].callback)
app.command(name="pool", help=data_app.registered_commands[0].help)(data_app.registered_commands[0].callback)
app.command(name="watch", help=trading_app.registered_commands[0].help)(trading_app.registered_commands[0].callback)
app.command(name="backtest", help=analysis_app.registered_commands[0].help)(analysis_app.registered_commands[0].callback)
app.command(name="debate", help=analysis_app.registered_commands[1].help)(analysis_app.registered_commands[1].callback)
app.command(name="scan", help=analysis_app.registered_commands[2].help)(analysis_app.registered_commands[2].callback)
app.command(name="predict", help=analysis_app.registered_commands[3].help)(analysis_app.registered_commands[3].callback)
app.command(name="stats", help=analysis_app.registered_commands[4].help)(analysis_app.registered_commands[4].callback)

console = Console()
err_console = Console(stderr=True)


@app.command()
def version():
    """查看版本。"""
    console.print(f"[bold cyan]ashquant[/bold cyan] v{__version__}")


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
