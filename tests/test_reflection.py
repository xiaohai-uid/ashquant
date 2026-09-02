
from ashquant.debate.memory import ReflectionMemory


def test_reflection_memory_lifecycle(tmp_path):
    mem_file = tmp_path / "test_memory.jsonl"
    memory = ReflectionMemory(file_path=mem_file)

    assert len(memory.load_all()) == 0

    # 记录一条教训
    rec = memory.record_post_mortem(
        symbol="600519",
        timestamp="2026-09-02T15:00:00",
        forecast_direction="UP",
        actual_return=-0.035,
        pattern_tags=["high_volume_breakout", "top_divergence"],
        fatal_blindspot="高位早盘放量出货被误认为突破",
        rule_learned="严禁在顶背离且北向流出超过3亿时追高",
    )

    assert rec.symbol == "600519"
    all_recs = memory.load_all()
    assert len(all_recs) == 1
    assert all_recs[0].rule_learned == "严禁在顶背离且北向流出超过3亿时追高"

    # 针对同股票检索
    rules = memory.retrieve_relevant_rules("600519", pattern_tags=["high_volume_breakout"])
    assert len(rules) >= 1
    assert "严禁在顶背离且北向流出超过3亿时追高" in rules[0]
