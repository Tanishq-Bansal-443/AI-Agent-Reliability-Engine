'use client';

import React from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import {
  GitBranch,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  Terminal,
  Activity,
} from 'lucide-react';

export default function RegressionPage() {
  const { activeAssessment } = useAssessment();

  if (!activeAssessment) return null;

  const regReport = activeAssessment.regression_report;

  // Empty state if regression report is missing
  if (!regReport) {
    return (
      <div className="max-w-4xl mx-auto my-12 space-y-6 font-mono">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center space-y-4 shadow-xl">
          <div className="h-12 w-12 bg-indigo-500/10 border border-indigo-500/30 rounded-lg flex items-center justify-center text-indigo-400 mx-auto mb-2">
            <GitBranch className="h-6 w-6" />
          </div>
          <h2 className="text-md font-bold text-zinc-200">No Regression Context Found</h2>
          <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
            This assessment run did not include a historical baseline comparison. To enable regression testing and baseline analytics, pass the previous assessment ID when running the CLI tool.
          </p>
          <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4 text-left text-[11px] text-zinc-300 max-w-lg mx-auto">
            <p className="text-zinc-500"># Run a fresh assessment comparing to a previous baseline</p>
            <p className="text-zinc-300 font-semibold mt-1">
              python -m packages.cli.main assess --agent demo-customer-support --previous {activeAssessment.assessment_id} --version 1.1.0
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Group failures by change type
  const categorizedFailures = {
    new: regReport.new_failures || [],
    fixed: regReport.fixed_failures || [],
    persisted: regReport.persistent_failures || [],
    severity_changes: regReport.severity_changes || [],
  };

  // High impact regressions check (New failures or Severity Increased)
  const highImpactRegressions = [
    ...categorizedFailures.new,
    ...categorizedFailures.severity_changes.filter(
      (f: any) => f.change_type === 'severity_increased'
    ),
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono text-xs">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 uppercase tracking-wide">Regression Intelligence</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Differential analysis comparing agent version scorecards, failure modes, and threat bounds.
          </p>
        </div>
        <div className="text-[10px] text-zinc-500 font-mono">
          Baseline ID: <span className="text-zinc-300">{regReport.previous_run_id}</span>
        </div>
      </div>

      {/* Grid: Overview scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Comparison status card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Verdict Status
          </div>
          <div className="flex items-center gap-2">
            {regReport.status === 'improved' ? (
              <TrendingUp className="h-6 w-6 text-emerald-400" />
            ) : regReport.status === 'regressed' ? (
              <TrendingDown className="h-6 w-6 text-red-400" />
            ) : (
              <GitBranch className="h-6 w-6 text-zinc-400" />
            )}
            <span
              className={`text-2xl font-bold uppercase ${
                regReport.status === 'improved'
                  ? 'text-emerald-400'
                  : regReport.status === 'regressed'
                  ? 'text-red-400'
                  : 'text-zinc-200'
              }`}
            >
              {regReport.status}
            </span>
          </div>
        </div>

        {/* Delta Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Score Delta
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-extrabold ${
                regReport.score_delta > 0
                  ? 'text-emerald-400'
                  : regReport.score_delta < 0
                  ? 'text-red-400'
                  : 'text-zinc-200'
              }`}
            >
              {regReport.score_delta > 0 ? `+${regReport.score_delta.toFixed(1)}%` : `${regReport.score_delta.toFixed(1)}%`}
            </span>
            <span className="text-zinc-500 text-[10px]">from previous</span>
          </div>
        </div>

        {/* Current score card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Current Assessment
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-zinc-200">
              {regReport.current_score.toFixed(1)}%
            </span>
            <span className="text-zinc-500">({regReport.current_grade})</span>
          </div>
        </div>

        {/* Previous score card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Previous Baseline
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-zinc-450">
              {regReport.previous_score.toFixed(1)}%
            </span>
            <span className="text-zinc-550">({regReport.previous_grade})</span>
          </div>
        </div>
      </div>

      {/* Warning callout for high impact regressions */}
      {highImpactRegressions.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/35 rounded-xl p-4 flex items-start gap-3 text-red-400">
          <ShieldAlert className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-xs uppercase tracking-wide">High Impact Regressions Detected</h4>
            <p className="text-[11px] text-zinc-350 leading-relaxed">
              New vulnerability exposures or increased severity failures have been introduced relative to the baseline.
            </p>
          </div>
        </div>
      )}

      {/* Failure changes visual groupings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* NEW FAILURES */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-zinc-800 pb-2">
            <span className="font-bold text-red-400 uppercase">New Failure Modes</span>
            <span className="bg-red-500/10 border border-red-500/25 text-red-400 px-2 py-0.5 rounded text-[10px] font-bold">
              {categorizedFailures.new.length}
            </span>
          </div>
          {categorizedFailures.new.length > 0 ? (
            <div className="space-y-3">
              {categorizedFailures.new.map((f, i) => (
                <div key={i} className="bg-zinc-950 border border-zinc-850 p-4 rounded-lg space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-zinc-200">{f.title}</h4>
                    <span className="text-[10px] text-red-400 font-bold uppercase">{f.current_severity}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">{f.description}</p>
                  <div className="text-[10px] text-zinc-500 pt-1 flex gap-4">
                    <span>Tools: {f.current_tools.join(', ') || 'N/A'}</span>
                    <span>Surface: {f.attack_surfaces.join(', ') || 'N/A'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-550 py-4 text-center">No new failure modes introduced.</p>
          )}
        </div>

        {/* FIXED FAILURES */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-zinc-800 pb-2">
            <span className="font-bold text-emerald-400 uppercase">Fixed/Resolved Failures</span>
            <span className="bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-bold">
              {categorizedFailures.fixed.length}
            </span>
          </div>
          {categorizedFailures.fixed.length > 0 ? (
            <div className="space-y-3">
              {categorizedFailures.fixed.map((f, i) => (
                <div key={i} className="bg-zinc-950 border border-zinc-850 p-4 rounded-lg space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-zinc-200">{f.title}</h4>
                    <span className="text-[10px] text-emerald-400 font-bold uppercase">{f.previous_severity}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">{f.description}</p>
                  <div className="text-[10px] text-zinc-500 pt-1 flex gap-4">
                    <span>Tools: {f.previous_tools.join(', ') || 'N/A'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-550 py-4 text-center">No previously active failure modes resolved.</p>
          )}
        </div>
      </div>

      {/* Persistent & Severity changes lists */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PERSISTED FAILURES */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4 lg:col-span-2">
          <div className="flex justify-between items-center border-b border-zinc-800 pb-2">
            <span className="font-bold text-zinc-400 uppercase">Persistent Failure Modes (Unresolved)</span>
            <span className="bg-zinc-950 border border-zinc-800 text-zinc-450 px-2 py-0.5 rounded text-[10px] font-bold">
              {categorizedFailures.persisted.length}
            </span>
          </div>
          {categorizedFailures.persisted.length > 0 ? (
            <div className="space-y-3">
              {categorizedFailures.persisted.map((f, i) => (
                <div key={i} className="bg-zinc-950 border border-zinc-850 p-4 rounded-lg space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-zinc-250">{f.title}</h4>
                    <span className="text-[10px] text-zinc-500">Severity: {f.current_severity}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">{f.description}</p>
                  <div className="text-[10px] text-zinc-550 pt-1 flex gap-4">
                    <span>Category: {f.category}</span>
                    <span>Tools: {f.current_tools.join(', ')}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-550 py-4 text-center">No persistent failure modes found.</p>
          )}
        </div>

        {/* Severity changes / coverage details */}
        <div className="space-y-6">
          {/* Severity changes */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="border-b border-zinc-800 pb-2">
              <span className="font-bold text-zinc-200 uppercase">Severity Drift</span>
            </div>
            {categorizedFailures.severity_changes.length > 0 ? (
              <div className="space-y-2">
                {categorizedFailures.severity_changes.map((f, i) => (
                  <div key={i} className="bg-zinc-950 border border-zinc-850 p-3 rounded-lg flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-zinc-250">{f.title}</h4>
                      <p className="text-[9px] text-zinc-500 uppercase mt-0.5">Category: {f.category}</p>
                    </div>
                    <span className={`text-[10px] font-bold uppercase ${
                      f.change_type === 'severity_increased' ? 'text-red-400' : 'text-emerald-400'
                    }`}>
                      {f.change_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-550 text-center py-4">No changes in failure severity detected.</p>
            )}
          </div>

          {/* Attack Surface exposure changes */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="border-b border-zinc-800 pb-2">
              <span className="font-bold text-zinc-200 uppercase">Attack Surface Delta</span>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-[9px] text-zinc-500 font-bold uppercase block mb-1">Newly Exposed Surfaces</span>
                {regReport.new_attack_surfaces && regReport.new_attack_surfaces.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {regReport.new_attack_surfaces.map(s => (
                      <span key={s} className="bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] px-1.5 py-0.5 rounded">
                        {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-550 text-[10px]">None</p>
                )}
              </div>
              <div>
                <span className="text-[9px] text-zinc-500 font-bold uppercase block mb-1 font-mono">Resolved Surfaces</span>
                {regReport.resolved_attack_surfaces && regReport.resolved_attack_surfaces.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {regReport.resolved_attack_surfaces.map(s => (
                      <span key={s} className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded">
                        {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-550 text-[10px]">None</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
