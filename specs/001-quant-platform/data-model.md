# Data Model: ashquant MVP

> 实现为 Python dataclass/dict，存储为 parquet/JSONL；本文件定义字段与校验规则。

## 1. Bar（日线，parquet 行）

| 字段 | 类型 | 说明/校验 |
|---|---|---|
| date | date（str YYYY-MM-DD） | 单调递增、无重复 |
| open/high/low/close | float | high≥max(open,close)、low≤min(open,close)、全>0 |
| volume | float | 成交量（股），≥0 |
| amount | float | 成交额（元），≥0 |

每股一文件 `data/bars/{symbol}.parquet`；侧车元数据：`source`、`adjust="qfq"`、
`fetched_at`（ISO 时间）、`date_range`。**校验**：重抓整段替换，不与旧数据拼接。

## 2. SpotQuote（实时快照，内存对象）

symbol、name、price、pct_chg、change、timestamp（快照时间或收盘时间）、
prev_close。来源 `stock_zh_a_spot_em` 字段映射；非交易时段返回最后快照并标注时点。

## 3. MasterSignal（大师信号）

master（代理名）、category（trend/momentum/reversion/risk/sentiment）、
score（float，[-1,1]，越界为 bug）、reason（中文理由，含关键数值）、
quote（名言中文+出处 URL）、as_of（计算时点=所用数据最后一根 bar 日期）。
**校验**：信号只允许使用 as_of 及之前的 bar（引擎断言）。

## 4. Prediction（预测记录，JSONL：data/predictions.jsonl）

id、symbol、as_of（T 日）、target_date（T+1）、direction（UP/DOWN/NEUTRAL）、
prob_up、confidence、signals（MasterSignal 列表摘要）、created_at、
**到期补记**：actual_close_t1、actual_ret（close-to-close）、hit（bool 或 null 未到期）。
**口径锁定**：hit ⇔ sign(actual_ret) 与 direction 一致（NEUTRAL 不计命中、计入覆盖率分母之外）。

## 5. Order / Fill（订单/成交）

symbol、side（BUY/SELL）、qty（股，BUY 必须为 100 整数倍）、limit_note
（拒单原因：T1_LOCK/LIMIT_UP/LIMIT_DOWN/INSUFFICIENT_CASH/ODD_LOT 等）、
status（FILLED/REJECTED/DEFERRED）、fill_price、fees{commission,stamp,transfer}。

## 6. Position（持仓）

symbol、shares_total、shares_sellable（T+1：当日买入部分次日才可卖）、
cost_price、opened_at。卖出校验 qty ≤ shares_sellable。

## 7. Portfolio（组合/账户，JSONL 状态文件）

cash、positions{symbol→Position}、trades（Order/Fill 流水）、
equity_curve[{date, total_equity}]。**不变式**：cash + Σ持仓市值 = total_equity
（每次撮合后断言，误差 < 1e-6）。

## 8. BoardRule / 涨跌停（codes.py 派生，非存储实体）

symbol→board（MAIN/GEM/STAR/BSE + is_st(name, date)）→ limit_pct(date)：
主板 ST 在 2026-07-06 前 0.05、之后 0.10；GEM/STAR 0.20；BSE 0.30；其余主板 0.10。
涨跌停价 = round(prev_close × (1±limit_pct), 2)。

## 9. BacktestReport（结果对象）

config（池/区间/K/间隔/费用开关）、equity_curve、benchmark_curve（沪深300 买入持有）、
metrics{total_ret, annual_ret, mdd, sharpe, win_rate}、
prediction_log（逐日：as_of/symbol/direction/prob_up/actual_ret/hit）、
cost_sensitivity{zero_cost_total_ret, with_cost_total_ret}。
**校验**：同缓存重跑逐日一致（SC-002 断言写在测试里）。

## 关系

Bar 1..* → MasterSignal（按 as_of）→ 聚合为 Prediction → 到期对账回写 hit；
Order 作用于 Portfolio，撮合由 BoardRule 校验；BacktestReport 聚合 prediction_log
与 Portfolio 权益曲线。
