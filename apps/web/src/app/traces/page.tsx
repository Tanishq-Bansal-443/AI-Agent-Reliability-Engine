'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAssessment } from '../../context/AssessmentContext';
import {
  Activity,
  User,
  Cpu,
  Wrench,
  FileCode,
  AlertTriangle,
  Play,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Eye,
  Sliders,
} from 'lucide-react';
import { Trace, TraceEvent } from '../../types';

function TracesContent() {
  const searchParams = useSearchParams();
  const traceIdParam = searchParams.get('traceId');

  const { activeAssessment } = useAssessment();
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [traceData, setTraceData] = useState<Trace | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Record<number, boolean>>({});

  // Sync selected trace ID from query param or fallback to first trace
  useEffect(() => {
    if (activeAssessment && activeAssessment.trace_ids.length > 0) {
      if (traceIdParam && activeAssessment.trace_ids.includes(traceIdParam)) {
        setSelectedTraceId(traceIdParam);
      } else {
        setSelectedTraceId(activeAssessment.trace_ids[0]);
      }
    } else {
      setSelectedTraceId(null);
    }
  }, [activeAssessment, traceIdParam]);

  // Load selected trace details
  useEffect(() => {
    if (!selectedTraceId) {
      setTraceData(null);
      return;
    }

    async function fetchTrace() {
      try {
        setLoadingTrace(true);
        setError(null);
        setExpandedEvents({});
        const res = await fetch(`/api/traces/${selectedTraceId}`);
        if (!res.ok) throw new Error('Failed to load trace events');
        const data = await res.json();
        setTraceData(data);

        // Expand first turn and tool calls by default
        const initialExpanded: Record<number, boolean> = {};
        data.events.forEach((ev: TraceEvent) => {
          if (ev.step_index === 0 || ev.type === 'tool_call' || ev.type === 'error') {
            initialExpanded[ev.step_index] = true;
          }
        });
        setExpandedEvents(initialExpanded);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoadingTrace(false);
      }
    }
    fetchTrace();
  }, [selectedTraceId]);

  if (!activeAssessment) return null;

  const toggleEventExpand = (idx: number) => {
    setExpandedEvents(prev => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Helper to resolve scenario result details for left listing
  const getScenarioDetailForTrace = (tId: string) => {
    const res = activeAssessment.evaluation_result.scenario_results.find(
      r => r.trace_id === tId
    );
    return res
      ? { name: res.scenario_name, verdict: res.verdict, severity: res.severity }
      : { name: 'Generic Trace', verdict: 'INCONCLUSIVE', severity: 'medium' };
  };

  // Helper: Event Icon resolver
  const getEventIcon = (type: string) => {
    switch (type) {
      case 'user_input':
        return <User className="h-4.5 w-4.5 text-indigo-400" />;
      case 'model_call':
        return <Sliders className="h-4.5 w-4.5 text-zinc-500" />;
      case 'model_output':
        return <Cpu className="h-4.5 w-4.5 text-purple-400" />;
      case 'tool_call':
        return <Wrench className="h-4.5 w-4.5 text-amber-400" />;
      case 'tool_result':
        return <FileCode className="h-4.5 w-4.5 text-emerald-400" />;
      case 'environment_change':
        return <Play className="h-4.5 w-4.5 text-blue-400" />;
      case 'final_response':
        return <Cpu className="h-4.5 w-4.5 text-emerald-400 font-bold" />;
      case 'error':
        return <AlertTriangle className="h-4.5 w-4.5 text-red-400" />;
      default:
        return <Activity className="h-4.5 w-4.5 text-zinc-400" />;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-zinc-800 pb-4">
        <h1 className="text-xl font-bold text-zinc-100 font-mono">Trace Timeline Explorer</h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">
          Chronological step-by-step telemetry of tool execution and prompt interactions.
        </p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
        {/* Left side: Trace Nodes List */}
        <div className="w-80 bg-zinc-900 border border-zinc-800 rounded-xl overflow-y-auto p-4 space-y-3 flex-shrink-0">
          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest block font-mono border-b border-zinc-800 pb-2 mb-2">
            Traces ({activeAssessment.trace_ids.length})
          </span>
          <div className="space-y-2">
            {activeAssessment.trace_ids.map(tId => {
              const sc = getScenarioDetailForTrace(tId);
              const active = selectedTraceId === tId;
              return (
                <div
                  key={tId}
                  onClick={() => setSelectedTraceId(tId)}
                  className={`p-3 rounded-lg border font-mono text-left cursor-pointer transition ${
                    active
                      ? 'bg-zinc-800 border-zinc-700 text-zinc-100'
                      : 'bg-zinc-950 border-zinc-900 text-zinc-400 hover:border-zinc-800 hover:text-zinc-200'
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-[10px] font-bold text-zinc-500 truncate max-w-[120px]">
                      {tId.slice(0, 8)}...
                    </span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[8px] font-bold uppercase border ${
                        sc.verdict === 'PASS'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : sc.verdict === 'FAIL'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}
                    >
                      {sc.verdict}
                    </span>
                  </div>
                  <h4 className="text-[11px] font-semibold text-zinc-300 mt-2 line-clamp-2 leading-tight">
                    {sc.name}
                  </h4>
                  <div className="text-[9px] text-zinc-550 uppercase mt-1.5">Severity: {sc.severity}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right side: Chronological timeline */}
        <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col">
          {loadingTrace ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 font-mono text-xs">
              <div className="h-6 w-6 animate-spin border-2 border-emerald-500 border-t-transparent rounded-full mb-2" />
              <span>Fetching trace timeline JSON...</span>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-center text-red-400 font-mono text-xs p-6">
              <AlertTriangle className="h-5 w-5 mr-2" />
              <span>Error fetching trace data: {error}</span>
            </div>
          ) : traceData ? (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Trace meta status header */}
              <div className="p-4 bg-zinc-950 border-b border-zinc-800 flex justify-between items-center flex-shrink-0 font-mono text-[11px]">
                <div className="flex items-center gap-3">
                  <span className="text-zinc-500">Scenario Name:</span>
                  <span className="text-zinc-300 font-semibold">{traceData.scenario_name}</span>
                </div>
                <div className="flex items-center gap-4 text-zinc-400">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5 text-zinc-500" />
                    <span>Run: {traceData.events.length} Steps</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-zinc-500">Status:</span>
                    <span
                      className={`font-bold capitalize ${
                        traceData.status === 'success' ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {traceData.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Scrollable event lists */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-zinc-950/20 font-mono">
                {traceData.events.map((event) => {
                  const expanded = !!expandedEvents[event.step_index];
                  
                  // Helper text based on event type
                  const getEventSnippet = (ev: TraceEvent) => {
                    if (ev.type === 'user_input') return ev.input_data.message;
                    if (ev.type === 'final_response') return ev.output_data.response;
                    if (ev.type === 'tool_call') return `Calls tool '${ev.input_data.name || ev.input_data.tool}'`;
                    if (ev.type === 'tool_result') return `Result: ${ev.output_data.success ? 'Success' : 'Error/Refusal'}`;
                    if (ev.type === 'model_output') return ev.output_data.thought || ev.output_data.content;
                    if (ev.type === 'error') return ev.output_data.error || 'Execution timeout or exception';
                    return '';
                  };

                  return (
                    <div key={event.step_index} className="relative flex gap-4 text-left">
                      {/* Timeline vertical bar connector */}
                      <div className="absolute left-[13px] top-[26px] bottom-[-28px] w-[1px] bg-zinc-800 last:hidden" />

                      {/* Icon point */}
                      <div className="h-7 w-7 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center flex-shrink-0 z-10">
                        {getEventIcon(event.type)}
                      </div>

                      {/* Content box */}
                      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-sm hover:border-zinc-700 transition">
                        {/* Box summary bar */}
                        <div
                          onClick={() => toggleEventExpand(event.step_index)}
                          className="p-3.5 flex justify-between items-center cursor-pointer select-none bg-zinc-900/60"
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wide">
                                Step #{event.step_index}
                              </span>
                              <span className="text-[10px] text-zinc-400 font-bold uppercase">
                                {event.type.replace(/_/g, ' ')}
                              </span>
                              {event.duration_ms > 0 && (
                                <span className="text-[9px] text-zinc-650">
                                  ({event.duration_ms}ms)
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-zinc-300 font-medium truncate max-w-lg md:max-w-2xl">
                              {getEventSnippet(event)}
                            </p>
                          </div>

                          <div className="text-zinc-500 hover:text-zinc-300 transition">
                            {expanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </div>
                        </div>

                        {/* Collapsible payloads */}
                        {expanded && (
                          <div className="p-4 border-t border-zinc-800 bg-zinc-950/60 text-[11px] text-zinc-400 space-y-4">
                            {/* Inputs payload */}
                            {Object.keys(event.input_data).length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Input Payload:</span>
                                <pre className="bg-zinc-950 border border-zinc-900 p-2.5 rounded-lg text-[10px] text-zinc-300 overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(event.input_data, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Outputs payload */}
                            {Object.keys(event.output_data).length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Output Payload:</span>
                                <pre className="bg-zinc-950 border border-zinc-900 p-2.5 rounded-lg text-[10px] text-zinc-300 overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(event.output_data, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Metadata */}
                            {Object.keys(event.metadata).length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Provenance & Metadata:</span>
                                <pre className="bg-zinc-950 border border-zinc-900 p-2.5 rounded-lg text-[10px] text-zinc-350 overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(event.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-zinc-500 py-12">
              <Activity className="h-8 w-8 text-zinc-700 mb-2 animate-pulse" />
              <p className="text-xs font-mono">Select a trace from the left panel to load execution timeline.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TracesPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-xs font-mono text-zinc-500">Loading traces...</div>}>
      <TracesContent />
    </React.Suspense>
  );
}
