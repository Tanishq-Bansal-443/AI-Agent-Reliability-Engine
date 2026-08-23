# AARE Security Intelligence Web Dashboard

This is the presentation, exploration, and playground interface for the AI Agent Reliability Engine (AARE), built with Next.js, TypeScript, Tailwind CSS, and shadcn/ui.

## 🚀 Getting Started

First, ensure the FastAPI backend is running on `127.0.0.1:8000`.

Then, install dependencies and launch the dev server:

```bash
# 1. Install dependencies
npm install

# 2. Run the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to explore the dashboard.

---

## 🏗️ Core Views & Components

1. **Dashboard Overview (`/`)**:
   - Visualizes overall security score, grade, pass rates, risk level, and failure breakdowns.
   - Highlights priority testing recommendations.
   - Links to active run assessments via query parameter `?assessmentId=<run_id>`.

2. **Evaluate Playground (`/evaluate`)**:
   - Allows judges and developers to run evaluations on custom agents.
   - **HTTP/API Agent tab**: Connects to external API agent endpoints (e.g. `http://127.0.0.1:5000/chat`).
   - **Python Agent tab**: Evaluates custom local Python classes dynamically via modular file paths.
   - Displays live execution logging and progress indicators.
   - Handles network timeouts (125 seconds limit) and shows troubleshooting guidelines when failures occur.

3. **Assessment History (`/assessments`)**:
   - Searchable, sortable listing of historical reliability runs.

4. **Traces Explorer (`/traces?traceId=...`)**:
   - Chronological event timeline showing exact user prompts, model outputs, tool calls, and result payloads (collapsible and sanitized).

5. **Regression Explorer (`/regression`)**:
   - Compares previous vs current assessments to detect verdict shifts, score deltas, and failure severity movements.

6. **Adaptive Intelligence (`/adaptive`)**:
   - Visualizes planned testing budgets, coverage gaps, and addressed strategies.

7. **Artifacts Debugger (`/artifacts`)**:
   - Tree representation verifying artifact references and listing raw JSON data.

---

## 🧪 Testing

We run frontend integration suites using Vitest. To run the tests:

```bash
npm run test
```
