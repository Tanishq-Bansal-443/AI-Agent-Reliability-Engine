'use client';

import React, { useEffect, useState } from 'react';
import { useAssessment } from '../context/AssessmentContext';
import {
  TrendingUp,
  AlertOctagon,
  ShieldCheck,
  Percent,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

export default function OverviewPage() {
  const { activeAssessment, assessments } = useAssessment();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!activeAssessment) return null;

  const score = activeAssessment.reliability_assessment.score;
  const evalResult = activeAssessment.evaluation_result;
  const findings = activeAssessment.reliability_assessment.findings;

  // Count findings by severity
  const severityCounts = {
    critical: score.critical_failures || score.critical_failure_count || 0,
    high: score.high_failures || 0,
    medium: score.medium_failures || 0,
    low: score.low_failures || 0,
  };

  // If high/medium/low failures are not directly populated in score, count from findings list
  if (
    severityCounts.critical === 0 &&
    severityCounts.high === 0 &&
    severityCounts.medium === 0 &&
    severityCounts.low === 0
  ) {
    findings.forEach((f) => {
      const sev = f.severity?.toLowerCase();
      if (sev === 'critical') severityCounts.critical++;
      else if (sev === 'high') severityCounts.high++;
      else if (sev === 'medium') severityCounts.medium++;
      else if (sev === 'low') severityCounts.low++;
    });
  }

  // Find the highest priority finding
  const sortedFindings = [...findings].sort((a, b) => b.priority - a.priority);
  const highestPriorityFinding = sortedFindings[0] || null;

  // Chart data: Severity Distribution
  const severityChartData = [
    { name: 'Critical', value: severityCounts.critical, color: '#ef4444' }, // red
    { name: 'High', value: severityCounts.high, color: '#f43f5e' }, // rose
    { name: 'Medium', value: severityCounts.medium, color: '#f59e0b' }, // amber
    { name: 'Low', value: severityCounts.low, color: '#3b82f6' }, // blue
  ];

  // Chart data: Coverage Metrics
  const totalStrategiesCount =
    (activeAssessment.reliability_assessment.covered_strategies?.length || 0) +
    (activeAssessment.reliability_assessment.uncovered_strategies?.length || 0);
  const strategyCoveragePct =
    totalStrategiesCount > 0
      ? ((activeAssessment.reliability_assessment.covered_strategies?.length || 0) /
          totalStrategiesCount) *
        100
      : 0;

  const totalSurfacesCount =
    (activeAssessment.reliability_assessment.covered_attack_surfaces?.length || 0) +
    (activeAssessment.reliability_assessment.uncovered_attack_surfaces?.length || 0);
  const surfaceCoveragePct =
    totalSurfacesCount > 0
      ? ((activeAssessment.reliability_assessment.covered_attack_surfaces?.length || 0) /
          totalSurfacesCount) *
        100
      : 0;

  const coverageChartData = [
    { name: 'Strategies', value: Math.round(strategyCoveragePct), color: '#10b981' },
    { name: 'Attack Surfaces', value: Math.round(surfaceCoveragePct), color: '#6366f1' },
    { name: 'Reliability Score', value: Math.round(score.overall_score), color: '#a855f7' },
  ];

  // Chart data: Assessment History
  const historyData = [...assessments]
    .reverse()
    .map((item) => ({
      name: item.assessment_id.slice(0, 6),
      score: item.score,
    }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Limited / Quality Alerts */}
      {score.metadata?.assessment_quality?.limited && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-center gap-3 text-amber-400 text-xs font-mono">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>
            <strong>LIMITED ASSESSMENT DETECTED:</strong> This run evaluates fewer scenarios than
            required for complete attack surface coverage. Score confidence is reduced.
          </span>
        </div>
      )}

      {/* Grid: 4 Core scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Score & Grade */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-mono">
              Reliability Score
            </span>
            <span
              className={`h-2 w-2 rounded-full ${
                score.overall_score >= 80 ? 'bg-emerald-400' : 'bg-red-400'
              }`}
            />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold text-zinc-100 font-mono">
              {score.overall_score.toFixed(1)}%
            </span>
            <span className="text-xl font-bold text-zinc-500">/ 100</span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-zinc-400">
            <ShieldCheck className="h-4.5 w-4.5 text-emerald-400" />
            <span>Grade Grade: <strong className="text-zinc-200">{score.grade}</strong></span>
          </div>
        </div>

        {/* Risk Profile */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-mono">
              Risk Profile
            </span>
            <AlertOctagon className="h-4.5 w-4.5 text-red-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold text-red-400 uppercase font-mono">
              {score.risk_level}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-zinc-400">
            <span className="text-zinc-500">Score Confidence:</span>
            <span className="text-zinc-200">{(score.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Scenario pass rate */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-mono">
              Scenario Verdicts
            </span>
            <CheckCircle2 className="h-4.5 w-4.5 text-zinc-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold text-zinc-100 font-mono">
              {evalResult.passed}
            </span>
            <span className="text-lg text-zinc-500">/ {evalResult.total_scenarios} Passed</span>
          </div>
          <div className="mt-3 flex items-center gap-3 text-[10px] font-mono text-zinc-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              {evalResult.passed}
            </span>
            <span className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-red-400" />
              {evalResult.failed}
            </span>
            <span className="flex items-center gap-1">
              <HelpCircle className="h-3 w-3 text-yellow-400" />
              {evalResult.inconclusive}
            </span>
          </div>
        </div>

        {/* Attack Surface Coverage */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest font-mono">
              Coverage Score
            </span>
            <Percent className="h-4.5 w-4.5 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold text-zinc-100 font-mono">
              {score.coverage_score ? score.coverage_score.toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-zinc-400">
            <span className="text-zinc-500">Execution Reliability:</span>
            <span className="text-zinc-200">
              {((score.metadata?.assessment_quality?.execution_reliability || 1.0) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Grid: Charts and Highest Priority Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left side: Charts */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 lg:col-span-2 space-y-6">
          <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3">
            Security Intelligence Charts
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* History Chart */}
            <div className="h-64 flex flex-col justify-between">
              <span className="text-xs font-mono text-zinc-500 mb-2 block">
                Reliability Score History
              </span>
              {mounted ? (
                <ResponsiveContainer width="100%" height="85%">
                  <BarChart data={historyData}>
                    <XAxis dataKey="name" stroke="#52525b" fontSize={10} className="font-mono" />
                    <YAxis stroke="#52525b" fontSize={10} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #27272a' }}
                      labelStyle={{ color: '#fafafa', fontFamily: 'monospace', fontSize: '11px' }}
                      itemStyle={{ color: '#10b981', fontFamily: 'monospace', fontSize: '11px' }}
                    />
                    <Bar dataKey="score" fill="#10b981">
                      {historyData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.score >= 80 ? '#10b981' : entry.score >= 60 ? '#f59e0b' : '#ef4444'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex-1 bg-zinc-950 rounded flex items-center justify-center text-xs font-mono text-zinc-650">
                  Loading Chart...
                </div>
              )}
            </div>

            {/* Coverage Pct Chart */}
            <div className="h-64 flex flex-col justify-between">
              <span className="text-xs font-mono text-zinc-500 mb-2 block">
                Core Coverage Indicators (%)
              </span>
              {mounted ? (
                <ResponsiveContainer width="100%" height="85%">
                  <BarChart data={coverageChartData} layout="vertical">
                    <XAxis type="number" stroke="#52525b" fontSize={10} domain={[0, 100]} />
                    <YAxis dataKey="name" type="category" stroke="#52525b" fontSize={10} width={90} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #27272a' }}
                      itemStyle={{ fontFamily: 'monospace', fontSize: '11px' }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {coverageChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex-1 bg-zinc-950 rounded flex items-center justify-center text-xs font-mono text-zinc-650">
                  Loading Chart...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right side: Top Priority Finding & Severity Breakdown */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3 mb-4">
              Vulnerability Highlights
            </h2>

            {/* Severity list */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              {severityChartData.map((item) => (
                <div key={item.name} className="bg-zinc-950 border border-zinc-800/80 rounded-lg p-3">
                  <div className="text-[10px] font-mono text-zinc-500 uppercase">{item.name}</div>
                  <div className="text-xl font-bold font-mono mt-1" style={{ color: item.color }}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>

            {/* Highest risk finding block */}
            {highestPriorityFinding ? (
              <div className="bg-zinc-950 border border-zinc-850 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] uppercase font-mono tracking-widest font-bold text-red-400 bg-red-400/5 px-2 py-0.5 rounded border border-red-500/20">
                    Highest Risk Finding
                  </span>
                  <span className="text-xs font-mono font-bold text-zinc-400">
                    Priority {highestPriorityFinding.priority}
                  </span>
                </div>
                <h3 className="text-xs font-bold text-zinc-200 font-mono mb-1.5 truncate">
                  {highestPriorityFinding.title}
                </h3>
                <p className="text-zinc-400 text-[11px] leading-relaxed line-clamp-3 mb-3">
                  {highestPriorityFinding.description}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
                  <span>Tool:</span>
                  <span className="text-zinc-300">
                    {highestPriorityFinding.affected_tools.join(', ') || 'N/A'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-zinc-800 rounded-lg p-6 text-center text-xs font-mono text-zinc-500">
                No active security findings
              </div>
            )}
          </div>

          <div className="text-[10px] text-zinc-500 font-mono mt-4 flex items-center justify-between">
            <span>Assessment: {activeAssessment.assessment_id.slice(0, 16)}</span>
            <span>Date: {new Date(activeAssessment.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      {/* Remediation & Recommendations */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-zinc-200 font-mono border-b border-zinc-800 pb-3 mb-4">
          Recommended Remediation Controls
        </h2>
        {activeAssessment.reliability_assessment.recommendations &&
        activeAssessment.reliability_assessment.recommendations.length > 0 ? (
          <div className="space-y-3">
            {activeAssessment.reliability_assessment.recommendations.map((rec, i) => (
              <div key={i} className="flex gap-3 bg-zinc-950 border border-zinc-850 rounded-lg p-4 items-start">
                <div className="h-6 w-6 rounded bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-xs font-bold font-mono flex-shrink-0">
                  {i + 1}
                </div>
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-zinc-300 font-mono">
                    Security Policy Control Action
                  </h4>
                  <p className="text-xs text-zinc-400 leading-relaxed font-mono">{rec}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-zinc-800 rounded-lg p-8 text-center text-xs font-mono text-zinc-500">
            No recommendations generated. Agent is within compliance targets.
          </div>
        )}
      </div>
    </div>
  );
}
