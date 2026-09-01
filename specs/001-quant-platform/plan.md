# Implementation Plan: ashquant 量化交易平台 MVP

**Branch**: `001-quant-platform` | **Date**: 2026-09-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-quant-platform/spec.md`

## Summary

单用户本地 A股量化平台：akshare 数据层（日线+实时快照，parquet 本地缓存）→
指标/大师信号代理 → A股规则保真回测引擎（T+1/涨跌停/费用，walk-forward 预测日志）→
次日预测（概率+置信度+弃权）→ 模拟盘（与回测共用规则引擎）+ 可选 QMT 实盘适配器；
typer CLI + FastAPI/lightweight-charts Web 薄壳；MIT 开源就绪。
原始诉求「99% 预测成功率」按宪法转译为诚实指标体系（可审计预测日志）。

## Technical Context

**Language/Version**: Python 3.12+（本机 3.12.10 实测）

**Primary Dependencies**: pandas, numpy, akshare（数据）, typer+rich（CLI）,
pyarrow（parquet）, requests; 可选 extra: fastapi+uvicorn（web）, scikit-learn（ml）。
前端零构建：lightweight-charts 经 CDN 引入单文件 HTML。

**Storage**: 本地文件级——日线缓存 parquet（`data/bars/{symbol}.parquet`，含元数据），
模拟盘组合与预测日志为 JSON Lines（`data/paper/portfolio.jsonl`、`data/predictions.jsonl`）。

**Testing**: pytest（规则引擎用合成确定性数据；网络层 mock，真实验收另跑 smoke）

**Target Platform**: Windows / Linux / macOS 本地运行（开发与验收在 Windows + Git Bash）

**Project Type**: library + cli + web（薄壳）混合

**Performance Goals**: 20 只×3 年抓取 <5 分钟（含限速间隔）；回测 20 只×3 年 <60 秒；
单标的预测 <5 秒（热缓存）；Web 快照接口 <1 秒

**Constraints**: 断网时回测/预测可完全离线复现（从 parquet）；数据源限流需指数退避；
仓库无凭据；akshare 接口变更由适配层吸收

**Scale/Scope**: 单用户；默认 20 只样本池，沪深300 全量可选（约 800 只/全市场不在 v1 性能承诺内）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法原则 | 门禁状态 | 落实点 |
|---|---|---|
| I. 诚实性优先 | PASS | 预测日志（close-to-close 口径）是唯一指标来源；README 引用 03 报告；无 99% 承诺文案 |
| II. A股规则保真 | PASS | 规则引擎（T+1/分板块涨跌停含 2026-07-06 ST 分界/佣金/印花/过户费/整手）被回测与模拟盘共用 |
| III. 安全默认 | PASS | 默认模拟盘；QMT 适配器 lazy-import 可选；无 GUI 自动化；无凭据入库 |
| IV. 数据确定性 | PASS | parquet 缓存+元数据；point-in-time 特征；回测确定性（SC-002） |
| V. 模块化核心 | PASS | core 库独立可导入；CLI/Web 薄壳；适配器可选依赖 |
| VI. 测试与真实验收 | PASS | 合成数据单测 + results/ 真实 smoke 产物 |

## Project Structure

### Documentation (this feature)

```text
specs/001-quant-platform/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (cli/web/python 三份契约)
└── tasks.md             # Phase 2 output ($speckit-tasks)
```

### Source Code (repository root)

```text
src/ashquant/
├── __init__.py
├── config.py            # 路径/费用/规则参数（全部可覆盖）
├── codes.py             # 代码规范化、板块与 ST 判定、涨跌停阈值
├── data/
│   ├── __init__.py
│   ├── aksource.py      # akshare 适配器（重试/退避/字段映射，唯一 import akshare 处）
│   └── store.py         # parquet 读写+元数据、股票池、断点续抓
├── indicators.py        # MA/EMA/MACD/RSI/BOLL/ATR/ROC/量比/波动率（point-in-time）
├── masters/
│   ├── __init__.py      # MasterSignal 数据类 + 注册表
│   ├── trend.py         # 利弗莫尔（趋势跟踪）、索罗斯（动量反身）
│   ├── reversion.py     # 格雷厄姆（深度低估代理）
│   ├── riskctl.py       # 芒格（风险/波动控制）
│   └── sentiment.py     # 巴菲特（别人恐惧我贪婪：超卖+企稳）
├── strategy.py          # 大师信号合成→分数→概率校准→Top-K 组合构建
├── backtest/
│   ├── __init__.py
│   ├── rules.py         # A股规则引擎：T+1/涨跌停/费用/整手（回测与模拟盘共用）
│   ├── engine.py        # 事件循环：t 收盘信号→t+1 开盘撮合→逐日预测日志
│   └── metrics.py       # 收益/回撤/夏普/命中率/覆盖率/校准 + 基准对照
├── predict.py           # 实时预测 + 预测日志追加/对账/统计
├── paper.py             # 模拟盘组合（JSONL 状态）复用 rules.py
├── live/
│   ├── __init__.py
│   └── qmt.py           # QMT/xtquant 可选适配器（lazy import，缺失不报错）
├── quotes.py            # 实时快照（watch 自选股）
├── cli.py               # typer 入口：fetch/pool/watch/backtest/predict/stats/paper/web
└── web/
    ├── __init__.py
    ├── app.py           # FastAPI：spot/kline/predict/paper 接口 + 静态页
    └── static/index.html # 单文件页面（CDN lightweight-charts）
tests/                   # 合成数据单测（指标/规则/引擎/预测/模拟盘/代码规范化）
results/                 # 真实数据 smoke 产物（验收证据）
pyproject.toml           # uv/pytest/ruff 配置 + extras: web, ml
```

**Structure Decision**: 单包 `src/ashquant` 布局（library-first），web/static 归属包内，
tests 平铺按模块对应；不引入 monorepo（单用户工具，无多包必要）。

## Complexity Tracking

> 无宪法违规项需要辩护。
