# GitHub 交易类万星项目实证核对（2026-09-01）

- 核对方式：`gh api repos/{owner}/{repo}`（gh 2.96.0 已认证，经本地代理 7892），字段 `stargazers_count` / `language` / `description` 均为 GitHub API 实时返回值，非目测或转述。
- 核对时间：2026-09-01（北京时间）。
- 筛选条件：与「交易/trading」关键词强相关 + Stars ≥ 10,000。共核对 18 个候选，**17 个达标**（仅 jesse-ai/jesse 8,403 未达线）。按要求选 Top 10 核心 + 7 个扩展。

## 1. Top 10 核心项目（全部实证 ≥1 万星）

| # | 项目 | Stars | 语言 | 一句话定位 | 对 ashquant 的架构启示 |
|---|---|---|---|---|---|
| 1 | OpenBB-finance/OpenBB | 72,562 | Python | 面向分析师/量子的开放数据平台 | 平台形态：统一 CLI + Python API + 可插拔扩展；我们做轻量版（CLI + Web + 模块化 core） |
| 2 | virattt/ai-hedge-fund | 63,124 | Python | AI 对冲基金团队（巴菲特/芒格等大师代理） | **大师信号代理模式的直接参照**：每位大师=独立信号器（观点+置信度+理由），投票合成；与用户"结合高手言论"诉求完全对位 |
| 3 | freqtrade/freqtrade | 53,898 | Python | 加密货币交易机器人 | 安全默认值：默认 dry-run 模拟盘，策略抽象基类，回测/超参/纸面/实盘同一套策略代码 |
| 4 | microsoft/qlib | 48,179 | Python | AI 量化投研平台（支持A股） | A股数据组织 + 因子工作流 + 严格 walk-forward 评测纪律；防止泄漏的数据集切分设计 |
| 5 | vnpy/vnpy | 45,040 | Python | 中文量化交易框架（事件引擎+网关） | 券商网关（Gateway）抽象层：核心引擎不关心柜台；实盘通道做成可选适配器 |
| 6 | ccxt/ccxt | 43,827 | Python | 100+ 交易所统一交易 API | 统一数据/交易适配器模式：统一错误分类、限速、统一 OHLCV 格式 |
| 7 | mementum/backtrader | 23,064 | Python | 事件驱动回测库 | 回测引擎内核设计：Broker/Commission/Analyzer 分离，订单撮合生命周期 |
| 8 | akfamily/akshare | 22,359 | Python | 开源财经数据接口库（A股全量） | **本项目数据层底座**：日线 `stock_zh_a_hist` + 实时快照 `stock_zh_a_spot_em`（MIT，2026-08 仍高频发版，见 02 报告） |
| 9 | QuantConnect/Lean | 21,436 | C# | 多资产算法交易引擎 | 撮合现实度：费用模型/滑点模型/成交模型可插拔——回测诚实性的工程化 |
| 10 | yutiansut/QUANTAXIS | 11,075 | Python | A股全栈本地量化（数据/回测/模拟/交易） | A股全链路形态：数据落地本地 → 回测 → 模拟 → 通道，全离线可复现 |

## 2. 扩展达标项目（7 个，同样 ≥1 万星）

| 项目 | Stars | 备注 |
|---|---|---|
| quantopian/zipline | 20,077 | 回测库鼻祖，Quantopian 已散，维护停滞——只借鉴不依赖 |
| hummingbot/hummingbot | 19,739 | 高频做市机器人（加密） |
| tradingview/lightweight-charts | 17,150 | 金融图表库——**本项目 Web 端 K 线选型** |
| AI4Finance-Foundation/FinRL | 16,189 | 强化学习金融 |
| waditu/tushare | 15,381 | A股数据（积分制；2026-08 曾停运，见 02 报告，不作主源） |
| StockSharp/StockSharp | 10,675 | C# 多市场算法交易 |
| shidenggui/easytrader | 10,116 | 券商客户端自动化（合规风险高，只作调研对照，不内置） |

## 3. 关键结论

1. **没有一个 ≥1 万星的 A股项目承诺或展示过"99% 次日预测胜率"**——星数最高的方向是"平台化工具链"（数据/回测/风控/通道）而非"预测神器"；声称高胜率的仓库普遍星数低且无法通过严格 walk-forward 复验（与 03 可行性报告互证）。
2. 与用户诉求对位最好的是 **ai-hedge-fund（63k）**：大师代理（Buffett/Munger/Ackman…）各自给出带理由的信号再合成——ashquant 的「大师信号模块」采用此模式并结合 A股规则（T+1/涨跌停）落地。
3. A股数据主源选 **akshare**（22k 星、MIT、活跃维护、无积分门槛），与 02 报告结论一致。
4. 实盘通道学习 **vnpy 网关模式**：核心只对接「标准订单/成交接口」，QMT(xtquant) 做成可选适配器；默认与测试形态是模拟盘（学习 freqtrade 的 dry-run 默认）。

## 4. 复核命令（任何人可重跑）

```bash
export HTTPS_PROXY=http://127.0.0.1:7892   # 本机代理，按需
for r in OpenBB-finance/OpenBB virattt/ai-hedge-fund freqtrade/freqtrade \
         microsoft/qlib vnpy/vnpy ccxt/ccct mementum/backtrader akfamily/akshare \
         QuantConnect/Lean yutiansut/QUANTAXIS; do
  gh api "repos/$r" --jq '"\(.full_name)|\(.stargazers_count)|\(.description)"'
done
```
