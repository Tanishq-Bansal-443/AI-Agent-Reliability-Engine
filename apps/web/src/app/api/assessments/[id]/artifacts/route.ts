import { NextRequest, NextResponse } from 'next/server';
import { loadAssessment, checkAssessmentIntegrity, checkArtifactExistence } from '../../../../../lib/api';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const params = await props.params;
    const id = params.id;
    
    const assessment = loadAssessment(id);
    if (!assessment) {
      return NextResponse.json({ error: 'Assessment not found' }, { status: 404 });
    }

    // Verify integrity hash of assessment itself
    const integrity = checkAssessmentIntegrity(assessment);

    // Build the graph node elements
    const tree = {
      type: 'Assessment',
      id: assessment.assessment_id,
      exists: true,
      path: `/data/assessments/${assessment.assessment_id}.json`,
      integrity: integrity.valid ? 'valid' : 'invalid',
      children: [
        {
          type: 'Challenge Pack',
          id: assessment.challenge_pack_id,
          ...checkArtifactExistence('Challenge Pack', assessment.challenge_pack_id)
        },
        {
          type: 'Execution Run',
          id: assessment.execution_run_id,
          ...checkArtifactExistence('Execution Run', assessment.execution_run_id),
          children: (assessment.trace_ids || []).map((tId: string) => ({
            type: 'Trace',
            id: tId,
            ...checkArtifactExistence('Trace', tId)
          }))
        },
        {
          type: 'Evaluation',
          id: assessment.evaluation_result.run_id,
          ...checkArtifactExistence('Evaluation', assessment.evaluation_result.run_id)
        },
        {
          type: 'Reliability Assessment',
          id: assessment.reliability_assessment.run_id,
          ...checkArtifactExistence('Reliability Assessment', assessment.reliability_assessment.run_id)
        },
        {
          type: 'Regression Report',
          id: assessment.regression_report ? assessment.reliability_assessment.run_id : null,
          exists: assessment.regression_report ? checkArtifactExistence('Regression Report', assessment.reliability_assessment.run_id).exists : false,
          path: assessment.regression_report ? checkArtifactExistence('Regression Report', assessment.reliability_assessment.run_id).path : ''
        },
        {
          type: 'Adaptive Test Plan',
          id: assessment.adaptive_test_plan ? assessment.reliability_assessment.run_id : null,
          exists: assessment.adaptive_test_plan ? checkArtifactExistence('Adaptive Test Plan', assessment.reliability_assessment.run_id).exists : false,
          path: assessment.adaptive_test_plan ? checkArtifactExistence('Adaptive Test Plan', assessment.reliability_assessment.run_id).path : ''
        }
      ]
    };

    return NextResponse.json(tree);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
