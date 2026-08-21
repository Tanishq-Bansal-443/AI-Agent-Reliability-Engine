'use client';

import React, { useState } from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import { useRouter } from 'next/navigation';
import { Search, Eye, Filter, ArrowRight } from 'lucide-react';

export default function ScenariosPage() {
  const { activeAssessment } = useAssessment();
  const router = useRouter();

  const [search, setSearch] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  if (!activeAssessment) return null;

  const results = activeAssessment.evaluation_result.scenario_results;

  // Filter list
  const filtered = results.filter(res => {
    const matchSearch =
      res.scenario_name.toLowerCase().includes(search.toLowerCase()) ||
      res.scenario_id.toLowerCase().includes(search.toLowerCase());
    const matchVerdict = verdictFilter === 'ALL' || res.verdict === verdictFilter;
    const matchSeverity = severityFilter === 'ALL' || res.severity?.toUpperCase() === severityFilter;

    return matchSearch && matchVerdict && matchSeverity;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 font-mono">Scenario Explorer</h1>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Browse and debug individual test scenarios and validator evaluation verdicts.
          </p>
        </div>
      </div>

      {/* Toolbar filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
        {/* Search */}
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search scenarios by name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs font-mono py-2 pl-10 pr-4 rounded-lg text-zinc-300 transition"
          />
        </div>

        {/* Verdict filter */}
        <select
          value={verdictFilter}
          onChange={(e) => setVerdictFilter(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-mono py-2 px-3 rounded-lg focus:outline-none transition"
        >
          <option value="ALL">ALL VERDICTS</option>
          <option value="PASS">PASS</option>
          <option value="FAIL">FAIL</option>
          <option value="INCONCLUSIVE">INCONCLUSIVE</option>
        </select>

        {/* Severity filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-mono py-2 px-3 rounded-lg focus:outline-none transition"
        >
          <option value="ALL">ALL SEVERITIES</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
      </div>

      {/* Scenarios Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-zinc-950 text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-500 border-b border-zinc-800">
                <th className="py-3 px-5">Scenario ID & Name</th>
                <th className="py-3 px-5">Verdict</th>
                <th className="py-3 px-5">Severity</th>
                <th className="py-3 px-5">Evaluation Status</th>
                <th className="py-3 px-5">Execution Status</th>
                <th className="py-3 px-5">Findings</th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-xs font-mono">
              {filtered.length > 0 ? (
                filtered.map((item) => (
                  <tr
                    key={item.scenario_id}
                    onClick={() => router.push(`/scenarios/${item.scenario_id}?assessmentId=${activeAssessment.assessment_id}`)}
                    className="hover:bg-zinc-850 cursor-pointer transition text-zinc-300"
                  >
                    <td className="py-4 px-5">
                      <div className="font-semibold text-zinc-200">{item.scenario_name || 'Generic Scenario'}</div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">{item.scenario_id}</div>
                    </td>
                    <td className="py-4 px-5">
                      <span
                        className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${
                          item.verdict === 'PASS'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : item.verdict === 'FAIL'
                            ? 'bg-red-500/10 text-red-400 border-red-500/20'
                            : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                        }`}
                      >
                        {item.verdict}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      <span className="text-zinc-400 uppercase">{item.severity}</span>
                    </td>
                    <td className="py-4 px-5 text-zinc-400">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                          item.evaluation_status === 'EVALUATED'
                            ? 'bg-zinc-950 text-zinc-400 border border-zinc-800'
                            : 'bg-red-500/10 text-red-400'
                        }`}
                      >
                        {item.evaluation_status}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      <span
                        className={`inline-flex items-center gap-1.5 text-[11px] ${
                          item.execution_status === 'success'
                            ? 'text-emerald-400'
                            : 'text-red-400 font-bold'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${item.execution_status === 'success' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        {item.execution_status}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      <span className="bg-zinc-950 border border-zinc-850 px-2 py-0.5 rounded text-[10px] font-bold text-zinc-400">
                        {item.findings.length} findings
                      </span>
                    </td>
                    <td className="py-4 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => router.push(`/scenarios/${item.scenario_id}?assessmentId=${activeAssessment.assessment_id}`)}
                        className="inline-flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 px-2.5 py-1.5 rounded-lg border border-zinc-700 transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-zinc-500 font-mono">
                    No scenarios matching the filter settings found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
