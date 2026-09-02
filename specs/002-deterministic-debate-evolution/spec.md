# Feature Specification: 002-deterministic-debate-evolution

**Feature Name**: `deterministic-debate-evolution` (ashquant v0.2.0 大版本演进与重构)  
**Created Date**: 2026-09-02  
**Status**: Clarified  
**Target Milestone**: ashquant v0.2.0  

---

## 1. Executive Summary & Vision

基于前序对全球顶级量化与交易 AI 开源项目（`TradingAgents`, `Qlib`, `FinRL`, `FinGPT`, `freqtrade`, `vn.py`, `OpenBB`）的深度炼化调研（`specs/research/12-fusion-blueprint.md`），将 `ashquant` 升级为具备**多维度正交共振门禁**、**多空大师对抗辩论**、**事后反思自进化飞轮**与**异常行情漂移熔断**的下一代工业级 A 股量化决策平台。

核心愿景：破除“全天候 100% 预测”的随机游走幻觉，转向**极度克制的非对称共振过滤（Asymmetric Confluence Gating）**——全市场 5000+ 标的中每日仅遴选 1~2 只在量价、主力资金、估值与大师对抗辩论中达成“九子连珠式共振”的 Grade AAA 机会，结合 3:1 盈亏比与凯利公式仓位管理，实现数学上近乎确定的长期复利增长。

---

## Clarifications

### Session 2026-09-02
- Q: 在 MasterDebateArena（多空对抗辩论）中，当没有配置外部 LLM API Key 或网络不可达时，系统应当如何处理？ → A: 纯量化离线兜底 + 在线LLM增强（默认内置纯量化逻辑状态机，无网络或无 API 时也能完整输出多空结构化辩论；配置 API Key 时自动升级为 DeepSeek/Qwen 驱动的深度推演）。
- Q: 交易后反思自进化记忆库（ReflectionMemory）的持久化与检索方式选用哪种？ → A: 本地结构化 JSON/JSONL 文件（零额外依赖，人类可读，每次结算增量追加写入，下次辩论基于标签与时间倒序加载近 50 条高价值教训）。
- Q: 当触发 RegimeBreaker（极端行情漂移熔断，如千股跌停或突发外盘崩盘）时，系统的行为应当是什么？ → A: 强制拒止预测并阻断开仓（大盘跌幅超过 2.5% 或涨跌停家数严重失衡时，直接锁定买入信号，模拟盘/实盘挂单自动拒止，强制空仓观望）。

---

## 2. User Scenarios & Key Workflows

### Scenario 1: 全市场多正交门禁共振初选 (Confluence Scanning)
- **User Action**: 用户执行 `ashquant scan --top 5` 或在 Web 界面点击「全市场共振扫描」。
- **System Behavior**:
  1. 系统自动拉取目标股票池最新的日 K 线与主力资金流向（北向资金、超大单净流入）。
  2. 计算 Qlib 式 Alpha 因子与 5 位大师量化打分。
  3. 过滤掉无共振或大师综合分 $<0.50$ 的杂波，输出具备高确定性特征的 Grade AAA 候选池。

### Scenario 2: 触发 MasterDebateArena 多空大师对抗辩论 (Adversarial Debate)
- **User Action**: 用户针对某只高分标的执行 `ashquant debate 600519` 或在 Web 界面查看「大师辩论竞技场」。
- **System Behavior**:
  1. 系统启动三方博弈状态机：
     - **利弗莫尔 (Bull)**：基于突破结构、成交量异动与趋势发散进行进攻性做多陈词。
     - **芒格/格雷厄姆 (Bear)**：基于历史反思教训、高位估值、减持风险与 T+1 流动性陷阱进行严苛挑刺与排雷质询。
     - **多头质辩 (Rebuttal)**：利弗莫尔针对芒格的质疑，出具主力资金锁仓或业绩催化论据。
     - **首席投资官 (CIO Arbitrator)**：综合裁决双方论据，评估空头是否指出未化解的致命硬伤。若存在致命风险，执行一票否决（VETO）；若化解，输出裁决报告与置信度。
  2. **双模式保障**：默认执行本地纯量化辩论规则；若环境变量配置了 `ASHQUANT_LLM_API_KEY`，自动并行升级为大模型自然语言高阶博弈。

### Scenario 3: 到期预测自动触发事后反思飞轮 (Post-Mortem Reflection)
- **User Action**: 每日收盘后，系统执行 `ashquant settle` 结算昨日预测结果。
- **System Behavior**:
  1. 结算 Close-to-Close 真实收益。
  2. 若预测看多但实际下跌超过 $2\%$（或触发模拟盘止损），自动触发反思 Agent 审查当时的辩论记录。
  3. 提炼出导致误判的前兆特征，格式化沉淀为规则追加写入 `data/reflection_memory.jsonl`。
  4. 下次辩论同类形态时，空头 Agent 自动调取并引用该反思规则。

