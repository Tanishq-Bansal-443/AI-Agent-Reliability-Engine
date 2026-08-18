export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4">
      {/* Header */}
      <div className="text-center max-w-3xl">
        {/* Status badge */}
        <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-medium px-4 py-1.5 rounded-full mb-8">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          Phase 0 — Foundation Complete
        </div>

        {/* Title */}
        <h1 className="text-5xl font-bold tracking-tight mb-4 bg-gradient-to-r from-white via-gray-100 to-gray-400 bg-clip-text text-transparent">
          AI Agent Reliability Engine
        </h1>

        {/* Tagline */}
        <p className="text-xl text-gray-400 mb-3">
          Sentry / Datadog for AI Agents
        </p>
        <p className="text-gray-500 text-base leading-relaxed mb-12">
          Automatically profile agents, generate adversarial tests, execute
          them safely, explain failures, score risk, and continuously convert
          discovered failures into regression tests.
        </p>

        {/* Core Loop */}
        <div className="flex flex-wrap justify-center gap-2 mb-12 text-xs font-mono">
          {[
            "PROFILE",
            "FIND RISKS",
            "GENERATE ATTACKS",
            "CHALLENGE PACK",
            "SANDBOX EXECUTION",
            "TRACE",
            "EVALUATE",
            "DIAGNOSE",
            "SCORE",
            "REGRESSION",
            "ADAPT",
          ].map((step, i, arr) => (
            <span key={step} className="flex items-center gap-2">
              <span className="bg-gray-800 border border-gray-700 text-gray-300 px-2.5 py-1 rounded">
                {step}
              </span>
              {i < arr.length - 1 && (
                <span className="text-gray-600">→</span>
              )}
            </span>
          ))}
        </div>

        {/* Phase status cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-12 text-left">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-2">
              ✓ Backend API
            </div>
            <p className="text-sm text-gray-400">
              FastAPI running. <code className="text-gray-300 text-xs bg-gray-800 px-1 py-0.5 rounded">GET /api/health</code> returns 200.
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-2">
              ✓ Core Models
            </div>
            <p className="text-sm text-gray-400">
              All Pydantic v2 domain models defined. 122 tests passing.
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-2">
              ✓ Vertical Slice
            </div>
            <p className="text-sm text-gray-400">
              Demo agent → sandbox → trace pipeline working end-to-end.
            </p>
          </div>
        </div>

        {/* Architecture callout */}
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 text-left">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">
            Phase 0 Architecture
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            {[
              { label: "Framework", value: "FastAPI + Next.js" },
              { label: "Models", value: "Pydantic v2" },
              { label: "LLM", value: "Gemini (primary)" },
              { label: "Sandbox", value: "LocalMockSandbox" },
            ].map((item) => (
              <div key={item.label}>
                <div className="text-gray-600 mb-1">{item.label}</div>
                <div className="text-gray-300 font-medium">{item.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer note */}
        <p className="text-gray-700 text-xs mt-8">
          Dashboard, evaluation results, and reliability scorecards — Phase 9
        </p>
      </div>
    </main>
  );
}
