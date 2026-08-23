'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAssessment } from '../../context/AssessmentContext';
import {
  Play,
  Cpu,
  Globe,
  FileCode,
  AlertCircle,
  CheckCircle2,
  Copy,
  Check,
  Loader2,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';

export default function EvaluatePage() {
  const router = useRouter();
  const { selectAssessment } = useAssessment();

  // Tabs: 'example' | 'http' | 'python'
  const [activeTab, setActiveTab] = useState<'example' | 'http' | 'python'>('example');

  // Common loading / error states
  const [running, setRunning] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ runId: string; message: string } | null>(null);
  const [copied, setCopied] = useState(false);

  // Form states: HTTP
  const [httpName, setHttpName] = useState('http_agent');
  const [httpEndpoint, setHttpEndpoint] = useState('http://localhost:5000/chat');
  const [httpMethod, setHttpMethod] = useState('POST');
  const [httpTimeout, setHttpTimeout] = useState('10');
  const [httpInputField, setHttpInputField] = useState('message');
  const [httpOutputField, setHttpOutputField] = useState('response');

  // Form states: Python (for CLI Command Helper)
  const [pyPath, setPyPath] = useState('agents/custom_agent_template.py');
  const [pyClass, setPyClass] = useState('CustomAgentAdapter');

  // Dynamic python command builder
  const buildPythonCommand = () => {
    let cmd = `python -m packages.cli.main assess --agent-type python --agent-path "${pyPath}"`;
    if (pyClass.trim()) {
      cmd += ` --agent-class "${pyClass.trim()}"`;
    }
    return cmd;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const runEvaluation = async () => {
    setRunning(true);
    setError(null);
    setSuccess(null);
    setProgressMsg('Initializing evaluation engine...');

    const payload: any = {
      agent_type: activeTab,
    };

    if (activeTab === 'example') {
      payload.agent_id = 'demo_customer_support';
      setProgressMsg('Profiling built-in agent and generating challenge pack...');
    } else if (activeTab === 'http') {
      payload.agent_id = httpName;
      payload.endpoint_url = httpEndpoint;
      payload.method = httpMethod;
      payload.timeout = parseFloat(httpTimeout) || 10.0;
      payload.request_input_field = httpInputField;
      payload.response_output_field = httpOutputField;
      setProgressMsg(`Connecting to HTTP agent at ${httpEndpoint}...`);
    } else {
      setRunning(false);
      return;
    }

    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to complete evaluation run.');
      }

      setSuccess({
        runId: data.run_id,
        message: data.message || 'Evaluation finished.',
      });

      // Automatically refresh the dashboard data and select the new assessment
      setTimeout(() => {
        selectAssessment(data.run_id);
        router.push(`/?assessmentId=${data.run_id}`);
      }, 1500);

    } catch (err: any) {
      setError(err.message || 'Unknown evaluation execution error.');
    } finally {
      setRunning(false);
      setProgressMsg('');
    }
  };

  const pythonTemplateCode = `from packages.agent_adapters.base import BaseAgentAdapter
from packages.core.models.agent import Agent, AgentInput, AgentOutput, AgentProfile
from packages.sandbox.tool_runtime import ToolRuntime

class CustomAgentAdapter(BaseAgentAdapter):
    def get_agent(self) -> Agent:
        return Agent(
            id="custom_agent",
            name="My Custom Agent",
            system_prompt="You are a customer service assistant.",
            tools=[]
        )

    def get_profile(self) -> AgentProfile:
        # Define capability profile and attack surfaces
        ...

    async def run(self, agent_input: AgentInput, runtime: ToolRuntime) -> AgentOutput:
        # Route your LLM execution and return AgentOutput
        ...`;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-5">
        <h1 className="text-xl font-bold text-zinc-100 font-mono flex items-center gap-2">
          <Cpu className="h-5.5 w-5.5 text-emerald-400" />
          Evaluate Your Agent
        </h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">
          Benchmark and test custom agents using our target adversarial test suite.
        </p>
      </div>

      {/* Tabs list */}
      <div className="flex bg-zinc-900 border border-zinc-850 p-1.5 rounded-xl gap-2">
        <button
          onClick={() => { setActiveTab('example'); setError(null); setSuccess(null); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-xs font-semibold font-mono transition-all duration-200 ${
            activeTab === 'example'
              ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-lg shadow-emerald-500/5'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/50'
          }`}
        >
          <Cpu className="h-4 w-4" />
          Built-in Demo Agent
        </button>
        <button
          onClick={() => { setActiveTab('http'); setError(null); setSuccess(null); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-xs font-semibold font-mono transition-all duration-200 ${
            activeTab === 'http'
              ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-lg shadow-emerald-500/5'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/50'
          }`}
        >
          <Globe className="h-4 w-4" />
          HTTP/API Agent
        </button>
        <button
          onClick={() => { setActiveTab('python'); setError(null); setSuccess(null); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-xs font-semibold font-mono transition-all duration-200 ${
            activeTab === 'python'
              ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-lg shadow-emerald-500/5'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/50'
          }`}
        >
          <FileCode className="h-4 w-4" />
          Python Agent
        </button>
      </div>

      {/* Main Tab Panel */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        {/* Glow Background accent */}
        <div className="absolute -top-24 -right-24 h-48 w-48 bg-emerald-500/10 blur-[80px] rounded-full pointer-events-none" />

        {/* Tab 1: Example Agent */}
        {activeTab === 'example' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200 font-mono">Demo Customer Support</h2>
              <p className="text-xs text-zinc-400 font-mono mt-1 leading-relaxed">
                Run the reliability engine against our built-in vulnerable agent. This will profile its tools (refunds, emails, status lookups) and execute adversarial spoofing and pressure tests.
              </p>
            </div>
            <div className="bg-zinc-950 border border-zinc-850 rounded-xl p-4 space-y-3 font-mono text-[11px]">
              <div className="flex justify-between border-b border-zinc-900 pb-2">
                <span className="text-zinc-500">Agent ID:</span>
                <span className="text-zinc-300 font-medium">demo-customer-support-v1</span>
              </div>
              <div className="flex justify-between border-b border-zinc-900 pb-2">
                <span className="text-zinc-500">Known Vulnerability:</span>
                <span className="text-rose-400 font-medium">Bypasses verification under supervisor authority</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Scenarios Included:</span>
                <span className="text-zinc-300 font-medium">Authority Spoofing, Urgency Pressure, etc.</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: HTTP Agent */}
        {activeTab === 'http' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200 font-mono">External HTTP Agent Integration</h2>
              <p className="text-xs text-zinc-400 font-mono mt-1 leading-relaxed">
                Connect an agent running independently on your network or local port. The engine sends scenario prompts to your endpoint and scores its reactions.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono">
              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Agent Identifier</label>
                <input
                  type="text"
                  value={httpName}
                  onChange={(e) => setHttpName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Endpoint URL</label>
                <input
                  type="text"
                  value={httpEndpoint}
                  onChange={(e) => setHttpEndpoint(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">HTTP Method</label>
                <select
                  value={httpMethod}
                  onChange={(e) => setHttpMethod(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs py-2 px-3 rounded-lg focus:outline-none"
                >
                  <option value="POST">POST</option>
                  <option value="GET">GET</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Timeout (seconds)</label>
                <input
                  type="number"
                  value={httpTimeout}
                  onChange={(e) => setHttpTimeout(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Request Input Field (JSON Path)</label>
                <input
                  type="text"
                  value={httpInputField}
                  onChange={(e) => setHttpInputField(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Response Output Field (JSON Path)</label>
                <input
                  type="text"
                  value={httpOutputField}
                  onChange={(e) => setHttpOutputField(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Python Agent */}
        {activeTab === 'python' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200 font-mono">Python Agent Local Execution</h2>
              <p className="text-xs text-zinc-400 font-mono mt-1 leading-relaxed">
                For security reasons, arbitrary Python scripts cannot be executed directly within the web process. However, you can run them safely in your own terminal using our local loader!
              </p>
            </div>

            {/* Warning block */}
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex gap-3 text-[11px] font-mono text-amber-400">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <div className="space-y-1">
                <div className="font-semibold uppercase">Security Limit Alert</div>
                <p className="leading-relaxed">
                  Executing user-provided Python scripts poses severe file deletion, secret leak, and process injection risks. Expose your agent via a local HTTP endpoint, or use the CLI command below to run the assessment locally.
                </p>
              </div>
            </div>

            {/* Dynamic CLI helper */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-zinc-300 font-mono uppercase tracking-wider">CLI Command Builder</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold">Python File Path</label>
                  <input
                    type="text"
                    value={pyPath}
                    onChange={(e) => setPyPath(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold">Adapter Class Name</label>
                  <input
                    type="text"
                    value={pyClass}
                    onChange={(e) => setPyClass(e.target.value)}
                    placeholder="CustomAgentAdapter"
                    className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs py-2 px-3 rounded-lg text-zinc-200"
                  />
                </div>
              </div>

              {/* Generated command terminal */}
              <div className="bg-zinc-950 border border-zinc-850 rounded-xl p-4 flex items-center justify-between font-mono text-xs text-zinc-300">
                <div className="overflow-x-auto whitespace-nowrap pr-4 scrollbar-thin">
                  <span className="text-emerald-400">$ </span>
                  {buildPythonCommand()}
                </div>
                <button
                  onClick={() => copyToClipboard(buildPythonCommand())}
                  className="flex-shrink-0 bg-zinc-900 border border-zinc-850 hover:bg-zinc-800 hover:text-zinc-100 text-zinc-400 p-2 rounded-lg transition"
                  title="Copy command"
                >
                  {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Adapter template block */}
            <div className="space-y-2">
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider font-mono">Agent Interface Contract</span>
              <pre className="bg-zinc-950 border border-zinc-850 rounded-xl p-4 text-[10px] leading-relaxed text-zinc-400 overflow-x-auto max-h-48 scrollbar-thin font-mono">
                {pythonTemplateCode}
              </pre>
            </div>
          </div>
        )}

        {/* Running loader / status indicator */}
        {running && (
          <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm flex flex-col items-center justify-center text-zinc-300 font-mono p-6 text-center z-20">
            <Loader2 className="h-10 w-10 text-emerald-500 animate-spin mb-4" />
            <div className="text-sm font-semibold text-zinc-200">Evaluation Execution Running</div>
            <div className="text-[11px] text-zinc-400 mt-2">{progressMsg}</div>
          </div>
        )}

        {/* Success block */}
        {success && (
          <div className="absolute inset-0 bg-zinc-950/90 backdrop-blur-sm flex flex-col items-center justify-center text-zinc-300 font-mono p-6 text-center z-20">
            <CheckCircle2 className="h-12 w-12 text-emerald-400 mb-4" />
            <div className="text-sm font-bold text-zinc-100">Assessment Run Completed!</div>
            <p className="text-[11px] text-zinc-400 mt-2 max-w-sm leading-relaxed">
              {success.message}
            </p>
            <p className="text-[10px] text-zinc-500 mt-4">
              Redirecting you to the dashboard views to audit the trace results...
            </p>
          </div>
        )}
      </div>

      {/* API Error Notification */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/35 rounded-xl p-4 flex gap-3 text-xs font-mono text-red-400">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <div className="space-y-1">
            <div className="font-semibold uppercase">API execution failed</div>
            <p className="leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Action Button for running built-in or HTTP evaluation */}
      {activeTab !== 'python' && (
        <div className="flex justify-end">
          <button
            onClick={runEvaluation}
            disabled={running}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-800 disabled:text-zinc-650 text-zinc-950 hover:text-zinc-950 px-6 py-3.5 rounded-xl font-mono text-xs font-bold transition duration-200 hover:shadow-lg hover:shadow-emerald-500/20 active:scale-[0.98]"
          >
            <Play className="h-4.5 w-4.5 fill-current" />
            [ Run Assessment ]
          </button>
        </div>
      )}
    </div>
  );
}
