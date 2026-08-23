# Implementation Roadmap

## Overview

```
Phase 0  — Foundation + Core Contracts (Complete)
Phase 1  — Vertical Slice (Complete)
Phase 2  — Profiler (Complete)
Phase 3  — Scenario Engine (Complete)
Phase 4  — Sandbox + Execution (Complete)
Phase 5  — Evaluation (Complete)
Phase 6  — Failure Intelligence (Complete)
Phase 7  — Reliability Scoring (Complete)
Phase 8  — Regression (Complete)
Phase 9  — Dashboard (Complete)
Phase 10 — Adaptive Testing (Complete)
Phase 11 — Version Comparison (Complete)
Phase 12 — Predictive Reliability (Future)
Phase 13 — Polish + Demo (Complete)
```

---

## Phase 0 — Foundation + Core Contracts

**Objective**: Establish the repo structure, all core Pydantic contracts, and base abstractions. Nothing executes yet, but every interface is defined.

**Dependencies**: None.

**Tasks**:
- [x] Repo layout and package scaffold
- [x] All core Pydantic models (`AgentProfile`, `Scenario`, `ExecutionTrace`, `EvaluationResult`, `ReliabilityScore`, `RegressionCase`)
- [x] Abstract base classes (`BaseLLMProvider`, `BaseAgentAdapter`, `BaseSandbox`, `BaseEvaluator`)
- [x] `ToolRuntime` / `ToolRegistry` skeleton
- [x] Project-level configuration (env vars, settings)
- [x] Unit tests for all contracts

**Definition of Done**: All models instantiate without error. All abstract classes are defined. All tests pass.

**Demo Capability**: None — foundation only.

---

## Phase 1 — Vertical Slice

**Objective**: Run one scenario through the full loop end-to-end. No UI. No real LLM calls. Prove the pipeline works.

**Dependencies**: Phase 0.

**Tasks**:
- [x] `DemoAgentAdapter` — hardcoded, controllable responses
- [x] `LocalMockSandbox` — in-process execution, no real tool side effects
- [x] `DeterministicEvaluator` — rule-based pass/fail
- [x] CLI script: profile → generate one scenario → execute → evaluate → print result
- [x] Integration test covering full loop

**Definition of Done**: A single scenario runs end-to-end and produces an `EvaluationResult`. No mocking of internal interfaces.

**Demo Capability**: `python run_eval.py` produces a printed evaluation result.

---

## Phase 2 — Profiler

**Objective**: Build the agent profiler so it can analyze an agent and produce a structured `AgentProfile`.

**Dependencies**: Phase 1.

**Tasks**:
- [x] Static profile loader (YAML/JSON input)
- [x] Adapter-introspection profiler
- [x] LLM-assisted profiler (optional enhancement)
- [x] `RiskSurface` derivation from profile
- [x] Tests for each profiler type

**Definition of Done**: Given a YAML agent description, the profiler produces a valid `AgentProfile` with a `RiskSurface`.

**Demo Capability**: CLI command prints the derived agent profile and risk surface.

---

## Phase 3 — Scenario Engine

**Objective**: Generate targeted adversarial scenarios from an `AgentProfile`.

**Dependencies**: Phase 2.

**Tasks**:
- [x] `ScenarioGenerator` base class
- [x] Template-based scenario generator (deterministic)
- [x] LLM-assisted scenario generator
- [x] `ChallengePack` builder
- [x] Scenario serialization / deserialization
- [x] Tests for scenario generation

**Definition of Done**: Given an `AgentProfile`, the engine generates a valid `ChallengePack` with scenarios across at least 3 categories.

**Demo Capability**: Print a generated challenge pack for the demo agent.

---

## Phase 4 — Sandbox + Execution

**Objective**: Reliable, isolated scenario execution with full trace capture.

**Dependencies**: Phase 3.

**Tasks**:
- [x] `LocalMockSandbox` — complete implementation
- [x] `ToolRuntime` and `ToolRegistry` — full implementation
- [x] Tool call routing (no `unittest.mock`)
- [x] `Tracer` (telemetry tracing) — capture all steps into `ExecutionTrace`
- [x] Trace serialization to JSON
- [x] File-system trace index and resolving
- [x] Tests for sandbox execution and tracing

**Definition of Done**: Every scenario execution produces a complete `ExecutionTrace` persisted to disk.

**Demo Capability**: Execute a challenge pack and inspect the resulting traces.

---

## Phase 5 — Evaluation

