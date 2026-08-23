'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAssessment } from '../../context/AssessmentContext';
import {
  Play,
  Globe,
  FileCode,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ArrowRight,
  TrendingUp,
  Shield,
  Activity,
  Gauge,
  ClipboardList,
  Eye,
} from 'lucide-react';

interface SuccessMetrics {
  runId: string;
  agentId: string;
  message: string;
  score: number;
  grade: string;
  riskLevel: string;
  totalScenarios: number;
  passedScenarios: number;
  failedScenarios: number;
  inconclusiveScenarios: number;
  coveredStrategies: string[];
}

export default function EvaluatePage() {
  const router = useRouter();
  const { selectAssessment } = useAssessment();

  // Tabs: 'http' | 'python'
  const [activeTab, setActiveTab] = useState<'http' | 'python'>('http');

  // Common loading / error / success states
  const [running, setRunning] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMetrics, setSuccessMetrics] = useState<SuccessMetrics | null>(null);

  // Form states: HTTP
  const [httpName, setHttpName] = useState('http_agent');
  const [httpEndpoint, setHttpEndpoint] = useState('http://127.0.0.1:5000/chat');
  const [httpMethod, setHttpMethod] = useState('POST');
  const [httpTimeout, setHttpTimeout] = useState('10');
  const [httpInputField, setHttpInputField] = useState('message');
  const [httpOutputField, setHttpOutputField] = useState('response');

  // Form states: Python
  const [pyPath, setPyPath] = useState('agents/custom_agent_template.py');
  const [pyClass, setPyClass] = useState('CustomAgentAdapter');

  const runEvaluation = async () => {
    setRunning(true);
    setError(null);
    setSuccessMetrics(null);
    setProgressMsg('Connecting to adapter and starting pipeline...');

    const payload: any = {
      agent_type: activeTab,
    };

    if (activeTab === 'http') {
      payload.agent_id = httpName;
      payload.endpoint_url = httpEndpoint;
      payload.method = httpMethod;
      payload.timeout = parseFloat(httpTimeout) || 10.0;
      payload.request_input_field = httpInputField;
      payload.response_output_field = httpOutputField;
      setProgressMsg('Initializing HTTP Agent client & querying metadata...');
    } else {
      payload.agent_id = 'custom_python_agent';
      payload.agent_path = pyPath;
      payload.agent_class = pyClass;
      setProgressMsg('Loading Python module & validating class signatures...');
    }

    try {
      // Step simulation message rotation
      const timers = [
        setTimeout(() => setProgressMsg('Analyzing system prompt and building attack surface profile...'), 1500),
        setTimeout(() => setProgressMsg('Matching strategies and generating adversarial challenge pack...'), 3500),
        setTimeout(() => setProgressMsg('Executing scenarios E2E in secure isolated sandbox environment...'), 6000),
        setTimeout(() => setProgressMsg('Evaluating traces & running adaptive planning loops...'), 9000),
      ];

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 125000); // 125s timeout

      console.log('[Frontend] Sending /api/evaluate request:', payload);

      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      // Clear timers
      timers.forEach(t => clearTimeout(t));
      clearTimeout(timeoutId);

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to complete evaluation run.');
      }

      setSuccessMetrics({
        runId: data.run_id,
        agentId: data.agent_id,
        message: data.message,
        score: data.score ?? 0,
        grade: data.grade ?? 'F',
        riskLevel: data.risk_level ?? 'CRITICAL',
        totalScenarios: data.total_scenarios ?? 0,
        passedScenarios: data.passed_scenarios ?? 0,
        failedScenarios: data.failed_scenarios ?? 0,
        inconclusiveScenarios: data.inconclusive_scenarios ?? 0,
        coveredStrategies: data.covered_strategies ?? [],
      });

    } catch (err: any) {
      console.error('[Frontend] Evaluation error:', err);
      let friendlyError = err.message || 'Unknown evaluation execution error.';
      if (err.name === 'AbortError') {
        friendlyError = 'Evaluation timed out. The operation took longer than 125 seconds.';
      }
      if (friendlyError.includes('Failed to connect') || friendlyError.includes('Connection Error')) {
        friendlyError += ' | Suggestion: Check that your HTTP agent process is running locally on the correct port and host address.';
      } else if (friendlyError.includes('No valid agent adapter class')) {
        friendlyError += ' | Suggestion: Verify that your Python file exists and contains a class subclassing BaseAgentAdapter.';
      }
      setError(friendlyError);
    } finally {
      setRunning(false);
      setProgressMsg('');
    }
  };

  const viewReport = () => {
    if (successMetrics) {
      selectAssessment(successMetrics.runId);
      router.push(`/?assessmentId=${successMetrics.runId}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-5">
        <h1 className="text-xl font-bold text-zinc-100 font-mono flex items-center gap-2">
          <Activity className="h-5.5 w-5.5 text-emerald-400" />
          Reliability Evaluation Playground
        </h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">
          Evaluate and benchmark custom LLM agents against generated targeted adversarial vectors.
        </p>
      </div>

      {/* Grid: Form & How it works */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Form Panel */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Tab Selector */}
          <div className="flex bg-zinc-900 border border-zinc-850 p-1 rounded-xl gap-2">
            <button
              onClick={() => { setActiveTab('http'); setError(null); setSuccessMetrics(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold font-mono transition-all duration-200 ${
                activeTab === 'http'
                  ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-lg'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/50'
              }`}
            >
              <Globe className="h-4 w-4" />
              HTTP/API Agent
            </button>
            <button
              onClick={() => { setActiveTab('python'); setError(null); setSuccessMetrics(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold font-mono transition-all duration-200 ${
                activeTab === 'python'
                  ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-lg'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/50'
              }`}
            >
              <FileCode className="h-4 w-4" />
              Python Agent
            </button>
          </div>

          {/* Form Content card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute -top-24 -right-24 h-48 w-48 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none" />

            {running && (
              <div className="absolute inset-0 bg-zinc-950/85 backdrop-blur-sm flex flex-col items-center justify-center text-zinc-300 font-mono p-6 text-center z-25">
                <Loader2 className="h-10 w-10 text-emerald-500 animate-spin mb-4" />
                <div className="text-sm font-semibold text-zinc-200">Executing Reliability Assessment...</div>
                <div className="text-[10px] text-zinc-400 mt-2 max-w-sm leading-relaxed">{progressMsg}</div>
              </div>
            )}

            {activeTab === 'http' ? (
              <div className="space-y-4 font-mono text-xs">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">Agent Name</label>
                    <input
                      type="text"
                      value={httpName}
                      onChange={(e) => setHttpName(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">Endpoint URL</label>
                    <input
                      type="text"
                      value={httpEndpoint}
                      onChange={(e) => setHttpEndpoint(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">HTTP Method</label>
                    <select
                      value={httpMethod}
                      onChange={(e) => setHttpMethod(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    >
                      <option value="POST">POST</option>
                      <option value="GET">GET</option>
                      <option value="PUT">PUT</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">Timeout (seconds)</label>
                    <input
                      type="number"
                      value={httpTimeout}
                      onChange={(e) => setHttpTimeout(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">Input Field (JSON Path)</label>
                    <input
                      type="text"
                      value={httpInputField}
                      onChange={(e) => setHttpInputField(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold">Output Field (JSON Path)</label>
                    <input
                      type="text"
                      value={httpOutputField}
                      onChange={(e) => setHttpOutputField(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4 font-mono text-xs">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold">Python File Path</label>
                  <input
                    type="text"
                    value={pyPath}
                    onChange={(e) => setPyPath(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold">Agent Class Name</label>
                  <input
                    type="text"
                    value={pyClass}
                    onChange={(e) => setPyClass(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 focus:outline-none py-2 px-3 rounded-lg text-zinc-200 text-xs"
                  />
                </div>
              </div>
            )}

            {/* Evaluate Button */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={runEvaluation}
                disabled={running}
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-800 disabled:text-zinc-650 text-zinc-950 px-6 py-3 rounded-xl font-mono text-xs font-bold transition duration-200 active:scale-[0.98] shadow-lg shadow-emerald-500/10"
              >
                <Play className="h-4 w-4 fill-current" />
                [ Evaluate Agent ]
              </button>
            </div>

          </div>

          {/* Success Panel */}
          {successMetrics && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6 font-mono">
              <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <h2 className="text-sm font-bold text-zinc-100">Evaluation Success</h2>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-zinc-950 border border-zinc-850 p-4 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase">Score</span>
                  <div className="text-lg font-bold text-zinc-100">{successMetrics.score.toFixed(1)}%</div>
                </div>
                <div className="bg-zinc-950 border border-zinc-850 p-4 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase">Grade</span>
                  <div className="text-lg font-bold text-zinc-100">{successMetrics.grade}</div>
                </div>
                <div className="bg-zinc-950 border border-zinc-850 p-4 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase">Risk Level</span>
                  <div className={`text-xs font-bold uppercase py-1 ${
                    successMetrics.riskLevel === 'CRITICAL' || successMetrics.riskLevel === 'HIGH'
                      ? 'text-rose-400'
                      : 'text-amber-400'
                  }`}>{successMetrics.riskLevel}</div>
                </div>
                <div className="bg-zinc-950 border border-zinc-850 p-4 rounded-xl text-center space-y-1">
                  <span className="text-[10px] text-zinc-500 uppercase">Scenarios</span>
                  <div className="text-lg font-bold text-zinc-100">{successMetrics.totalScenarios}</div>
                </div>
              </div>

              {/* Scenarios Split Table */}
              <div className="bg-zinc-950 border border-zinc-850 rounded-xl p-4 text-[11px] space-y-2 text-zinc-400">
                <div className="flex justify-between border-b border-zinc-900 pb-1.5">
                  <span>Passed Scenarios:</span>
                  <span className="text-emerald-400 font-bold">{successMetrics.passedScenarios}</span>
                </div>
                <div className="flex justify-between border-b border-zinc-900 pb-1.5">
                  <span>Failed Scenarios:</span>
                  <span className="text-rose-400 font-bold">{successMetrics.failedScenarios}</span>
                </div>
                <div className="flex justify-between">
                  <span>Inconclusive Scenarios:</span>
                  <span className="text-zinc-500 font-bold">{successMetrics.inconclusiveScenarios}</span>
                </div>
              </div>

              {/* Covered Strategies */}
              <div className="space-y-2">
                <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Covered Attack Strategies</span>
                <div className="flex flex-wrap gap-1.5">
                  {successMetrics.coveredStrategies.length > 0 ? (
                    successMetrics.coveredStrategies.map(strat => (
                      <span key={strat} className="bg-zinc-950 border border-zinc-850 text-zinc-400 text-[10px] px-2.5 py-1 rounded-md">
                        {strat}
                      </span>
                    ))
                  ) : (
                    <span className="text-zinc-500 text-xs italic">No strategies covered.</span>
                  )}
                </div>
              </div>

              <div className="flex justify-between items-center bg-zinc-950 border border-zinc-850 p-3.5 rounded-xl text-[10px]">
                <div className="text-zinc-500">Run ID: <span className="text-zinc-400">{successMetrics.runId}</span></div>
                <button
                  onClick={viewReport}
                  className="flex items-center gap-1.5 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 hover:text-zinc-100 text-zinc-300 px-4 py-2 rounded-lg font-bold transition"
                >
                  <Eye className="h-3.5 w-3.5" />
                  View Full Report
                </button>
              </div>

            </div>
          )}

          {/* Failure Alert */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/35 rounded-2xl p-5 flex gap-4 text-xs font-mono text-red-400 shadow-lg shadow-red-500/5">
              <AlertCircle className="h-6 w-6 flex-shrink-0 text-red-500" />
              <div className="space-y-1">
                <div className="font-bold uppercase tracking-wider text-red-200">Evaluation Execution Failed</div>
                <p className="leading-relaxed text-zinc-300">{error}</p>
              </div>
            </div>
          )}

        </div>

        {/* How it works sidebar panel */}
        <div className="space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl font-mono text-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
              <Shield className="h-4.5 w-4.5 text-emerald-400" />
              <span className="font-bold text-zinc-100 uppercase tracking-wider">How it works</span>
            </div>

            <div className="space-y-6 relative">
              <div className="flex gap-3">
                <div className="h-6 w-6 bg-zinc-800 rounded-full flex items-center justify-center font-bold text-[10px] text-zinc-300 flex-shrink-0">
                  1
                </div>
                <div className="space-y-1">
                  <div className="font-bold text-zinc-200">Agent Adapter</div>
                  <p className="text-[10px] text-zinc-400 leading-relaxed">
                    Connects to your agent via custom local Python adapter script or external REST endpoint.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="h-6 w-6 bg-zinc-800 rounded-full flex items-center justify-center font-bold text-[10px] text-zinc-300 flex-shrink-0">
                  2
                </div>
                <div className="space-y-1">
                  <div className="font-bold text-zinc-200">Adversarial Tests</div>
                  <p className="text-[10px] text-zinc-400 leading-relaxed">
                    Automatically scans the agent prompt/tools and constructs targeted security pressure packs.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="h-6 w-6 bg-zinc-800 rounded-full flex items-center justify-center font-bold text-[10px] text-zinc-300 flex-shrink-0">
                  3
                </div>
                <div className="space-y-1">
                  <div className="font-bold text-zinc-200">Sandbox Execution</div>
                  <p className="text-[10px] text-zinc-400 leading-relaxed">
                    Safely executes the scenarios inside isolated environment sandboxes recording complete traces.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="h-6 w-6 bg-zinc-800 rounded-full flex items-center justify-center font-bold text-[10px] text-zinc-300 flex-shrink-0">
                  4
                </div>
                <div className="space-y-1">
                  <div className="font-bold text-zinc-200">Reliability Score</div>
                  <p className="text-[10px] text-zinc-400 leading-relaxed">
                    Aggregates verdicts, extracts critical findings, scores metrics, and recommends fixes.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-zinc-950 border border-zinc-850 p-4 rounded-xl text-zinc-400 text-[10px] leading-relaxed">
              <strong>Demo Tip:</strong> To E2E test the HTTP Agent, run `python agents/sample_http_agent.py` in your terminal, then query it here.
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
