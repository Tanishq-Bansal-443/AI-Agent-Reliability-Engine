'use client';

import React, { useEffect, useState } from 'react';
import { useAssessment } from '../../context/AssessmentContext';
import {
  Package,
  FileCode,
  CheckCircle,
  XCircle,
  ChevronRight,
  ChevronDown,
  Loader2,
  Copy,
  Check,
  AlertTriangle,
} from 'lucide-react';

interface ArtifactNode {
  type: string;
  id: string | null;
  exists: boolean;
  path: string;
  integrity?: string;
  children?: ArtifactNode[];
}

export default function ArtifactsPage() {
  const { activeAssessment } = useAssessment();
  const [treeData, setTreeData] = useState<ArtifactNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedNode, setSelectedNode] = useState<ArtifactNode | null>(null);
  const [rawJson, setRawJson] = useState<any>(null);
  const [loadingRaw, setLoadingRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  // Load the artifacts tree structure for the active assessment
  useEffect(() => {
    if (!activeAssessment) return;
    async function fetchTree() {
      try {
        setLoading(true);
        setError(null);
        setTreeData(null);
        setSelectedNode(null);
        setRawJson(null);
        
        const res = await fetch(`/api/assessments/${activeAssessment.assessment_id}/artifacts`);
        if (!res.ok) throw new Error('Failed to load artifacts graph');
        const data = await res.json();
        setTreeData(data);
        
        // Select the root assessment node by default
        setSelectedNode(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchTree();
  }, [activeAssessment]);

  // Load raw JSON contents when selectedNode changes
  useEffect(() => {
    if (!selectedNode || !selectedNode.exists || !selectedNode.path) {
      setRawJson(null);
      return;
    }

    async function fetchRawJson() {
      try {
        setLoadingRaw(true);
        setRawJson(null);
        const res = await fetch(`/api/raw-artifact?path=${encodeURIComponent(selectedNode.path)}`);
        if (!res.ok) throw new Error('Failed to fetch raw JSON content');
        const data = await res.json();
        setRawJson(data);
      } catch (err: any) {
        console.error(err);
      } finally {
        setLoadingRaw(false);
      }
    }
    fetchRawJson();
  }, [selectedNode]);

  if (!activeAssessment) return null;

  const handleCopy = () => {
    if (!rawJson) return;
    navigator.clipboard.writeText(JSON.stringify(rawJson, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Tree Node Renderer Component
  const TreeNode = ({ node, depth = 0 }: { node: ArtifactNode; depth: number }) => {
    const isSelected = selectedNode?.path === node.path;
    const hasChildren = node.children && node.children.length > 0;
    
    return (
      <div className="font-mono text-xs">
        <div
          onClick={() => node.exists && setSelectedNode(node)}
          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition select-none group ${
            isSelected
              ? 'bg-zinc-800 text-zinc-100'
              : node.exists
              ? 'hover:bg-zinc-850 text-zinc-350'
              : 'text-zinc-600 cursor-not-allowed opacity-50'
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          <div className="flex items-center gap-2 truncate max-w-xs md:max-w-md">
            <FileCode className={`h-4 w-4 flex-shrink-0 ${node.exists ? 'text-indigo-400' : 'text-zinc-650'}`} />
            <span className="font-bold">{node.type}</span>
            {node.id ? (
              <span className="text-[10px] text-zinc-500 font-mono truncate">
                ({node.id.slice(0, 8)}...)
              </span>
            ) : (
              <span className="text-[10px] text-zinc-600 italic">(not generated)</span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {node.integrity && (
              <span className={`text-[9px] uppercase px-1.5 py-0.2 rounded border font-semibold ${
                node.integrity === 'valid'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/10 border-red-500/20 text-red-400'
              }`}>
                {node.integrity === 'valid' ? 'Checksum Valid' : 'Checksum Invalid'}
              </span>
            )}
            
            <span
              className={`px-1.5 py-0.2 rounded text-[8px] font-bold uppercase border ${
                node.exists
                  ? 'bg-zinc-950 text-emerald-400 border-emerald-500/10'
                  : 'bg-zinc-950 text-zinc-600 border-zinc-900'
              }`}
            >
              {node.exists ? 'Exists' : 'Missing'}
            </span>
          </div>
        </div>

        {hasChildren && (
          <div className="mt-1 space-y-1">
            {node.children!.map((child, i) => (
              <TreeNode key={i} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-zinc-800 pb-4">
        <h1 className="text-xl font-bold text-zinc-100 font-mono">Artifact Explorer</h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">
          Trace and verify the complete engine output hierarchy, hashes, and integrity checkers.
        </p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
        {/* Left: Artifact tree */}
        <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-y-auto p-4 space-y-4">
          <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest block font-mono border-b border-zinc-800 pb-2 mb-2">
            Artifact Dependency Graph
          </span>

          {loading ? (
            <div className="flex flex-col items-center justify-center text-zinc-500 py-12">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-500 mb-2" />
              <span>Scanning directories...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-400 py-6">
              <AlertTriangle className="h-5 w-5" />
              <span>Error loading graph: {error}</span>
            </div>
          ) : treeData ? (
            <div className="space-y-1">
              <TreeNode node={treeData} depth={0} />
            </div>
          ) : null}
        </div>

        {/* Right: JSON contents viewer */}
        <div className="w-96 lg:w-[480px] bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col flex-shrink-0">
          <div className="p-4 bg-zinc-950 border-b border-zinc-850 flex justify-between items-center flex-shrink-0 font-mono text-[10px] uppercase font-bold tracking-wider text-zinc-500">
            <span>JSON Inspector</span>
            {rawJson && (
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 transition"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            )}
          </div>

          <div className="flex-1 overflow-auto bg-zinc-950/20 p-4 font-mono text-[11px]">
            {loadingRaw ? (
              <div className="h-full flex items-center justify-center text-zinc-500">
                <Loader2 className="h-5 w-5 animate-spin text-emerald-500 mr-2" />
                <span>Loading payload file...</span>
              </div>
            ) : rawJson ? (
              <pre className="text-zinc-300 overflow-x-auto whitespace-pre-wrap leading-relaxed select-text">
                {JSON.stringify(rawJson, null, 2)}
              </pre>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-650 p-6">
                <Package className="h-8 w-8 text-zinc-800 mb-2" />
                <span>Select a file from the dependency graph to inspect raw JSON data structures.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
