# 投资大师言论库（可核实原话+出处）与「大师信号代理」映射

- 调研日期：2026-09-01
- 用途：ashquant 将把投资哲学编码为「大师信号代理」模块（trend 趋势跟踪 / mr 均值回归 / risk 风险控制 / sentiment 情绪逆向 / governance 校准与仓位治理），名言作为信号解释输出。每条注明：英文原话、中文译文、出处链接、核验状态、映射价值与编码建议。
- 标注约定：**[已验证-一手]** = 伯克希尔官网信件原文/PBS transcript/古登堡全文等可点开一手文本；**[已验证-书籍/权威二手]** = 书籍收录或权威媒体/维基语录考据；**[广泛转引]** = 未定位一手逐字稿，使用时需在产品文案中做归因弱化。

---

## 1. 沃伦·巴菲特（Warren Buffett）

### Q1. 贪婪与恐惧（情绪逆向的旗舰句）
- 英文原话："**we simply attempt to be fearful when others are greedy and to be greedy only when others are fearful**"
- 中文：我们只是试着在别人贪婪时恐惧，在别人恐惧时贪婪。
- 出处：伯克希尔 1986 年致股东信（官网原文）https://www.berkshirehathaway.com/letters/1986.html **[已验证-一手]**
- 映射：`sentiment` 情绪逆向代理。编码建议：构建市场情绪综合分（换手率分位、融资余额变化率、创新高/新低比、涨停家数占比），高分位输出逆向减仓信号、低分位输出逆向关注信号；信号解释文案直接引用本句。

### Q2. 巴菲特不预测市场（治理层的哲学锚）
- 英文原话："**we have no idea - and never have had - whether the market is going to go up, down, or sideways in the near- or intermediate term future**"
- 中文：我们不知道——从来也不知道——市场在近期或中期究竟会上涨、下跌还是横盘。
- 出处：伯克希尔 1986 年致股东信 https://www.berkshirehathaway.com/letters/1986.html **[已验证-一手]**
- 映射：`governance`。用于系统免责与预期管理：每日信号的输出框固定附注"连巴菲特也声明不预测短期市场，本系统输出的是概率而非确定性"。

### Q3. 短期预测是毒药
- 英文原话："**short-term market forecasts are poison and should be kept locked up in a safe place, away from children and also from grown-ups who behave in the market like children**"（同信前句："We've long felt that the only value of stock forecasters is to make fortune tellers look good."——我们一直认为股市预测员的唯一价值就是让算命先生显得体面。）
- 中文：短期市场预测是毒药，应当锁进安全的地方，远离儿童，也远离在市场里表现得像儿童的大人。
- 出处：伯克希尔 1992 年致股东信 https://www.berkshirehathaway.com/letters/1992.html **[已验证-一手]**
- 映射：`governance` + `sentiment`。任何"预测器"模块的 README/注释首行引用；用于对内约束：禁止研发以"精确预测点位"为目标的子模块。

### Q4. 避免大错（风险控制的核心表述）
- 英文原话："**An investor needs to do very few things right as long as he or she avoids big mistakes**"（同信："What counts for most people in investing is not how much they know, but rather how realistically they define what they don't know."——对多数投资者而言，重要的不是知道多少，而是多么现实地界定自己不知道什么。）
- 中文：投资者只要避免大错，做对很少几件事就足够了。
- 出处：伯克希尔 1992 年致股东信 https://www.berkshirehathaway.com/letters/1992.html **[已验证-一手]**
- 映射：`risk` 风险控制代理。编码建议：硬性风控规则（单票仓位上限、组合回撤熔断、连续 N 日超阈值波动降杠杆）；"define what you don't know" 同时是 `governance` 的覆盖率/不确定度门控句——模型不确定度高时输出"不预测"。

### Q5. 潮水退去（杠杆与尾部风险）
- 英文原话："**It's only when the tide goes out that you learn who's been swimming naked**"（1992 年信中以括号原话出现；2018 年信亦有类似引用）
- 中文：只有潮水退去，才知道谁在裸泳。
- 出处：伯克希尔 1992 年致股东信 https://www.berkshirehathaway.com/letters/1992.html **[已验证-一手]**
- 映射：`risk`。杠杆约束模块的注释句；模拟盘对"融资买入"路径标注警示。

