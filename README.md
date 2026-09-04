# ashquant · A股量化交易与预测平台

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

> **诚实指标 · 规则保真 · 投资大师信号代理 · 默认模拟盘**

`ashquant` 是一个面向 A股个人投资者与量化爱好者的轻量本地量化投研与模拟交易平台。
本项目遵循**诚实性优先原则**：所有预测指标均由可审计的逐日预测日志生成，绝不采用
带未来函数、过拟合或幸存者偏差的回测指标。

---

## ⚠️ 核心声明与免责（请先阅读）

1. **不构成投资建议**：本软件输出的所有分析、预测、概率及大师观点均为历史数据统计推演与学术性探索，**不构成任何投资建议或买卖指引**。股市有风险，入市需谨慎。
2. **为什么我们不承诺「99% 预测成功率」？**
   - 在金融计量学与机器学习资产定价学术界，个股日度方向预测准确率的有效区间通常在 **52% ~ 58%** 之间（参见 Gu, Kelly & Xiu, 2020 等经典文献）。
   - 数学归谬：若存在 99% 胜率且日边际仅 1% 的次日预测系统，10 万元本金在 9.3 年内即可超过 A 股全市场总市值（逻辑不可能）。
   - 任何声称 99% 次日预测胜率的系统必然存在**未来函数、过拟合、幸存者偏差或忽略真实成交摩擦**。详细论证见 [`specs/research/03-prediction-feasibility.md`](specs/research/03-prediction-feasibility.md)。
   - 本项目以**彼得·林奇**的名言为治理锚点：*「在这个行当里，如果你优秀，你十次能对六次。你永远不可能十次对九次。」*

---

## 🌟 核心特性

- 📈 **行情与看盘**：全市场实时快照轮询（涨跌幅着色） + 本地 Parquet 高速历史 K 线存储（基于 akshare 免费源）。
- 🧠 **投资大师信号代理**：将巴菲特（情绪逆向）、芒格（低波等待）、格雷厄姆（安全边际/超卖回归）、利弗莫尔（趋势突破）、德鲁肯米勒（动量反身）的经典哲学编码为可计算的量化特征，输出附带可核验出处名言的独立分析报告。
- ⚙️ **A股微观规则保真回测（对标 Qlib / RQAlpha）**：严格建模 **T+1、分板块涨跌停、流动性成交量限额（Volume Participation Limit）、平方根冲击成本滑点（Square-Root Impact Slippage）、涨停买不进、跌停卖不出顺延、佣金（万2.5最低5元）、印花税（卖0.05%）、过户费（双边0.001%）、整手买入**。
- 🤖 **Multi-Agent 对抗辩论与强类型 Schema（对标 TradingAgents）**：内置双层辩论架构（100% 确定性离线规则机 + 在线大模型增强），引入 Pydantic 风格容错清洗器（自动清洗 `"None"` / `"N/A"` 等脏字符），支持结构化审计报告导出与空头一票否决权。
- 🧊 **数据层动态复权因子（Qlib 风格）**：支持原始价（Raw）存储与动态前复权（QFQ）按截面折算，杜绝回测跨期数据被未来除权除息“污染”的潜在隐患。
- 🛡️ **MiniQMT 实盘工程化（对标 EasyXT）**：提供事件队列异步解耦回调（防止卡死 XtQuant C++ 消息循环）与盘前持仓资金对账防御状态机（Reconciliation Engine）。
- 📊 **可审计预测日志**：回测与实时预测均生成逐日预测日志（严格采用 close-to-close 收益口径对账），提供真实命中率、覆盖率与分置信度校准表。
- 💼 **安全模拟盘**：本地 JSONL 账本，严格遵循 T+1 资金与持仓锁定，支持对账单 CSV 导出。
- 🖥️ **双端形态**：功能完备的 Typer CLI 终端工具 + 基于 FastAPI 与 TradingView Lightweight Charts 的免构建 Web 控制台。

---

## 🚀 快速开始

### 1. 安装

本项目支持 Python 3.12+，推荐使用 `uv` 进行极速安装：

```bash
# 克隆或下载本仓库
cd ashquant

# 使用 uv 一键同步依赖与 Web 控制台
uv sync --extra web
```

或使用标准 `pip`：
```bash
pip install -e ".[web]"
```

### 2. 运行单测

```bash
uv run pytest
```

### 3. 三分钟上手演示

#### 步骤 1：抓取近三年日线数据（支持断点续抓）
```bash
# 抓取默认 20 只样本蓝筹股及沪深300指数
uv run ashquant fetch --pool sample20
```

#### 步骤 2：查看自选股实时行情
```bash
uv run ashquant watch --symbols 600519,000001,300750 --once
```

#### 步骤 3：运行三年规则保真回测
```bash
uv run ashquant backtest --pool sample20 --topk 5 --rebalance 5
```

#### 步骤 4：发起明日走势预测与大师观点
```bash
uv run ashquant predict 600519
```

#### 步骤 5：体验模拟盘交易
```bash
# 初始化 100 万虚拟资金
uv run ashquant paper init --cash 1000000

# 模拟买入 100 股贵州茅台
uv run ashquant paper buy 600519 --qty 100

# 查看持仓与资产
uv run ashquant paper show

# 当日尝试卖出将触发 T+1 锁定拒绝
uv run ashquant paper sell 600519 --qty 100
```

#### 步骤 6：启动本地 Web 可视化控制台
```bash
uv run ashquant web --port 8000
# 打开浏览器访问 http://127.0.0.1:8000
```

---

## 📖 CLI 命令大全

