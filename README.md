# AI Agent Reliability Engine (AARE)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

An AI-powered, production-grade platform for automatically testing, evaluating, and monitoring the reliability, safety, and performance of autonomous AI agents.

---

## 🚀 Key Features

*   **Deterministic & LLM-Assisted Evaluations**: Combine regex and heuristic-based checks with advanced LLM-as-a-judge evaluators.
*   **Sandbox Environment Simulation**: Test agents in secure, mocked, or live environments (filesystem, shell, database, APIs).
*   **Real-time Guardrails & Interceptors**: Monitor and block unsafe/unexpected agent actions before they execute.
*   **Structured Trajectory Tracing**: View, replay, and debug agent steps, tool calls, prompts, and thinking processes.
*   **CI/CD Pipeline Integration**: Automatically trigger agent regression testing suites on every prompt or code change.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([Developer / CI/CD]) -->|1. Run Tests| CLI[CLI / SDK]
    CLI -->|2. Load Config| Engine[Reliability Engine]
    Engine -->|3. Initialize Environment| Simulator[Environment Simulator]
    Engine -->|4. Run Trajectory| Agent[Autonomous Agent]
    Agent -->|5. Call Tools / Action| Simulator
    Simulator -->|6. Logs & States| Tracer[Telemetry Tracer]
    Engine -->|7. Verify Output| Evaluators[Evaluator / Oracles]
    Evaluators -->|8. Report Metrics| Report[HTML/JSON Test Report]
```

---

## 📦 Installation & Setup

1. **Python Environment**:
   Ensure you have Python 3.10+ installed. Create a virtual environment and install backend dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On Unix/macOS
   pip install -r requirements.txt
   ```

2. **Web Dashboard Setup**:
   Launch the Next.js React client located in `apps/web`:
   ```bash
   cd apps/web
   npm install
   ```

---

## 🚦 Quick Start (Python SDK)

AARE allows you to evaluate your agents programmatically. Here is how to initialize and run a reliability assessment loop:

