'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { ReliabilityAssessmentArtifact } from '../types';

interface AssessmentSummary {
  assessment_id: string;
  agent_id: string;
  agent_version: string;
  score: number;
  grade: string;
  regression_status: string | null;
  scenario_count: number;
  created_at: string;
}

interface AssessmentContextType {
  assessments: AssessmentSummary[];
  activeAssessment: ReliabilityAssessmentArtifact | null;
  loadingList: boolean;
  loadingDetail: boolean;
  error: string | null;
  selectedId: string | null;
  selectAssessment: (id: string) => void;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export function AssessmentProvider({ children }: { children: React.ReactNode }) {
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [activeAssessment, setActiveAssessment] = useState<ReliabilityAssessmentArtifact | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const selectedId = searchParams.get('assessmentId');

  // Load the list of assessments
  useEffect(() => {
    async function fetchList() {
      try {
        setLoadingList(true);
        const res = await fetch('/api/assessments');
        if (!res.ok) throw new Error('Failed to load assessments list');
        const data = await res.json();
        setAssessments(data);
        
        // If there is no assessmentId in the query parameters but assessments exist, redirect to the latest
        if (!searchParams.get('assessmentId') && data.length > 0) {
          const latestId = data[0].assessment_id;
          router.replace(`${pathname}?assessmentId=${latestId}`);
        }
      } catch (err: any) {
        setError(err.message || 'Unknown error');
      } finally {
        setLoadingList(false);
      }
    }
    fetchList();
  }, [pathname, searchParams, router]);

  // Load detail of the selected assessment
  useEffect(() => {
    if (!selectedId) {
      setActiveAssessment(null);
      return;
    }

    async function fetchDetail() {
      try {
        setLoadingDetail(true);
        setError(null);
        const res = await fetch(`/api/assessments/${selectedId}`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error(`Assessment '${selectedId}' not found`);
          }
          throw new Error('Failed to load assessment details');
        }
        const data = await res.json();
        setActiveAssessment(data);
      } catch (err: any) {
        setError(err.message || 'Unknown error loading details');
      } finally {
        setLoadingDetail(false);
      }
    }
    fetchDetail();
  }, [selectedId]);

  const selectAssessment = (id: string) => {
    router.push(`${pathname}?assessmentId=${id}`);
  };

  return (
    <AssessmentContext.Provider
      value={{
        assessments,
        activeAssessment,
        loadingList,
        loadingDetail,
        error,
        selectedId,
        selectAssessment,
      }}
    >
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment() {
  const context = useContext(AssessmentContext);
  if (context === undefined) {
    throw new Error('useAssessment must be used within an AssessmentProvider');
  }
  return context;
}
export type { AssessmentSummary };
