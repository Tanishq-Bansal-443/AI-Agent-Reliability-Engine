'use client';

import React, { useState } from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import {
  AlertTriangle,
  Search,
  CheckCircle,
  Eye,
  SlidersHorizontal,
  Lightbulb,
  Workflow,
  Sparkles,
} from 'lucide-react';
import { ReliabilityFinding } from '../../types';

export default function FindingsPage() {
  const { activeAssessment } = useAssessment();

  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [selectedFinding, setSelectedFinding] = useState<ReliabilityFinding | null>(null);

  if (!activeAssessment) return null;

  const findings = activeAssessment.reliability_assessment.findings;

  // Filter list
  const filtered = findings.filter(f => {
    const matchSearch =
      f.title.toLowerCase().includes(search.toLowerCase()) ||
      f.description.toLowerCase().includes(search.toLowerCase()) ||
      f.category.toLowerCase().includes(search.toLowerCase()) ||
      f.affected_tools.some(t => t.toLowerCase().includes(search.toLowerCase()));

    const matchSeverity = severityFilter === 'ALL' || f.severity?.toUpperCase() === severityFilter;
    const matchCategory = categoryFilter === 'ALL' || f.category.toUpperCase() === categoryFilter;

    return matchSearch && matchSeverity && matchCategory;
  });

  // Extract unique categories for filter
  const uniqueCategories = Array.from(new Set(findings.map(f => f.category.toUpperCase()))).sort();

  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-zinc-800 pb-4">
        <h1 className="text-xl font-bold text-zinc-100 font-mono">Findings Explorer</h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">
          Explore and audit structural vulnerabilities and policy violations detected under adversarial tests.
        </p>
      </div>

      {/* Toolbar filters */}
      <div className="flex-shrink-0 grid grid-cols-1 md:grid-cols-4 gap-4 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
        {/* Search */}
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search findings, descriptions, or tools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs font-mono py-2 pl-10 pr-4 rounded-lg text-zinc-300 transition"
          />
        </div>

        {/* Severity */}
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

        {/* Category */}
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-mono py-2 px-3 rounded-lg focus:outline-none transition"
        >
          <option value="ALL">ALL CATEGORIES</option>
          {uniqueCategories.map(c => (
            <option key={c} value={c}>
              {c.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      {/* Main split display */}
      <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
        {/* Left column: list of findings */}
        <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-zinc-950 z-10 border-b border-zinc-800">
                <tr className="text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-500">
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Title & Category</th>
                  <th className="py-3 px-4">Target Tool</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 text-xs font-mono">
                {filtered.length > 0 ? (
                  filtered.map((item, i) => {
                    const active = selectedFinding?.title === item.title;
                    return (
                      <tr
                        key={i}
                        onClick={() => setSelectedFinding(item)}
                        className={`cursor-pointer transition ${
                          active ? 'bg-zinc-800 text-zinc-100' : 'hover:bg-zinc-850 text-zinc-300'
                        }`}
                      >
                        <td className="py-3.5 px-4">
                          <span
                            className={`px-2 py-0.5 rounded font-bold text-[9px] uppercase ${
                              item.severity?.toLowerCase() === 'critical'
                                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                : item.severity?.toLowerCase() === 'high'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : item.severity?.toLowerCase() === 'medium'
                                ? 'bg-amber-500/10 text-yellow-500 border border-amber-500/20'
                                : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            }`}
                          >
                            {item.severity || 'medium'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-bold text-zinc-200">{item.priority}</td>
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-zinc-200">{item.title}</div>
                          <div className="text-[9px] text-zinc-500 mt-0.5 uppercase tracking-wider">{item.category}</div>
                        </td>
                        <td className="py-3.5 px-4">
                          {item.affected_tools.length > 0 ? (
                            <span className="bg-zinc-950 px-2 py-1 rounded text-[10px] text-zinc-400 border border-zinc-850">
                              {item.affected_tools.join(', ')}
                            </span>
                          ) : (
                            <span className="text-zinc-600">None</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            className="bg-zinc-950 hover:bg-zinc-800 border border-zinc-850 text-zinc-400 hover:text-zinc-200 p-1.5 rounded"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedFinding(item);
                            }}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-zinc-500 font-mono">
                      No findings found matching the criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right column: detailed view */}
        <div className="w-80 lg:w-96 bg-zinc-900 border border-zinc-800 rounded-xl overflow-y-auto p-5 font-mono flex flex-col justify-between flex-shrink-0">
          {selectedFinding ? (
            <div className="space-y-5">
              <div className="border-b border-zinc-800 pb-3 flex justify-between items-center">
                <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">
                  Finding Detail
                </span>
                <span className="text-xs text-zinc-400 font-bold">Priority {selectedFinding.priority}</span>
              </div>

              <div>
                <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wide">
                  {selectedFinding.title}
                </h3>
                <div className="text-[9px] text-zinc-500 uppercase mt-1">Category: {selectedFinding.category}</div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[9px] uppercase font-bold text-zinc-500 block">Vulnerability Summary</span>
                <p className="text-[11px] text-zinc-400 leading-relaxed bg-zinc-950 p-3 rounded-lg border border-zinc-850">
                  {selectedFinding.description}
                </p>
              </div>

              {/* Evidence */}
              {selectedFinding.evidence && selectedFinding.evidence.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[9px] uppercase font-bold text-zinc-500 block flex items-center gap-1.5">
                    <Workflow className="h-3 w-3" />
                    <span>Deduplicated Evidence</span>
                  </span>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {selectedFinding.evidence.map((ev, i) => (
                      <div key={i} className="bg-zinc-950 border border-zinc-900 p-2.5 rounded text-[10px] text-zinc-400 leading-relaxed">
                        {ev}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action plan / recommendations */}
              <div className="space-y-1.5">
                <span className="text-[9px] uppercase font-bold text-zinc-500 block flex items-center gap-1.5">
                  <Lightbulb className="h-3 w-3 text-emerald-400" />
                  <span>Recommendation</span>
                </span>
                <p className="text-[11px] text-zinc-400 leading-relaxed bg-zinc-950/40 border border-zinc-800 rounded-lg p-3">
                  {activeAssessment.reliability_assessment.recommendations?.[0] || 'Implement strict checks for tool boundaries.'}
                </p>
              </div>

              {/* Scenarios affected list */}
              {selectedFinding.affected_scenarios.length > 0 && (
                <div className="space-y-1.5 border-t border-zinc-800 pt-3">
                  <span className="text-[9px] uppercase font-bold text-zinc-500 block">Affected Scenarios</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedFinding.affected_scenarios.map(sc => (
                      <span key={sc} className="bg-zinc-950 text-[10px] text-zinc-400 px-2 py-0.5 rounded border border-zinc-900 break-all truncate max-w-full">
                        {sc.slice(0, 8)}...
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-zinc-500 py-12">
              <SlidersHorizontal className="h-8 w-8 text-zinc-700 mb-2" />
              <p className="text-xs">Select a finding from the list to explore evidence details.</p>
            </div>
          )}

          {selectedFinding && (
            <div className="mt-6 border-t border-zinc-800 pt-3 text-[9px] text-zinc-500 flex items-center gap-1.5 justify-between">
              <span>Severity: <strong className="text-zinc-400 uppercase">{selectedFinding.severity || 'Medium'}</strong></span>
              <span>Target: <strong className="text-zinc-400">{selectedFinding.affected_tools.join(', ') || 'N/A'}</strong></span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
