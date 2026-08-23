import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  console.log('[Next.js API] Received request on /api/evaluate');
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000); // 120s timeout

  try {
    const body = await request.json();
    console.log('[Next.js API] Forwarding request to FastAPI:', JSON.stringify(body));

    // Call the FastAPI backend on port 8000 using 127.0.0.1 explicitly
    const response = await fetch('http://127.0.0.1:8000/api/evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    console.log('[Next.js API] Received response from FastAPI with status:', response.status);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'FastAPI server error' }));
      console.error('[Next.js API] FastAPI returned error:', errorData);
      return NextResponse.json(
        { error: errorData.detail || 'Failed to execute evaluation' },
        { status: response.status }
      );
    }

    const result = await response.json();
    console.log('[Next.js API] Successfully received evaluation result from FastAPI');
    return NextResponse.json(result);
  } catch (error: any) {
    clearTimeout(timeoutId);
    console.error('[Next.js API] Error occurred during evaluation forward:', error);
    if (error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Evaluation request timed out. The reliability engine took longer than 120 seconds.' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: `Backend connection error: ${error.message}. Is the FastAPI server running on port 8000?` },
      { status: 500 }
    );
  }
}

