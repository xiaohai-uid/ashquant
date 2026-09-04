"""Multi-Agent 强类型 Schema 与容错数据清洗模块（对标 TradingAgents 架构）。

设计要点：
- 强类型 Pydantic/Dataclass 约束智能体推理产物
- 内置 _NULLISH_FLOAT 容错清洗器，自动修复 LLM 偶尔产出的脏浮点占位符
- 双向适配：支持与底层领域模型无缝互转及生成 Markdown 审计报告
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ashquant.domain import DebateTranscript, DebateVerdict, VerdictDecision

# 常见 LLM 异常占位字符
_NULLISH_FLOAT = {"", "none", "n/a", "na", "null", "nil", "-", "tbd", "unknown"}


def coerce_optional_float(value: Any) -> float | None:
    """针对金融 LLM 经常输出占位字符串 (None, N/A, -) 的容错浮点数转换器。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in _NULLISH_FLOAT:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class DebateTranscriptSchema:
    """辩论实录强类型模式。"""

    bull_speech: str = ""
    bear_speech: str = ""
    bull_rebuttal: str = ""
    cio_summary: str = ""
    reflection_rules_cited: list[str] = field(default_factory=list)

    @classmethod
    def from_domain(cls, t: DebateTranscript) -> DebateTranscriptSchema:
        return cls(
            bull_speech=t.bull_speech,
            bear_speech=t.bear_speech,
            bull_rebuttal=t.bull_rebuttal,
            cio_summary=t.cio_summary,
            reflection_rules_cited=list(t.reflection_rules_cited),
        )

    def to_domain(self) -> DebateTranscript:
        return DebateTranscript(
            bull_speech=self.bull_speech,
            bear_speech=self.bear_speech,
            bull_rebuttal=self.bull_rebuttal,
            cio_summary=self.cio_summary,
            reflection_rules_cited=list(self.reflection_rules_cited),
        )


@dataclass(frozen=True)
class DebateVerdictSchema:
    """辩论裁决强类型模式。"""

    symbol: str
    as_of: str
    decision: VerdictDecision
    conviction_score: float
    veto_reasons: list[str] = field(default_factory=list)
    transcript: DebateTranscriptSchema = field(default_factory=DebateTranscriptSchema)

    @classmethod
    def validate_dict(cls, data: dict[str, Any]) -> DebateVerdictSchema:
        """解析并清洗原始字典数据（支持脏数据容错）。"""
        symbol = str(data.get("symbol", ""))
        as_of = str(data.get("as_of", ""))

        raw_decision = data.get("decision", VerdictDecision.NEUTRAL_WAIT)
        if isinstance(raw_decision, VerdictDecision):
            decision = raw_decision
        else:
            try:
                decision = VerdictDecision(str(raw_decision))
            except ValueError:
                decision = VerdictDecision.NEUTRAL_WAIT

        score_val = coerce_optional_float(data.get("conviction_score"))
        if score_val is None:
            conviction_score = 0.50
        else:
            conviction_score = max(0.0, min(1.0, float(score_val)))

        veto_reasons = list(data.get("veto_reasons") or [])

        raw_transcript = data.get("transcript") or {}
        if isinstance(raw_transcript, DebateTranscript):
            transcript = DebateTranscriptSchema.from_domain(raw_transcript)
        elif isinstance(raw_transcript, DebateTranscriptSchema):
            transcript = raw_transcript
        elif isinstance(raw_transcript, dict):
            transcript = DebateTranscriptSchema(
                bull_speech=str(raw_transcript.get("bull_speech", "")),
                bear_speech=str(raw_transcript.get("bear_speech", "")),
                bull_rebuttal=str(raw_transcript.get("bull_rebuttal", "")),
                cio_summary=str(raw_transcript.get("cio_summary", "")),
                reflection_rules_cited=list(raw_transcript.get("reflection_rules_cited") or []),
            )
        else:
            transcript = DebateTranscriptSchema()

        return cls(
            symbol=symbol,
            as_of=as_of,
            decision=decision,
            conviction_score=conviction_score,
            veto_reasons=veto_reasons,
            transcript=transcript,
        )

    @classmethod
    def from_domain(cls, v: DebateVerdict) -> DebateVerdictSchema:
        return cls(
            symbol=v.symbol,
            as_of=v.as_of,
            decision=v.decision,
            conviction_score=v.conviction_score,
            veto_reasons=list(v.veto_reasons),
            transcript=DebateTranscriptSchema.from_domain(v.transcript),
        )

    def to_domain(self) -> DebateVerdict:
        return DebateVerdict(
            symbol=self.symbol,
            as_of=self.as_of,
            decision=self.decision,
            conviction_score=self.conviction_score,
            veto_reasons=list(self.veto_reasons),
            transcript=self.transcript.to_domain(),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        return d

    def to_markdown(self) -> str:
        """渲染为结构化审计报告 Markdown（对标 TradingAgents Render Helper）。"""
        lines = [
            f"# {self.symbol} 大师多空辩论裁决报告",
            f"- **评估基准日**: {self.as_of}",
            f"- **最终裁决**: `{self.decision.value}`",
            f"- **置信度评分**: `{self.conviction_score:.2f}`",
        ]
        if self.veto_reasons:
            lines.append("### ⚠️ 一票否决原因")
            for r in self.veto_reasons:
                lines.append(f"- {r}")

        lines.extend([
            "### 🐂 多头立论 (利弗莫尔视角)",
            self.transcript.bull_speech or "（无）",
            "### 🐻 空头风控审计 (芒格/格雷厄姆视角)",
            self.transcript.bear_speech or "（无）",
            "### 🔄 多头抗辩",
            self.transcript.bull_rebuttal or "（无）",
            "### ⚖️ CIO 仲裁结论",
            self.transcript.cio_summary or "（无）",
        ])
        return "\n\n".join(lines)
