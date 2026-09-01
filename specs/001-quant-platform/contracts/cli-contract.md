# CLI Contract（typer，入口 `ashquant`）

所有命令支持 `--json`（机器可读输出到 stdout，人类可读错误到 stderr）。
股票代码容错：`600519` / `sh600519` / `600519.SH` / `600519.SZ` 归一为 6 位数字串。

| 命令 | 参数（默认） | 语义 | 退出码 |
|---|---|---|---|
| `ashquant fetch` | `--symbols` 或 `--pool sample20/csi300`（sample20）、`--years 3` | 抓取日线入 parquet，断点续抓 | 0 成功 / 2 数据源失败 |
| `ashquant pool` | `--name sample20/csi300` | 列出/解析股票池成分 | 0 |
| `ashquant watch` | `--symbols`、`--interval 10`、`--once` | 实时快照表（涨跌幅着色）；`--once` 单次 | 0 / 2 网络失败 |
| `ashquant backtest` | `--pool/--symbols`、`--start`、`--end`、`--topk 5`、`--rebalance 5`、`--fee on/off` | 跑回测：控制台摘要 + `results/backtest_*.json`（含预测日志） | 0 / 2 数据不足 |
| `ashquant predict` | `--symbols`（可多值） | 输出方向/概率/置信度/大师观点；数据不足→退出码 3 | 0 / 3 |
| `ashquant stats` | `--min-count 20` | 预测日志命中率/覆盖率/按置信度分层校准表 | 0 / 3 无到期记录 |
| `ashquant paper init` | `--cash 1000000` | 初始化模拟账户 | 0 |
| `ashquant paper buy` | `SYMBOL --qty 100` | 模拟买入（实时价撮合，规则引擎校验） | 0 / 4 规则拒单（打印原因） |
| `ashquant paper sell` | `SYMBOL --qty` | 模拟卖出（T+1/跌停/整手校验） | 0 / 4 |
| `ashquant paper show` | — | 持仓+浮动盈亏+净值摘要 | 0 |
| `ashquant paper export` | `--out CSV路径` | 导出交易流水对账单 | 0 |
| `ashquant web` | `--host 127.0.0.1 --port 8000` | 启动 Web 控制台 | 0 |

约定：拒单（T+1/涨跌停/资金不足/零股）不是程序错误——正常输出原因并以 4 退出，
便于脚本区分"系统坏"与"规则拦截"。
