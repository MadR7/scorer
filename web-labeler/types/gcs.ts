export interface VideoInfo {
  name: string;
  path: string;
  signedUrl: string;
  hasAnnotations: boolean;
  annotationStatus: 'labeled' | 'in_progress' | 'not_started';
}

export interface GCSAnnotation {
  segments: AnnotationSegment[];
}

export interface AnnotationSegment {
  start: string; // "MM:SS" format
  end: string;   // "MM:SS" format
  description: string;
  subtitlePosition?: { x: number; y: number }; // Percentage-based (0-100)
}

export interface SaveStatus {
  state: 'idle' | 'pending' | 'saving' | 'saved' | 'error';
  lastSaved: Date | null;
  error: string | null;
}

export interface VideoBrowserFilter {
  status: 'all' | 'labeled' | 'unlabeled' | 'in_progress';
}
