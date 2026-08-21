'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useAssessment } from '../context/AssessmentContext';
import {
  ShieldAlert,
  History,
  AlertTriangle,
  FileText,
  Activity,
  GitBranch,
  Brain,
  Package,
  Loader2,
  Terminal,
  ChevronRight,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const assessmentId = searchParams.get('assessmentId');

  const {
    assessments,
    activeAssessment,
    loadingList,
    loadingDetail,
    error,
    selectedId,
    selectAssessment,
  } = useAssessment();

  // Helper to build links keeping the active assessmentId query param
  const buildLink = (path: string) => {
    return assessmentId ? `${path}?assessmentId=${assessmentId}` : path;
  };

  const menuItems = [
    { name: 'Overview', path: '/', icon: ShieldAlert },
    { name: 'Assessments', path: '/assessments', icon: History },
    { name: 'Findings', path: '/findings', icon: AlertTriangle },
    { name: 'Scenarios', path: '/scenarios', icon: FileText },
    { name: 'Traces', path: '/traces', icon: Activity },
    { name: 'Regression', path: '/regression', icon: GitBranch },
    { name: 'Adaptive Intelligence', path: '/adaptive', icon: Brain },
    { name: 'Artifacts', path: '/artifacts', icon: Package },
  ];

  // Breadcrumbs title based on route
  const getBreadcrumbTitle = () => {
    const item = menuItems.find(m => m.path === pathname);
    if (item) return item.name;
    if (pathname.startsWith('/assessments/')) return 'Assessment Detail';
    if (pathname.startsWith('/scenarios/')) return 'Scenario Detail';
    return 'Dashboard';
  };

  if (loadingList) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center text-zinc-400">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500 mb-4" />
        <p className="text-sm font-mono">Loading reliability dashboard shell...</p>
      </div>
    );
  }

  // Welcome state if no assessments exist
  if (assessments.length === 0) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-xl p-8 shadow-2xl">
          <div className="h-12 w-12 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-center text-emerald-400 mx-auto mb-6">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-zinc-100 mb-2">No Assessments Found</h1>
          <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
            Generate an assessment using the CLI tool in your repository to visualize the results here.
          </p>
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 text-left text-xs font-mono text-zinc-300 mb-6 space-y-2">
            <p className="text-zinc-500"># Run a fresh assessment</p>
            <p className="text-zinc-300 font-medium">python -m packages.cli.main assess --agent demo-customer-support</p>
            <p className="text-zinc-500 mt-4"># Run with a previous baseline comparison</p>
            <p className="text-zinc-300 font-medium">python -m packages.cli.main assess --agent demo-customer-support --previous &lt;ID&gt; --version 1.1.0</p>
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
            <Terminal className="h-4 w-4" />
            <span>AI Agent Reliability Engine v0.1.0</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col justify-between flex-shrink-0">
        <div>
          {/* Logo */}
          <div className="p-5 border-b border-zinc-800 flex items-center gap-3">
            <div className="h-8 w-8 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-center text-emerald-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-sm text-zinc-100 leading-tight">AI Agent Reliability</div>
              <div className="text-[10px] text-zinc-500 font-mono">RELIABILITY ENGINE</div>
            </div>
          </div>

          {/* Active assessment dropdown in sidebar */}
          <div className="p-4 border-b border-zinc-800 bg-zinc-950/50">
            <label className="block text-[10px] uppercase font-bold tracking-wider text-zinc-500 mb-1.5 font-mono">
              Active Assessment
            </label>
            <select
              value={selectedId || ''}
              onChange={(e) => selectAssessment(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs font-mono py-1.5 px-2.5 rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 transition"
            >
              {assessments.map(item => (
                <option key={item.assessment_id} value={item.assessment_id}>
                  {item.agent_id} ({item.grade} - {item.score.toFixed(1)}%)
                </option>
              ))}
            </select>
          </div>

          {/* Nav Links */}
          <nav className="p-3 space-y-1">
            {menuItems.map(item => {
              const active = pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={buildLink(item.path)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium font-mono transition ${
                    active
                      ? 'bg-zinc-800 text-zinc-100 border-l-2 border-emerald-500 pl-2.5'
                      : 'text-zinc-400 hover:bg-zinc-850 hover:text-zinc-200'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? 'text-emerald-400' : 'text-zinc-500'}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 text-[10px] text-zinc-500 font-mono text-center">
          <div>Read-Only Console</div>
          <div className="mt-1">v0.1.0 (Phase 6D)</div>
        </div>
      </aside>

      {/* Main Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-2">
            <span className="text-zinc-500 text-xs font-mono">Engine</span>
            <ChevronRight className="h-3 w-3 text-zinc-650" />
            <h1 className="text-sm font-semibold text-zinc-100 font-mono">{getBreadcrumbTitle()}</h1>
          </div>

          {/* Active assessment stats context */}
          {activeAssessment && (
            <div className="flex items-center gap-4 text-xs font-mono">
              <div className="hidden md:flex items-center gap-2 text-zinc-400">
                <span className="text-zinc-500">Agent:</span>
                <span className="text-zinc-300 font-medium">{activeAssessment.agent_id}</span>
                <span className="text-zinc-600">v{activeAssessment.agent_version}</span>
              </div>
              <div className="hidden lg:flex items-center gap-2 text-zinc-400">
                <span className="text-zinc-500">Run ID:</span>
                <span className="text-zinc-300 font-medium text-[11px] bg-zinc-800 px-1.5 py-0.5 rounded">
                  {activeAssessment.assessment_id.slice(0, 8)}...
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Verdict:</span>
                <span
                  className={`px-2.5 py-0.5 rounded font-bold text-xs ${
                    activeAssessment.reliability_assessment.score.overall_score >= 80
                      ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
                      : activeAssessment.reliability_assessment.score.overall_score >= 60
                      ? 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                      : 'bg-red-500/10 border border-red-500/30 text-red-400'
                  }`}
                >
                  {activeAssessment.reliability_assessment.score.grade} ({activeAssessment.reliability_assessment.score.overall_score.toFixed(1)}%)
                </span>
              </div>
            </div>
          )}
        </header>

        {/* Content panel */}
        <main className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-6 bg-red-500/10 border border-red-500/35 rounded-xl p-5 text-left max-w-4xl shadow-lg">
              <div className="flex items-center gap-3 text-red-400 font-semibold mb-2">
                <AlertTriangle className="h-5 w-5" />
                <span>Error Loading Assessment</span>
              </div>
              <p className="text-zinc-300 text-sm font-mono">{error}</p>
            </div>
          )}

          {loadingDetail ? (
            <div className="min-h-[400px] flex flex-col items-center justify-center text-zinc-400">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-500 mb-2" />
              <p className="text-xs font-mono">Loading assessment details...</p>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
