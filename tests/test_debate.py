
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
