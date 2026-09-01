# Phase 0 Research: 实现级决策记录

> 领域级调研已完成于 `specs/research/`（01 GitHub 实证 / 02 数据源与规则 / 03 预测
> 可行性 / 04 大师言论），本文件只记录**实现级**决策，全部带依据。

## D1 数据源与接口名

- **Decision**: 主源 akshare：日线 `stock_zh_a_hist(symbol, period="daily", adjust="qfq")`，
  全市场快照 `stock_zh_a_spot_em()`，指数 `index_zh_a_hist / stock_zh_index_daily_em`。
- **Rationale**: 02 报告（MIT、活跃、无门槛）；接口名以安装版本实测为准，适配层
  `aksource.py` 是唯一 import akshare 的模块，上游改名只改一处。
- **Alternatives**: tushare（积分制+2026-08 停运风险）、baostock（无实时）——列为
  备份源方向，v1 不实现。

## D2 存储格式

- **Decision**: parquet（pyarrow），每股一个文件，`data/bars/{symbol}.parquet`，
  侧车元数据 JSON 记录 source/adjust/fetched_at/date_range；重抓整段替换。
- **Rationale**: 列式读取快、类型保真、pandas 原生 to/read_parquet；逐股文件天然
  支持断点续抓与原子替换（写临时文件后 rename）。
- **Alternatives**: CSV（无类型、体积大）、SQLite（时序列读慢、增加 SQL 依赖）。

## D3 涨跌停与费用参数（规则引擎常量，config 可覆盖）

- **Decision**: 主板 ±10%（ST：2026-07-06 前 ±5%、之后 ±10%）；创业板(30)/科创板(68)
  ±20%；北交所(8/4 开头) ±30%。佣金默认万 2.5 最低 5 元；印花税卖出 0.05%；
  过户费双边 0.001%；整手 100 股（卖出允许零股清仓）。涨跌停价=前收 ×(1±限) 四舍五入到分。
- **Rationale**: 02 报告逐条已验证（含 2026-07 上交所修订）。
- **Alternatives**: 无——这是规则保真的强制项。

## D4 预测与校准方法

- **Decision**: 大师信号加权合成分数 s∈[-1,1] → 滚动窗口（≥250 交易日）逻辑回归
  校准为 P(涨)；|P-0.5|<0.05 输出"观望"。ml extra 下可用 sklearn 梯度提升做对照模型。
- **Rationale**: 可解释、参数少、样本外稳健；校准保证概率有意义（校准度可审计）。
- **Alternatives**: 纯 ML 端到端（不可解释、易过拟合）；深度学习（样本量不足+依赖重）。

## D5 Web 栈

- **Decision**: FastAPI + 单文件 HTML（CDN 引 lightweight-charts），5 秒轮询快照。
- **Rationale**: 零前端构建链，开源用户 `pip install ashquant[web]` 即用；
  lightweight-charts 17.2k 星（01 报告）专为金融图设计。
- **Alternatives**: React/Vite 全家桶（构建链重，违背最小闭环）；Streamlit（定制弱、
  依赖重）。

## D6 回测执行模型

- **Decision**: t 日收盘后出信号 → t+1 开盘价撮合（开盘涨停拒买/开盘跌停拒卖，
  未成交买单当日撤销，未成交卖单顺延次日再试）；t+1 收盘对 t 收盘计预测命中率。
- **Rationale**: 不可用"未来"的 t+1 收盘价成交（未来函数）；开盘撮合是保守且常见
  的日频假设；涨跌停拒单是 A股现实（02 报告）。
- **Alternatives**: t 收盘价成交（需要盘中实时计算信号，日频缓存下不可复现）。

## D7 大师信号代理（≥4 个，全部可独立单测）

- **Decision**: 利弗莫尔（趋势：MA 多头排列+20 日新高突破）、索罗斯（动量反身：
  强动量+量能放大顺势）、格雷厄姆（均值回归：BOLL 下轨+RSI 超卖）、芒格（风险控制：
  波动率收缩+ATR 占比低时加分，反之减分）、巴菲特（情绪逆向：深度超卖后止跌企稳）。
  每个信号输出：score∈[-1,1]、理由文本、名言（04 报告已核验语录+出处）。
- **Rationale**: 覆盖 spec FR-005 四类哲学；全部基于日线可计算特征，point-in-time。
- **Alternatives**: ai-hedge-fund 式 LLM 代理（依赖 API key+不可确定性回测，违背
  宪法 IV/VI）。

## D8 环境与包管理

- **Decision**: uv + pyproject（src 布局），pytest+ruff；akshare 仅在适配层出现，
  测试不触网（mock），真实验收走 smoke 脚本产物存 results/。
- **Rationale**: 本机实测 uv 0.12.3/Python 3.12.10；宪法 VI。
- **Alternatives**: poetry（速度慢）、conda（重）。