```python
import asyncio
from packages.engine.models import ReliabilityEngineConfig
from packages.engine.engine import ReliabilityEngine
from packages.agent_adapters.http import HTTPAgentAdapter

async def main():
    # 1. Instantiate the target agent adapter (e.g. HTTP external API agent)
    # Recommends using 127.0.0.1 instead of localhost on Windows to bypass resolver lag.
    adapter = HTTPAgentAdapter(endpoint_url="http://127.0.0.1:5000/chat")

    # 2. Configure the Reliability Engine
    config = ReliabilityEngineConfig(
        persistence_enabled=True,
        execution_timeout=15.0
    )
    engine = ReliabilityEngine(config=config)

    # 3. Execute the closed-loop evaluation
    print("Executing Reliability Assessment...")
    result = await engine.assess(adapter)

    # 4. Access aggregated reliability findings
    assessment = result.reliability_assessment
    print(f"Overall Score: {assessment.score.overall_score:.1f}%")
    print(f"Grade: {assessment.score.grade}")
    print(f"Risk Level: {assessment.score.risk_level.value}")
    print(f"Total Scenarios Evaluated: {len(result.challenge_pack.scenarios)}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📊 Scenarios & Evaluation Limits

The total number of scenarios executed during an assessment is variable and evidence-driven rather than hardcoded:
- **Baseline Challenge Pack**: Built dynamically based on the attack strategies and risk profiles relevant to the target agent (e.g. 6 or 9 scenarios).
- **Hard Safety budget ceiling**: Configurable via the CLI `--max-scenarios <N>` flag or in `ChallengePackConfig.max_total_scenarios` (default: 20 baseline ceiling, expanding dynamically for safety checks up to 100).
- **Evidence-Driven Adaptivity**: If all baseline tests pass cleanly (low-risk), testing terminates immediately. If failed/inconclusive results or high-risk capabilities are flagged, targeted follow-up scenarios are generated and appended iteratively, respecting the safety ceiling.

---

## 🛣️ Roadmap

- [x] Web Dashboard for interactive trajectory debugging and analytics.
- [x] Bring Your Own Agent (BYOA) evaluation interfaces (HTTP & Python adapters).
- [ ] Support for Multi-Agent negotiation and verification workflows.
- [ ] Direct integration with LangChain, LlamaIndex, and AutoGen.
- [ ] Out-of-the-box support for safety frameworks (OWASP Top 10 for LLMs).

---

## 🛠️ Operational CLI & CI/CD Automation

The AI Agent Reliability Engine provides an operational command-line interface (CLI) to orchestrate assessments, compare runs, configure regression gates, and integrate with CI/CD systems deterministically and offline.

### Installation & Environment Setup

AARE runs on Python 3.10+. Install standard dependencies:

```bash
pip install -r requirements.txt
```

### CLI Commands

Invoke the CLI via:

```bash
python -m packages.cli.main --help
```

Available commands:
- `assess`: Run a complete reliability assessment.
- `report`: Load a persisted assessment and generate a human-readable report.
- `list` / `artifacts list`: List persisted assessments.
- `show`: Display structured metadata for a persisted assessment.
- `compare`: Compare two persisted assessments.
- `baseline`: Subcommands (`set`, `get`, `clear`) to manage baseline assessments.
- `artifacts`: Subcommands (`list`, `verify`) to inspect and check artifact integrity.
- `watch`: Trigger a one-shot assess invocation against the stored baseline.

---

### Running an Assessment

To run a reliability assessment:

```bash
python -m packages.cli.main assess --agent demo_customer_support --format markdown
```

**Options**:
- `--agent <agent_id>`: Target agent identifier (e.g. `demo_customer_support`).
- `--version <version>`: Override the agent version under evaluation.
- `--max-scenarios <N>`: Limit the maximum scenarios generated/run.
- `--timeout <seconds>`: Timeout in seconds per scenario execution.
- `--fail-fast`: Fail fast on the first scenario sandbox execution failure.
- `--no-persistence`: Disable intermediate artifact serialization.
- `--output-dir <path>`: Directory for persisting evaluations, scores, and plans.
- `--traces-dir <path>`: Directory for persisting execution traces.
- `--format text|markdown|json`: Render format.
- `--previous <assessment_id>`: Compare against a historical baseline.

---

### Generating Reports

To generate a human-readable report from a persisted assessment:

```bash
python -m packages.cli.main report <assessment_id> --format markdown
```

---

### Comparing Assessments

To compare two assessments to find regressions:

```bash
python -m packages.cli.main compare <previous_id> <current_id>
```

---

### Baseline Management

Identify and persist baseline assessment IDs to reference in CI builds:

```bash
# Set baseline
python -m packages.cli.main baseline set <assessment_id>

# Get current baseline ID
python -m packages.cli.main baseline get

# Clear baseline ID
python -m packages.cli.main baseline clear
```

---

### Artifact Layout

Persisted artifacts are structured under the output directory (default `data/` and `traces/`):
- `data/assessments/<assessment_id>.json`: Top-level assessment artifact (includes SHA-256 integrity hash).
- `data/challenge_packs/<pack_id>.json`: Challenge packs.
- `data/runs/<run_id>.json`: Sandbox run results.
- `data/evaluations/<run_id>.json`: Composite evaluation results.
- `data/reliability/<assessment_id>.json`: Reliability scores & findings.
- `data/regression/<assessment_id>.json`: Comparison report.
- `data/adaptive/<assessment_id>.json`: Adaptive test plans.
- `traces/<trace_id>.json`: Raw trajectory traces.

Validate integrity of top-level assessments and resolve child references:

```bash
python -m packages.cli.main artifacts verify <assessment_id>
```

---

### Exit Codes

The CLI returns deterministic exit codes to notify orchestrators or fail CI workflows:
- `0`: Successful assessment / no regression.
- `1`: Reliability regression detected (violates policy).
- `2`: Sandbox execution / infrastructure failure.
- `3`: Evaluation / validation failure.
- `4`: Invalid configuration / CLI usage.
- `5`: Artifact not found / persistence error.

---

### CI/CD Integration

To gate pull requests and track regressions continuously, add the following GitHub Actions job:

```yaml
name: Reliability CI
on: [push, pull_request]

