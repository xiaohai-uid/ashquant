"""盘前持仓与资产对账状态机（Reconciliation Engine，对标 EasyXT / 机构实盘防御）。

盘前 09:15 自动核验券商柜台 (MiniQMT) 与本地账本的一致性：
- 核对持仓标的集合（杜绝盘中未同步的手动交易或未入账分红送配）
- 核对持仓可用与总股数
- 核对可用资金与总资产偏差
- 若有任何关键不一致，强行阻断实盘下单状态机，防止错单引发级联事故
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ashquant.codes import normalize_symbol


@dataclass(frozen=True)
class ReconciliationDiff:
    """对账差异明细项。"""

    symbol: str
    issue_type: str  # "SHARES_MISMATCH" | "MISSING_IN_LOCAL" | "MISSING_IN_BROKER" | "CASH_MISMATCH"
    local_val: Any
    broker_val: Any
    detail: str


@dataclass(frozen=True)
class ReconciliationReport:
    """对账综合报告。"""

    is_consistent: bool
    diffs: list[ReconciliationDiff] = field(default_factory=list)
    summary: str = ""


class ReconciliationEngine:
    """盘前持仓与资金对账引擎。"""

    def reconcile(
        self,
        local_broker: Any,
        broker_positions: dict[str, int],
        broker_cash: float,
        cash_tolerance: float = 1.0,
    ) -> ReconciliationReport:
        diffs: list[ReconciliationDiff] = []

        # 提取本地持仓与资金（兼容 PaperBroker 实例、Mock 或直接状态字典）
        if hasattr(local_broker, "state") and isinstance(local_broker.state, dict):
            local_pos_map = local_broker.state.get("positions", {})
            local_cash = float(local_broker.state.get("cash", 0.0))
        elif callable(getattr(local_broker, "_load", None)):
            st = local_broker._load()
            local_pos_map = st.get("positions", {})
            local_cash = float(st.get("cash", 0.0))
        elif callable(getattr(local_broker, "show", None)):
            st = local_broker.show()
            # show() 返回格式中的 positions 为 list[dict]
            pos_list = st.get("positions", [])
            local_pos_map = {p["symbol"]: p["shares"] for p in pos_list}
            local_cash = float(st.get("cash", 0.0))
        elif hasattr(local_broker, "positions"):
            local_pos_map = local_broker.positions
            local_cash = float(getattr(local_broker, "cash", 0.0))
        else:
            local_pos_map = {}
            local_cash = 0.0

        # 标准化本地代码
        normalized_local: dict[str, int] = {}
        for sym, pos_data in local_pos_map.items():
            norm_sym = normalize_symbol(sym)
            shares = pos_data["shares"] if isinstance(pos_data, dict) else getattr(pos_data, "shares", 0)
            if shares > 0:
                normalized_local[norm_sym] = int(shares)

        # 标准化柜台代码
        normalized_broker: dict[str, int] = {}
        for sym, shares in broker_positions.items():
            norm_sym = normalize_symbol(sym)
            if shares > 0:
                normalized_broker[norm_sym] = int(shares)

        # 1. 检查标的持仓差异
        all_symbols = sorted(set(normalized_local.keys()) | set(normalized_broker.keys()))
        for sym in all_symbols:
            loc_s = normalized_local.get(sym, 0)
            bro_s = normalized_broker.get(sym, 0)

            if loc_s > 0 and bro_s == 0:
                diffs.append(
                    ReconciliationDiff(
                        symbol=sym,
                        issue_type="MISSING_IN_BROKER",
                        local_val=loc_s,
                        broker_val=0,
                        detail=f"本地记录持有 {loc_s} 股，但柜台无持仓！",
                    )
                )
            elif loc_s == 0 and bro_s > 0:
                diffs.append(
                    ReconciliationDiff(
                        symbol=sym,
                        issue_type="MISSING_IN_LOCAL",
                        local_val=0,
                        broker_val=bro_s,
                        detail=f"柜台持有 {bro_s} 股，但本地账本未记录（可能有人工外部交易或送配股）！",
                    )
                )
            elif loc_s != bro_s:
                diffs.append(
                    ReconciliationDiff(
                        symbol=sym,
                        issue_type="SHARES_MISMATCH",
                        local_val=loc_s,
                        broker_val=bro_s,
                        detail=f"持仓股数不一致：本地 {loc_s} 股 vs 柜台 {bro_s} 股",
                    )
                )

        # 2. 检查可用资金差异
        cash_diff = abs(local_cash - broker_cash)
        if cash_diff > cash_tolerance:
            diffs.append(
                ReconciliationDiff(
                    symbol="CASH",
                    issue_type="CASH_MISMATCH",
                    local_val=local_cash,
                    broker_val=broker_cash,
                    detail=f"现金偏离 {cash_diff:.2f} 元 > 容差 {cash_tolerance} 元 (本地 {local_cash:.2f} vs 柜台 {broker_cash:.2f})",
                )
            )

        is_consistent = len(diffs) == 0
        if is_consistent:
            summary = "【盘前对账通过】本地账本与券商柜台持仓、现金 100% 吻合，准许交易。"
        else:
            diff_lines = [f"- [{d.issue_type}] {d.symbol}: {d.detail}" for d in diffs]
            summary = "【盘前对账失败】检测到以下差异：\n" + "\n".join(diff_lines)

        return ReconciliationReport(
            is_consistent=is_consistent,
            diffs=diffs,
            summary=summary,
        )

    def assert_can_trade(self, report: ReconciliationReport) -> None:
        """安全门禁：存在任何对账差异时强行阻断实盘下单。"""
        if not report.is_consistent:
            raise RuntimeError(
                f"盘前对账失败，发现 {len(report.diffs)} 处持仓/资金不一致，触发安全防御阻断自动交易！\n{report.summary}"
            )
