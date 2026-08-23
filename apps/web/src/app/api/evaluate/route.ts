import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Call the FastAPI backend on port 8000
    const response = await fetch('http://localhost:8000/api/evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'FastAPI server error' }));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to execute evaluation' },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error: any) {
    return NextResponse.json(
      { error: `Backend connection error: ${error.message}. Is the FastAPI server running on port 8000?` },
      { status: 500 }
    );
  }
}
