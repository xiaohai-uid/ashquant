"""ashquant 核心领域模型（Domain Models & Enums）。

遵循 codebase-design 深度模块设计：
- 消除 Primitive Obsession：用强类型枚举替代裸字符串（兼容 str）
- 消除 Data Clumps：将反复同行的市场上下文封装为 MarketContext 值对象
- v0.2.0 演进：新增资金流（CapitalFlow）、Alpha因子（AlphaFactors）、辩论裁决（DebateVerdict）与反思记录（ReflectionRecord）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class OrderSide(StrEnum):
    """订单买卖方向。"""
    BUY = "BUY"
    SELL = "SELL"


class FillStatus(StrEnum):
    """撮合结果状态。"""
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class SignalDirection(StrEnum):
    """预测与信号方向。"""
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class RejectReason(StrEnum):
    """拒单原因码。"""
    LIMIT_UP = "LIMIT_UP"            # 涨停买不进
    LIMIT_DOWN = "LIMIT_DOWN"        # 跌停卖不出
    T1_LOCK = "T1_LOCK"              # 当日买入 T+1 锁定
    ODD_LOT = "ODD_LOT"              # 零股/非整手限制
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    NO_POSITION = "NO_POSITION"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"  # 流动性不足 (成交量限制)
    REGIME_CIRCUIT_BREAKER = "REGIME_CIRCUIT_BREAKER"  # 极端行情漂移熔断


class VerdictDecision(StrEnum):
    """多空大师辩论裁决。"""
    BULLISH_APPROVED = "BULLISH_APPROVED"  # 多头获胜且通过风控，做多
    VETOED_ON_RISK = "VETOED_ON_RISK"      # 空头指出致命硬伤，一票否决
    BEARISH_REJECTED = "BEARISH_REJECTED"  # 空头占优，明确看空
    NEUTRAL_WAIT = "NEUTRAL_WAIT"          # 双方分歧或无显著催化剂，观望


class MarketRegime(StrEnum):
    """宏观与市场环境分级。"""
    NORMAL = "NORMAL"                      # 常态市场
    TURBULENT = "TURBULENT"                # 波动放大，减半仓位
    PANIC_CIRCUIT_BROKEN = "PANIC_CIRCUIT_BROKEN"  # 极端踩踏/千股跌停，拒绝入场


@dataclass(frozen=True)
class MarketContext:
    """市场环境值对象：封装标的、日期、现价、昨收价、ST 状态与当日成交量。"""
    symbol: str
    trade_date: date | str
    price: float
    prev_close: float
    is_st: bool = False
    volume: float = 0.0

    @property
    def trade_date_obj(self) -> date:
        if isinstance(self.trade_date, str):
            return date.fromisoformat(self.trade_date)
        return self.trade_date


@dataclass(frozen=True)
class CapitalFlow:
    """主力与特色资金流向数据结构。"""
    date: str
    symbol: str
    northbound_net_shares: float = 0.0     # 北向资金净买入股数
    northbound_hold_ratio: float = 0.0     # 北向资金占流通股比率
    margin_balance: float = 0.0            # 融资余额 (元)
    margin_buy_amount: float = 0.0         # 融资买入额 (元)
    super_large_net_inflow: float = 0.0    # 超大单净流入金额 (元)
    large_net_inflow: float = 0.0          # 大单净流入金额 (元)


@dataclass(frozen=True)
class AlphaFactors:
    """Qlib 风格量化 Alpha 因子向量。"""
    vol_surge: float = 0.0                 # 5日成交量相对20日波动爆发度
    pv_divergence: float = 0.0             # 量价背离度 (-1.0 到 1.0, 负值表示顶背离)
    squeeze_breakout: float = 0.0          # 布林带/通道挤压突破强度
    smart_money_acc: float = 0.0           # 聪明钱多日累积流入强度
    composite_alpha: float = 0.0           # 综合量化因子分 (-1.0 到 1.0)


@dataclass(frozen=True)
class DebateContext:
    """消除方法参数团 (Data Clump) 的辩论输入上下文值对象。"""
    symbol: str
    as_of: str
    price: float
    ma20: float
    ma60: float
    rsi: float
    alpha: AlphaFactors
    ensemble_score: float


@dataclass(frozen=True)
class DebateTranscript:
    """大师辩论对话与陈词记录。"""
    bull_speech: str                       # 利弗莫尔多头立论
    bear_speech: str                       # 芒格/格雷厄姆空头质询与排雷
    bull_rebuttal: str                     # 多头抗辩与补充证据
    cio_summary: str                       # CIO 终审分析
    reflection_rules_cited: list[str] = field(default_factory=list)  # 引用的历史反思规则条目


@dataclass(frozen=True)
class DebateVerdict:
    """多空大师辩论终审裁决。"""
    symbol: str
    as_of: str
    decision: VerdictDecision
    conviction_score: float                # 裁决置信度 0.0 ~ 1.0
    veto_reasons: list[str] = field(default_factory=list)
    transcript: DebateTranscript = field(default_factory=lambda: DebateTranscript("", "", "", ""))


@dataclass(frozen=True)
class ReflectionRecord:
    """事后复盘与经验规则记录。"""
    id: str                                # 记录唯一 ID (如 refl_20260902_600519)
    symbol: str
    timestamp: str
    forecast_direction: SignalDirection    # 强类型枚举替代裸字符串
    actual_return: float                   # Close-to-Close 实际收益率
    pattern_tags: list[str] = field(default_factory=list)
    fatal_blindspot: str = ""              # 致命盲点剖析
    rule_learned: str = ""                 # 提炼出的不可再犯规则
