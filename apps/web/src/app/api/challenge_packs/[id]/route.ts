import { NextRequest, NextResponse } from 'next/server';
import { loadChallengePack } from '../../../../lib/api';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const params = await props.params;
    const id = params.id;
    
    const pack = loadChallengePack(id);
    if (!pack) {
      return NextResponse.json({ error: 'Challenge pack not found' }, { status: 404 });
    }
    return NextResponse.json(pack);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
