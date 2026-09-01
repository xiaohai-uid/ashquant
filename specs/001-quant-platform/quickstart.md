# Quickstart 验证指南（发布前逐条真实验收）

前置：Python 3.12+、uv（或 pip）、可访问国内行情源（东财）。

```bash
# 1. 安装（≤3 条命令目标）
uv sync --extra web          # 或: pip install -e ".[web]"

# 2. 单测（不触网，合成数据）
uv run pytest -q             # 全绿

# 3. 真实数据端到端
uv run ashquant fetch --pool sample20          # 20 只×3 年日线入缓存
uv run ashquant watch --symbols 600519,300750 --once   # 实时快照
uv run ashquant backtest --pool sample20       # 三年回测+基准+预测日志
uv run ashquant predict --symbols 600519       # 明日预测+大师观点
uv run ashquant paper init && uv run ashquant paper buy 600519 --qty 100
uv run ashquant paper show

# 4. Web 控制台
uv run ashquant web           # 浏览器 http://127.0.0.1:8000
```

预期结果（= 验收断言）：

- [ ] fetch：`data/bars/*.parquet` ≥20 个文件，元数据含 fetched_at；中断重跑只补缺失。
- [ ] watch：表格含现价/涨跌幅；非交易时段标注最后快照时间。
- [ ] backtest：输出收益/年化/回撤/夏普/胜率 + 沪深300 基准对照 + 零成本敏感性；
      `results/backtest_*.json` 含逐日预测日志；**重跑两次结果逐字节一致**（diff 验证）。
- [ ] predict：方向/概率/置信度 + ≥4 位大师观点（含名言出处）；`<120` 交易日的标的
      被拒绝并说明。
- [ ] paper：买入扣款含佣金（最低 5 元）；当日买当日卖被 T+1 拒绝；对账单流水与
      现金变动勾稽一致。
- [ ] web：10 秒内见快照表与 K 线；预测按钮出观点卡片；页面含免责声明。
- [ ] 发布检查：`git ls-files | xargs grep -l "TOKEN\|SECRET\|PASSWORD"` 无命中
      （密钥扫描）；README 三命令可完成安装+测试+启动。
