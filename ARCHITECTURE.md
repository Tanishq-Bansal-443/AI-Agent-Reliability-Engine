# AI Agent Reliability Engine

## 1. Product Definition

**Vision**: An AI-powered reliability engine that understands an agent's capabilities, automatically generates targeted adversarial tests, safely executes them, explains failures, scores risk, and continuously converts discovered failures into regression tests.

**Positioning**: "Sentry / Datadog for AI Agents" — developer infrastructure, not a generic prompt tester.

**Target Users**: AI engineers and teams who deploy LLM-powered agents and need confidence in their reliability, safety, and correctness before and after deployment.

---

## 2. Core Loop

```
PROFILE
  → FIND RISKS
  → GENERATE ATTACKS
  → BUILD CHALLENGE PACK
  → SANDBOX EXECUTION
  → TRACE
  → EVALUATE
  → DIAGNOSE
  → SCORE
  → REGRESSION
  → ADAPT
```

| Stage | Description |
|---|---|
| **PROFILE** | Analyze agent capabilities, tools, goals, and constraints |
| **FIND RISKS** | Identify failure modes given the agent's profile |
| **GENERATE ATTACKS** | Create adversarial scenarios targeting identified risks |
| **BUILD CHALLENGE PACK** | Assemble a structured set of test scenarios |
| **SANDBOX EXECUTION** | Run scenarios in an isolated, controlled environment |
| **TRACE** | Capture full agent execution traces |
| **EVALUATE** | Score outcomes against expected behaviors |
| **DIAGNOSE** | Explain why failures occurred |
| **SCORE** | Produce a reliability score and risk breakdown |
| **REGRESSION** | Convert failures into permanent regression test cases |
| **ADAPT** | Refine attack strategies based on observed behavior |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│         Dashboard / Results / Reliability UI         │
└────────────────────────┬────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────┐
│                  Backend (FastAPI)                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Profiler │  │ Scenario │  │ Evaluation Engine  │ │
│  │  Engine  │  │  Engine  │  │                    │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Sandbox  │  │  Tracer  │  │  Regression Store  │ │
│  │  Layer   │  │          │  │                    │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
│  ┌──────────────────────────────────────────────┐   │
│  │            LLM Provider Layer                │   │
│  │   BaseLLMProvider → Gemini / OpenAI          │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                   Storage Layer                      │
│     File-based JSON Artifacts (via ArtifactStore)    │
└─────────────────────────────────────────────────────┘
```

---

## 4. Package Responsibilities

| Package | Responsibility |
|---|---|
| `packages/core` | Base interfaces (`BaseLLMProvider`, `BaseAgentAdapter`, `BaseSandbox`, `BaseEvaluator`) and core Pydantic models (`Agent`, `Scenario`, `Trace`, `EvaluationResult`, `ReliabilityScore`, `RegressionCase`, `AdaptiveTestPlan`). |
| `packages/profiler` | Analyze agent capabilities statically and with LLM inference to produce an `AgentProfile`. |
| `packages/scenario_engine` | Generate baseline scenarios and build `ChallengePack` collections. |
| `packages/sandbox` | Sandbox isolated environments, fake tool runtimes, and local mock execute bounds. |
| `packages/tracing` | telemetry recorders, sanitization logic (`SecretSanitizer`), and transaction traces. |
| `packages/evaluator` | Validate trajectory correctness via `DeterministicEvaluator` and semantic `LLMJudgeEvaluator`. |
| `packages/reliability` | Score aggregated runs, compute grade, confidence, and vulnerability risks (`ReliabilityScorer`). |
| `packages/regression` | Compute differential delta comparison metrics and orchestrate the `AdaptiveRegressionAnalyzer` loop. |
| `packages/agent_adapters` | Expose custom HTTP adapters (`HTTPAgentAdapter`), local python class loaders, and demo support adapters. |
| `packages/artifacts` | Manage file system read/write serialization, path validation, and SHA-256 integrity checksums (`ArtifactStore`). |
| `packages/cli` | Orchestrate evaluations, compare baseline regression gates, and format console/markdown reports. |
| `packages/execution` | Manage executor schedules and challenge pack orchestration. |
| `packages/shared` | Core shared utilities and mock patterns. |
| `apps/api` | REST API layer exposing FastAPI endpoints for execution triggers. |
| `apps/web` | Next.js presentation frontend application dashboard. |
| `agents/` | Sample HTTP agent endpoints and custom agent adapters. |

---

## 5. Agent Adapter Architecture

```python
class BaseAgentAdapter(ABC):
    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput: ...

    @abstractmethod
    def get_profile(self) -> AgentProfile: ...
```

**Implementations**:
- `DemoAgentAdapter` — built-in controllable agent for MVP
- Future: `LangChainAgentAdapter`, `CrewAIAgentAdapter`, `CustomHTTPAgentAdapter`

**Constraint**: The evaluation engine must only depend on `BaseAgentAdapter`. It must never import a concrete adapter.

---

## 6. Profiler Architecture

The profiler produces a structured `AgentProfile` that drives the rest of the loop.

```python
class AgentProfile(BaseModel):
    agent_id: str
    name: str
    description: str
    capabilities: list[Capability]
    tools: list[ToolSpec]
    constraints: list[Constraint]
    risk_surface: RiskSurface
```

**Profiling sources**:
1. Static declaration (developer-provided YAML/JSON)
2. Introspection (adapter-provided metadata)
3. LLM-assisted inference (from agent description)

---

## 7. Scenario Architecture

A `Scenario` is the unit of work for the evaluation engine.

```python
class Scenario(BaseModel):
    scenario_id: str
    name: str
    description: str
    category: ScenarioCategory
    severity: Severity
    input: AgentInput
    expected_behavior: ExpectedBehavior
    tags: list[str]
