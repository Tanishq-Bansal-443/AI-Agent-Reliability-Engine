'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ShieldAlert,
  GitBranch,
  Brain,
  History,
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  Layers,
  Fingerprint,
  ExternalLink,
} from 'lucide-react';
import { ReliabilityAssessmentArtifact } from '../../../types';

export default function AssessmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [unwrappedParams, setUnwrappedParams] = useState<{ id: string } | null>(null);
  const [assessment, setAssessment] = useState<ReliabilityAssessmentArtifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Await route params
  useEffect(() => {
    params.then(setUnwrappedParams).catch(err => setError(err.message));
  }, [params]);

  // Load assessment detail
  useEffect(() => {
    if (!unwrappedParams) return;
    const assessmentId = unwrappedParams.id;
    async function fetchDetail() {
      try {
        setLoading(true);
        const res = await fetch(`/api/assessments/${assessmentId}`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error(`Assessment '${assessmentId}' not found`);
          }
          throw new Error('Failed to load assessment');
        }
        const data = await res.json();
        setAssessment(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchDetail();
  }, [unwrappedParams]);

  if (loading) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs">
        <div className="h-6 w-6 animate-spin border-2 border-emerald-500 border-t-transparent rounded-full mb-2" />
        <span>Loading assessment details...</span>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-left max-w-2xl mx-auto my-12">
        <h2 className="text-red-400 font-bold font-mono flex items-center gap-2 mb-2">
          <AlertTriangle className="h-5 w-5" />
          <span>Failed to load assessment detail</span>
        </h2>
        <p className="text-zinc-300 text-xs font-mono mb-4">{error || 'Record not found'}</p>
        <button
          onClick={() => router.push('/assessments')}
          className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono py-2 px-4 rounded border border-zinc-700 transition"
        >
          Back to History
        </button>
      </div>
    );
  }

  const score = assessment.reliability_assessment.score;
  const relAssess = assessment.reliability_assessment;
  const regReport = assessment.regression_report;
  const adaptPlan = assessment.adaptive_test_plan;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back link & Actions */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <button
          onClick={() => router.push('/assessments')}
          className="inline-flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Assessment History</span>
        </button>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider bg-zinc-900 border border-zinc-800 px-3 py-1 rounded-full">
          Assessment Artifact
        </span>
      </div>

      {/* Header Info Banner */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-sm font-mono space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-lg font-bold text-zinc-200">Assessment Detail</h1>
            <div className="text-xs text-zinc-400 flex flex-wrap gap-x-4 gap-y-1">
              <span className="flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-zinc-500" />
                Agent: <strong className="text-zinc-300">{assessment.agent_id}</strong> (v{assessment.agent_version})
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-zinc-500" />
                Ran: <span className="text-zinc-300">{new Date(assessment.created_at).toLocaleString()}</span>
              </span>
            </div>
          </div>
          {/* Large badge */}
          <div className="flex items-center gap-3">
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-center">
              <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">Score</div>
              <div className="text-xl font-extrabold text-emerald-400 mt-0.5">{score.overall_score.toFixed(1)}%</div>
            </div>
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-center">
              <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">Grade</div>
              <div className="text-xl font-extrabold text-zinc-300 mt-0.5">{score.grade}</div>
            </div>
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-center">
              <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">Risk</div>
              <div className="text-xl font-extrabold text-red-400 uppercase mt-0.5">{score.risk_level}</div>
            </div>
          </div>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-zinc-800 text-[11px] text-zinc-400">
          <div>
            <span className="text-zinc-500 block">Assessment ID</span>
            <span className="text-zinc-300 font-medium break-all">{assessment.assessment_id}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">Execution Run ID</span>
            <span className="text-zinc-300 font-medium break-all">{assessment.execution_run_id}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">Challenge Pack ID</span>
            <span className="text-zinc-300 font-medium break-all">{assessment.challenge_pack_id}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">SHA-256 Hash Integrity</span>
            <span className="text-zinc-300 font-medium break-all flex items-center gap-1.5">
              <Fingerprint className="h-3.5 w-3.5 text-zinc-500" />
              {assessment.content_hash.slice(0, 16)}...
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Findings & Coverage */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side (col-span-2): Findings */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3 mb-4 flex items-center gap-2">
              <ShieldAlert className="h-4.5 w-4.5 text-red-400" />
              <span>Security & Reliability Findings ({relAssess.findings.length})</span>
            </h2>

            {relAssess.findings && relAssess.findings.length > 0 ? (
              <div className="space-y-4">
                {relAssess.findings.map((finding, idx) => (
                  <div key={idx} className="bg-zinc-950 border border-zinc-850 rounded-lg p-5 space-y-3 font-mono">
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <span
                          className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border ${
                            finding.severity?.toLowerCase() === 'critical'
                              ? 'bg-red-500/10 border-red-500/30 text-red-400'
                              : finding.severity?.toLowerCase() === 'high'
                              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                              : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                          }`}
                        >
                          {finding.severity || 'Medium'} Severity
                        </span>
                        <h3 className="text-sm font-bold text-zinc-200 mt-2">{finding.title}</h3>
                      </div>
                      <span className="text-xs text-zinc-500 font-bold bg-zinc-900 border border-zinc-800 px-2.5 py-1 rounded">
                        Priority {finding.priority}/100
                      </span>
                    </div>

                    <p className="text-xs text-zinc-400 leading-relaxed">{finding.description}</p>

                    {/* Affected items */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[10px] text-zinc-500 border-t border-zinc-900 pt-3">
                      <div>
                        <span className="text-zinc-600 block">Affected Tools</span>
                        <span className="text-zinc-300 font-medium">
                          {finding.affected_tools.join(', ') || 'None'}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-600 block">Attack Surfaces</span>
                        <span className="text-zinc-300 font-medium">
                          {finding.attack_surfaces.join(', ') || 'None'}
                        </span>
                      </div>
                    </div>

                    {/* Evidence */}
                    {finding.evidence && finding.evidence.length > 0 && (
                      <div className="bg-zinc-900 border border-zinc-850 rounded-lg p-3 space-y-2 mt-2">
                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                          Trace Evidence:
                        </span>
                        <ul className="list-disc pl-4 space-y-1.5 text-[10px] text-zinc-400 leading-relaxed">
                          {finding.evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="border border-dashed border-zinc-800 rounded-lg p-8 text-center text-xs font-mono text-zinc-500">
                No security vulnerabilities or failures discovered in this evaluation pack.
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Attack Surface & Strategy Coverage */}
        <div className="space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 font-mono">
            <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 mb-4">
              Attack Strategy Coverage
            </h2>
            <div className="space-y-4">
              <div>
                <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-2">
                  Covered ({relAssess.covered_strategies.length})
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {relAssess.covered_strategies.map(s => (
                    <span key={s} className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] py-1 px-2 rounded-lg">
                      {s.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
              <div className="pt-2">
                <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-2">
                  Uncovered ({relAssess.uncovered_strategies.length})
                </span>
                {relAssess.uncovered_strategies.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {relAssess.uncovered_strategies.map(s => (
                      <span key={s} className="bg-zinc-950 border border-zinc-800 text-zinc-400 text-[10px] py-1 px-2 rounded-lg">
                        {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[10px] text-zinc-500 font-normal">None — Full Strategy Coverage</span>
                )}
              </div>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 font-mono">
            <h2 className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-3 mb-4">
              Attack Surface Coverage
            </h2>
            <div className="space-y-4">
              <div>
                <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-2">
                  Covered ({relAssess.covered_attack_surfaces.length})
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {relAssess.covered_attack_surfaces.map(s => (
                    <span key={s} className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] py-1 px-2 rounded-lg">
                      {s.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
              <div className="pt-2">
                <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-2">
                  Uncovered ({relAssess.uncovered_attack_surfaces.length})
                </span>
                {relAssess.uncovered_attack_surfaces.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {relAssess.uncovered_attack_surfaces.map(s => (
                      <span key={s} className="bg-zinc-950 border border-zinc-800 text-zinc-400 text-[10px] py-1 px-2 rounded-lg">
                        {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[10px] text-zinc-500 font-normal">None — Full Attack Surface Coverage</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Regression comparison block */}
      {regReport ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3 mb-4 flex items-center gap-2">
            <GitBranch className="h-4.5 w-4.5 text-indigo-400" />
            <span>Regression Comparison Report</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 font-mono">
            {/* Left summary cards */}
            <div className="space-y-3">
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="text-[10px] text-zinc-500">Status</div>
                <div className={`text-xl font-bold uppercase mt-1 ${
                  regReport.status === 'improved'
                    ? 'text-emerald-400'
                    : regReport.status === 'regressed'
                    ? 'text-red-400'
                    : 'text-zinc-300'
                }`}>
                  {regReport.status}
                </div>
              </div>
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="text-[10px] text-zinc-500">Score Delta</div>
                <div className={`text-xl font-extrabold mt-1 ${
                  regReport.score_delta > 0
                    ? 'text-emerald-400'
                    : regReport.score_delta < 0
                    ? 'text-red-400'
                    : 'text-zinc-300'
                }`}>
                  {regReport.score_delta > 0 ? `+${regReport.score_delta.toFixed(1)}%` : `${regReport.score_delta.toFixed(1)}%`}
                </div>
              </div>
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4 text-[10px] text-zinc-500 space-y-1">
                <div>Previous Run ID:</div>
                <div className="text-zinc-300 font-semibold text-[9px] break-all">{regReport.previous_run_id}</div>
                <div className="mt-2">Previous Grade/Score:</div>
                <div className="text-zinc-300 font-semibold">{regReport.previous_grade} ({regReport.previous_score.toFixed(1)}%)</div>
              </div>
            </div>

            {/* Right details */}
            <div className="lg:col-span-3 space-y-4">
              {/* Failure changes lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* New failures */}
                <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                  <div className="text-xs font-bold text-red-400 mb-2 pb-1 border-b border-zinc-850 flex items-center justify-between">
                    <span>NEW FAILURES</span>
                    <span className="bg-red-500/10 text-red-400 px-2 py-0.5 rounded text-[10px]">{regReport.new_failures?.length || 0}</span>
                  </div>
                  {regReport.new_failures && regReport.new_failures.length > 0 ? (
                    <ul className="space-y-2 text-[11px]">
                      {regReport.new_failures.map((f, i) => (
                        <li key={i} className="text-zinc-300">
                          <strong className="text-zinc-200">{f.title}</strong>
                          <div className="text-zinc-500 text-[10px] mt-0.5">{f.description}</div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-zinc-500 text-[11px] py-2">No new failure modes introduced.</p>
                  )}
                </div>

                {/* Fixed failures */}
                <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                  <div className="text-xs font-bold text-emerald-400 mb-2 pb-1 border-b border-zinc-850 flex items-center justify-between">
                    <span>FIXED FAILURES</span>
                    <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded text-[10px]">{regReport.fixed_failures?.length || 0}</span>
                  </div>
                  {regReport.fixed_failures && regReport.fixed_failures.length > 0 ? (
                    <ul className="space-y-2 text-[11px]">
                      {regReport.fixed_failures.map((f, i) => (
                        <li key={i} className="text-zinc-300">
                          <strong className="text-zinc-200">{f.title}</strong>
                          <div className="text-zinc-500 text-[10px] mt-0.5">{f.description}</div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-zinc-500 text-[11px] py-2">No previously active failure modes resolved.</p>
                  )}
                </div>
              </div>

              {/* Persistent failures */}
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="text-xs font-bold text-zinc-400 mb-2 pb-1 border-b border-zinc-850 flex items-center justify-between">
                  <span>PERSISTENT FAILURES</span>
                  <span className="bg-zinc-850 text-zinc-400 px-2 py-0.5 rounded text-[10px]">{regReport.persistent_failures?.length || 0}</span>
                </div>
                {regReport.persistent_failures && regReport.persistent_failures.length > 0 ? (
                  <div className="space-y-2 text-[11px] divide-y divide-zinc-850">
                    {regReport.persistent_failures.map((f, i) => (
                      <div key={i} className="pt-2 first:pt-0">
                        <div className="font-semibold text-zinc-200">{f.title}</div>
                        <p className="text-zinc-500 text-[10px] mt-0.5 leading-relaxed">{f.description}</p>
                        <div className="mt-1 text-[9px] text-zinc-400">
                          Severity: <span className="text-zinc-300">{f.current_severity}</span> | Tool: <span className="text-zinc-300">{f.current_tools.join(', ')}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-500 text-[11px] py-2">No persistent failures carried over.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Adaptive plan block */}
      {adaptPlan ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3 mb-4 flex items-center gap-2">
            <Brain className="h-4.5 w-4.5 text-purple-400" />
            <span>Adaptive Challenge Planning</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono text-xs">
            <div className="space-y-3">
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="text-[10px] text-zinc-500 uppercase">Test Suite Budget</div>
                <div className="text-2xl font-extrabold text-indigo-400 mt-1">{adaptPlan.budget} Scenarios</div>
              </div>
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="text-[10px] text-zinc-500 uppercase">Reasoning Summary</div>
                <p className="text-zinc-300 text-[11px] mt-1.5 leading-relaxed">{adaptPlan.reasoning_summary}</p>
              </div>
            </div>

            <div className="lg:col-span-2 bg-zinc-950 border border-zinc-850 rounded-lg p-4">
              <div className="text-xs font-bold text-zinc-400 mb-3 pb-1 border-b border-zinc-850">
                Prioritized Strategy Allocation
              </div>
              <div className="space-y-3">
                {adaptPlan.strategy_priorities && adaptPlan.strategy_priorities.length > 0 ? (
                  adaptPlan.strategy_priorities
                    .filter(sp => sp.priority_score > 0)
                    .sort((a, b) => b.priority_score - a.priority_score)
                    .map((sp, idx) => (
                      <div key={idx} className="flex items-center justify-between border-b border-zinc-900 pb-2 last:border-0 last:pb-0">
                        <div>
                          <div className="font-semibold text-zinc-250">{sp.strategy_id.replace(/_/g, ' ')}</div>
                          <div className="text-[10px] text-zinc-500 max-w-md line-clamp-1 mt-0.5">{sp.reason}</div>
                        </div>
                        <div className="flex items-center gap-4 text-right">
                          <div>
                            <div className="text-[10px] text-zinc-500">Allocation</div>
                            <div className="font-bold text-zinc-300 mt-0.5">{sp.recommended_scenario_count} scenarios</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-zinc-500">Priority</div>
                            <div className="font-bold text-indigo-400 mt-0.5">{sp.priority_score}</div>
                          </div>
                        </div>
                      </div>
                    ))
                ) : (
                  <p className="text-zinc-500 py-4 text-center">No strategies prioritized under current budget.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
