"""事后反思自进化记忆库（ReflectionMemory）。

闭环学习飞轮：
1. 预测到期结算时，若产生显著亏损（>2%）或触发出场止损，自动提取隐蔽盲点与形态特征。
2. 提炼为「不可再犯经验规则」追加持久化到 data/reflection_memory.jsonl。
3. 在未来的多空大师辩论中，基于特征标签自动检索并注入空头 Agent 作为风险预警。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ashquant.config import DATA_DIR
from ashquant.domain import ReflectionRecord

logger = logging.getLogger(__name__)

MEMORY_FILE = DATA_DIR / "reflection_memory.jsonl"


class ReflectionMemory:
    """反思记忆管理器。"""

    def __init__(self, file_path: Path = MEMORY_FILE):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("", encoding="utf-8")

    def record_post_mortem(
        self,
        symbol: str,
        timestamp: str,
        forecast_direction: str,
        actual_return: float,
        pattern_tags: list[str],
        fatal_blindspot: str,
        rule_learned: str,
    ) -> ReflectionRecord:
        """记录一条失败反思剖析并持久化。"""
        rec_id = f"refl_{timestamp.replace('-', '').replace(':', '')[:12]}_{symbol}"
        record = ReflectionRecord(
            id=rec_id,
            symbol=symbol,
            timestamp=timestamp,
            forecast_direction=forecast_direction,
            actual_return=actual_return,
            pattern_tags=pattern_tags,
            fatal_blindspot=fatal_blindspot,
            rule_learned=rule_learned,
        )

        line_data = {
            "id": record.id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "forecast_direction": record.forecast_direction,
            "actual_return": record.actual_return,
            "pattern_tags": record.pattern_tags,
            "fatal_blindspot": record.fatal_blindspot,
            "rule_learned": record.rule_learned,
        }

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line_data, ensure_ascii=False) + "\n")

        logger.info("已记录反思规则 [%s]: %s", symbol, rule_learned)
        return record

    def load_all(self) -> list[ReflectionRecord]:
        """加载所有历史反思记录。"""
        if not self.file_path.exists():
            return []
        records = []
        with open(self.file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(
                        ReflectionRecord(
                            id=d["id"],
                            symbol=d["symbol"],
                            timestamp=d["timestamp"],
                            forecast_direction=d["forecast_direction"],
                            actual_return=float(d["actual_return"]),
                            pattern_tags=d.get("pattern_tags", []),
                            fatal_blindspot=d.get("fatal_blindspot", ""),
                            rule_learned=d.get("rule_learned", ""),
                        )
                    )
                except Exception as e:
                    logger.debug("解析反思记录行失败: %s", e)
        return records

    def retrieve_relevant_rules(
        self,
        symbol: str,
        current_tags: list[str] | None = None,
        pattern_tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[str]:
        """检索与当前标的或形态相关的历史教训规则（兼容 current_tags 与 pattern_tags 参数命名）。"""
        all_recs = self.load_all()
        tags = current_tags or pattern_tags

        if not all_recs:
            return [
                "【通用戒律】严禁在量价顶背离且主力资金持续流出时追高突破。",
                "【流动性警示】牢记 A 股 T+1 规则，禁止在尾盘异动缺乏次日承接时盲目开仓。",
            ]

        matching_rules = []
        # 1. 优先匹配同股票历史教训
        for r in reversed(all_recs):
            if r.symbol == symbol and r.rule_learned:
                matching_rules.append(f"【{symbol}历史警示】{r.rule_learned} (教训: {r.fatal_blindspot})")

        # 2. 匹配同形态标签教训
        if tags:
            tag_set = set(tags)
            for r in reversed(all_recs):
                if tag_set.intersection(set(r.pattern_tags)) and r.rule_learned:
                    formatted = f"【形态避坑】{r.rule_learned}"
                    if formatted not in matching_rules:
                        matching_rules.append(formatted)

        # 3. 补充最近的全局通用教训
        for r in reversed(all_recs):
            formatted = f"【全局反思】{r.rule_learned}"
            if formatted not in matching_rules:
                matching_rules.append(formatted)
            if len(matching_rules) >= limit:
                break

        return matching_rules[:limit]
