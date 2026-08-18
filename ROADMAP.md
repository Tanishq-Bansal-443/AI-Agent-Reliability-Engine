# Implementation Roadmap

## Overview

```
Phase 0  — Foundation + Core Contracts
Phase 1  — Vertical Slice
Phase 2  — Profiler
Phase 3  — Scenario Engine
Phase 4  — Sandbox + Execution
Phase 5  — Evaluation
Phase 6  — Failure Intelligence
Phase 7  — Reliability Scoring
Phase 8  — Regression
Phase 9  — Dashboard
Phase 10 — Adaptive Testing
Phase 11 — Version Comparison
Phase 12 — Predictive Reliability
Phase 13 — Polish + Demo
```

---

## Phase 0 — Foundation + Core Contracts

**Objective**: Establish the repo structure, all core Pydantic contracts, and base abstractions. Nothing executes yet, but every interface is defined.

**Dependencies**: None.

**Tasks**:
- [ ] Repo layout and package scaffold
- [ ] All core Pydantic models (`AgentProfile`, `Scenario`, `ExecutionTrace`, `EvaluationResult`, `ReliabilityScore`, `RegressionCase`)
- [ ] Abstract base classes (`BaseLLMProvider`, `BaseAgentAdapter`, `BaseSandbox`, `BaseEvaluator`)
- [ ] `ToolRuntime` / `ToolRegistry` skeleton
- [ ] Project-level configuration (env vars, settings)
- [ ] Unit tests for all contracts

**Definition of Done**: All models instantiate without error. All abstract classes are defined. All tests pass.

**Demo Capability**: None — foundation only.

---

## Phase 1 — Vertical Slice

**Objective**: Run one scenario through the full loop end-to-end. No UI. No real LLM calls. Prove the pipeline works.

**Dependencies**: Phase 0.

**Tasks**:
- [ ] `DemoAgentAdapter` — hardcoded, controllable responses
- [ ] `LocalMockSandbox` — in-process execution, no real tool side effects
- [ ] `DeterministicEvaluator` — rule-based pass/fail
- [ ] CLI script: profile → generate one scenario → execute → evaluate → print result
- [ ] Integration test covering full loop

**Definition of Done**: A single scenario runs end-to-end and produces an `EvaluationResult`. No mocking of internal interfaces.

**Demo Capability**: `python run_eval.py` produces a printed evaluation result.

---

## Phase 2 — Profiler

**Objective**: Build the agent profiler so it can analyze an agent and produce a structured `AgentProfile`.

**Dependencies**: Phase 1.

**Tasks**:
- [ ] Static profile loader (YAML/JSON input)
- [ ] Adapter-introspection profiler
- [ ] LLM-assisted profiler (optional enhancement)
- [ ] `RiskSurface` derivation from profile
- [ ] Tests for each profiler type

**Definition of Done**: Given a YAML agent description, the profiler produces a valid `AgentProfile` with a `RiskSurface`.

**Demo Capability**: CLI command prints the derived agent profile and risk surface.

---

## Phase 3 — Scenario Engine

**Objective**: Generate targeted adversarial scenarios from an `AgentProfile`.

**Dependencies**: Phase 2.

**Tasks**:
- [ ] `ScenarioGenerator` base class
- [ ] Template-based scenario generator (deterministic)
- [ ] LLM-assisted scenario generator
- [ ] `ChallengePack` builder
- [ ] Scenario serialization / deserialization
- [ ] Tests for scenario generation

**Definition of Done**: Given an `AgentProfile`, the engine generates a valid `ChallengePack` with scenarios across at least 3 categories.

**Demo Capability**: Print a generated challenge pack for the demo agent.

---

## Phase 4 — Sandbox + Execution

**Objective**: Reliable, isolated scenario execution with full trace capture.

**Dependencies**: Phase 3.

**Tasks**:
- [ ] `LocalMockSandbox` — complete implementation
- [ ] `ToolRuntime` and `ToolRegistry` — full implementation
- [ ] Tool call routing (no `unittest.mock`)
- [ ] `Tracer` — capture all steps into `ExecutionTrace`
- [ ] Trace serialization to JSON
- [ ] Trace indexing in SQLite
- [ ] Tests for sandbox execution and tracing

**Definition of Done**: Every scenario execution produces a complete `ExecutionTrace` persisted to disk and indexed in SQLite.

**Demo Capability**: Execute a challenge pack and inspect the resulting traces.

---

## Phase 5 — Evaluation

**Objective**: Score traces against expected behaviors.

**Dependencies**: Phase 4.

**Tasks**:
- [ ] `DeterministicEvaluator` — complete implementation
- [ ] `LLMJudgeEvaluator` — semantic evaluation via `BaseLLMProvider`
- [ ] `CompositeEvaluator` — weighted combination
- [ ] `EvaluationResult` persistence
- [ ] Gemini provider implementation
- [ ] OpenAI provider implementation
- [ ] Tests for each evaluator type

