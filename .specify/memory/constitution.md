<!--
Sync Impact Report
- Version change: (template scaffold) → 1.0.0
- Modified principles: N/A (initial ratification from resolved constitution-template)
- Added sections: Core Principles ×6; A股合规与技术约束; 开发工作流与质量门禁; Governance
- Removed sections: none
- Follow-up TODOs: none
-->

# ashquant Constitution

## Core Principles

### I. 诚实性优先（Honesty First）— 不可协商

一切指标必须诚实：严禁未来函数（lookahead）、过拟合美化和幸存者偏差入库。
任何对外展示的预测/回测指标 MUST 由可审计的预测日志（逐日预测 vs 实际，含覆盖率与校准度）
支撑；严禁承诺或暗示「99% 次日预测胜率」——该目标已被
`specs/research/03-prediction-feasibility.md` 三重证据（学术/现实/数学归谬）证伪，
产品文案与 README MUST 引用该报告。预测输出 MUST 附置信度，并允许弃权（NEUTRAL）。

### II. A股规则保真（Market Fidelity）

回测与模拟盘 MUST 建模：T+1、分板块涨跌停（主板 10%、创业板/科创板 20%、
北交所 30%、主板 ST 5%→10% 的 2026-07-06 分界）、印花税卖出单边 0.05%、
佣金（默认万 2.5、最低 5 元）、过户费双边 0.001%、100 股整手。
涨停不可买、跌停不可卖 MUST 体现在成交撮合中，不得「先算收益再补规则」。

### III. 安全默认（Safe by Default）

默认形态是模拟盘（paper trading）。实盘仅通过用户显式配置的券商适配器
（QMT/miniQMT·xtquant）启用，凭据永不入库、永不日志。禁止内置任何券商/第三方
客户端 GUI 自动化（合规风险，见 `specs/research/02-ashare-data-and-brokers.md`）。
开源仓库 MUST 无任何私人文凭与账号信息，README MUST 附「不构成投资建议」声明。

### IV. 数据确定性（Deterministic Data Layer）

行情数据统一落地本地缓存（parquet，含来源与抓取时间元数据）；回测 MUST 可从
本地缓存完全复现。特征计算遵守 point-in-time 纪律：任意时点 t 的信号只允许使用
≤t 的数据。主数据源 akshare，接口封装隔离上游变更（适配器模式，参照 ccxt/vnpy）。

### V. 模块化核心（Modular Core, Library-First）

核心能力（数据/指标/大师信号/回测/预测/模拟盘）是可独立导入、独立测试的库；
CLI 与 Web 是薄壳。大师信号代理遵循 ai-hedge-fund 模式：每位大师=独立信号器
（打分 + 理由 + 出处名言），可独立单测、可合成投票。适配器（QMT、备用数据源）
为可选依赖，缺失时核心功能 MUST 可用。

### VI. 测试与真实验收（Test-First + Real Acceptance）

规则引擎（T+1、涨跌停、费用、指标计算）用合成数据做确定性单测；
每个交付 MUST 附真实数据端到端验收（fetch→backtest→predict→quotes 实跑输出存
`results/`）。单测通过不等于验收通过；涉及网络/数据的功能以真实链路为准。

## A股合规与技术约束

- 技术栈：Python 3.12+，uv 管理；核心依赖 pandas/numpy/akshare/typer/rich；
  Web 为 FastAPI + lightweight-charts（CDN，无构建步骤）；ML 为可选 extra（scikit-learn）。
- License：MIT；发布前通过密钥扫描（无 token/账号入库）。
- 面向中文用户优先，文档中文为主；代码注释与命名英文。
- 程序化交易须遵守中国证监会 2024 年 8 号公告及沪深北交易所细则（见 02 报告）；
  本项目不提供高频能力（tick 级抢单/撤单不属于项目范围）。

## 开发工作流与质量门禁

- 一切功能先有 spec（specs/）再有实现；需求变更先改 spec 再改代码。
- 任何对外指标 MUST 来自 walk-forward（滚动训练/验证）产出的预测日志，
  禁止用全样本内拟合指标充当「预测成功率」。
- 提交前：单测全绿 + ruff 通过；发布前：真实数据验收产物齐全。
- 回测结果 MUST 同时给出基准对照（沪深300 买入持有）与成本敏感性。

## Governance

- 本宪法是最高工程准则，与其冲突的实现一律不接受。
- 修订须记录：修订内容、理由、影响面与迁移方案；版本遵循语义化（原则增删=MAJOR，
  新增条款=MINOR，措辞澄清=PATCH）。
- 代码评审 MUST 包含宪法合规项检查（诚实性、规则保真、安全默认）。
- 运行时开发指引见 `.specify/memory/`；调研依据见 `specs/research/`。

**Version**: 1.0.0 | **Ratified**: 2026-09-01 | **Last Amended**: 2026-09-01
