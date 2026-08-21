import { NextResponse } from 'next/server';
import { listAssessments } from '../../../lib/api';

export async function GET() {
  try {
    const assessments = listAssessments();
    const summary = assessments.map(art => {
      const score = art.reliability_assessment.score;
      return {
        assessment_id: art.assessment_id,
        agent_id: art.agent_id,
        agent_version: art.agent_version,
        score: score.overall_score,
        grade: score.grade,
        regression_status: art.regression_report?.status || null,
        scenario_count: score.scenario_count,
        created_at: art.created_at,
      };
    });
    return NextResponse.json(summary);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