**Objective**: Score traces against expected behaviors.

**Dependencies**: Phase 4.

**Tasks**:
- [x] `DeterministicEvaluator` — complete implementation
- [x] `LLMJudgeEvaluator` — semantic evaluation via `BaseLLMProvider`
- [x] `CompositeEvaluator` — weighted combination
- [x] `EvaluationResult` persistence (file-based JSON)
- [x] Gemini provider implementation
- [x] OpenAI provider implementation
- [x] Tests for each evaluator type

**Definition of Done**: Traces from the demo agent are evaluated and produce `EvaluationResult` records with accurate pass/fail and scores.

**Demo Capability**: Run a full evaluation on a challenge pack and print results by category.

---

## Phase 6 — Failure Intelligence

**Objective**: Explain why failures occurred in human-readable language.

**Dependencies**: Phase 5.

**Tasks**:
- [x] `Diagnoser` — failure explanation
- [x] `FailureDetail` enrichment
- [x] Failure taxonomy classification
- [x] Failure summary generation
- [x] Tests for diagnosis accuracy

**Definition of Done**: Every failed `EvaluationResult` has a human-readable explanation with a classified `FailureCategory`.

**Demo Capability**: Print failure explanations for each failing scenario in a challenge pack.

---

## Phase 7 — Reliability Scoring

**Objective**: Aggregate evaluation results into a `ReliabilityScore`.

**Dependencies**: Phase 6.

**Tasks**:
- [x] `Scorer` — compute overall score, pass rate, severity breakdown, category breakdown
- [x] `RiskLevel` classification logic
- [x] Recommendations generation
- [x] Score persistence in JSON artifacts (managed by `ArtifactStore`)
- [x] Tests for scoring logic

**Definition of Done**: Any completed evaluation run produces a `ReliabilityScore` with a `RiskLevel` and recommendations.

**Demo Capability**: Print the reliability score for the demo agent after a full evaluation run.

---

## Phase 8 — Regression

**Objective**: Convert discovered failures into persistent regression test cases.

**Dependencies**: Phase 7.

**Tasks**:
- [x] `RegressionStore` / `ArtifactStore` — persist and load `RegressionCase` records
- [x] Automatic regression case creation from failures
- [x] Regression suite management (create, list, run)
- [x] Regression run output: pass/fail delta vs. previous run
- [x] Tests for regression lifecycle

**Definition of Done**: Failures from Phase 7 are stored as regression cases and re-runnable against any new agent version.

**Demo Capability**: Run regression suite against a modified demo agent and show which cases now pass/fail.

---

## Phase 9 — Dashboard

**Objective**: Build the frontend dashboard to visualize evaluation results, reliability scores, and failure intelligence.

**Dependencies**: Phase 8.

**Tasks**:
- [x] Next.js project setup with TypeScript, Tailwind CSS, shadcn/ui, Recharts
- [x] FastAPI REST API for all backend data
- [x] Dashboard: reliability score overview
- [x] Dashboard: evaluation run results table
- [x] Dashboard: failure breakdown by category
- [x] Dashboard: scenario detail view with trace
- [x] Dashboard: regression suite status
- [x] Responsive design

**Definition of Done**: The dashboard displays a complete evaluation run with score, failures, and regression status. All data comes from the API.

**Demo Capability**: Full browser demo of an agent evaluation.

---

## Phase 10 — Adaptive Testing

**Objective**: Close the loop — learn from past runs to generate better attacks.

**Dependencies**: Phase 9.

**Tasks**:
- [x] `AdaptiveAttackStrategy` — analyze historical results via `AdaptiveRegressionAnalyzer`
- [x] Scenario mutation/variant generation
- [x] Coverage tracking and allocations
- [x] Adaptive challenge pack generation

**Definition of Done**: The engine generates a follow-up challenge pack that specifically targets previously observed weaknesses.

---

## Phase 11 — Version Comparison

**Objective**: Compare reliability across agent versions.

**Dependencies**: Phase 10.

**Tasks**:
- [x] Version tagging for evaluation runs
- [x] Side-by-side score comparison
- [x] Regression delta (new failures vs. fixed failures)
- [x] Trend visualization in dashboard

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
- [x] UI polish and accessibility
- [x] Performance optimization
- [x] Demo script and sample data
- [x] Documentation
- [x] README with quickstart

**Definition of Done**: A first-time user can clone the repo, run the FastAPI backend, launch Next.js, and evaluate custom HTTP/Python agents in the playground.
