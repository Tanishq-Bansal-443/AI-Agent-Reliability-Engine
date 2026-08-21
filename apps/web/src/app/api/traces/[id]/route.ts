import { NextRequest, NextResponse } from 'next/server';
import { loadTrace } from '../../../lib/api';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const params = await props.params;
    const id = params.id;
    
    const trace = loadTrace(id);
    if (!trace) {
      return NextResponse.json({ error: 'Trace not found' }, { status: 404 });
    }
    return NextResponse.json(trace);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