| 命令 | 示例 | 说明 |
|---|---|---|
| `fetch` | `ashquant fetch --pool sample20 --years 3` | 批量拉取日线入本地 parquet 缓存 |
| `watch` | `ashquant watch --symbols 600519,300750 -i 5` | 终端实时快照（涨跌幅着色，Ctrl+C 退出） |
| `backtest` | `ashquant backtest --pool sample20 --fee` | 运行回测，输出收益、夏普、回撤与基准对照 |
| `predict` | `ashquant predict 600519,300750` | 给出明日预测方向、上涨概率与大师独立观点 |
| `stats` | `ashquant stats --min-count 10` | 统计历史预测日志的真实命中率与校准度 |
| `paper init` | `ashquant paper init --cash 500000` | 初始化模拟盘账户资金 |
| `paper buy` | `ashquant paper buy 600519 --qty 100` | 模拟买入（规则引擎校验整手与资金） |
| `paper sell` | `ashquant paper sell 600519 --qty 100` | 模拟卖出（T+1 锁定与跌停校验） |
| `paper show` | `ashquant paper show` | 查看账户资产、持仓与浮动盈亏 |
| `paper export`| `ashquant paper export -o trades.csv` | 导出模拟交易对账流水 |
| `research snapshot` | `ashquant research snapshot --symbols 600519,000001 --data-dir ./data --out ./snapshots/s1` | 冻结研究输入并生成 SHA-256 清单 |
| `research evaluate` | `ashquant research evaluate --snapshot ./snapshots/s1 ... --out report.json` | 确定性三阶段回测评估与版本审计报告 |
| `web` | `ashquant web --port 8000` | 启动 Web 控制台（TradingView K线 + 预测） |

> 所有命令均支持 `--json` 选项，方便第三方脚本与自动化工具调用。

---

## 🔬 可复现研究闸门（Reproducible Research Gate）

为了防止策略过拟合、数据窥探与参数调优偏差，`ashquant` 提供了严格的「可复现研究闸门」机制，采用标准的 **`snapshot → evaluate`** 工作流：

### 1. 冻结输入快照（Snapshot）
从本地存储中提取指定标的日线、基准指数日线及已缓存资金流，生成包含全文件 SHA-256 签名的不可变快照目录：
```bash
uv run ashquant research snapshot \
  --symbols 600519,000001 \
  --data-dir ./data \
  --out ./snapshots/snap_202401
```
快照过程严格禁止触网或生成合成数据，确保输入完全固化。

### 2. 确定性三阶段评估（Evaluate）
对快照进行校验，在三段互不重叠的时间窗口（训练集 `train`、验证集 `validation`、测试集 `test`）上运行完全相同配置的回测评估：
```bash
uv run ashquant research evaluate \
  --snapshot ./snapshots/snap_202401 \
  --train-start 2023-01-01 --train-end 2023-05-31 \
  --validation-start 2023-06-01 --validation-end 2023-09-30 \
  --test-start 2023-10-01 --test-end 2024-01-31 \
  --out ./reports/research_report.json
```
- **完整性门禁**：读取数据前强校验全部文件 SHA-256 签名，篡改即拒绝。
- **版本证据**：强制关联 40 位 `git rev-parse HEAD` 提交号。
- **确定性保证**：无时间戳等随机因子，相同代码与快照多次运行产生完全一致的 JSON 报告。

### ⚠️ 研究证据声明
生成的评估报告中顶层固定标记：
```json
"research_status": "EVALUATED_NOT_APPROVED"
```
**明确声明**：`EVALUATED_NOT_APPROVED` 仅代表已完成标准三阶段回测验证的研究证据记录，**不代表策略已获准进入模拟盘或实盘，更不是任何形式的投资建议**。未经过进一步风险审查与实盘门禁批准前，严禁用于实际资产配置。

---

## 🏛️ 项目结构

```text
ashquant/
├── src/ashquant/
│   ├── config.py           # 路径/费率/策略超参（全部可配置）
│   ├── codes.py            # A股代码归一化、板块与ST涨跌幅规则
│   ├── data/
│   │   ├── aksource.py     # akshare 适配器（重试/退避/代理隔离）
│   │   └── store.py        # Parquet 高速存储与股票池管理
│   ├── indicators.py       # 技术指标（MA/MACD/RSI/BOLL/ATR等，无未来函数）
│   ├── masters/            # 5 位投资大师独立量化信号代理
│   │   ├── trend.py        # 利弗莫尔（趋势突破）
│   │   ├── momentum.py     # 德鲁肯米勒/索罗斯（动量反身）
│   │   ├── reversion.py    # 格雷厄姆（安全边际/超卖回归）
│   │   ├── riskctl.py      # 芒格（低波等待）
│   │   └── sentiment.py    # 巴菲特（恐惧贪婪逆向）
│   ├── strategy.py         # 信号加权合成与 Walk-forward 概率校准
│   ├── backtest/
│   │   ├── rules.py        # A股微观规则撮合引擎（T+1/涨跌停/费率）
│   │   ├── engine.py       # 事件驱动回测引擎与逐日预测日志
│   │   └── metrics.py      # 收益/回撤/夏普/胜率/校准度统计
│   ├── predict.py          # 实时预测与预测日志自动对账
│   ├── paper.py            # 模拟交易账户与持仓账本
│   ├── live/qmt.py         # QMT/miniQMT 实盘通道可选适配器
│   ├── quotes.py           # 实时快照封装
│   ├── cli.py              # Typer CLI 终端入口
│   └── web/                # FastAPI 后端与单文件 Lightweight Charts 页面
├── specs/                  # spec-kit 规范与一手调研报告
│   └── research/           # GitHub Top10实证 / A股规则 / 99%可行性 / 大师言论库
├── tests/                  # 7 组确定性单测（合成数据，不触网）
└── pyproject.toml          # 打包与依赖配置
```

---

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源。
