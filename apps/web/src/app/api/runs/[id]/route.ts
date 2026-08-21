import { NextRequest, NextResponse } from 'next/server';
import { loadExecutionRun } from '../../../lib/api';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const params = await props.params;
    const id = params.id;
    
    const run = loadExecutionRun(id);
    if (!run) {
      return NextResponse.json({ error: 'Execution run not found' }, { status: 404 });
    }
    return NextResponse.json(run);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
