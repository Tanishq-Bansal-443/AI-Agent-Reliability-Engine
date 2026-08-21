import { NextRequest, NextResponse } from 'next/server';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';
import { getWorkspacePath } from '../../../lib/api';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const pathParam = searchParams.get('path');
    if (!pathParam) {
      return NextResponse.json({ error: 'Path parameter is required' }, { status: 400 });
    }

    // Direct path boundary checks
    const cleanPath = pathParam.replace(/^\/+/, ''); // remove leading slashes
    if (!cleanPath.startsWith('data/') && !cleanPath.startsWith('traces/')) {
      return NextResponse.json({ error: 'Access denied: confined to data/ and traces/ directories' }, { status: 403 });
    }

    if (cleanPath.includes('..') || cleanPath.includes('\\')) {
      return NextResponse.json({ error: 'Access denied: path traversal attempt blocked' }, { status: 403 });
    }

    const fullPath = join(getWorkspacePath(''), cleanPath);
    if (!existsSync(fullPath)) {
      return NextResponse.json({ error: 'Artifact file not found' }, { status: 404 });
    }

    const raw = readFileSync(fullPath, 'utf-8');
    return NextResponse.json(JSON.parse(raw));
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
