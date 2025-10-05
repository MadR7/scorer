import { Storage } from '@google-cloud/storage';
import type { VideoInfo, GCSAnnotation } from '@/types/gcs';

// Initialize GCS client with Application Default Credentials
const storage = new Storage({
  projectId: process.env.GCP_PROJECT_ID,
});

const BUCKET_NAME = process.env.GCS_BUCKET || 'buildai-dataset';
const VIDEO_PATH ='finetune_dataset';

// Helper to generate signed URL using IAM signBlob (works with ADC)
async function generateSignedUrl(file: any): Promise<string> {
  try {
    const [signedUrl] = await file.getSignedUrl({
      version: 'v4',
      action: 'read',
      expires: Date.now() + 60 * 60 * 1000, // 1 hour
    });
    return signedUrl;
  } catch (error) {
    // If signing fails (ADC without service account), fall back to public URL
    // This works if the bucket has public access or we're in dev mode
    console.warn('Failed to generate signed URL, using public URL:', error);
    return `https://storage.googleapis.com/${BUCKET_NAME}/${file.name}`;
  }
}

/**
 * List all videos from a GCS path
 */
export async function listVideos(gcsPath?: string): Promise<VideoInfo[]> {
  const path = gcsPath || VIDEO_PATH;
  const bucket = storage.bucket(BUCKET_NAME);
  
  // Ensure path ends with /
  const prefix = path.endsWith('/') ? path : `${path}/`;
  
  const [files] = await bucket.getFiles({ prefix });
  
  // Filter for video files only
  const videoExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];
  const videoFiles = files.filter(file => 
    videoExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
  );
  
  // Check for annotations
  const videoInfos: VideoInfo[] = await Promise.all(
    videoFiles.map(async (file) => {
      const videoName = file.name.split('/').pop() || file.name;
      const baseName = videoName.replace(/\.[^.]+$/, '');
      const annotationPath = `${prefix}${baseName}.jsonl`;
      
      // Check if annotation file exists
      const annotationFile = bucket.file(annotationPath);
      const [exists] = await annotationFile.exists();
      
      // Generate signed URL (1 hour expiry)
      const signedUrl = await generateSignedUrl(file);
      
      // Determine annotation status
      let annotationStatus: 'labeled' | 'in_progress' | 'not_started' = 'not_started';
      if (exists) {
        // Check if it has segments
        try {
          const [content] = await annotationFile.download();
          const annotation: GCSAnnotation = JSON.parse(content.toString());
          if (annotation.segments && annotation.segments.length > 0) {
            annotationStatus = 'labeled';
          } else {
            annotationStatus = 'in_progress';
          }
        } catch (e) {
          annotationStatus = 'in_progress';
        }
      }
      
      return {
        name: videoName,
        path: file.name,
        signedUrl,
        hasAnnotations: exists,
        annotationStatus,
      };
    })
  );
  
  // Sort numerically by extracting numbers from filenames
  return videoInfos.sort((a, b) => {
    const numA = parseInt(a.name.match(/\d+/)?.[0] || '0', 10);
    const numB = parseInt(b.name.match(/\d+/)?.[0] || '0', 10);
    return numA - numB;
  });
}

/**
 * Generate a new signed URL for a video
 */
export async function getSignedUrl(videoPath: string): Promise<string> {
  const bucket = storage.bucket(BUCKET_NAME);
  const file = bucket.file(videoPath);
  
  return await generateSignedUrl(file);
}

/**
 * Load annotations for a video
 */
export async function loadAnnotations(videoPath: string): Promise<GCSAnnotation | null> {
  const bucket = storage.bucket(BUCKET_NAME);
  
  // Get base name (without extension)
  const baseName = videoPath.replace(/\.[^.]+$/, '');
  const annotationPath = `${baseName}.jsonl`;
  
  const file = bucket.file(annotationPath);
  const [exists] = await file.exists();
  
  if (!exists) {
    return null;
  }
  
  try {
    const [content] = await file.download();
    const annotation: GCSAnnotation = JSON.parse(content.toString());
    return annotation;
  } catch (error) {
    console.error('Error loading annotations:', error);
    return null;
  }
}

/**
 * Save annotations for a video (atomic write)
 */
export async function saveAnnotations(
  videoPath: string,
  annotation: GCSAnnotation
): Promise<void> {
  const bucket = storage.bucket(BUCKET_NAME);
  
  // Get base name (without extension)
  const baseName = videoPath.replace(/\.[^.]+$/, '');
  const annotationPath = `${baseName}.jsonl`;
  
  const file = bucket.file(annotationPath);
  
  // Write to a temp file first, then rename (atomic)
  const tempPath = `${annotationPath}.tmp`;
  const tempFile = bucket.file(tempPath);
  
  try {
    // Write to temp file
    await tempFile.save(JSON.stringify(annotation, null, 2), {
      contentType: 'application/json',
      metadata: {
        cacheControl: 'no-cache',
      },
    });
    
    // Move temp file to final location (atomic)
    await tempFile.move(file);
  } catch (error) {
    // Clean up temp file if it exists
    try {
      await tempFile.delete();
    } catch (e) {
      // Ignore cleanup errors
    }
    throw error;
  }
}
