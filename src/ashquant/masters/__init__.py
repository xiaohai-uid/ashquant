"""大师信号代理（ai-hedge-fund 模式）：每位大师 = 独立、可测、带出处的信号器。

所有打分为向量化因果序列（只用 ≤t 数据）；名言均取自已核验言论库
specs/research/04-master-quotes.md。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ashquant.masters import momentum, reversion, riskctl, sentiment, trend


@dataclass(frozen=True)
class MasterSignal:
    master: str
    category: str
    score: float
    reason: str
    quote: str
    source: str
    as_of: str


@dataclass(frozen=True)
class MasterDef:
    name: str
    category: str
    quote: str
    source: str
    attribution: str  # 出处标注（一手/书籍/广泛转引）
    score_fn: object  # Callable[[DataFrame], Series]


REGISTRY: list[MasterDef] = [
    MasterDef(
        name="利弗莫尔",
        category="trend",
        quote="让我赚到大钱的从来不是我的思考，而是我的坐等。明白吗？我的坐等不动！",
        source="https://www.gutenberg.org/files/60979/60979-h/60979-h.htm",
        attribution="《股票作手回忆录》(1923)·古登堡公版全文",
        score_fn=trend.livermore,
    ),
    MasterDef(
        name="德鲁肯米勒（谈索罗斯）",
        category="momentum",
        quote="重要的不是你对还是错，而是你对时赚多少、错时亏多少。",
        source="https://en.wikiquote.org/wiki/George_Soros",
        attribution="Wikiquote 考据·《新金融怪杰》(1992) 访谈",
        score_fn=momentum.druckenmiller,
    ),
    MasterDef(
        name="格雷厄姆",
        category="reversion",
        quote="稳健投资的秘密，三个词：安全边际。",
        source="https://www.ifa.com/quotes/benjamin_graham",
        attribution="《聪明的投资者》第 20 章",
        score_fn=reversion.graham,
    ),
    MasterDef(
        name="芒格",
        category="risk",
        quote="大钱不在买卖之中，而在等待之中。",
        source="https://finance.yahoo.com/news/charlie-munger-says-big-money-173549307.html",
        attribution="芒格（广为流传，未定位一手逐字稿）",
        score_fn=riskctl.munger,
    ),
    MasterDef(
        name="巴菲特",
        category="sentiment",
        quote="我们只是试着在别人贪婪时恐惧，在别人恐惧时贪婪。",
        source="https://www.berkshirehathaway.com/letters/1986.html",
        attribution="伯克希尔 1986 年致股东信（一手）",
        score_fn=sentiment.buffett,
    ),
]

ALL_MASTER_NAMES = [m.name for m in REGISTRY]


def compute_master_series(df_ind: pd.DataFrame) -> pd.DataFrame:
    """对带指标列的日线逐大师计算打分序列（列名=大师名）。"""
    cols = {}
    for m in REGISTRY:
        cols[m.name] = m.score_fn(df_ind)
    return pd.DataFrame(cols, index=df_ind.index)


def signal_at(df_ind: pd.DataFrame, master_df: pd.DataFrame, as_of) -> list[MasterSignal]:
    """提取某时点 t 的全部大师信号（断言：df_ind 截止到 as_of）。"""
    assert pd.Timestamp(as_of) == df_ind.index[-1], "signal_at 必须以截至 as_of 的数据调用"
    row = master_df.loc[pd.Timestamp(as_of)]
    px_row = df_ind.loc[pd.Timestamp(as_of)]
    out = []
    for m in REGISTRY:
        score = float(row[m.name]) if pd.notna(row[m.name]) else 0.0
        out.append(
            MasterSignal(
                master=m.name,
                category=m.category,
                score=round(score, 4),
                reason=_reason(m.name, px_row, score),
                quote=m.quote,
                source=m.source,
                as_of=str(pd.Timestamp(as_of).date()),
            )
        )
    return out


def _reason(name: str, r: pd.Series, score: float) -> str:
    def f(k, fmt="{:.2f}"):
        v = r.get(k)
        return fmt.format(v) if v is not None and pd.notna(v) else "n/a"

    arrow = "看多" if score > 0.15 else ("看空" if score < -0.15 else "中性")
    ctx = {
        "利弗莫尔": f"收盘 {f('close')} vs MA20 {f('ma20')}/MA60 {f('ma60')}，"
                    f"ROC10 {f('roc10', '{:+.1%}')}",
        "德鲁肯米勒（谈索罗斯）": f"ROC10 {f('roc10', '{:+.1%}')}，量比 {f('vol_ratio')}",
        "格雷厄姆": f"RSI14 {f('rsi14', '{:.1f}')}，收盘相对布林下轨 "
                    f"{f('boll_low')}（现价 {f('close')}）",
        "芒格": f"20日波动率 {f('vol20', '{:.2%}')}（相对长期基线）",
        "巴菲特": f"RSI14 {f('rsi14', '{:.1f}')}，今收 {f('close')} 对今开 {f('open_', '{:.2f}')}",
    }
    return f"{arrow}。{ctx.get(name, '')}"
