import { NextRequest, NextResponse } from 'next/server';
import { listVideos } from '@/lib/gcs-client';

export async function GET(request: NextRequest) {
  try {
    // Get optional GCS path from query params
    const searchParams = request.nextUrl.searchParams;
    const gcsPath = searchParams.get('path') || undefined;
    
    const videos = await listVideos(gcsPath);
    
    return NextResponse.json({ videos });
  } catch (error) {
    console.error('Error listing videos:', error);
    
    // Check for auth errors
    if (error instanceof Error && error.message.includes('Could not load the default credentials')) {
      return NextResponse.json(
        { 
          error: 'GCS authentication failed. Run: gcloud auth application-default login',
          details: error.message 
        },
        { status: 401 }
      );
    }
    
    return NextResponse.json(
      { error: 'Failed to list videos', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
