import { NextRequest, NextResponse } from 'next/server';
import { loadAnnotations, saveAnnotations } from '@/lib/gcs-client';
import type { GCSAnnotation } from '@/types/gcs';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const videoPath = searchParams.get('videoPath');
    
    if (!videoPath) {
      return NextResponse.json(
        { error: 'videoPath is required' },
        { status: 400 }
      );
    }
    
    const annotation = await loadAnnotations(videoPath);
    
    if (!annotation) {
      return NextResponse.json(
        { error: 'Annotations not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ annotation });
  } catch (error) {
    console.error('Error loading annotations:', error);
    return NextResponse.json(
      { error: 'Failed to load annotations', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const { videoPath, annotation } = await request.json();
    
    if (!videoPath || !annotation) {
      return NextResponse.json(
        { error: 'videoPath and annotation are required' },
        { status: 400 }
      );
    }
    
    // Validate annotation structure
    if (!annotation.segments || !Array.isArray(annotation.segments)) {
      return NextResponse.json(
        { error: 'Invalid annotation format: segments array is required' },
        { status: 400 }
      );
    }
    
    await saveAnnotations(videoPath, annotation as GCSAnnotation);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error saving annotations:', error);
    return NextResponse.json(
      { error: 'Failed to save annotations', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