**Definition of Done**: Traces from the demo agent are evaluated and produce `EvaluationResult` records with accurate pass/fail and scores.

**Demo Capability**: Run a full evaluation on a challenge pack and print results by category.

---

## Phase 6 — Failure Intelligence

**Objective**: Explain why failures occurred in human-readable language.

**Dependencies**: Phase 5.

**Tasks**:
- [ ] `Diagnoser` — LLM-assisted failure explanation
- [ ] `FailureDetail` enrichment
- [ ] Failure taxonomy classification
- [ ] Failure summary generation
- [ ] Tests for diagnosis accuracy

**Definition of Done**: Every failed `EvaluationResult` has a human-readable explanation with a classified `FailureCategory`.

**Demo Capability**: Print failure explanations for each failing scenario in a challenge pack.

---

## Phase 7 — Reliability Scoring

**Objective**: Aggregate evaluation results into a `ReliabilityScore`.

**Dependencies**: Phase 6.

**Tasks**:
- [ ] `Scorer` — compute overall score, pass rate, severity breakdown, category breakdown
- [ ] `RiskLevel` classification logic
- [ ] Recommendations generation
- [ ] Score persistence in SQLite
- [ ] Tests for scoring logic

**Definition of Done**: Any completed evaluation run produces a `ReliabilityScore` with a `RiskLevel` and recommendations.

**Demo Capability**: Print the reliability score for the demo agent after a full evaluation run.

---

## Phase 8 — Regression

**Objective**: Convert discovered failures into persistent regression test cases.

**Dependencies**: Phase 7.

**Tasks**:
- [ ] `RegressionStore` — persist and load `RegressionCase` records
- [ ] Automatic regression case creation from failures
- [ ] Regression suite management (create, list, run)
- [ ] Regression run output: pass/fail delta vs. previous run
- [ ] Tests for regression lifecycle

**Definition of Done**: Failures from Phase 7 are stored as regression cases and re-runnable against any new agent version.

**Demo Capability**: Run regression suite against a modified demo agent and show which cases now pass/fail.

---

## Phase 9 — Dashboard

**Objective**: Build the frontend dashboard to visualize evaluation results, reliability scores, and failure intelligence.

**Dependencies**: Phase 8.

**Tasks**:
- [ ] Next.js project setup with TypeScript, Tailwind CSS, shadcn/ui, Recharts
- [ ] FastAPI REST API for all backend data
- [ ] Dashboard: reliability score overview
- [ ] Dashboard: evaluation run results table
- [ ] Dashboard: failure breakdown by category
- [ ] Dashboard: scenario detail view with trace
- [ ] Dashboard: regression suite status
- [ ] Responsive design

**Definition of Done**: The dashboard displays a complete evaluation run with score, failures, and regression status. All data comes from the API.

**Demo Capability**: Full browser demo of an agent evaluation.

---

## Phase 10 — Adaptive Testing

**Objective**: Close the loop — learn from past runs to generate better attacks.

**Dependencies**: Phase 9.

**Tasks**:
- [ ] `AdaptiveAttackStrategy` — analyze historical results
- [ ] Scenario mutation engine
- [ ] Coverage tracking
- [ ] Adaptive challenge pack generation

**Definition of Done**: The engine generates a follow-up challenge pack that specifically targets previously observed weaknesses.

---

## Phase 11 — Version Comparison

**Objective**: Compare reliability across agent versions.

**Dependencies**: Phase 10.

**Tasks**:
- [ ] Version tagging for evaluation runs
- [ ] Side-by-side score comparison
- [ ] Regression delta (new failures vs. fixed failures)
- [ ] Trend visualization in dashboard

**Definition of Done**: Dashboard shows side-by-side reliability comparison for two agent versions.

---

## Phase 12 — Predictive Reliability

**Objective**: Predict failure probability before execution.

**Dependencies**: Phase 11.

**Tasks**:
- [ ] Feature extraction from trace patterns
- [ ] Failure probability classifier
- [ ] Risk forecasting API
- [ ] Dashboard risk forecast panel

**Definition of Done**: Given a scenario and agent profile, the system returns a failure probability estimate.

---

## Phase 13 — Polish + Demo

**Objective**: Finalize UX, fix rough edges, prepare for external demo.

**Dependencies**: Phase 12.

**Tasks**:
- [ ] UI polish and accessibility
- [ ] Performance optimization
- [ ] Demo script and sample data
- [ ] Documentation
- [ ] README with quickstart

**Definition of Done**: A first-time user can clone the repo, run `docker compose up`, and see a complete demo evaluation in the browser.
