# Tasks: ashquant 量化交易平台 MVP

**Input**: Design documents from `/specs/001-quant-platform/`（spec/plan/research/data-model/contracts/quickstart）

**Tests**: 宪法第 VI 原则强制：规则引擎与指标必须单测，故包含测试任务（合成数据，不触网）。

**Organization**: 按用户故事分组（US1 看盘 / US2 回测 / US3 预测 / US4 交易 / US5 开源就绪）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事

## Phase 1: Setup（共享基础设施）

- [x] T001 创建 pyproject.toml（src 布局、deps: pandas/numpy/requests/typer/rich/pyarrow/akshare；extras: web=fastapi+uvicorn, ml=scikit-learn；pytest/ruff 配置）与包骨架 src/ashquant/__init__.py
- [x] T002 [P] 实现 src/ashquant/config.py：数据目录探测（./data 优先）、费用参数（佣金万2.5最低5元/印花0.05%卖/过户0.001%双边）、回测默认参数（topk=5/rebalance=5/单票上限20%/观望阈值0.05）
- [x] T003 [P] 实现 src/ashquant/codes.py：代码归一化（600519/sh600519/600519.SH→"600519"）、板块判定（主板/创业板30/科创板68/北交所）、ST 判定、limit_pct(symbol, is_st, date)（含 2026-07-06 主板 ST 5%→10% 分界）、涨跌停价计算（round 到分）

## Phase 2: Foundational（阻塞性前置）

- [x] T004 实现 src/ashquant/data/aksource.py：akshare 适配器（唯一 import akshare 处）——日线 stock_zh_a_hist(qfq)、快照 stock_zh_a_spot_em、指数日线；字段映射→[date,open,high,low,close,volume,amount]；重试+指数退避+明确错误（含接口名）；stock_zh_a_spot_em 全表→按代码过滤+名称缓存
- [x] T005 实现 src/ashquant/data/store.py：BarStore（parquet 原子写、元数据侧车 JSON、断点续抓 missing_symbols、load/save、股票池 sample20 硬编码列表与 csi300 动态成分）
- [x] T006 [P] 实现 src/ashquant/indicators.py：add_indicators(df)→附 MA5/20/60、EMA12/26、MACD(12,26,9)、RSI14、BOLL(20,2)、ATR14、ROC10、量比(VOL_RATIO vs MA5)、20日波动率；全部仅用当前及历史行（无 center/无未来引用）
- [x] T007 实现 src/ashquant/backtest/rules.py：MarketRules——费用计算（buy: 佣金+过户；sell: 佣金+印花+过户）、simulate_fill(决策日t, 撮合日t+1 OHLC, prev_close, 方向)→FILLED/REJECTED(LIMIT_UP|LIMIT_DOWN|T1_LOCK|ODD_LOT|INSUFFICIENT_CASH)/DEFERRED（卖单跌停顺延）；整手校验（卖出允许零股清仓）
- [x] T008 [P] tests/test_codes.py + tests/test_indicators.py：代码归一化/板块/ST分界日期两侧涨停价；RSI 已知小样本手算值、MACD/MA 无未来引用断言（截断前缀输出不变）

**Checkpoint**: 数据层+规则引擎就绪，各故事可开始。

---

## Phase 3: User Story 2 - 回测（P1，数据依赖最少故先于 US1 实施）

**Goal**: 三年 A股规则保真回测+基准对照+成本敏感性+逐日预测日志。
**Independent Test**: 合成数据引擎测试全绿后，`ashquant backtest --pool sample20` 真实运行，重跑两次 diff 一致。

- [x] T009 [P] [US2] 实现 src/ashquant/masters/__init__.py：MasterSignal dataclass（master/category/score/reason/quote/source/as_of）+ 注册表
- [x] T010 [P] [US2] 实现 5 个大师代理：masters/trend.py（利弗莫尔趋势、索罗斯动量反身）、masters/reversion.py（格雷厄姆超卖回归）、masters/riskctl.py（芒格低波优选）、masters/sentiment.py（巴菲特恐惧贪婪逆向）——每个输出 score∈[-1,1]+理由（含数值）+名言（specs/research/04-master-quotes.md 已核验出处）
- [x] T011 [US2] 实现 src/ashquant/strategy.py：ensemble_score（加权合成，权重可配）、calibrate_prob（滚动≥250日逻辑回归校准，无 sklearn 时用等价 numpy 实现）、build_target_portfolio（Top-K+单票上限）
- [x] T012 [US2] 实现 src/ashquant/backtest/engine.py：run_backtest（t 收盘信号→t+1 开盘撮合→组合权益逐日推进；停牌跳过；逐日预测日志含 direction/prob/actual_ret/hit；基准=同期沪深300买入持有；零成本对照）
- [x] T013 [US2] 实现 src/ashquant/backtest/metrics.py：total/annual return、MDD、Sharpe(rf=1.5%年化)、win_rate、方向命中率/覆盖率、按置信度分层校准表
- [x] T014 [P] [US2] tests/test_rules.py + tests/test_engine.py：T+1当日买当日卖拒单；开盘涨停拒买/跌停拒卖顺延；费用手算断言（万2.5最低5元+印花+过户）；合成数据下权益曲线确定性（同输入重跑逐位一致）；无未来函数（信号只依赖≤t）

