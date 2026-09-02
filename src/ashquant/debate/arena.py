"""MasterDebateArena 多空大师对抗辩论状态机（Adversarial Debate Arena）。

实现两级博弈架构：
1. 离线定量模式 (Deterministic Offline Engine)：
   - 基于 Alpha 因子、Master 信号与反思记忆规则进行严苛的逻辑对抗。
   - 保证无网络、无外部 API 时 100% 确定性产出专业的多空辩论记录与裁决。
2. 在线大模型模式 (Online LLM Enhancement)：
   - 若检测到环境变量 `ASHQUANT_LLM_API_KEY`，可选择调用外部 LLM 丰富自然语言辩驳。
"""

from __future__ import annotations

import logging

from ashquant.debate.memory import ReflectionMemory
from ashquant.domain import (
    AlphaFactors,
    DebateContext,
    DebateTranscript,
    DebateVerdict,
    VerdictDecision,
)

logger = logging.getLogger(__name__)


class MasterDebateArena:
    """多空大师对抗辩论竞技场。"""

    def __init__(self, memory: ReflectionMemory | None = None):
        self.memory = memory or ReflectionMemory()

    def run_debate(
        self,
        symbol: str,
        as_of: str,
        price: float,
        ma20: float,
        ma60: float,
        rsi: float,
        alpha: AlphaFactors | None = None,
        ensemble_score: float = 0.0,
        # 兼容旧单标量参数以平滑过渡
        vol_surge: float | None = None,
        pv_divergence: float | None = None,
        squeeze_breakout: float | None = None,
        smart_money_acc: float | None = None,
    ) -> DebateVerdict:
        """执行完整的多空大师对抗辩论，支持封装值对象与兼容调用。"""
        if alpha is None:
            alpha = AlphaFactors(
                vol_surge=vol_surge or 0.0,
                pv_divergence=pv_divergence or 0.0,
                squeeze_breakout=squeeze_breakout or 0.0,
                smart_money_acc=smart_money_acc or 0.0,
            )

        ctx = DebateContext(
            symbol=symbol,
            as_of=as_of,
            price=price,
            ma20=ma20,
            ma60=ma60,
            rsi=rsi,
            alpha=alpha,
            ensemble_score=ensemble_score,
        )

        return self.debate_context(ctx)

    def debate_context(self, ctx: DebateContext) -> DebateVerdict:
        """基于 DebateContext 值对象执行辩论。"""
        # 1. 提取形态标签与相关历史反思规则
        pattern_tags = []
        if ctx.alpha.vol_surge > 0.4:
            pattern_tags.append("high_volume_breakout")
        if ctx.alpha.pv_divergence < -0.3:
            pattern_tags.append("top_divergence")
        if ctx.rsi > 70:
            pattern_tags.append("rsi_overbought")

        rules_cited = self.memory.retrieve_relevant_rules(ctx.symbol, pattern_tags, limit=3)
        rules_text = "\n".join(f"- {r}" for r in rules_cited)

        # 2. 生成多头陈词 (Livermore Bull)
        bull_speech = self._generate_bull_speech(ctx)

        # 3. 生成空头排雷质询 (Munger Bear)
        bear_speech, veto_reasons = self._generate_bear_speech(ctx, rules_text)

        # 4. 生成多头反驳 (Rebuttal)
        bull_rebuttal = self._generate_bull_rebuttal(bull_speech, bear_speech, ctx.alpha.smart_money_acc, ctx.alpha.vol_surge)

        # 5. CIO 终审裁决
        decision, conviction, cio_summary = self._arbitrate(ctx, veto_reasons, bull_speech, bear_speech)

        transcript = DebateTranscript(
            bull_speech=bull_speech,
            bear_speech=bear_speech,
            bull_rebuttal=bull_rebuttal,
            cio_summary=cio_summary,
            reflection_rules_cited=rules_cited,
        )

        return DebateVerdict(
            symbol=ctx.symbol,
            as_of=ctx.as_of,
            decision=decision,
            conviction_score=conviction,
            veto_reasons=veto_reasons,
            transcript=transcript,
        )

    def _generate_bull_speech(self, ctx: DebateContext) -> str:
        points = []
        if ctx.price > ctx.ma20:
            points.append(f"股价稳定运行于 20 日均线 ({ctx.ma20:.2f}) 上方，中期均线呈多头排列形态。")
        if ctx.alpha.vol_surge > 0.2:
            points.append(f"成交量爆发度达到 {ctx.alpha.vol_surge:.2f}，增量资金进场推升，动能充沛。")
        if ctx.alpha.smart_money_acc > 0.1:
            points.append(f"主力超大单与聪明钱累积流向评分 {ctx.alpha.smart_money_acc:.2f}，机构持仓坚挺。")
        if ctx.alpha.squeeze_breakout > 0.3:
            points.append("布林带波动率通道压缩后向上放量突破，主升浪特征显著。")

        if not points:
            points.append(f"当前技术面维持震荡整理，综合大师评分 {ctx.ensemble_score:.2f}，等待右侧放量信号。")

        return (
            "【利弗莫尔·多头立论】：\n"
            "根据杰西·利弗莫尔的趋势指引——'股价沿着阻力最小的路线前进'。\n"
            + "\n".join(f"- {p}" for p in points)
            + "\n【结论】：多头动能已形成共振，建议顺应主趋势建仓！"
        )

    def _generate_bear_speech(self, ctx: DebateContext, rules_text: str) -> tuple[str, list[str]]:
        veto_reasons = []
        critiques = []

        if ctx.alpha.pv_divergence < -0.4:
            critiques.append(f"量价存在严重顶背离 (背离评分 {ctx.alpha.pv_divergence:.2f})，存在主力高位拉高出货嫌疑。")
            veto_reasons.append("严重量价顶背离，假突破风险极高")
        if ctx.rsi > 75:
            critiques.append(f"RSI 处于高位超买区 ({ctx.rsi:.1f})，短线获利盘回吐压力巨大。")
            veto_reasons.append("短期严重超买，盈亏比失衡")
        if ctx.alpha.smart_money_acc < -0.2:
            critiques.append(f"主力大单持续净流出 (评分 {ctx.alpha.smart_money_acc:.2f})，缺乏真实大资金支撑。")
            veto_reasons.append("主力大单与北向资金流向背离")
        if ctx.price < ctx.ma60:
            critiques.append(f"价格仍处于 60 日生命线 ({ctx.ma60:.2f}) 压制之下，属于下跌中继反弹而非主升浪。")

        critiques.append("牢记 A 股 T+1 交易制度：一旦当日高位追入被套，次日开盘前无平仓机会。")

        if not veto_reasons:
            critiques.append("常规风险提示：严格设置 3%~4% 追踪止损位，防范大盘系统性突发回撤。")

        bear_text = (
            "【芒格/格雷厄姆·空头质询与排雷】：\n"
            "根据查理·芒格的逆向思维——'如果我知道我会死在哪里，我将永远不去那个地方'。\n"
            + "\n".join(f"- {c}" for c in critiques)
            + f"\n\n【引用的历史反思禁忌】：\n{rules_text}"
        )

        return bear_text, veto_reasons

    def _generate_bull_rebuttal(self, bull: str, bear: str, smart_money: float, vol_surge: float) -> str:
        if smart_money > 0.2 and vol_surge > 0.3:
            return "【多头抗辩】：空头提示的流动性风险已知悉，但主力大单与换手率深度证明并非虚涨，趋势惯性将消化短期浮筹。"
        return "【多头抗辩】：认可空头对安全边际的审慎提醒，建议采取轻仓分批试探，而非一次性激进重仓。"

    def _arbitrate(
        self,
        ctx: DebateContext,
        veto_reasons: list[str],
        bull_speech: str,
        bear_speech: str,
    ) -> tuple[VerdictDecision, float, str]:
        # 一票否决硬约束
        if veto_reasons:
            summary = (
                f"【CIO 终审裁决：一票否决 (VETOED)】\n"
                f"空头指出了未被化解的致命风险：{'; '.join(veto_reasons)}。\n"
                f"在确定性门禁面前，防守永远先于进攻，强制终止本次买入计划！"
            )
            return VerdictDecision.VETOED_ON_RISK, 0.20, summary

        # 多头胜出条件
        if ctx.ensemble_score >= 0.45 and ctx.alpha.vol_surge > 0.1 and ctx.alpha.smart_money_acc >= 0.0:
            conviction = min(0.92, 0.60 + ctx.ensemble_score * 0.3 + ctx.alpha.vol_surge * 0.1)
            summary = (
                f"【CIO 终审裁决：批准做多 (BULLISH_APPROVED)】\n"
                f"多头在量价突破与资金共振上提供了充分依据，且通过了空头的全项排雷审查。\n"
                f"核定做多置信度为 {conviction:.2%}，批准执行开仓计划。"
            )
            return VerdictDecision.BULLISH_APPROVED, conviction, summary

        # 双方均衡或分歧
        summary = (
            "【CIO 终审裁决：观望等待 (NEUTRAL_WAIT)】\n"
            "当前多空双方证据均未达到 Grade AAA 共振标准，建议保留资金，等待确定性信号出现。"
        )
        return VerdictDecision.NEUTRAL_WAIT, 0.50, summary