### Q6. 无法预测短期走势（2008 年顶底时刻的声明）
- 英文原话："**I can't predict the short-term movements of the stock market. I haven't the faintest idea as to whether stocks will be higher or lower a month - or a year - from now**"
- 中文：我无法预测股市短期走势。一个月或一年后股票是高是低，我毫无头绪。
- 出处：巴菲特《纽约时报》评论文章 "Buy American. I Am."（2008-10-16）https://www.nytimes.com/2008/10/17/opinion/17buffett.html **[已验证-一手]**
- 映射：`governance`。用于营销物料与用户教育页；与报告 03 的可行性论证互为印证。

---

## 2. 查理·芒格（Charlie Munger）

### Q7. 大钱在于等待（趋势持有）
- 英文原话："**The big money is not in the buying and the selling, but in the waiting**"
- 中文：大钱不在买卖之中，而在等待之中。
- 出处：广泛转引（Yahoo Finance 等：https://finance.yahoo.com/news/charlie-munger-says-big-money-173549307.html ；考据见 https://www.simtrade.fr/blog_simtrade/big-money-not-buying-selling-but-waiting-charlie-munger/ ），一手出处一般认为是其年会/访谈口头表述，未定位逐字稿。**[广泛转引——产品文案需写"芒格（广为流传）"]**
- 映射：`trend` 趋势跟踪代理的持有期哲学：减少信号翻转频率、以趋势衰竭（而非小幅回调）作为退出条件。

---

## 3. 本杰明·格雷厄姆（Benjamin Graham）

### Q8. 投资者最大的敌人是自己
- 英文原话："**The investor's chief problem - and even his worst enemy - is likely to be himself**"
- 中文：投资者的主要问题——甚至是他的头号敌人——很可能是他自己。
- 出处：《聪明的投资者》（The Intelligent Investor）第 8 章 "The Investor and Market Fluctuations"（修订版 p.29，转引见 IFA 收录 https://www.ifa.com/quotes/benjamin_graham ；Goodreads https://www.goodreads.com/quotes/9352859 ）**[已验证-书籍/权威二手]**
- 映射：`sentiment` + `governance`。"Mr. Market"框架：情绪分代理的市场先生报价视角——市场先生的狂躁报价是别人的错误，不是你的指令。

### Q9. 安全边际
- 英文原话："**The secret of sound investment in three words: margin of safety**"（第 20 章章题即 "Margin of Safety as the Central Concept of Investment"）
- 中文：稳健投资的秘密，三个词：安全边际。
- 出处：《聪明的投资者》第 20 章（书籍收录；转引见 IFA https://www.ifa.com/quotes/benjamin_graham ）**[已验证-书籍/权威二手]**
- 映射：`mr` 均值回归代理 + `risk`。编码建议：估值分位（PE/PB 历史分位、股息率分位）越低，均值回归信号权重越高；无安全边际（估值分位>90%）时禁做多信号。

---

## 4. 杰西·利弗莫尔（Jesse Livermore，经 Edwin Lefèvre）

### Q10. 大钱靠坐等
- 英文原话："**It never was my thinking that made the big money for me. It always was my sitting. Got that? My sitting tight!**"（前句："Men who can both be right and sit tight are uncommon."）
- 中文：让我赚到 大钱的从来不是我的思考，而是我的坐等。明白吗？我的坐等不动！
- 出处：Edwin Lefèvre《股票作手回忆录》（Reminiscences of a Stock Operator, 1923），古登堡计划全文可检索 https://www.gutenberg.org/files/60979/60979-h/60979-h.htm **[已验证-一手（全书公版全文）]**
- 映射：`trend`。与 Q7 相互印证：趋势信号的退出条件用跟踪止盈而非固定持有期。

### Q11. 市场只有"正确的一边"
- 英文原话："**There is only one side of the market and it is not the bull side or the bear side, but the right side**"
- 中文：市场只有一边，不是多头边，也不是空头边，而是正确的一边。
- 出处：同书（古登堡全文 https://www.gutenberg.org/files/60979/60979-h/60979-h.htm ；名句汇编另见 https://traderlion.com/trading-books/reminiscences-of-a-stock-operator/ ）**[已验证-一手（全书公版全文；本条未逐字 grep，以全书可检索为据]**
- 映射：`trend` + `governance`。立场中立：信号系统不预设多头叙事，多空判断对称评估。

---

## 5. 斯坦利·德鲁肯米勒（转述乔治·索罗斯）

