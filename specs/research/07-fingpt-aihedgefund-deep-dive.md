# 07. FinGPT & ai-hedge-fund Deep Dive: Financial LLMs & Guru Agent Architectures

## 1. AI4Finance FinGPT - Financial LLM & Sentiment Pipeline

### 1.1 Core Architecture Patterns
- **Open-Source Financial Data-Centric LLM**:
  - Rather than training trillion-token LLMs from scratch, FinGPT applies Parameter-Efficient Fine-Tuning (PEFT, specifically LoRA/QLoRA) on base open models (e.g., LLaMA-2/3, ChatGLM-3, Qwen-2).
- **Instruction Tuning for Financial NLP**:
  - Tasks include:
    1. Financial Sentiment Analysis (News headline / tweet -> Positive / Negative / Neutral + score $\in [-1, 1]$).
    2. Quantitative Question Answering (Earnings call transcripts -> Margin trend forecast).
    3. Named Entity & Relation Extraction (Identify ticker mentions and executive departures).
- **Prompt Engineering for Numeric Outputs**:
  - Enforces JSON output with explicit confidence ratings:
    ```json
    {
      "sentiment": "positive",
      "score": 0.85,
      "reasoning": "Substantial Q3 net profit surge exceeding consensus estimates, gross margin expanded by 340 bps."
    }
    ```
- **A-Share Adaptation**:
  - Using Chinese open-weight models (Qwen-2.5 / DeepSeek-V3 / ChatGLM), financial news from EastMoney, Sina Finance, and Xueqiu can be distilled into structured polarity scores without needing dedicated training clusters.

### 1.2 Applicability to ashquant
- `ashquant` already features a `sentiment` master agent modeled after Buffett's greed/fear doctrine.
- **Takeaway for v0.2.0**: Allow `ashquant` to accept an optional LLM provider (e.g., DeepSeek-V3 / Qwen) to score the latest company announcement and market headlines, providing an empirical NLP sentiment signal that complements technical price-volume indicators.

---

## 2. virattt/ai-hedge-fund (63.1k Stars) - Multi-Guru Agent System

### 2.1 Core Architectural Patterns
- **Named Master Agent Personas**:
  - Each agent represents a legendary investor:
    - **Warren Buffett**: Focuses on moat, low debt, consistent ROE, high free cash flow.
    - **Charlie Munger**: Looks for capital allocation discipline, pricing power, avoidance of stupidity.
    - **Peter Lynch**: Searches for PEG ratio, earnings growth visibility, simple business models.
    - **Ray Dalio**: Macro regime matching, all-weather risk parity, debt cycle evaluation.
    - **Bill Ackman / Carl Icahn**: Activist value catalysts, buyback potential, undervaluation.
- **Workflow / LangGraph State Orchestration**:
  1. Data Gathering Node (pulls historical financials, ratios, price bars).
  2. Analyst Nodes (each Guru evaluates the data concurrently and produces a structured thesis + conviction rating).
  3. Risk Manager Node (evaluates portfolio correlation, max drawdown constraints, leverage limits).
  4. Portfolio Manager Node (weighs the Guru votes, reconciles disagreements, decides target sizing).

### 2.2 Applicability to ashquant
- `ashquant`'s architectural blueprint already aligns with this philosophy, but with **critical superiorities**:
  - `ai-hedge-fund` is mostly US-market oriented, lacks A-share microstructure (T+1, 10%/20% limits, stamp duty), and lacks quantitative walk-forward probability calibration.
  - `ashquant` fuses **vectorized quantitative signals** with **verifiable master quotes** and rigorous **backtest fill simulation**.
- **Takeaway for v0.2.0**:
  - Upgrade `ashquant`'s master agents into a dual-mode engine:
    - **Mode A (Quantitative Fast Path)**: Pure vectorized indicators (instant, 0 latency, 0 token cost).
    - **Mode B (Master Debate LLM Path)**: An opt-in LangGraph debate arena where Master personas cross-examine quantitative evidence and produce audited debate verdicts.
