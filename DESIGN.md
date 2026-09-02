# ashquant Design System Tokens & Guidelines

> 本规范基于 [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 优秀的金融与专业工具系统（Binance 交易层级 + Linear 精密暗黑发丝线）转译而成，服务于 A股量化投研与交易场景。

---

## 🎨 Design Tokens (色彩与层级)

```css
:root {
  /* Canvas & Surfaces (深度暗黑，层级分明) */
  --canvas: #090d16;          /* 底层画布 (Deep Slate Navy) */
  --surface-card: #131b2a;    /* 一级卡片容器 */
  --surface-elevated: #1e293b;/* 二级悬浮/活跃项 */
  --surface-soft: #0f172a;    /* 内部凹陷容器/输入框背景 */

  /* Hairlines & Borders (高精度发丝线) */
  --hairline: #1e293b;        /* 常规分割线 */
  --hairline-strong: #334155; /* 强调边框 / 表格头 */
  --hairline-focus: #38bdf8;  /* 聚焦外边框 */

  /* Typography Colors (字阶清晰，弱对比防疲劳) */
  --ink: #f8fafc;             /* 主文本 (High Contrast) */
  --ink-muted: #94a3b8;       /* 次要说明 / 指标名称 */
  --ink-subtle: #64748b;      /* 辅助弱文本 / 名言出处 */
  --ink-dim: #475569;         /* 占位符 / 禁用文本 */

  /* Semantic A-Share Trading Colors (A股经典：红涨绿跌) */
  --trading-up: #ef4444;      /* 涨 / 看多 / 正收益 */
  --trading-up-bg: #ef444415; /* 涨色微透明背景标签 */
  --trading-down: #22c55e;    /* 跌 / 看空 / 负收益 */
  --trading-down-bg: #22c55e15;/* 跌色微透明背景标签 */
  --trading-neutral: #f59e0b; /* 观望 / 平盘 */

  /* Brand Accents (科技蓝与黄金重点) */
  --accent-cyan: #38bdf8;     /* 重点高亮 / 核心数据 */
  --accent-amber: #fbbf24;    /* 大师名言 / 重点警示 */
  --accent-purple: #c084fc;   /* 长期均线 / 特殊状态 */
}
```

---

## 📐 Typography & Hierarchy (排版与数字呈现)

- **字体栈**：优先使用系统高可读无衬线体 `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif`。
- **金额与价格**：数值类采用等宽特性 `font-feature-settings: "tnum" 1`，保证表格与看板中价格上下对齐不抖动。
- **信息层级**：
  - **H1 / 大屏标题**：18px / 700 权重 / 品牌 Accent 色
  - **卡片标题**：14px / 600 权重 / Ink
  - **表格正文 / 价格**：13px / 500 权重
  - **辅助标签 / 状态**：11px ~ 12px / 400 权重 / Muted

---

## 📊 Component Specifications (组件规范)

1. **自选股快照看板 (Spot Table)**：
   - 紧凑网格（Row Height ~36px），双色微弱行交替或 Hover 显亮。
   - 涨跌幅采用微透明背景胶囊 (`padding: 2px 6px; border-radius: 4px`)，增强扫描效率。

2. **大师信号卡片 (Master Signal Card)**：
   - 双层结构：上层为大师打分与哲学标签，中层为核心量化因果理由，下层为引用名言与一手出处。
   - 引用名言左侧配置 2px Accent 彩色竖线。

3. **TradingView K 线图表区 (Chart Container)**：
   - 深色背景与全局 Canvas 浑然一体，MA5 (黄)、MA20 (蓝)、MA60 (紫) 使用 1px 细发丝线。
   - 成交量 Histogram 置于底部 20% 空间，涨红跌绿 40% 透明度。