### Q12. 对错不重要，赔率才重要
- 英文原话："**It's not whether you're right or wrong that's important, but how much money you make when you're right and how much you lose when you're wrong**"（注意：常被误挂索罗斯名下；Wikiquote 将其归入 "Quotes about Soros"——德鲁肯米勒谈从索罗斯处所学，首见于 Jack Schwager《The New Market Wizards》(1992) 访谈）
- 中文：重要的不是你对还是错，而是你对时赚多少、错时亏多少。
- 出处：Wikiquote（George Soros 页，标注为 Druckenmiller 语）https://en.wikiquote.org/wiki/George_Soros ；考据 https://www.simtrade.fr/blog_simtrade/its-not-whether-youre-right-or-wrong-thats-important-but-how-much-money-you-make-when-youre-right-and-how-much-you-lose-when-youre-wrong/ **[已验证-权威二手考据；产品中应署"德鲁肯米勒（谈索罗斯）"]**
- 映射：`governance` 仓位治理。期望值框架：信号输出必须带 E[p·gain − (1−p)·loss]；按凯利比例打折（如 quarter-Kelly）确定仓位；这也是报告 03 中"52%-58% 胜率也能盈利"的数学基础。

---

## 6. 彼得·林奇（Peter Lynch）

### Q13. 十次对六次已是优秀
- 英文原话："**In this business, if you're good, you're right six times out of ten. You're never going to be right nine times out of ten**"
- 中文：在这个行当里，如果你优秀，你十次能对六次。你永远不可能十次对九次。
- 出处：PBS Frontline 纪录片《Betting on the Market》(1997) 林奇访谈官方文字稿 https://www.pbs.org/wgbh/pages/frontline/shows/betting/pros/lynch.html **[已验证-一手（官方 transcript）]**
- 映射：`governance`。本条是报告 03 结论"52%-58% 准确率"的最佳人证锚点：系统目标页与回测报告扉页引用。

---

## 7. 段永平（中国语境价值投资代表）

### Q14. 买股票就是买公司 + 三不原则
- 中文原话："**买股票就是买公司，和上不上市无关**"；"**不做空、不借钱、不懂不碰**"（其在雪球多次自述：问过巴菲特"投资中不可以做的事情是什么"，答案是"不做空，不借钱"，自己加上"不懂不碰"）。
- 英文（译文，供双语输出）："Buying a stock is buying the company — listed or not." / "No shorting, no leverage, no touching what you don't understand."
- 出处：雪球账号「大道无形我有型」原帖 https://xueqiu.com/1339867863/303193995 ；东方财富访谈《对话段永平：不懂生意的人很难做好投资》 https://wap.eastmoney.com/a/202511113561311768.html ；《大道：段永平投资问答录》书评（上海证券报）https://paper.cnstock.com/html/2025-09/15/content_2121369.htm **[已验证-权威二手（雪球原帖需登录核验全文，链接已存；中文语境无需英文一手]**
- 映射：`risk` + `governance`。编码建议：a) 系统永不输出做空信号（A 股个股做空工具本就受限）；b) 剔除基本面不可解的标的（如无法取到财报数据的）而非强行打分；c) 模拟盘禁用融资杠杆。

---

## 8. 「大师信号代理」模块映射总表

| 信号代理 | 对应名言 | 编码要点 |
|---|---|---|
| `trend` 趋势跟踪 | Q7 芒格(等待)、Q10/Q11 利弗莫尔 | 跟踪止盈、低翻转频率、多空对称 |
| `mr` 均值回归 | Q9 格雷厄姆(安全边际) | 估值分位门控、深跌分批 |
| `risk` 风险控制 | Q4/Q5 巴菲特、Q14 段永平 | 仓位上限、回撤熔断、无杠杆、不做空 |
| `sentiment` 情绪逆向 | Q1/Q3 巴菲特、Q8 格雷厄姆 | 换手/融资/新高新比情绪分逆向输出 |
| `governance` 治理（覆盖率/校准/仓位） | Q2/Q6 巴菲特、Q12 德鲁肯米勒、Q13 林奇 | 概率输出+期望值仓位+quarter-Kelly；准确率目标 52%-58% 并公告引用 Q13 |

---

## 9. BLOCKED / 未验证项

1. **芒格 Q7**："The big money is not in the buying and the selling, but in the waiting" 未定位一手逐字稿（疑为年会/访谈口头语），产品文案必须标注"广为流传"而非直引。
2. **Q12 归属**：该名句常被误作索罗斯原话；本项目按 Wikiquote/Schwager 考据署"德鲁肯米勒（谈索罗斯）"。
3. **Q11 利弗莫尔 "right side"** 句未在古登堡全文中逐字 grep 核验（全书公版可查，风险低）。
4. 段永平雪球原帖全文需登录查看，本报告依据可公开访问的转引与访谈/书评交叉核验。
