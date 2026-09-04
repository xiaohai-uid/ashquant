
from ashquant.debate.arena import MasterDebateArena
from ashquant.debate.memory import ReflectionMemory
from ashquant.domain import VerdictDecision


def test_master_debate_bullish_approval(tmp_path):
    mem_file = tmp_path / "test_memory.jsonl"
    memory = ReflectionMemory(file_path=mem_file)
    arena = MasterDebateArena(memory=memory)

    verdict = arena.run_debate(
        symbol="600519",
        as_of="2026-09-02",
        price=1800.0,
        ma20=1750.0,
        ma60=1700.0,
        rsi=60.0,
        vol_surge=0.5,
        pv_divergence=0.1,
        squeeze_breakout=0.4,
        smart_money_acc=0.3,
        ensemble_score=0.65,
    )

    assert verdict.decision == VerdictDecision.BULLISH_APPROVED
    assert verdict.conviction_score >= 0.60
    assert len(verdict.veto_reasons) == 0
    assert "利弗莫尔" in verdict.transcript.bull_speech
    assert "批准做多" in verdict.transcript.cio_summary


def test_master_debate_bearish_veto(tmp_path):
    mem_file = tmp_path / "test_memory.jsonl"
    memory = ReflectionMemory(file_path=mem_file)
    arena = MasterDebateArena(memory=memory)

    # 模拟严重量价顶背离 + 高位超买
    verdict = arena.run_debate(
        symbol="000001",
        as_of="2026-09-02",
        price=15.0,
        ma20=14.0,
        ma60=13.0,
        rsi=82.0,
        vol_surge=0.2,
        pv_divergence=-0.6,
        squeeze_breakout=0.1,
        smart_money_acc=-0.3,
        ensemble_score=0.40,
    )

    assert verdict.decision == VerdictDecision.VETOED_ON_RISK
    assert len(verdict.veto_reasons) >= 1
    assert "一票否决" in verdict.transcript.cio_summary


def test_debate_schema_cleaning_and_validation():
    from ashquant.debate.schemas import (
        DebateVerdictSchema,
        coerce_optional_float,
    )

    # 1. 脏浮点数清洗器 (对标 TradingAgents _NULLISH_FLOAT)
    assert coerce_optional_float("None") is None
    assert coerce_optional_float("n/a") is None
    assert coerce_optional_float("N/A") is None
    assert coerce_optional_float("-") is None
    assert coerce_optional_float("null") is None
    assert coerce_optional_float("") is None
    assert coerce_optional_float("0.85") == 0.85
    assert coerce_optional_float(0.75) == 0.75

    # 2. 脏输入结构化字典清洗校验
    dirty_data = {
        "symbol": "600519",
        "as_of": "2026-09-02",
        "decision": "BULLISH_APPROVED",
        "conviction_score": "0.85",
        "veto_reasons": [],
        "transcript": {
            "bull_speech": "利弗莫尔多头突破",
            "bear_speech": "芒格暂无否决",
            "bull_rebuttal": "趋势良好",
            "cio_summary": "批准做多",
        },
    }

    schema = DebateVerdictSchema.validate_dict(dirty_data)
    assert schema.symbol == "600519"
    assert schema.decision == VerdictDecision.BULLISH_APPROVED
    assert schema.conviction_score == 0.85

    # 3. 校验置信度超出 [0, 1] 范围自动钳制
    clamped_data = dict(dirty_data, conviction_score=1.5)
    schema_clamped = DebateVerdictSchema.validate_dict(clamped_data)
    assert schema_clamped.conviction_score == 1.0

    # 4. 渲染 Markdown 输出
    md = schema.to_markdown()
    assert "# 600519 大师多空辩论裁决报告" in md
    assert "利弗莫尔多头突破" in md


def test_arena_run_debate_schema(tmp_path):
    mem_file = tmp_path / "test_memory.jsonl"
    memory = ReflectionMemory(file_path=mem_file)
    arena = MasterDebateArena(memory=memory)

    schema_verdict = arena.run_debate_schema(
        symbol="600519",
        as_of="2026-09-02",
        price=1800.0,
        ma20=1750.0,
        ma60=1700.0,
        rsi=60.0,
        vol_surge=0.5,
        pv_divergence=0.1,
        squeeze_breakout=0.4,
        smart_money_acc=0.3,
        ensemble_score=0.65,
    )
    assert schema_verdict.decision == VerdictDecision.BULLISH_APPROVED
    assert isinstance(schema_verdict.conviction_score, float)
    json_dict = schema_verdict.to_dict()
    assert json_dict["decision"] == "BULLISH_APPROVED"


