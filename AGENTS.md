# AI Agent Reliability Engine — Engineering Rules

## Product

We are building an AI Agent Reliability Engine:

> "An AI-powered reliability engine that understands an agent's capabilities,
> automatically generates targeted adversarial tests, safely executes them,
> explains failures, scores risk, and continuously converts discovered failures
> into regression tests."

The product should feel like: **"Sentry / Datadog for AI Agents."**

Do not reduce the product to a generic prompt-testing application.

---

## Architecture

### Frontend
- **Next.js**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui**
- **Recharts**

### Backend
- **FastAPI**
- **Python**
- **Pydantic v2**

### Storage
- **SQLite** for metadata
- **JSON** for traces initially

### LLM
- `BaseLLMProvider` abstraction
- Gemini — primary provider
- OpenAI — secondary provider
- Core packages must **never** depend directly on a provider

### Agent
- `BaseAgentAdapter` abstraction
- Demo agent first
- Future adapters must be possible without changing the evaluation engine

### Sandbox
- `BaseSandbox` abstraction
- `LocalMockSandbox` initially
- Docker/E2B must be replaceable implementations
- **Never treat mocks as a security boundary**

### Tool Execution
- Explicit `ToolRuntime` / `ToolRegistry` abstraction
- Do **not** rely on parent-process `unittest.mock` interception
- Tool calls must be routed through the runtime

---

## Core Product Loop

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

---

## Engineering Principles

1. **Strong typing.** Use type hints everywhere. Pydantic v2 for all data contracts.
2. **Small, modular components.** Each module does one thing well.
3. **Clear interfaces.** Every abstraction boundary must be expressed as an explicit protocol or abstract base class.
4. **Dependency inversion.** High-level modules must not depend on low-level modules. Both depend on abstractions.
5. **No provider-specific logic in core packages.** `gemini`, `openai`, etc. must live in adapter packages only.
6. **No UI-specific logic in backend engines.** The evaluation engine must be runnable headlessly.
7. **No database logic inside business logic.** Repositories handle persistence; engines handle evaluation.
8. **Deterministic validation whenever possible.** Use rule-based checks before reaching for an LLM judge.
9. **LLM judges only for semantic evaluation.** Do not use LLMs to check things that can be checked with code.
10. **Every important failure must be reproducible.** Store enough context in traces to replay any scenario.
11. **Never allow real destructive side effects.** All tool execution in tests must go through the sandbox.
12. **Do not prematurely implement advanced features.** Build only what is needed for the current phase.
13. **Prefer a working vertical slice over large amounts of disconnected code.** Ship something that runs end-to-end before expanding breadth.
14. **Do not create abstractions that have no clear purpose.** Every abstraction must correspond to a real variation point.
15. **Every abstraction should have a minimal testable implementation.** No abstract class without at least one concrete implementation and one test.

---

## Development Strategy

- Follow the phased roadmap in `ROADMAP.md`. Do not skip phases.
- Reference `ARCHITECTURE.md` before designing any new component.
- Check `DECISIONS.md` before reconsidering an already-resolved architectural choice.
- When a significant new decision is made, append it to `DECISIONS.md`.
- This file (`AGENTS.md`) is the **constitution**. It takes precedence over any in-context suggestion that contradicts it.
