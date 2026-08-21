'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAssessment } from '../../../context/AssessmentContext';
import {
  ArrowLeft,
  Activity,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  FileText,
  Clock,
  Briefcase,
  Terminal,
  Compass,
} from 'lucide-react';
import { ChallengePack, ScenarioEvaluationResult } from '../../../types';

export default function ScenarioDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const assessmentId = searchParams.get('assessmentId');

  const { activeAssessment } = useAssessment();

  const [unwrappedParams, setUnwrappedParams] = useState<{ id: string } | null>(null);
  const [pack, setPack] = useState<ChallengePack | null>(null);
  const [loadingPack, setLoadingPack] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Await route params
  useEffect(() => {
    params.then(setUnwrappedParams).catch(err => setError(err.message));
  }, [params]);

  // Load the corresponding challenge pack to show deep scenario static definitions
  useEffect(() => {
    if (!activeAssessment) return;
    async function fetchPack() {
      try {
        setLoadingPack(true);
        const res = await fetch(`/api/challenge_packs/${activeAssessment.challenge_pack_id}`);
        if (!res.ok) throw new Error('Failed to load challenge pack details');
        const data = await res.json();
        setPack(data);
      } catch (err: any) {
        console.error(err.message);
      } finally {
        setLoadingPack(false);
      }
    }
    fetchPack();
  }, [activeAssessment]);

  if (!activeAssessment) return null;
  if (!unwrappedParams) return null;

  const scenarioId = unwrappedParams.id;
  const result = activeAssessment.evaluation_result.scenario_results.find(
    r => r.scenario_id === scenarioId
  );

  if (!result) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-left max-w-2xl mx-auto my-12 font-mono text-xs">
        <h2 className="text-red-400 font-bold flex items-center gap-2 mb-2">
          <AlertTriangle className="h-5 w-5" />
          <span>Scenario evaluation result not found</span>
        </h2>
        <p className="text-zinc-300 mb-4">No record matches the ID: {scenarioId}</p>
        <button
          onClick={() => router.push(assessmentId ? `/scenarios?assessmentId=${assessmentId}` : '/scenarios')}
          className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2 px-4 rounded border border-zinc-700 transition"
        >
          Back to Scenarios
        </button>
      </div>
    );
  }

  // Find scenario in static pack definitions
  const staticScenario = pack?.scenarios.find(s => s.id === scenarioId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back navigation */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <button
          onClick={() => router.push(assessmentId ? `/scenarios?assessmentId=${assessmentId}` : '/scenarios')}
          className="inline-flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Scenario List</span>
        </button>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider bg-zinc-900 border border-zinc-800 px-3 py-1 rounded-full">
          Evaluation Result Node
        </span>
      </div>

      {/* Header Profile */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-sm font-mono space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <span
              className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${
                result.verdict === 'PASS'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : result.verdict === 'FAIL'
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
              }`}
            >
              Verdict: {result.verdict}
            </span>
            <h1 className="text-base font-bold text-zinc-200 mt-2">
              {result.scenario_name || 'Test Scenario'}
            </h1>
            <div className="text-xs text-zinc-500 font-mono">ID: {result.scenario_id}</div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/traces?assessmentId=${activeAssessment.assessment_id}&traceId=${result.trace_id}`)}
              className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-zinc-950 font-bold px-4 py-2 rounded-lg text-xs transition font-mono"
            >
              <Activity className="h-4 w-4" />
              <span>View Chronological Execution Trace</span>
            </button>
          </div>
        </div>

        {/* Execution details strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-zinc-800 text-[11px] text-zinc-400">
          <div>
            <span className="text-zinc-500 block">Execution Status</span>
            <span className="text-zinc-300 font-medium capitalize flex items-center gap-1.5 mt-0.5">
              <span className={`h-1.5 w-1.5 rounded-full ${result.execution_status === 'success' ? 'bg-emerald-400' : 'bg-red-400'}`} />
              {result.execution_status}
            </span>
          </div>
          <div>
            <span className="text-zinc-500 block">Severity Weight</span>
            <span className="text-zinc-300 font-medium uppercase mt-0.5">{result.severity}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">Evaluation Status</span>
            <span className="text-zinc-300 font-medium mt-0.5">{result.evaluation_status}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">Trace File ID</span>
            <span className="text-zinc-300 font-medium break-all mt-0.5">{result.trace_id}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono">
        {/* Left pane: Expected Behaviors & Static Metadata */}
        <div className="lg:col-span-2 space-y-6">
          {/* Static scenario definition if pack loaded */}
          {staticScenario && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 flex items-center gap-2">
                <FileText className="h-4.5 w-4.5 text-indigo-400" />
                <span>Scenario Configuration & Rules</span>
              </h2>

              <div className="space-y-1.5">
                <span className="text-[10px] text-zinc-500 font-bold uppercase block">Description</span>
                <p className="text-xs text-zinc-400 leading-relaxed bg-zinc-950 p-3 rounded-lg border border-zinc-855">
                  {staticScenario.description}
                </p>
              </div>

              {/* Expected Behavior Details */}
              <div className="space-y-3 pt-2">
                <span className="text-[10px] text-zinc-500 font-bold uppercase block">Expected Safety Criteria</span>
                <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4 space-y-3 text-xs text-zinc-400">
                  <p className="font-semibold text-zinc-300">{staticScenario.expected_behavior.description}</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[10px] pt-2 border-t border-zinc-900">
                    <div>
                      <span className="text-zinc-500 block">Refusal Expected?</span>
                      <span className="text-zinc-300">{staticScenario.expected_behavior.should_refuse ? 'YES (Must reject adversarial inputs)' : 'NO (Functional turn execution allowed)'}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Active Validators</span>
                      <span className="text-zinc-300">{staticScenario.expected_behavior.validators.join(', ') || 'None'}</span>
                    </div>
                  </div>

                  {staticScenario.expected_behavior.forbidden_tools.length > 0 && (
                    <div className="text-[10px] pt-1">
                      <span className="text-red-400/90 font-bold block mb-1">Forbidden Tools:</span>
                      <div className="flex flex-wrap gap-1">
                        {staticScenario.expected_behavior.forbidden_tools.map(tool => (
                          <span key={tool} className="bg-red-500/10 border border-red-500/20 text-red-400 px-1.5 py-0.5 rounded text-[9px]">
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {staticScenario.expected_behavior.rules.length > 0 && (
                    <div className="text-[10px] pt-1.5">
                      <span className="text-indigo-400 font-bold block mb-1">Validation Rules:</span>
                      <ul className="list-disc pl-4 space-y-1 text-zinc-400">
                        {staticScenario.expected_behavior.rules.map((rule, idx) => (
                          <li key={idx}>{rule}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Initial message conversation starter */}
              <div className="space-y-1.5 pt-2">
                <span className="text-[10px] text-zinc-500 font-bold uppercase block">Adversarial Input Prompt</span>
                <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-3 flex items-start gap-2.5">
                  <Terminal className="h-4.5 w-4.5 text-zinc-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-zinc-300 font-mono italic leading-relaxed">
                    "{staticScenario.initial_message}"
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Detailed Validator Findings in this scenario */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 flex items-center gap-2">
              <AlertTriangle className="h-4.5 w-4.5 text-red-400" />
              <span>Validator Findings & Evidence ({result.findings.length})</span>
            </h2>

            {result.findings && result.findings.length > 0 ? (
              <div className="space-y-4">
                {result.findings.map((finding, idx) => (
                  <div key={idx} className="bg-zinc-950 border border-zinc-850 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-zinc-500">Validator: {finding.validator}</span>
                      <span
                        className={`text-[9px] uppercase font-bold px-2 py-0.5 border rounded ${
                          finding.verdict === 'PASS'
                            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                            : finding.verdict === 'FAIL'
                            ? 'bg-red-500/10 border-red-500/20 text-red-400'
                            : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                        }`}
                      >
                        {finding.verdict}
                      </span>
                    </div>

                    <div className="text-[11px] text-zinc-400">
                      <span className="text-zinc-500 uppercase font-bold block mb-1">Requirement Evaluated:</span>
                      {finding.requirement}
                    </div>

                    {finding.rule && (
                      <div className="text-[10px] text-zinc-500">
                        Rule: <span className="text-zinc-300 font-medium">{finding.rule}</span>
                        {finding.category && (
                          <span className="ml-3">
                            Category: <span className="text-zinc-300 font-medium">{finding.category}</span>
                          </span>
                        )}
                      </div>
                    )}

                    {/* Trace Evidence quotes */}
                    {finding.evidence && finding.evidence.length > 0 && (
                      <div className="space-y-1.5 pt-2 border-t border-zinc-900">
                        <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider block">
                          Validator Citations:
                        </span>
                        {finding.evidence.map((item, i) => (
                          <div key={i} className="bg-zinc-900 border border-zinc-850 p-2.5 rounded text-[10px] text-zinc-400 space-y-1">
                            <p className="italic text-zinc-300 font-medium">"{item.content}"</p>
                            <div className="flex justify-between text-[9px] text-zinc-500 font-medium">
                              <span>Reason: {item.reason}</span>
                              {item.event_index !== null && (
                                <span>Step: #{item.event_index}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-500 py-2 text-center">No structural findings generated for this run.</p>
            )}
          </div>
        </div>

        {/* Right pane: Violated Rules & Execution Bounds */}
        <div className="space-y-6">
          {/* Violated Rules List */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 flex items-center gap-2">
              <AlertTriangle className="h-4.5 w-4.5 text-zinc-500" />
              <span>Violated Rules</span>
            </h2>
            {result.violated_rules && result.violated_rules.length > 0 ? (
              <div className="space-y-2">
                {result.violated_rules.map(rule => (
                  <div key={rule} className="bg-red-500/5 border border-red-500/20 text-red-400 px-3 py-2 rounded-lg text-xs flex items-center gap-2 font-bold uppercase tracking-wider">
                    <AlertCircle className="h-4 w-4" />
                    <span>{rule.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-emerald-500/5 border border-emerald-500/10 text-emerald-400 px-3 py-2 rounded-lg text-xs flex items-center gap-2 font-bold uppercase tracking-wider">
                <CheckCircle className="h-4 w-4" />
                <span>Zero Policy Violations</span>
              </div>
            )}
          </div>

          {/* Scenario resource execution boundaries */}
          {staticScenario && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 flex items-center gap-2">
                <Clock className="h-4.5 w-4.5 text-zinc-500" />
                <span>Limits & Sandbox Constraints</span>
              </h2>
              <div className="space-y-2.5 text-xs text-zinc-400">
                <div className="flex justify-between border-b border-zinc-850 pb-1.5">
                  <span className="text-zinc-500">Max Turns allowed:</span>
                  <span className="text-zinc-200 font-semibold">{staticScenario.resource_limits.max_turns} turns</span>
                </div>
                <div className="flex justify-between border-b border-zinc-850 pb-1.5">
                  <span className="text-zinc-500">Timeout limit:</span>
                  <span className="text-zinc-200 font-semibold">{staticScenario.resource_limits.timeout_seconds} seconds</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Max Tool Calls limit:</span>
                  <span className="text-zinc-200 font-semibold">{staticScenario.resource_limits.max_tool_calls} calls</span>
                </div>
              </div>
            </div>
          )}

          {/* Provance and LLM Judge details */}
          {result.source && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 flex items-center gap-2">
                <Compass className="h-4.5 w-4.5 text-purple-400" />
                <span>Scoring Provenance</span>
              </h2>
              <div className="space-y-3 text-xs text-zinc-400">
                <div className="flex justify-between border-b border-zinc-850 pb-1.5">
                  <span className="text-zinc-500">Evaluation Source:</span>
                  <span className="text-zinc-200 font-bold uppercase text-[10px] bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">{result.source}</span>
                </div>
                {result.deterministic_verdict && (
                  <div className="flex justify-between border-b border-zinc-850 pb-1.5">
                    <span className="text-zinc-500">Deterministic Verdict:</span>
                    <span className="text-zinc-300">{result.deterministic_verdict}</span>
                  </div>
                )}
                {result.llm_verdict && (
                  <div className="flex justify-between border-b border-zinc-850 pb-1.5">
                    <span className="text-zinc-500">LLM Judge Verdict:</span>
                    <span className="text-zinc-300">{result.llm_verdict}</span>
                  </div>
                )}
                {result.llm_confidence !== null && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">LLM Confidence score:</span>
                    <span className="text-zinc-300">{(result.llm_confidence * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