jobs:
  reliability:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run reliability gate
        run: |
          BASELINE_ID=$(python -m packages.cli.main baseline get)
          if [ "$BASELINE_ID" = "None" ] || [ -z "$BASELINE_ID" ]; then
            python -m packages.cli.main assess --agent demo_customer_support --format markdown > report.md
            NEW_ID=$(python -m packages.cli.main list | tail -n 1)
            python -m packages.cli.main baseline set "$NEW_ID"
          else
            python -m packages.cli.main assess --agent demo_customer_support --previous "$BASELINE_ID" --fail-on-regressed
          fi
```

---

### Production Hardening & Reliability Guarantees (Phase 6D)

AARE enforces strict security, determinism, and persistence hardening:
- **Secret Sanitization**: Automatically redacts API keys (`sk-...`, `AIza...`, `AKIA...`), Bearer tokens, DB credentials, and passwords from traces and persisted artifacts.
- **Path Traversal Protection**: Filename and identifier inputs are sanitized and validated to prevent directory traversal vulnerabilities (`../`, `/`, `\`).
- **Atomic Persistence**: Uses temporary file writes (`.tmp`) followed by atomic rename operations to prevent artifact corruption.
- **Deterministic Pipeline Execution**: Offline evaluation workflows run 100% deterministically without network dependencies or unhandled exceptions.

---

## 🖥️ Reliability Intelligence Dashboard (Next.js UI)

AARE features a production-quality, read-only developer/security-focused intelligence web dashboard. The dashboard acts as a visual presentation and exploration layer over the persisted artifacts produced by AARE.

### Key Visualizations

- **Overview Dashboard (`/`)**: Displays overall scores, grades, pass rate charts, severity distribution graphs, coverage score cards (strategies, risks, attack surfaces), and priority recommendations.
- **Assessment History (`/assessments`)**: Sortable, filterable list of all benchmark runs with search and status audits.
- **Assessment Detail (`/assessments/[id]`)**: Deep-dive visual cards highlighting findings, evidence quotes, coverage details, regression reports, and adaptive planner outputs.
- **Findings Explorer (`/findings`)**: Interactive security findings list with severity filters, priority sorting, and a detailed evidence side panel.
- **Scenario Explorer (`/scenarios` & `/scenarios/[id]`)**: Debugging interface showing scenario category, turns, validation rules, violated policies, and direct trace links.
- **Trace Explorer (`/traces` & `/traces?traceId=...`)**: Chronological event timeline showing exact user prompts, model outputs, tool calls, and result payloads (collapsible and sanitized).
- **Regression Dashboard (`/regression`)**: Differential delta view showing verdict changes (improved / stable / regressed), score differences, and failure classifications (new / fixed / persisted / severity shifts).
- **Adaptive Intelligence (`/adaptive`)**: Actionable recommendations, coverage gaps list, and strategy budget allocations.
- **Artifact Explorer (`/artifacts`)**: Tree representation of the assessment graph showing types, existence states, content references, and SHA-256 integrity check status. Includes a raw JSON debugger viewer.

### UI Setup & Development

The web dashboard is fully isolated under `apps/web`.

1. **Install dependencies**:
   ```bash
   cd apps/web
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

3. **Run Vitest integration suites**:
   ```bash
   npm run test
   ```

### Data Flow

