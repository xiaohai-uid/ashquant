# Data Model: 002-deterministic-debate-evolution

## 1. New Core Entities

### 1.1 `CapitalFlow` (主力与特色资金流)
```python
@dataclass(frozen=True)
class CapitalFlow:
    date: str
    symbol: str
    northbound_net_shares: float     # 北向资金净买入股数
    northbound_hold_ratio: float     # 北向资金占流通股比率
    margin_balance: float            # 融资余额
    margin_buy_amount: float         # 融资买入额
    super_large_net_inflow: float    # 超大单净流入金额 (元)
    large_net_inflow: float          # 大单净流入金额 (元)
```

### 1.2 `AlphaFactors` (量化 Alpha 向量)
```python
@dataclass(frozen=True)
class AlphaFactors:
    vol_surge: float                 # 5日成交量相对20日波动爆发度
    pv_divergence: float             # 量价背离度 (-1.0 到 1.0, 负值表示顶背离)
    squeeze_breakout: float          # 布林带/通道挤压突破强度
    smart_money_acc: float           # 聪明钱多日累积流入强度
    composite_alpha: float           # 综合量化因子分
```

### 1.3 `DebateVerdict` (多空大师辩论裁决)
```python
class VerdictDecision(str, Enum):
    BULLISH_APPROVED = "BULLISH_APPROVED"  # 多头获胜且通过风控，建议做多
    VETOED_ON_RISK = "VETOED_ON_RISK"      # 空头指出致命硬伤，一票否决
    BEARISH_REJECTED = "BEARISH_REJECTED"  # 空头占优，明确看空
    NEUTRAL_WAIT = "NEUTRAL_WAIT"          # 双方分歧过大或无显著催化剂，观望

@dataclass(frozen=True)
class DebateTranscript:
    bull_speech: str                 # 利弗莫尔多头立论
    bear_speech: str                 # 芒格/格雷厄姆空头质询与排雷
    bull_rebuttal: str               # 多头抗辩与补充证据
    cio_summary: str                 # CIO 终审分析
    reflection_rules_cited: list[str]# 引用的历史反思规则条目

@dataclass(frozen=True)
class DebateVerdict:
    symbol: str
    as_of: str
    decision: VerdictDecision
    conviction_score: float          # 裁决置信度 0.0 ~ 1.0
    veto_reasons: list[str]          # 否决或看空硬伤清单
    transcript: DebateTranscript
```

### 1.4 `ReflectionRecord` (事后复盘与经验规则)
```python
@dataclass(frozen=True)
class ReflectionRecord:
    id: str                          # e.g., "refl_20260902_600519"
    symbol: str
    timestamp: str
    forecast_direction: str          # "UP" / "DOWN"
    actual_return: float             # Close-to-Close 实际收益率
    pattern_tags: list[str]          # ["high_volume_breakout", "rsi_overbought"]
    fatal_blindspot: str             # 致命盲点剖析
    rule_learned: str                # 提炼出的不可再犯规则
```
