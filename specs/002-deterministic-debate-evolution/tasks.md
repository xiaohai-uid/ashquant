# Implementation Tasks: 002-deterministic-debate-evolution

**Feature**: `deterministic-debate-evolution` (ashquant v0.2.0)  
**Status**: Ready to Implement  

---

## Phase 1: Setup & Data Layer Enhancement

- [ ] T001 Define new core data structures (`CapitalFlow`, `AlphaFactors`, `DebateVerdict`, `ReflectionRecord`) in `src/ashquant/domain.py`
- [ ] T002 [P] Implement A-share alternative data fetchers (Northbound smart money, Margin balances, Super-large fund flow) in `src/ashquant/data/alternative.py`
- [ ] T003 [P] Add unit tests for alternative data fetchers and caching in `tests/test_alternative.py`

---

## Phase 2: Qlib-Style Alpha Factor Zoo

- [ ] T004 Implement causal Alpha Factor calculations (Volume Surge, Price-Volume Divergence, Volatility Squeeze Breakout) in `src/ashquant/alpha/__init__.py`
- [ ] T005 [P] Implement Smart Money Accumulation and composite alpha scoring in `src/ashquant/alpha/factors.py`
- [ ] T006 [P] Add unit tests verifying zero lookahead bias in Alpha Factor calculations in `tests/test_alpha.py`

---

## Phase 3: TradingAgents Master Debate Arena

- [ ] T007 Implement Master Persona prompt templates (Livermore Bull, Munger Bear, Graham Value, CIO Arbitrator) in `src/ashquant/debate/personas.py`
- [ ] T008 Implement `MasterDebateArena` state machine with offline quantitative fallback and online LLM support in `src/ashquant/debate/arena.py`
- [ ] T009 [P] Implement CIO Arbitrator decision engine with strict VETO logic on unmitigated risks in `src/ashquant/debate/arbitrator.py`
- [ ] T010 [P] Add unit tests for `MasterDebateArena` covering Bull approval and Bear VETO triggers in `tests/test_debate.py`

---

## Phase 4: Reflection Memory Flywheel & Regime Breaker

- [ ] T011 Implement `ReflectionMemory` store (`data/reflection_memory.jsonl`) with post-mortem recording and rule retrieval in `src/ashquant/debate/memory.py`
- [ ] T012 Implement `RegimeBreaker` market crash detector and 24-hour account pause circuit in `src/ashquant/backtest/breaker.py`
- [ ] T013 [P] Add unit tests for reflection rule recording and retrieval in `tests/test_reflection.py`
- [ ] T014 [P] Add unit tests for `RegimeBreaker` under simulated market plunge conditions in `tests/test_breaker.py`

---

## Phase 5: Pipeline Synthesis, CLI & Web Interface Enhancement

- [ ] T015 Integrate Alpha Factors, Master Debate Arena, and Regime Breaker into the main `StockAnalysis` pipeline in `src/ashquant/strategy.py`
- [ ] T016 Decompose and enhance CLI commands (`ashquant data`, `ashquant scan`, `ashquant debate`, `ashquant backtest`, `ashquant paper`) in `src/ashquant/cli.py`
- [ ] T017 Update FastAPI routes and Web UI to expose the Master Debate transcripts and Reflection Memory in `src/ashquant/web/`
- [ ] T018 Run end-to-end acceptance run, verify all unit tests pass (`pytest`), verify `ruff` is clean, and verify GitNexus Zero Cycle Gate (`gitnexus check`).
