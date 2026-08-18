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
│           SQLite (metadata) + JSON (traces)          │
└─────────────────────────────────────────────────────┘
```

---

## 4. Package Responsibilities

| Package | Responsibility |
|---|---|
| `core/` | Shared contracts, base classes, Pydantic models — zero provider dependencies |
| `profiler/` | Analyze agent capabilities and produce a structured `AgentProfile` |
| `scenario/` | Generate `Scenario` objects from risk profiles |
| `sandbox/` | Execute scenarios in isolation via `BaseSandbox` |
| `tracer/` | Capture and serialize `ExecutionTrace` objects |
| `evaluator/` | Score traces against expected outcomes |
| `diagnoser/` | Explain failures in human-readable form |
| `scorer/` | Produce `ReliabilityScore` from evaluation results |
| `regression/` | Persist and load regression test cases |
| `adapters/llm/` | Provider-specific LLM implementations |
| `adapters/agent/` | Agent-specific adapter implementations |
| `adapters/sandbox/` | Sandbox-specific implementations (Docker, E2B) |
| `api/` | FastAPI routers, request/response schemas |
| `db/` | SQLite repositories — no business logic |
| `frontend/` | Next.js application |

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

The adaptive testing engine closes the loop by learning from previous evaluation runs.

**Inputs**:
- Historical `EvaluationResult` records
- `ReliabilityScore` trends across agent versions
- `RegressionCase` library

**Outputs**:
- Updated attack strategies
- Newly generated scenarios targeting observed weaknesses
- Prioritization weights for scenario categories

**Implementation**: Phase 10. Do not implement prematurely.

---

## 15. Future Architecture

### Phase 10 — Adaptive Testing Engine
- `AdaptiveAttackStrategy` — learns which attack vectors are most effective per agent class
- Scenario mutation: generate variants of known-failing scenarios
- Coverage tracking: ensure diverse failure mode exploration

### Phase 11 — Version Comparison
- Side-by-side `ReliabilityScore` comparison across agent versions
- Regression delta: new failures introduced vs. failures fixed
- Improvement trend visualization

### Phase 12 — Predictive Reliability
- Train lightweight classifier on trace features to predict failure probability before execution
- Risk forecasting: "This scenario has 87% probability of failure"
- Prioritize high-risk scenarios for limited evaluation budgets

### Phase 13 — External Integrations
- CI/CD integration (GitHub Actions, GitLab CI)
- Webhook notifications on reliability degradation
- Slack/PagerDuty alerts for CRITICAL risk level
- Export formats: JUnit XML, SARIF

### Phase 14 — Multi-Agent Systems
- Evaluate agent-to-agent trust boundaries
- Orchestrator/subagent failure propagation
- Shared tool registry across agent network
