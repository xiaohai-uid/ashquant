# 「次日涨跌预测 99% 成功率」可行性论证

- 调研日期：2026-09-01
- 结论先行：**「99% 次日方向胜率」在学术证据、现实证据与数学推演三个层面均不成立**。诚实系统的合理目标是 52%-58% 方向准确率 + 覆盖率/校准度报告。任何展示 99% 胜率的回测必然包含本报告第 4 节所列的至少一种作弊机制。
- 标注约定：**[已验证]** = 有可点开的论文/官方原文/权威报道；**[推断]** = 合理推论。

---

## 1. 学术证据

### 1.1 有效市场与随机游走

- **Fama (1970)** "Efficient Capital Markets: A Review of Theory and Empirical Work", *Journal of Finance* 25(2):383-417。核心结论：在半强式有效市场下，基于公开信息的交易无法获得超额收益；股价短期变动近似随机游走，"过去的股价历史对未来没有预测力"是该领域近半个世纪的实证共识。**[已验证——经典文献]**
- 现实修正：A 股散户占比高、T+1、涨跌停等摩擦使市场并非完全有效——这正是"52%-58% 而非 50%"预测准确率的空间来源，但也**同时封顶了可实现的上限**。**[推断]**

### 1.2 机器学习资产定价的 SOTA 量级：月度 R² ≈ 0.4%

- **Gu, Kelly & Xiu (2020)** "Empirical Asset Pricing via Machine Learning", *Review of Financial Studies* 33(5):2223-2273。
  - 结论：用 94 个特征、多种 ML 模型（NN1-NN5、GBRT、RF 等）预测美股**月度**个股收益，最优模型（神经网络 NN3）**样本外月度预测 R² ≈ 0.4%**（约为主流计量方法的两倍）。R²=0.4% 意味着个股收益方差中 99.6% 不可预测。
  - 链接：RFS https://academic.oup.com/rfs/article-abstract/33/5/2223/5717868 ；NBER 工作论文 w25398 https://www.nber.org/papers/w25398 （PDF：https://www.nber.org/system/files/working_papers/w25398/revisions/w25398.rev1.pdf ）
  - 量级换算：即便 0.4%/月的 R² 已是该文献的"顶尖"结果——**面对"99% 次日方向胜率"的宣称，学术 SOTA 与其相差数个数量级**。**[已验证]**

### 1.3 ML 方向预测论文的典型准确率：52%-58%

- **Krauss, Do & Huck (2017)** "Deep neural networks, gradient-boosted trees, random forests: Statistical arbitrage on the S&P 500", *European Journal of Operational Research* 259(2):689-702。S&P 500 成分股 1992-2015 日度数据，DNN/GBT/RF 及其集成做统计套利（多空对冲、非纯方向预测）；摘要结论：**最优模型（ensemble）样本外日均收益 >0.45%（费用前），且盈利性随时间递减**；论文正文报告的各模型日度方向分类准确率在 50%-56% 区间（RF 最优约 55%，二级转述）。链接：https://www.sciencedirect.com/science/article/abs/pii/S0377221716308657 ；https://ideas.repec.org/a/eee/ejores/v259y2017i2p689-702.html **[已验证（摘要数字）；准确率具体值标注为二级转述]**
- **Fischer & Krauss (2018)** "Deep learning with long short-term memory networks for financial market predictions", *EJOR* 270(2):654-669。LSTM 预测 S&P 500 成分股次日方向，1992-2015：**样本外日均收益 0.46%、费用前 Sharpe 5.8**；方向命中率约 56%（二级转述口径），且收益随时间衰减、费用后大幅缩水。链接：https://www.sciencedirect.com/science/article/abs/pii/S0377221717310652 **[已验证（摘要数字）；56% 命中率为二级转述]**
- 汇总：顶刊口径下，**全球最顶尖的日度方向预测研究停留在 52%-58% 准确率、日均不足 0.5% 毛收益**，且这还是多空对冲、费用前、随市场有效性提升而衰减的结果。**[已验证+推断]**

---

## 2. 现实证据

### 2.1 顶级量化基金的真相：高频套利 ≠ 次日方向预测

- **文艺复兴大奖章基金（Medallion）**：1988-2018 年化毛收益约 66%、费后约 39%（Gregory Zuckerman《The Man Who Solved the Market》2019；Business Insider 报道 https://www.businessinsider.com/how-jim-simons-renaissance-technologies-has-outperformed-market-30-years-2019-12 ）。换算：**约 0.2%/交易日（毛）**——人类史上最强资金机器的日均边际，仅为"99% 胜率保守按 +1%/日"宣称值的 1/5。**[已验证]**
- **前联席 CEO Robert Mercer 的著名披露**：大奖章在**交易层面仅 50.75% 的胜率**——靠海量微小优势的统计套利（高频、短线、多品种对冲）而非方向预测复利，规模被刻意限制在约 100 亿美元内。出处：Institutional Investor https://www.institutionalinvestor.com/article/2bswymr8cih3jeaslxc00/portfolio/famed-medallion-fund-stretches-explanation-to-the-limit-professor-claims 。**[已验证（媒体报道口径）]**
- 论证：若"次日方向 99%"存在，其日边际远超 Medallion，且可容纳规模应更大——与现实（顶级机构 50.75% 交易胜率、20 万+员工规模的行业无人做到）直接矛盾。**[推断（基于已验证事实的推演）]**

