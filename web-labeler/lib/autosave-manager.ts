import type { Segment } from '@/components/VideoAnnotator';
import type { GCSAnnotation, SaveStatus } from '@/types/gcs';

interface SaveTask {
  videoPath: string;
  annotation: GCSAnnotation;
  timestamp: number;
}

type SaveCallback = (status: SaveStatus) => void;

export class AutosaveManager {
  private debounceTimer: NodeJS.Timeout | null = null;
  private saveQueue: SaveTask[] = [];
  private isSaving = false;
  private currentVideoPath: string | null = null;
  private lastSavedState: string | null = null;
  private retryCount = 0;
  private maxRetries = 3;
  private readonly debounceMs = 2000;
  private callback: SaveCallback | null = null;

  constructor() {
    // Warn on page close if there are unsaved changes
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', (e) => {
        if (this.debounceTimer || this.isSaving) {
          e.preventDefault();
          e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
          return e.returnValue;
        }
      });
    }
  }

  /**
   * Set callback for status updates
   */
  setCallback(callback: SaveCallback) {
    this.callback = callback;
  }

  /**
   * Schedule a save with debouncing
   */
  scheduleSave(videoPath: string, segments: Segment[]) {
    this.currentVideoPath = videoPath;
    
    // Cancel any pending save
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    // Update status to pending
    this.updateStatus({
      state: 'pending',
      lastSaved: null,
      error: null,
    });

    // Convert segments to GCS format
    const annotation = this.segmentsToGCSAnnotation(segments);
    const currentState = JSON.stringify(annotation);

    // Check if state actually changed
    if (currentState === this.lastSavedState) {
      // No changes, update to saved
      this.updateStatus({
        state: 'saved',
        lastSaved: new Date(),
        error: null,
      });
      return;
    }

    // Debounce the save
    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      this.enqueueSave(videoPath, annotation);
    }, this.debounceMs);
  }

  /**
   * Force save immediately (bypass debounce)
   */
  async forceSave(): Promise<boolean> {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }

    if (this.saveQueue.length > 0) {
      return await this.processQueue();
    }

    return true;
  }

  /**
   * Enqueue a save task
   */
  private enqueueSave(videoPath: string, annotation: GCSAnnotation) {
    const task: SaveTask = {
      videoPath,
      annotation,
      timestamp: Date.now(),
    };

    // Replace any existing task for this video (deduplication)
    this.saveQueue = this.saveQueue.filter(t => t.videoPath !== videoPath);
    this.saveQueue.push(task);

    // Start processing if not already
    if (!this.isSaving) {
      this.processQueue();
    }
  }

  /**
   * Process the save queue
   */
  private async processQueue(): Promise<boolean> {
    if (this.saveQueue.length === 0) {
      return true;
    }

    this.isSaving = true;
    const task = this.saveQueue[0];

    this.updateStatus({
      state: 'saving',
      lastSaved: null,
      error: null,
    });

    try {
      await this.saveWithRetry(task);
      
      // Save successful
      this.lastSavedState = JSON.stringify(task.annotation);
      this.retryCount = 0;
      
      this.updateStatus({
        state: 'saved',
        lastSaved: new Date(),
        error: null,
      });

      // Remove completed task
      this.saveQueue.shift();

      // Process next task
      this.isSaving = false;
      if (this.saveQueue.length > 0) {
        return await this.processQueue();
      }

      return true;
    } catch (error) {
      // Save failed
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      this.updateStatus({
        state: 'error',
        lastSaved: null,
        error: errorMessage,
      });

      this.isSaving = false;
      return false;
    }
  }

  /**
   * Save with retry logic
   */
  private async saveWithRetry(task: SaveTask): Promise<void> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        await this.saveToGCS(task.videoPath, task.annotation);
        return; // Success
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');
        this.retryCount = attempt + 1;

        // Update status with retry info
        this.updateStatus({
          state: 'saving',
          lastSaved: null,
          error: `Retrying... (attempt ${attempt + 2}/${this.maxRetries})`,
        });

        // Exponential backoff
        if (attempt < this.maxRetries - 1) {
          await this.sleep(Math.pow(2, attempt) * 1000);
        }
      }
    }

    // All retries failed
    throw lastError;
  }

  /**
   * Save to GCS via API
   */
  private async saveToGCS(videoPath: string, annotation: GCSAnnotation): Promise<void> {
    const response = await fetch('/api/gcs/annotations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ videoPath, annotation }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to save annotations');
    }
  }

  /**
   * Convert internal segments to GCS annotation format
   */
  private segmentsToGCSAnnotation(segments: Segment[]): GCSAnnotation {
    return {
      segments: segments.map(seg => ({
        start: this.secondsToMMSS(seg.start),
        end: this.secondsToMMSS(seg.end),
        description: seg.description,
        ...(seg.subtitlePosition && { subtitlePosition: seg.subtitlePosition }),
      })),
    };
  }

  /**
   * Convert seconds to MM:SS format
   */
  private secondsToMMSS(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Update status via callback
   */
  private updateStatus(status: SaveStatus) {
    if (this.callback) {
      this.callback(status);
    }
  }

  /**
   * Sleep helper
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current status
   */
  get hasPendingChanges(): boolean {
    return this.debounceTimer !== null || this.isSaving || this.saveQueue.length > 0;
  }
}