```

**ScenarioCategory** (taxonomy):
- `tool_misuse`
- `prompt_injection`
- `boundary_violation`
- `instruction_following`
- `refusal_bypass`
- `safety_violation`
- `data_exfiltration`
- `goal_drift`

**Challenge Pack**: A named, versioned collection of `Scenario` objects targeted at a specific agent profile.

---

## 8. Sandbox Architecture

```python
class BaseSandbox(ABC):
    @abstractmethod
    async def execute(self, scenario: Scenario, adapter: BaseAgentAdapter) -> ExecutionTrace: ...

    @abstractmethod
    async def reset(self) -> None: ...
```

**Implementations**:
- `LocalMockSandbox` — in-process, deterministic, zero side effects (MVP)
- `DockerSandbox` — process isolation via Docker (Phase 4+)
- `E2BSandbox` — cloud sandbox via E2B API (future)

**Tool Execution**: All tool calls within a sandbox session are routed through the `ToolRuntime`. The sandbox never intercepts calls via `unittest.mock` or monkey-patching.

---

## 9. Trace Architecture

Every sandbox execution produces an `ExecutionTrace` — the ground truth record of what happened.

```python
class ExecutionTrace(BaseModel):
    trace_id: str
    scenario_id: str
    agent_id: str
    started_at: datetime
    completed_at: datetime
    steps: list[TraceStep]
    final_output: AgentOutput | None
    error: str | None
    metadata: dict[str, Any]
```

```python
class TraceStep(BaseModel):
    step_index: int
    type: StepType  # llm_call | tool_call | tool_result | reasoning
    input: Any
    output: Any
    timestamp: datetime
    duration_ms: int
```

**Storage**: Traces serialized as JSON files. Indexed by `trace_id` in SQLite.

---

## 10. Evaluation Architecture

```python
class BaseEvaluator(ABC):
    @abstractmethod
    async def evaluate(self, trace: ExecutionTrace, scenario: Scenario) -> EvaluationResult: ...
```

**Evaluator types**:
- `DeterministicEvaluator` — rule-based checks (tool called, output format, refusal detection)
- `LLMJudgeEvaluator` — semantic correctness when deterministic is insufficient
- `CompositeEvaluator` — chains multiple evaluators with configurable weighting

```python
class EvaluationResult(BaseModel):
    trace_id: str
    scenario_id: str
    passed: bool
    score: float  # 0.0 - 1.0
    failures: list[FailureDetail]
    evaluator_type: str
    reasoning: str | None
```

---

## 11. Failure Taxonomy

| Category | Description |
|---|---|
| `TOOL_MISUSE` | Agent called a tool incorrectly, unnecessarily, or harmfully |
| `REFUSAL_FAILURE` | Agent failed to refuse a clearly unsafe request |
| `INSTRUCTION_VIOLATION` | Agent violated explicit constraints |
| `GOAL_DRIFT` | Agent pursued a goal inconsistent with the user's intent |
| `PROMPT_INJECTION` | Agent was manipulated by injected instructions |
| `DATA_EXPOSURE` | Agent leaked sensitive information |
| `LOOP_FAILURE` | Agent entered an infinite or unproductive loop |
| `FORMAT_FAILURE` | Agent produced output in the wrong format |
| `HALLUCINATION` | Agent fabricated facts or tool results |
| `SAFETY_VIOLATION` | Agent produced harmful content |

---

## 12. Reliability Scoring

```python
class ReliabilityScore(BaseModel):
    agent_id: str
    run_id: str
    overall_score: float        # 0.0 - 100.0
    pass_rate: float
    failure_rate: float
    severity_breakdown: dict[Severity, int]
    category_breakdown: dict[ScenarioCategory, float]
    risk_level: RiskLevel       # LOW | MEDIUM | HIGH | CRITICAL
    confidence: float
    recommendations: list[str]
```

**Risk levels**:
- `LOW` — ≥ 90% pass rate, no CRITICAL failures
- `MEDIUM` — 75–89% pass rate, or 1–2 HIGH failures
- `HIGH` — 60–74% pass rate, or any CRITICAL failure
- `CRITICAL` — < 60% pass rate, or multiple CRITICAL failures

---

## 13. Regression Architecture

Every failure discovered during an evaluation run is a candidate for regression.

```python
class RegressionCase(BaseModel):
    case_id: str
    source_trace_id: str
    scenario: Scenario
    expected_behavior: ExpectedBehavior
    failure_type: FailureCategory
    created_at: datetime
    tags: list[str]
```

**Regression suite**: A named collection of `RegressionCase` objects. Each new agent version is evaluated against all existing regression suites automatically.

---

## 14. Adaptive Testing

The adaptive testing engine closes the loop by learning from previous evaluation runs dynamically during execution loops:
- **Historical Analysis**: Scores and findings are loaded by `AdaptiveRegressionAnalyzer` to find priority strategies.
- **Budget Allocation**: Distributes test budgets deterministically across strategies via Largest Remainder Method.
- **Targeted Scenario Mutation**: Appends variations of failed, inconclusive, or high-risk tool scenarios to verify vulnerabilities.
- **Stop Controls**: Terminate testing early if baseline runs pass cleanly, preserving safety limits.

---

## 15. Future Architecture

### Phase 12 — Predictive Reliability
- Train lightweight classifier on trace features to predict failure probability before execution.
- Risk forecasting: "This scenario has 87% probability of failure".
- Prioritize high-risk scenarios for limited evaluation budgets.

### Phase 14 — Multi-Agent Systems
- Evaluate agent-to-agent trust boundaries.
- Orchestrator/subagent failure propagation.
- Shared tool registry across agent network.
