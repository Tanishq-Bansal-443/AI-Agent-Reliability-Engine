import { NextRequest, NextResponse } from 'next/server';
import { loadAssessment } from '../../../lib/api';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    // Resolve params which can be a Promise in Next.js 15/16
    const params = await props.params;
    const id = params.id;
    
    const assessment = loadAssessment(id);
    if (!assessment) {
      return NextResponse.json({ error: 'Assessment not found' }, { status: 404 });
    }
    return NextResponse.json(assessment);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