### 2.2 巴菲特/芒格：明确表示无法预测短期市场

- **巴菲特，2008-10-16《纽约时报》评论文章 "Buy American. I Am."**（原文可点开）：
  > "Let me be clear on one point: I can't predict the short-term movements of the stock market. I haven't the faintest idea as to whether stocks will be higher or lower a month — or a year — from now."
  > （"说清楚一点：我无法预测股市的短期走势。一个月或一年后股票是涨是跌，我毫无头绪。"）
  > https://www.nytimes.com/2008/10/17/opinion/17buffett.html **[已验证——原文]**
- **巴菲特，1986 年致股东信**（伯克希尔官网原文）：
  > "we have no idea — and never have had — whether the market is going to go up, down, or sideways in the near- or intermediate term future."
  > （"我们不知道——从来也不知道——市场在近期或中期会涨、会跌还是横盘。"）
  > https://www.berkshirehathaway.com/letters/1986.html **[已验证——原文]**
- **巴菲特，1992 年致股东信**：
  > "short-term market forecasts are poison and should be kept locked up in a safe place, away from children and also from grown-ups who behave in the market like children."
  > （"短期市场预测是毒药，应当锁进安全的地方，远离儿童，也远离在市场里表现得像儿童的成年人。"）
  > https://www.berkshirehathaway.com/letters/1992.html **[已验证——原文]**
- 芒格的对应表述见报告 04（其对"预测"的态度与巴菲特一致）；芒格单独关于"无法预测短期市场"的一手逐字稿本次未定位（见 BLOCKED）。**[部分验证]**

---

## 3. 数学论证：99% 次日方向胜率的复利悖论

设某系统次日方向胜率 99%，采取最保守的假设：**每次只赚 1% 净边际**（99% 的日子里 +1%，1% 的日子里 -1%，期望日收益 ≈ +0.98%，以下按 1.01^N 复利估算）。

### 3.1 复利推演（250 个交易日/年）

| 时间 | 倍数（1.01^N） | 10 万元本金变为 |
|---|---|---|
| 1 年（N=250） | 1.01^250 ≈ **12.0 倍** | 120 万 |
| 2 年 | ≈ 145 倍 | 1,448 万 |
| 3 年 | ≈ 1,742 倍 | 1.74 亿 |
| 5 年（N=1250） | ≈ **2.52×10^5 倍** | 252 亿 |
| 9.3 年（N≈2332） | ≈ 1.2×10^10 倍 | **≈ 120 万亿元** |
| 10 年（N=2500） | ≈ 6.4×10^10 倍 | ≈ 6,400 万亿元 |

### 3.2 与市场总量对照 → 逻辑矛盾

- A 股总市值：2026-02-28 为 **116.87 万亿元**（新华社：http://www.news.cn/finance/20260316/37614982eab54ac7a3241f4af9a7b74c/c.html ）；2026-05 已站上 **120 万亿元**（新浪财经援引沪深北交易所数据：https://finance.sina.cn/stock/qz/2026-05-13/detail-inhxsxzs1022550.d.html ）。**[已验证]**
- 推演：**10 万元本金 + 99% 胜率 + 每日仅 1% 边际 ≈ 9.3 年吃下整个 A 股总市值**；10 年后（6,400 万亿元）将超过全球家庭总财富量级（数百万亿美元 ≈ 数千万亿元人民币，量级推断 **[推断]**）。
- 这构成归谬：如果该系统能连续兑现，市场其他参与者的对手盘（谁在持续把钱输给你？）与容量约束（买哪家公司能装下你的资金？）都不存在——唯一自洽的解释是**该胜率本身不真实（回测作弊）或不可持续（样本极小/单次事件）**。**[推断（算术+已验证市值数据）]**

### 3.3 统计视角补充

- 99% vs 55% 的差异巨大：250 个交易日样本下，日度方向准确率的标准差约 sqrt(0.55×0.45/250) ≈ 3.1%——**实盘只需不到一年就能以极高置信度证伪/证实 99% 的宣称**。然而全球没有任何一家机构的公开业绩展示过这种持续性（对照 Medallion 的 50.75%）。**[推断]**
- 换算对照：99% 胜率系统的信息比率将比 Medallion 高一个数量级以上，与"最强已知系统日均约 0.2%（毛）"的现实冲突。**[推断]**