**Checkpoint**: `uv run ashquant backtest --pool sample20` 可出报告。

---

## Phase 4: User Story 1 - 看盘（P1）

**Goal**: 自选股实时快照（CLI+Web）+ 三年 K 线页。
**Independent Test**: 交易时段 `ashquant watch --symbols 600519 --once` 出实时涨跌；`ashquant web` 后浏览器 10 秒内见快照+K线。

- [x] T015 [US1] 实现 src/ashquant/quotes.py：snapshot(symbols)→SpotQuote 列表（含名称、快照时间、非交易时段标注）
- [x] T016 [US1] 实现 src/ashquant/cli.py：typer 入口——fetch/pool/watch/backtest/predict/stats/paper子命令/web；全局 --json；退出码约定（2 数据失败/3 数据不足/4 规则拒单）
- [x] T017 [US1] 实现 src/ashquant/web/app.py + web/static/index.html：FastAPI（/api/spot,/api/kline/{symbol},/api/predict/{symbol},/api/paper*,静态页）；页面=快照表5秒轮询+lightweight-charts K线(MA5/20/60+成交量)+预测卡片+免责声明
- [x] T018 [P] [US1] tests/test_quotes.py：快照字段映射/缺代码容错（mock aksource）

**Checkpoint**: 看盘闭环可用。

---

## Phase 5: User Story 3 - 预测（P2）

**Goal**: 明日方向/概率/置信度/大师观点 + 可审计预测日志与统计。
**Independent Test**: `ashquant predict 600519` 输出完整结构；`ashquant stats` 对回测日志出命中率/覆盖率/校准表。

- [x] T019 [US3] 实现 src/ashquant/predict.py：predict_next_day（≥120交易日校验、复用 strategy 合成+校准、写 predictions.jsonl）、settle_expired（收盘后对账回写 hit）、prediction_stats（命中率/覆盖率/分置信度校准）
- [x] T020 [P] [US3] tests/test_predict.py：数据不足拒绝；NEUTRAL 弃权阈值；对账回写 hit 的 close-to-close 口径断言

**Checkpoint**: 预测闭环可用。

---

## Phase 6: User Story 4 - 交易（P2）

**Goal**: 模拟盘完整闭环 + QMT 可选适配器。
**Independent Test**: paper init→buy→当日sell被拒→次日sell成交→export 对账勾稽一致。

- [x] T021 [US4] 实现 src/ashquant/paper.py：PaperBroker（JSONL 状态、复用 rules.MarketRules、实时快照价撮合、T+1 shares_sellable、净值曲线、CSV 导出）
- [x] T022 [P] [US4] 实现 src/ashquant/live/qmt.py：lazy import xtquant 的可选适配器（未安装/未配置时给出可操作指引，不影响其他功能）；README 段落说明合规边界
- [x] T023 [P] [US4] tests/test_paper.py：现金+费用勾稽不变式（|cash+市值-equity|<1e-6）；T+1；拒单原因码；零股清仓允许

**Checkpoint**: 交易闭环可用。

---

## Phase 7: User Story 5 - 开源就绪（P3）

**Goal**: 任何人三条命令跑起来；密钥扫描零命中。
**Independent Test**: quickstart.md 全清单逐条通过。

- [x] T024 [P] [US5] README.md（中文为主）：定位/诚实性声明（链接 specs/research/03）/快速开始/架构图/免责声明/FAQ（含"为什么不是99%"）
- [x] T025 [P] [US5] LICENSE(MIT) + .gitignore(data/、results/ 可选保留) + pyproject 最终核对（extras 完整）
- [x] T026 [US5] 真实验收：fetch sample20→backtest→predict→paper→web 全链路 smoke，产物存 results/；两次 backtest diff 一致性验证；密钥扫描

---

## Phase 8: Polish & Cross-Cutting

- [x] T027 [P] ruff 全绿 + pytest 全绿 + README 命令与实际输出核对
- [x] T028 [P] .specify/memory/ 与 specs/ 索引更新（宪法合规复查：诚实性/规则保真/安全默认逐项过）

---

## Dependencies & Execution Order

- Phase 1→2 严格顺序；Phase 2 的 T004/T005 先行（T011/012 依赖），T006/T007/T008 可与其并行
- US2（回测）先于 US1（看盘）实施：CLI/Web 需要 backtest/predict 命令已存在
- US3 依赖 T009-T011（大师信号与校准）；US4 只依赖 T007（规则引擎）
- MVP 最小闭环 = Phase 1+2+3（US2）+ T015/T016

## Parallel Opportunities

- T002/T003、T006/T008、T009/T010、T020/T022/T023、T024/T025 各组内可并行
- 单 agent 顺序执行时按任务号即可

## Implementation Strategy

MVP First：T001-T014 完成即有可演示回测闭环；随后 T015-T017 看盘、T019 预测、
T021-T023 交易、T024-T026 发布就绪。每个 Checkpoint 做一次真实运行验证（宪法 VI）。
