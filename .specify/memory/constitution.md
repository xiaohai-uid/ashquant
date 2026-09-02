<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0
- Modified principles:
  - Principle I: 诚实性优先升级为「诚实性与正交共振门禁优先（Honesty & Confluence Gating First）」
  - Principle V: 模块化核心升级为「多智能体对抗辩论与模块化核心（Adversarial Debate & Modular Core）」
- Added sections:
  - Principle VII: 持续进化与反思飞轮（Reflection & Self-Evolution Flywheel）
  - Principle VIII: 异常行情漂移熔断（Regime Breaker & Protective Circuits）
  - 代码知识图谱门禁（GitNexus Code Knowledge Graph Gate）
- Removed sections: none
- Follow-up TODOs: none
-->

# ashquant Constitution

## Core Principles

### I. 诚实性与正交共振门禁优先（Honesty & Confluence Gating First）— 不可协商

一切指标必须诚实：严禁未来函数（lookahead）、过拟合美化和幸存者偏差入库。
严禁承诺或暗示「全天候 100% 预测胜率」——该伪科学目标已被 `specs/research/03-prediction-feasibility.md` 与 `specs/research/09-ml-academic-benchmarks.md` 证伪。
真正的工程确定性在于**极度克制与非对称共振过滤（Asymmetric Confluence Gating）**：
系统放弃 95% 的随机噪音行情，仅在量价突破、北向聪明钱流动、安全边际与大师量化打分全维度达成**九子连珠式正交共振**时，才触发「Grade AAA 高确定性决策」（目标胜率 68%~75%，结合 3:1 盈亏比与凯利公式仓位管理）。
预测输出 MUST 附置信度与辩论审计日志，并允许弃权（NEUTRAL）。

### II. A股规则保真（Market Fidelity）

回测与模拟盘 MUST 建模：T+1、分板块涨跌停（主板 10%、创业板/科创板 20%、北交所 30%、主板 ST 5%→10% 的 2026-07-06 分界）、印花税卖出单边 0.05%、佣金（默认万 2.5、最低 5 元）、过户费双边 0.001%、100 股整手。
涨停不可买、跌停不可卖 MUST 体现在撮合逻辑中，严禁假定无法成交的价格完成撮合。

### III. 安全默认（Safe by Default）

默认形态是模拟盘（paper trading）。实盘仅通过用户显式配置的券商适配器（QMT/miniQMT·xtquant）启用，凭据永不入库、永不日志。禁止内置任何券商 GUI 自动化。开源仓库 MUST 无任何私人凭证，README MUST 附「不构成投资建议」声明。

### IV. 数据确定性（Deterministic Data Layer）

行情与替代数据统一落地本地缓存（parquet，含来源与抓取时间元数据）；回测 MUST 可从本地缓存完全复现。特征计算遵守 point-in-time 纪律：任意时点 $t$ 的信号只允许使用 $\le t$ 的数据。数据源以 AkShare 为主，腾讯/新浪为备用降级，统一输出 Pydantic 规范化数据模型。

### V. 多智能体对抗辩论与模块化核心（Adversarial Debate & Modular Core）

系统核心为可独立导入、独立测试的轻量库。
引入 **TradingAgents 式多智能体对抗辩论引擎（MasterDebateArena）**：
任何高确定性决策必须经受利弗莫尔（进攻多头）与格雷厄姆/芒格（挑刺空头）的双向交叉质询，最终由首席投资官（CIO）综合裁决。若空头指出的致命风险（如次日巨量解禁、T+1 无法出逃、假突破背离）未被化解，必须执行**一票否决（VETO）**。

### VI. 测试与真实验收（Test-First + Real Acceptance）

规则引擎（T+1、涨跌停、费用、指标计算、辩论状态机）用合成数据做确定性单测；每个交付 MUST 附真实数据端到端验收（fetch→alpha→debate→backtest→predict→paper 输出存 `results/`）。单测通过不等于验收通过；涉及网络与大模型调用的功能以真实链路为准。

### VII. 持续进化与反思飞轮（Reflection & Self-Evolution Flywheel）

系统具备“不在同一个地方跌倒两次”的自学习进化能力。
每日收盘后，系统对到期预测进行真实结算（Close-to-Close）。若预测失误或触发止损，自动触发**事后复盘剖析（Post-Mortem）**，提炼隐蔽前兆与失败教训，将其格式化为规则持久化写入反思记忆库（`data/reflection_memory.json`）。在未来的辩论中，空头 Agent 会自动检索并援引这些规则作为风控预警。

### VIII. 异常行情漂移熔断（Regime Breaker & Protective Circuits）

借鉴 FreqAI 与专业量化风控机制，当市场遭遇极端黑天鹅、千股跌停或数据分布严重漂移（Dissimilarity Index 超标）时，系统强制拒绝输出盲目预测；模拟盘与实盘账户在连续触发 3 次止损后自动触发 24 小时交易冷静熔断，防止情绪化与恶劣市况下的连续回撤。

## A股合规与技术约束

- 技术栈：Python 3.12+，uv 管理；核心依赖 pandas/numpy/akshare/typer/rich/fastapi；Web 为轻量 TradingView 图表；LLM/Agent 辩论模块采用模块化松耦合设计。
- License：MIT；发布前通过密钥与敏感信息扫描。
- 面向中文用户优先，CLI 与 Web 界面中文友好，代码与架构命名遵循标准规范。
- 程序化交易须遵守中国证监会 2024 年 8 号公告及沪深北交易所细则；本项目不提供高频抢单等违法违规功能。

## 代码图谱与质量门禁（GitNexus Gate）

1. **修改前影响面评估**：重构或修改跨模块接口前，必须使用 `gitnexus impact` 检查波及半径。
2. **拓扑无环门禁**：每个版本交付前，必须执行 `gitnexus check` 验证全仓库结构纯净度（要求 `status: clean, cycleCount: 0`），严禁循环依赖。
3. **测试全绿门禁**：交付前必须通过 `pytest` 与 `ruff check`。

## Governance

- 本宪法是最高工程准则，与其冲突的实现一律不接受。
- 修订记录：
  - v1.0.0 (2026-09-01): 初始宪法确立（六大基础原则）。
  - v2.0.0 (2026-09-02): 重大演进（新增正交共振门禁、多智能体对抗辩论、事后反思飞轮、漂移熔断与代码图谱门禁）。
- 代码评审 MUST 包含宪法合规项检查。

**Version**: 2.0.0 | **Ratified**: 2026-09-01 | **Last Amended**: 2026-09-02