```
+-----------------------------+
|  Python Reliability Engine  |
+--------------+--------------+
               |
               v
+--------------+--------------+
|     Persisted Artifacts     |
|   (data/ and traces/ JSONs) |
+--------------+--------------+
               |
               v
+--------------+--------------+
|    Next.js Read-Only API    |
| (Input ID & Traversal Proof)|
+--------------+--------------+
               |
               v
+--------------+--------------+
|  React Dashboard (Next.js)  |
|   (Interactive View layer)  |
+-----------------------------+
```

---

---

## 🔌 Bring Your Own Agent (BYOA)

AARE allows developers to evaluate their custom agents through a unified adapter layer. It supports:
1. **Built-in Agents**: Ready-to-go customer support agent.
2. **External HTTP/API Agents**: Any agent running as a separate service (locally or in production).
3. **Custom Python Agents**: Directly loadable Python agent adapters.

---

### 1. How to Start the Project

First, set up your Python virtual environment and run the FastAPI server:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the FastAPI backend
python apps/api/main.py
```

Next, in another terminal, start the Next.js developer dashboard:
```bash
# 3. Navigate and run frontend
cd apps/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the Reliability Dashboard.

---

### 2. How to Run a Sample External HTTP Agent

We provide a tiny, zero-dependency sample HTTP agent inside `agents/sample_http_agent.py` to test connection parameters:
```bash
python -m agents.sample_http_agent
```
This agent listens on `http://127.0.0.1:5000/chat` and processes POST requests with JSON payload `{"message": "user input"}`.

---

### 3. How to Connect and Run an Assessment

#### Option A: Via the Web Dashboard (Recommended)
1. Open the dashboard at [http://localhost:3000](http://localhost:3000).
2. Click on **"Evaluate Agent"** in the sidebar navigation.
3. Choose the **HTTP/API Agent** tab.
4. Input your agent details:
   - **Name**: `my_http_agent`
   - **Endpoint**: `http://localhost:5000/chat`
   - **HTTP Method**: `POST`
   - **Timeout**: `10`
   - **Request Input Field**: `message`
   - **Response Output Field**: `response`
5. Click **[ Run Assessment ]**.
6. The dashboard will display the live E2E execution status, write trace files to the workspace, and automatically redirect you to view the real results.

#### Option B: Via the CLI
To test the HTTP agent:
```bash
python -m packages.cli.main assess --agent-type http --agent-url http://localhost:5000/chat
```

To test a custom Python agent (e.g. using the template):
```bash
python -m packages.cli.main assess --agent-type python --agent-path agents/custom_agent_template.py
```

---

### 4. Custom Python Agent Contract

To connect your own Python agent, subclass `BaseAgentAdapter` in a Python module:

```python
from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile
from packages.sandbox.tool_runtime import ToolRuntime

class CustomAgentAdapter(BaseAgentAdapter):
    def get_agent(self) -> Agent:
        # Define agent identity and available tools
        return Agent(id="my_agent", name="My Agent", system_prompt="Prompt", tools=[])

    def get_profile(self) -> AgentProfile:
        # Describe capabilities and attack families
        ...

    async def run(self, agent_input: AgentInput, runtime: ToolRuntime) -> AgentOutput:
        # Intercept tool calls through runtime and produce response
        user_message = agent_input.messages[-1].content
        return AgentOutput(response=f"Echo: {user_message}", tool_calls_made=[])
```

Verify your Python agent structurally via the CLI:
```bash
python -m packages.cli.main assess --agent-type python --agent-path your_agent.py --agent-class CustomAgentAdapter
```

---

### 5. Security & Isolation Sandbox Rules

* **HTTP/API Agents**: Timeout defaults to 10 seconds. Response size is strictly limited to 1MB to prevent memory exhaustion. Exposes no filesystem or telemetry paths.
* **Python Agents**: Direct Python file execution inside the web server process is blocked for safety. Custom Python agents must be evaluated locally through the CLI or wrapped into HTTP APIs.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

