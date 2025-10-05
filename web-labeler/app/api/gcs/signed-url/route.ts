import { NextRequest, NextResponse } from 'next/server';
import { getSignedUrl } from '@/lib/gcs-client';

export async function POST(request: NextRequest) {
  try {
    const { videoPath } = await request.json();
    
    if (!videoPath) {
      return NextResponse.json(
        { error: 'videoPath is required' },
        { status: 400 }
      );
    }
    
    const signedUrl = await getSignedUrl(videoPath);
    
    return NextResponse.json({ signedUrl });
  } catch (error) {
    console.error('Error generating signed URL:', error);
    return NextResponse.json(
      { error: 'Failed to generate signed URL', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