---

## 4. 回测作弊机制清单（每条含把胜率虚推到 99% 的具体做法）

> 学术语境：Bailey, Borwein, López de Prado & Zhu (2017) "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4):39-69（https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 ）；Harvey, Liu & Zhu (2016) "…and the Cross-Section of Expected Returns", *RFS* 29(1):5-68（新因子 t 统计量应 >3.0，https://www.nber.org/papers/w20592 ）。**[已验证]**

1. **未来函数（lookahead bias）**
   做法：在 T 日开盘决策时使用 T 日收盘后才产生的数据。例：信号为"当日龙虎榜机构净买入 + 当日收盘价站上 MA20 → 次日买入"，回测却在 T 日 9:30 就用 T 日龙虎榜与 T 日收盘价判定并按 T 日开盘价成交；或特征直接用"今日涨跌幅"。此类信号在 A 股大量存在（龙虎榜、融资余额、北向数据均为盘后/次日公布），一旦偷看一天，胜率轻松从 55% 抬到 90%+。**[已验证（数据公布时点为公开事实）+推断]**
2. **过拟合 / 多重检验（数据挖掘）**
   做法：网格搜索 MA(5..500)×阈值×板块过滤共数万次回测，只汇报胜率最高的组合（如"2023-06 至 2023-09 的创业板 + MA37 + 量比>2.8 组合胜率 98.7%"）。Bailey 等的 PBO 框架证明：从大量试验中挑出的样本外最差者往往就是样本内最优者；Harvey 等要求新因子 t>3.0 才可信。**[已验证]**
3. **幸存者偏差**
   做法：用**今天**的成分股/股票列表回测历史（akshare/tushare 默认拉取的都是现存股票）。乐视网、康得新、康美药业等后来退市/崩塌的股票从未入样，回测里全市场"长生不老"；再叠加只统计"信号出现且成交"的日子，胜率可被推到接近全对。对策：必须使用含退市股票的点时（point-in-time)证券主表。**[已验证（机制）+推断]**
4. **复权处理错误**
   做法：a) 用"以今天为基准的前复权价"回测历史——历史价格被未来分红送转稀释，技术信号整体失真；b) 完全不复权——把"10 送 10 除权"当作当日 -50% 暴跌（或反向暴涨），若信号恰好只在"除权后买入"，收益被系统性高估；c) 用复权价计算但用不复权价判定涨跌停/下单价位，撮合错乱。**[推断（机制为工程常识，akshare 文档明确 stock_zh_a_hist 需指定 adjust 参数）]**
5. **涨停/跌停无法成交却计入收益**
   做法：信号"昨日一字涨停且封单巨大 → 今日买入"，回测按今日开盘价成交并吃下后续连板收益。现实中一字板排队的市价单大概率不成交（尤其叠加 T+1 与集合竞价不可撤单规则，见报告 02 第 3 节）。把"买不进的涨停板"全部记为盈利，是把幸存路径塞进回测的最直接方式；同理还有 ST/新股首日不设涨跌幅的特殊行情被当成常规样本。**[已验证（涨跌停规则为官方原文）+推断]**
6. **配套造假（把 60% 抬到 99% 的"包装术"）**：忽略印花税/过户费/佣金/冲击成本（对日频策略费用可吞掉全部边际，见报告 02 第 3.3-3.5 节）；违反 T+1（回测当日买入当日卖出）；只统计有信号的日子（覆盖率不可知，可能一天只报 1 只最容易的票）；在极小样本上宣称（20 个交易日全对≈运气概率不低）；样本内评估、无 walk-forward。**[推断]**

---

## 5. 结论：诚实系统的合理目标

1. **方向准确率目标：52%-58%**（与 GKX 2020、Krauss 2017、Fischer-Krauss 2018 顶刊口径一致）。宣称长期 >60% 需 extraordinary evidence；宣称 99% 直接判定为作弊或欺诈。**[已验证（文献锚点）+推断（目标设定）]**
2. **必须随准确率一同报告**：
   - **覆盖率（coverage）**：多少交易日/多少标的给出了信号（"全知全能只报一天一只"无效）；
   - **校准度（calibration）**：预测概率 vs 实际频率（说 70% 把握时长期命中率应≈70%）；
   - **费用后收益、容量约束（涨跌停可成交性）、walk-forward/滚动样本外**结果。**[推断]**
3. **产品话术红线**：ashquant 输出的是"概率化、带不确定度的每日信号 + 完整诚实回测"，绝不使用"99% 胜率/稳赚"类表述；信号解释引用报告 04 的大师名言时同样保持这个基调（林奇："你不可能十次对九次"）。**[推断]**
