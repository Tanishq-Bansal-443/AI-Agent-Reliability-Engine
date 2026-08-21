'use client';

import React from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import {
  Brain,
  Sliders,
  AlertTriangle,
  Lightbulb,
  CheckCircle,
  Clock,
  ExternalLink,
} from 'lucide-react';

export default function AdaptivePage() {
  const { activeAssessment } = useAssessment();

  if (!activeAssessment) return null;

  const plan = activeAssessment.adaptive_test_plan;

  if (!plan) {
    return (
      <div className="max-w-4xl mx-auto my-12 space-y-6 font-mono">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center space-y-4 shadow-xl">
          <div className="h-12 w-12 bg-purple-500/10 border border-purple-500/30 rounded-lg flex items-center justify-center text-purple-400 mx-auto mb-2">
            <Brain className="h-6 w-6" />
          </div>
          <h2 className="text-md font-bold text-zinc-200">No Adaptive Plan Found</h2>
          <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
            This assessment run did not trigger the adaptive planner. Ensure adaptive test planning is enabled in your engine configuration parameter.
          </p>
        </div>
      </div>
    );
  }

  // Calculate allocated vs total budget
  const allocatedScenarios = plan.strategy_priorities.reduce(
    (acc, sp) => acc + sp.recommended_scenario_count,
    0
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono text-xs">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-xl font-bold text-zinc-100 uppercase tracking-wide">Adaptive Intelligence</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Dynamic adversarial test suite generation and automated scenario allocation based on historical risk vectors.
        </p>
      </div>

      {/* Overview stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Scenario Budget
          </div>
          <div className="text-2xl font-extrabold text-indigo-400">
            {plan.budget} Scenarios
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Selected Strategies
          </div>
          <div className="text-2xl font-extrabold text-purple-400">
            {plan.selected_strategies?.length || 0} / 11
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Coverage Gaps
          </div>
          <div className="text-2xl font-extrabold text-red-400">
            {plan.coverage_gaps?.length || 0} Gaps
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-2">
            Allocated Count
          </div>
          <div className="text-2xl font-extrabold text-zinc-200">
            {allocatedScenarios} Scenarios
          </div>
        </div>
      </div>

      {/* Reasoning Summary Panel */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-2">
        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block">
          Adaptive Planner Reasoning
        </span>
        <p className="text-zinc-300 text-[11px] leading-relaxed">
          {plan.reasoning_summary}
        </p>
      </div>

      {/* Main Grid: Priorities vs Gaps */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left (col-span-2): Strategy Priorities Table */}
        <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="border-b border-zinc-800 pb-2 flex justify-between items-center">
            <span className="font-bold text-zinc-200 uppercase">Visual Priority Ranking</span>
            <span className="text-[10px] text-zinc-500">Sorted by Priority Score</span>
          </div>

          <div className="space-y-4">
            {plan.strategy_priorities && plan.strategy_priorities.length > 0 ? (
              [...plan.strategy_priorities]
                .sort((a, b) => b.priority_score - a.priority_score)
                .map((sp, idx) => {
                  const barPct = Math.min(100, Math.max(5, sp.priority_score));
                  return (
                    <div key={idx} className="bg-zinc-950 border border-zinc-850 p-4 rounded-lg space-y-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-bold text-zinc-200 text-xs uppercase tracking-wide">
                            {sp.strategy_id.replace(/_/g, ' ')}
                          </h4>
                          <span className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border inline-block mt-1 ${
                            sp.risk_level === 'critical'
                              ? 'bg-red-500/10 border-red-500/25 text-red-400'
                              : sp.risk_level === 'high'
                              ? 'bg-rose-500/10 border-rose-500/25 text-rose-400'
                              : sp.risk_level === 'medium'
                              ? 'bg-amber-500/10 border-amber-500/25 text-yellow-500'
                              : 'bg-zinc-800 border-zinc-700 text-zinc-400'
                          }`}>
                            {sp.risk_level} risk
                          </span>
                        </div>

                        <div className="text-right">
                          <div className="text-[10px] text-zinc-500 font-bold uppercase">Priority</div>
                          <div className="text-sm font-extrabold text-indigo-400 mt-0.5">{sp.priority_score.toFixed(0)}</div>
                        </div>
                      </div>

                      {/* Visual progress bar */}
                      <div className="w-full bg-zinc-900 h-2 rounded-full overflow-hidden border border-zinc-850">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                          style={{ width: `${barPct}%` }}
                        />
                      </div>

                      <p className="text-[11px] text-zinc-450 leading-relaxed pt-1">{sp.reason}</p>

                      {/* Evidence citation */}
                      {sp.evidence && sp.evidence.length > 0 && (
                        <div className="bg-zinc-900 border border-zinc-850 p-2.5 rounded text-[10px] text-zinc-550 italic">
                          Evidence: {sp.evidence.join(' | ')}
                        </div>
                      )}

                      <div className="flex justify-between text-[10px] text-zinc-500 border-t border-zinc-900 pt-2.5">
                        <span>Budget Allocation:</span>
                        <span className="text-zinc-300 font-bold">{sp.recommended_scenario_count} scenarios</span>
                      </div>
                    </div>
                  );
                })
            ) : (
              <p className="text-zinc-550 py-4 text-center">No strategy priorities cataloged.</p>
            )}
          </div>
        </div>

        {/* Right side: Gaps list */}
        <div className="space-y-6">
          {/* Coverage Gaps */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="border-b border-zinc-800 pb-2">
              <span className="font-bold text-zinc-200 uppercase">Coverage Gaps Detected</span>
            </div>
            {plan.coverage_gaps && plan.coverage_gaps.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {plan.coverage_gaps.map((gap, i) => (
                  <div key={i} className="bg-zinc-950 border border-zinc-850 p-3 rounded-lg flex items-start gap-2.5">
                    <AlertTriangle className="h-4.5 w-4.5 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-zinc-300 capitalize">{gap.split(':').slice(-1)[0].replace(/_/g, ' ')}</div>
                      <div className="text-[9px] text-zinc-550 uppercase mt-0.5">{gap.split(':')[0].replace(/_/g, ' ')}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-emerald-500/5 border border-emerald-500/10 text-emerald-400 p-3 rounded-lg text-center font-bold">
                Zero Gaps — Full Coverage
              </div>
            )}
          </div>

          {/* Actionable recommendations */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="border-b border-zinc-800 pb-2">
              <span className="font-bold text-zinc-200 uppercase">Actionable Recommendations</span>
            </div>
            {plan.recommendations && plan.recommendations.length > 0 ? (
              <div className="space-y-3">
                {plan.recommendations.map((rec, i) => (
                  <div key={i} className="bg-zinc-950 border border-zinc-850 p-3.5 rounded-lg space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Priority {rec.priority}</span>
                      {rec.target_tool && (
                        <span className="text-[9px] text-zinc-400 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                          {rec.target_tool}
                        </span>
                      )}
                    </div>
                    <h4 className="font-bold text-zinc-200 leading-snug">{rec.title}</h4>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">{rec.description}</p>
                    
                    <div className="bg-zinc-900/60 p-2.5 rounded border border-zinc-850 mt-1 space-y-1">
                      <span className="text-[9px] text-zinc-500 font-bold uppercase flex items-center gap-1.5">
                        <Lightbulb className="h-3.5 w-3.5 text-indigo-400" />
                        <span>Recommended action:</span>
                      </span>
                      <p className="text-[10px] text-zinc-350 leading-relaxed font-mono">{rec.recommended_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-550 text-center py-4">No planning recommendations available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