### Scenario 4: 极端异动行情自动触发漂移熔断 (Regime Breaker)
- **User Action**: 市场发生千股跌停或突发外盘黑天鹅。
- **System Behavior**:
  1. 系统检测到全市场特征偏离历史训练分布（大盘跌幅 $\ge 2.5\%$，或下跌个股占比 $> 80\%$）。
  2. 自动触发全局熔断电路，强制拒止所有买入预测，模拟盘与实盘阻断开仓，保护资金免遭系统性流动性踩踏。

---

## 3. Functional Requirements (功能需求清单)

### FR-001: 替代数据与主力资金流向支持 (Alternative Capital Flow Data)
- 系统 MUST 支持通过 AkShare 采集并持久化 A 股特色资金流向数据：
  - 北向资金（沪深港通）持股变动与净买入。
  - 融资融券余额及变动率。
  - 个股主力超大单/大单/中单/小单分时资金净流入。
- 资金数据 MUST 落地本地 Parquet 缓存，与日 K 线按交易日对其。

### FR-002: Qlib 风格 Alpha 因子库 (Alpha Factor Zoo)
- 系统 MUST 提供向量化计算的 Alpha 因子扩展模块（`ashquant.alpha`）：
  - 量价背离因子（Price-Volume Divergence）。
  - 波动率压缩与突破因子（Volatility Squeeze / ATR Band Breakout）。
  - 筹码集中度与大单净流入强度因子。
- 所有因子计算 MUST 遵守 point-in-time 因果纪律，严禁未来函数。

### FR-003: MasterDebateArena 多智能体对抗辩论引擎
- 系统 MUST 提供轻量结构化的多空博弈辩论框架（`ashquant.debate`）：
  - 支持模块化的大师 Agent 角色（利弗莫尔多头、芒格空头、格雷厄姆估值裁判、CIO 终审）。
  - 支持**离线量化状态机模式**（无网络/无 API 依赖，100% 可用）与**在线大模型模式**（OpenAI 兼容端点）。
  - CIO 裁决必须输出确定性结论：`BULLISH_APPROVED`, `BEARISH_REJECTED`, `VETOED_ON_RISK`, `NEUTRAL_WAIT`。

### FR-004: ReflectionMemory 持续自进化反思库
- 系统 MUST 在预测结算时建立闭环学习飞轮：
  - 记录预测与真实结果的偏差。
  - 生成结构化 Post-Mortem 记录（包含标的代码、入场形态、致命盲点、禁止规则），保存在本地 `data/reflection_memory.jsonl` 中。
  - 在生成新辩论时，支持基于形态标签检索历史教训并注入空头 Agent 提示词与决策逻辑。

### FR-005: RegimeBreaker 市场环境漂移与风控熔断
- 系统 MUST 提供账户与市场双重熔断机制：
  - 市场级熔断：大盘跌幅超过 2.5% 或全市场下跌家数占比 $>80\%$ 时，强制拒止所有买入预测，阻断开仓。
  - 账户级熔断：模拟盘或实盘发生连续 3 次止损时，强制休眠 24 小时冷静期。

### FR-006: CLI 与 Web 交互升级
- CLI 重构为模块化子命令组：`ashquant data`, `ashquant analyze`, `ashquant debate`, `ashquant backtest`, `ashquant paper`, `ashquant web`。
- Web 控制台新增「多空大师辩论视窗」与「反思记忆库面板」，支持查看三方辩论全过程。

---

## 4. Success Criteria (验收成功标准)

- **SC-001 (共振过滤有效性)**: 在全市场 5,000+ 股票池扫描中，Grade AAA 信号触发率保持在每日 $\le 0.5\%$ 的极度克制水平，杜绝滥发信号。
- **SC-002 (回测基准胜率)**: 在历史 3 年（2023-2026）严格 A 股微观规则（T+1、涨跌停、滑点、印花税）回测中，Grade AAA 共振策略的 Directional Hit Rate $\ge 62\%$，最大回撤 $< 12\%$，显著超越沪深 300 基准。
- **SC-003 (辩论一票否决率)**: 在对抗辩论测试中，当股票存在高位放量滞涨或北向大幅撤退等隐蔽硬伤时，空头/CIO 的 VETO 拦截率达到 $100\%$。
- **SC-004 (反思记忆闭环)**: 在结算出现负收益后，反思日志成功生成并写入 `data/reflection_memory.jsonl`，后续针对同代码/同形态的辩论中能明确引述该反思规则。
- **SC-005 (质量与图谱门禁)**: 单元测试全绿（通过率 100%），`ruff check` 无告警，`gitnexus check` 保持 `status: clean, cycleCount: 0`。

---

## 5. Assumptions & Dependencies

- **A1**: 大模型辩论模块必须支持“纯定量逻辑回退”（Fallback Mode），即在无 API Key 或无外网网络时，仍能依据量化规则生成结构化多空对比报告。
- **A2**: 资金流数据源若出现 AkShare 临时接口反爬，系统必须平滑降级，仅依赖量价 Alpha 与现有 Master 信号运行，不能导致主进程崩溃。
