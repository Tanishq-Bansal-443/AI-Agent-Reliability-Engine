# Architecture Decisions

This document records significant architectural decisions made for the AI Agent Reliability Engine.
Before proposing a change to any decision marked **Accepted**, review the reasoning here first.

---

## ADR-001: FastAPI Backend

**Decision**: Use FastAPI as the evaluation engine backend.

**Reason**: The core evaluation, sandbox, and LLM tooling ecosystem is Python-oriented. FastAPI provides async support, automatic OpenAPI documentation, and native Pydantic v2 integration — all required for this project.

**Alternatives Considered**: Flask (no async, no native Pydantic), Django (too heavy for an API-only service).

**Status**: Accepted

---

## ADR-002: Next.js Frontend

**Decision**: Use Next.js rather than Streamlit or Gradio.

**Reason**: The product is a developer infrastructure platform — it needs a professional, production-quality dashboard experience. Streamlit and Gradio are prototyping tools and would make the product feel like a demo, not infrastructure.

**Alternatives Considered**: Streamlit (not suitable for production dashboards), plain React (Next.js adds routing and SSR with no downside at this scale).

**Status**: Accepted

---

## ADR-003: LLM Provider Abstraction

**Decision**: All LLM access goes through `BaseLLMProvider`. No core package may import a provider SDK directly.

**Providers**:
- Gemini — primary
- OpenAI — secondary

**Reason**: Avoid provider lock-in. Keep the evaluation engine portable across providers and testable without real API calls.

**Alternatives Considered**: Direct Gemini SDK usage in core (rejected — creates hard dependency and makes testing expensive).

**Status**: Accepted

---

## ADR-004: Sandbox Abstraction

**Decision**: All agent execution goes through `BaseSandbox`. Sandboxes are pluggable implementations.

**Initial Implementation**: `LocalMockSandbox` — in-process, deterministic, zero real side effects.

**Future Implementations**: `DockerSandbox`, `E2BSandbox`.

**Reason**: The MVP needs controlled execution for speed. Real isolation (Docker, E2B) must be possible without changing the evaluation engine. The abstraction ensures this.

**Constraint**: `LocalMockSandbox` is never treated as a real security boundary. It exists for development and testing only.

**Status**: Accepted

---

## ADR-005: ToolRuntime / ToolRegistry (No unittest.mock)

**Decision**: All tool calls within a sandbox session are routed through an explicit `ToolRuntime` and `ToolRegistry`. `unittest.mock` is never used to intercept tool calls.

**Reason**: `unittest.mock` interception is fragile, invisible, and breaks when tool call routing changes. An explicit runtime is self-documenting, testable, and replaceable.

**Alternatives Considered**: `unittest.mock.patch` on tool functions (rejected — creates invisible coupling between test infrastructure and production code).

**Status**: Accepted

---

## ADR-006: SQLite + JSON Storage (Initial)

**Decision**: Use SQLite for metadata (runs, scores, regression cases) and JSON files for trace storage.

**Reason**: Zero infrastructure dependencies for Phase 0–8. Simplicity is correct at this stage. Traces are naturally document-shaped — JSON is the right format.

**Migration Path**: When scale demands it, SQLite → PostgreSQL. JSON traces → object store (S3, GCS). This migration is not planned before Phase 9.

**Alternatives Considered**: PostgreSQL from day one (premature — adds infrastructure complexity with no benefit at MVP scale), Redis (not appropriate for persistent storage).

**Status**: Accepted

---

## ADR-007: Pydantic v2 for All Data Contracts

**Decision**: All internal data models use Pydantic v2. No dataclasses, TypedDicts, or plain dicts for contract types.

**Reason**: Pydantic v2 provides runtime validation, serialization, schema generation, and FastAPI integration. Using it consistently eliminates entire classes of bugs at boundaries.

**Status**: Accepted

---

## ADR-008: Demo Agent First

**Decision**: The first `BaseAgentAdapter` implementation is a built-in `DemoAgentAdapter` with hardcoded, controllable behavior.

**Reason**: A real agent would require external dependencies and API keys to test the evaluation engine. The demo agent allows full end-to-end testing of the pipeline with zero external dependencies.

**Constraint**: The evaluation engine must never depend on `DemoAgentAdapter` directly. It only depends on `BaseAgentAdapter`.

**Status**: Accepted

---

## ADR-009: Deterministic Evaluation First, LLM Judges Second

**Decision**: Every evaluation check that can be expressed as a deterministic rule must be. LLM judges are used only for checks that genuinely require semantic understanding.

**Reason**: Deterministic checks are fast, free, reproducible, and not subject to model drift. LLM judges are expensive, slow, and can vary across runs. Use the right tool for the right job.

**Status**: Accepted

---

## ADR-010: No Premature Adaptive Testing

**Decision**: The adaptive testing engine (Phase 10) must not be implemented before Phase 9 is complete.

**Reason**: Adaptive testing requires rich evaluation history to learn from. Building it before that history exists produces a system with nothing to adapt to. Premature implementation creates complexity without benefit.

**Status**: Accepted

---

## ADR-011: openai_provider Package Name (Not openai)

**Decision**: The OpenAI provider package is named `providers/openai_provider/` instead of `providers/openai/`.

**Reason**: `openai` is the name of the official OpenAI Python SDK package. Naming our internal package `openai` would create a namespace collision — `import openai` inside our package would import itself rather than the SDK. Using `openai_provider` avoids this conflict.

**Status**: Accepted

---

## ADR-012: MockReasoningEngine for Phase 0 Demo Agent

**Decision**: The demo agent uses a `MockReasoningEngine` (rule-based, no LLM calls) in Phase 0 instead of a real `BaseLLMProvider` implementation.

**Reason**: Phase 0 must be runnable without API keys. The mock engine demonstrates the deliberate vulnerability (authority spoofing + urgency) deterministically, making tests reproducible without external dependencies. The `DemoCustomerSupportAgent` accepts an optional `llm_provider` argument so it can be upgraded in Phase 5 without interface changes.

**Constraint**: The mock engine's reasoning is for demonstration only. It does not replicate real LLM behavior. Real LLM-backed testing comes in Phase 5.

**Status**: Accepted

---

## ADR-013: Providers Directory vs. packages/ Directory

**Decision**: Concrete LLM provider implementations live in `providers/` (top-level), not in `packages/`.

**Reason**: Provider packages contain SDK-specific code (google-generativeai, openai) that must never be imported by core packages. Placing them in a separate `providers/` directory makes the dependency boundary visually and structurally clear. Any `from packages.X import Y` in a provider file would be a lint-time error.

**Status**: Accepted
