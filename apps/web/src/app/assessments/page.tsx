'use client';

import React, { useState } from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import { useRouter } from 'next/navigation';
import { Search, ArrowUpDown, ChevronRight, Eye } from 'lucide-react';

type SortField = 'created_at' | 'score' | 'agent_id';
type SortOrder = 'asc' | 'desc';

export default function AssessmentsPage() {
  const { assessments } = useAssessment();
  const router = useRouter();

  const [search, setSearch] = useState('');
  const [gradeFilter, setGradeFilter] = useState('ALL');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Filter list
  const filtered = assessments
    .filter(a => {
      const matchSearch =
        a.assessment_id.toLowerCase().includes(search.toLowerCase()) ||
        a.agent_id.toLowerCase().includes(search.toLowerCase());
      const matchGrade = gradeFilter === 'ALL' || a.grade === gradeFilter;
      return matchSearch && matchGrade;
    })
    .sort((a, b) => {
      let multiplier = sortOrder === 'asc' ? 1 : -1;
      if (sortField === 'created_at') {
        return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * multiplier;
      }
      if (sortField === 'score') {
        return (a.score - b.score) * multiplier;
      }
      if (sortField === 'agent_id') {
        return a.agent_id.localeCompare(b.agent_id) * multiplier;
      }
      return 0;
    });

  // Extract unique grades for filters
  const uniqueGrades = Array.from(new Set(assessments.map(a => a.grade))).sort();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 font-mono">Assessment History</h1>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Review and audit historical reliability runs and benchmark scorecards.
          </p>
        </div>
      </div>

      {/* Filter and Search controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search by ID or Agent..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-emerald-500 focus:outline-none text-xs font-mono py-2.5 pl-10 pr-4 rounded-lg text-zinc-300 placeholder-zinc-500 transition"
          />
        </div>

        {/* Grade Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-zinc-500">Grade:</span>
          <select
            value={gradeFilter}
            onChange={(e) => setGradeFilter(e.target.value)}
            className="flex-1 bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-mono py-2 px-3 rounded-lg focus:outline-none transition"
          >
            <option value="ALL">ALL GRADES</option>
            {uniqueGrades.map(g => (
              <option key={g} value={g}>
                GRADE {g}
              </option>
            ))}
          </select>
        </div>

        {/* Counter */}
        <div className="flex items-center justify-end text-xs font-mono text-zinc-500 pr-2">
          Showing {filtered.length} of {assessments.length} assessments
        </div>
      </div>

      {/* Assessments Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-zinc-950 text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-500 border-b border-zinc-800">
                <th className="py-3 px-5">
                  <button
                    onClick={() => handleSort('agent_id')}
                    className="flex items-center gap-1.5 hover:text-zinc-300"
                  >
                    <span>Agent & ID</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="py-3 px-5">Version</th>
                <th className="py-3 px-5">
                  <button
                    onClick={() => handleSort('score')}
                    className="flex items-center gap-1.5 hover:text-zinc-300"
                  >
                    <span>Score</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="py-3 px-5">Grade</th>
                <th className="py-3 px-5">Regression Status</th>
                <th className="py-3 px-5">Scenarios</th>
                <th className="py-3 px-5">
                  <button
                    onClick={() => handleSort('created_at')}
                    className="flex items-center gap-1.5 hover:text-zinc-300"
                  >
                    <span>Created Date</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-xs font-mono">
              {filtered.length > 0 ? (
                filtered.map((item) => (
                  <tr
                    key={item.assessment_id}
                    onClick={() => router.push(`/assessments/${item.assessment_id}?assessmentId=${item.assessment_id}`)}
                    className="hover:bg-zinc-850 cursor-pointer transition text-zinc-300"
                  >
                    <td className="py-4 px-5">
                      <div className="font-semibold text-zinc-200">{item.agent_id}</div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">{item.assessment_id}</div>
                    </td>
                    <td className="py-4 px-5 text-zinc-400">v{item.agent_version}</td>
                    <td className="py-4 px-5">
                      <span className="font-bold text-zinc-100">{item.score.toFixed(1)}%</span>
                    </td>
                    <td className="py-4 px-5">
                      <span
                        className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          item.score >= 80
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : item.score >= 60
                            ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}
                      >
                        {item.grade}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      {item.regression_status ? (
                        <span
                          className={`px-2 py-0.5 rounded font-medium text-[10px] uppercase ${
                            item.regression_status === 'improved'
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : item.regression_status === 'regressed'
                              ? 'bg-red-500/10 text-red-400'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {item.regression_status}
                        </span>
                      ) : (
                        <span className="text-zinc-600 font-normal">None</span>
                      )}
                    </td>
                    <td className="py-4 px-5 text-zinc-400">{item.scenario_count} scenarios</td>
                    <td className="py-4 px-5 text-zinc-400">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-4 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => router.push(`/assessments/${item.assessment_id}?assessmentId=${item.assessment_id}`)}
                        className="inline-flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 px-2.5 py-1.5 rounded-lg border border-zinc-700 transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-500 font-mono">
                    No assessments match the current filters.
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
