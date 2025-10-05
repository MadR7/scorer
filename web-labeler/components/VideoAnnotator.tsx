'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { VideoPlayer } from './VideoPlayer';
import { Timeline } from './Timeline';
import { SegmentList } from './SegmentList';
import { AnnotationForm } from './AnnotationForm';
import { SaveStatusIndicator } from './SaveStatusIndicator';
import { AutosaveManager } from '@/lib/autosave-manager';
import type { VideoInfo, SaveStatus, GCSAnnotation } from '@/types/gcs';

export interface Segment {
  id: string;
  start: number;
  end: number;
  description: string;
  subtitlePosition?: { x: number; y: number }; // Percentage-based (0-100)
}

export interface Schema {
  fields: { name: string; type: 'text' }[];
}

// Generate a consistent color for a segment based on its index
function getSegmentColor(index: number): string {
  const colors = [
    '#ef4444', // red
    '#f59e0b', // amber
    '#10b981', // emerald
    '#3b82f6', // blue
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316', // orange
    '#6366f1', // indigo
    '#14b8a6', // teal
    '#a855f7', // purple
    '#eab308', // yellow
    '#22c55e', // green
    '#d946ef', // fuchsia
  ];
  return colors[index % colors.length];
}

interface VideoAnnotatorProps {
  video: VideoInfo | null;
  videoList: VideoInfo[];
  onBack: () => void;
  onNavigate: (video: VideoInfo) => void;
}

export function VideoAnnotator({ video, videoList, onBack, onNavigate }: VideoAnnotatorProps) {
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [inPoint, setInPoint] = useState<number | null>(null);
  const [outPoint, setOutPoint] = useState<number | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>({
    state: 'idle',
    lastSaved: null,
    error: null,
  });
  const [loading, setLoading] = useState(false);
  const [undoHistory, setUndoHistory] = useState<Segment[][]>([]);
  const [redoHistory, setRedoHistory] = useState<Segment[][]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Create autosave manager instance
  const autosaveManager = useMemo(() => {
    const manager = new AutosaveManager();
    manager.setCallback(setSaveStatus);
    return manager;
  }, []);

  // Calculate current video index and navigation
  const currentIndex = video ? videoList.findIndex(v => v.path === video.path) : -1;
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < videoList.length - 1;
  const previousVideo = hasPrevious ? videoList[currentIndex - 1] : null;
  const nextVideo = hasNext ? videoList[currentIndex + 1] : null;

  // Simple schema
  const schema: Schema = {
    fields: [
      { name: 'description', type: 'text' }
    ]
  };

  // Load video and annotations from GCS
  useEffect(() => {
    if (!video) return;

    const loadVideoAndAnnotations = async () => {
      setLoading(true);
      
      // Reset all state for clean slate when switching videos
      setSegments([]);
      setInPoint(null);
      setOutPoint(null);
      setSelectedSegment(null);
      setUndoHistory([]);
      setRedoHistory([]);
      
      try {
        // Set video URL from signed URL
        setVideoUrl(video.signedUrl);

        // Load existing annotations if they exist
        if (video.hasAnnotations) {
          const response = await fetch(`/api/gcs/annotations?videoPath=${encodeURIComponent(video.path)}`);
          if (response.ok) {
            const data = await response.json();
            const annotation: GCSAnnotation = data.annotation;
            
            // Convert GCS format to internal format
            const loadedSegments: Segment[] = annotation.segments.map((seg, idx) => ({
              id: `${Date.now()}_${idx}`,
              start: mmssToSeconds(seg.start),
              end: mmssToSeconds(seg.end),
              description: seg.description,
              ...(seg.subtitlePosition && { subtitlePosition: seg.subtitlePosition }),
            }));
            
            setSegments(loadedSegments);
          }
        }
      } catch (error) {
        console.error('Error loading video/annotations:', error);
        alert('Failed to load video or annotations');
      } finally {
        setLoading(false);
      }
    };

    loadVideoAndAnnotations();
  }, [video]);

  // Autosave when segments change
  useEffect(() => {
    if (video && segments.length > 0) {
      autosaveManager.scheduleSave(video.path, segments);
    }
  }, [segments, video, autosaveManager]);

  // Convert MM:SS to seconds
  const mmssToSeconds = (mmss: string): number => {
    const [mins, secs] = mmss.split(':').map(Number);
    return mins * 60 + secs;
  };

  // Update segments with history tracking
  const updateSegmentsWithHistory = useCallback((newSegments: Segment[]) => {
    setUndoHistory(prev => [...prev, segments]);
    setRedoHistory([]); // Clear redo history on new change
    setSegments(newSegments);
  }, [segments]);

  // Undo
  const undo = useCallback(() => {
    if (undoHistory.length > 0) {
      const previousState = undoHistory[undoHistory.length - 1];
      setRedoHistory(prev => [...prev, segments]);
      setSegments(previousState);
      setUndoHistory(prev => prev.slice(0, -1));
    }
  }, [undoHistory, segments]);

  // Redo
  const redo = useCallback(() => {
    if (redoHistory.length > 0) {
      const nextState = redoHistory[redoHistory.length - 1];
      setUndoHistory(prev => [...prev, segments]);
      setSegments(nextState);
      setRedoHistory(prev => prev.slice(0, -1));
    }
  }, [redoHistory, segments]);

  // Mark IN point
  const markIn = useCallback(() => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      
      // If a segment is selected, update its start time
      if (selectedSegment) {
        const newSegments = segments.map(seg => 
          seg.id === selectedSegment ? { ...seg, start: time } : seg
        );
        updateSegmentsWithHistory(newSegments);
      } else {
        setInPoint(time);
      }
    }
  }, [selectedSegment, segments, updateSegmentsWithHistory]);

  // Mark OUT point
  const markOut = useCallback(() => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      
      // If a segment is selected, update its end time
      if (selectedSegment) {
        const newSegments = segments.map(seg => 
          seg.id === selectedSegment ? { ...seg, end: time } : seg
        );
        updateSegmentsWithHistory(newSegments);
      } else {
        setOutPoint(time);
      }
    }
  }, [selectedSegment, segments, updateSegmentsWithHistory]);

  // Commit segment
  const commitSegment = useCallback((description: string) => {
    if (inPoint !== null && outPoint !== null) {
      const newSegment: Segment = {
        id: Date.now().toString(),
        start: Math.min(inPoint, outPoint),
        end: Math.max(inPoint, outPoint),
        description
      };
      const newSegments = [...segments, newSegment].sort((a, b) => a.start - b.start);
      updateSegmentsWithHistory(newSegments);
      setInPoint(null);
      setOutPoint(null);
    }
  }, [inPoint, outPoint, segments, updateSegmentsWithHistory]);

  // Delete segment
  const deleteSegment = useCallback((id: string) => {
    const newSegments = segments.filter(s => s.id !== id);
    updateSegmentsWithHistory(newSegments);
    if (selectedSegment === id) setSelectedSegment(null);
  }, [segments, selectedSegment, updateSegmentsWithHistory]);

  // Edit segment
  const editSegment = useCallback((id: string, newDescription: string) => {
    const newSegments = segments.map(seg => 
      seg.id === id ? { ...seg, description: newDescription } : seg
    );
    updateSegmentsWithHistory(newSegments);
  }, [segments, updateSegmentsWithHistory]);

  // Handle segment drag update from Timeline
  const handleSegmentDragUpdate = useCallback((segmentId: string, newStart: number, newEnd: number) => {
    const newSegments = segments.map(seg => 
      seg.id === segmentId ? { ...seg, start: newStart, end: newEnd } : seg
    );
    updateSegmentsWithHistory(newSegments);
  }, [segments, updateSegmentsWithHistory]);

  // Handle subtitle position update
  const handleSubtitlePositionUpdate = useCallback((segmentId: string, position: { x: number; y: number }) => {
    const newSegments = segments.map(seg => 
      seg.id === segmentId ? { ...seg, subtitlePosition: position } : seg
    );
    setSegments(newSegments); // Direct set, not history (positioning is not undo-able)
    // Trigger autosave
    if (video?.path) {
      autosaveManager.scheduleSave(video.path, newSegments);
    }
  }, [segments, autosaveManager, video]);

  // Seek
  const seek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(time, duration));
    }
  };

  // Force save
  const handleForceSave = async () => {
    await autosaveManager.forceSave();
  };

  // Handle back with unsaved check
  const handleBack = async () => {
    if (autosaveManager.hasPendingChanges) {
      if (confirm('You have unsaved changes. Save before leaving?')) {
        const success = await autosaveManager.forceSave();
        if (success) {
          onBack();
        }
      } else {
        onBack();
      }
    } else {
      onBack();
    }
  };

  // Handle navigation to another video
  const handleNavigateToVideo = async (targetVideo: VideoInfo | null) => {
    if (!targetVideo) return;

    if (autosaveManager.hasPendingChanges) {
      if (confirm('You have unsaved changes. Save before switching videos?')) {
        const success = await autosaveManager.forceSave();
        if (success) {
          onNavigate(targetVideo);
        }
      } else {
        onNavigate(targetVideo);
      }
    } else {
      onNavigate(targetVideo);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'i':
          e.preventDefault();
          markIn();
          break;
        case 'o':
          e.preventDefault();
          markOut();
          break;
        case ' ':
          e.preventDefault();
          setPlaying(p => !p);
          break;
        case 'h':
          // Seek backward: 10 frames (shift) or 60 frames (shift)
          e.preventDefault();
          setPlaying(false);
          if (e.shiftKey) {
            seek(currentTime - (0.033 * 60)); // 60 frames back
          } else {
            seek(currentTime - (0.033 * 10)); // 10 frames back
          }
          break;
        case 'j':
          // Mark IN point
          e.preventDefault();
          markIn();
          break;
        case 'k':
          // Mark OUT point
          e.preventDefault();
          markOut();
          break;
        case 'l':
          // Seek forward: 10 frames or 60 frames (shift)
          e.preventDefault();
          setPlaying(false);
          if (e.shiftKey) {
            seek(currentTime + (0.033 * 60)); // 60 frames forward
          } else {
            seek(currentTime + (0.033 * 10)); // 10 frames forward
          }
          break;
        case 'arrowleft':
          e.preventDefault();
          seek(currentTime - (e.shiftKey ? 5 : 1));
          break;
        case 'arrowright':
          e.preventDefault();
          seek(currentTime + (e.shiftKey ? 5 : 1));
          break;
        case 'enter':
          // Allow Enter to submit form when description is focused
          if ((e.target as HTMLElement).id === 'description-input') {
            // Let the form handle it
            return;
          }
          break;
        case 'z':
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            if (e.shiftKey) {
              // Redo
              redo();
            } else {
              // Undo
              undo();
            }
          }
          break;
        case 'escape':
          e.preventDefault();
          setSelectedSegment(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [markIn, markOut, currentTime, duration, segments.length, undo, redo]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-black text-white">
        <div className="text-center">
          <div className="text-6xl mb-4 animate-spin">↻</div>
          <h2 className="text-2xl font-bold">Loading video...</h2>
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="h-screen flex items-center justify-center bg-black text-white">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold mb-4">No video selected</h2>
          <button
            onClick={onBack}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Back to Browser
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-black text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Back to browser"
          >
            ← Back
          </button>
          
          {/* Navigation arrows */}
          <div className="flex items-center gap-1 border-l border-gray-700 pl-3">
            <button
              onClick={() => handleNavigateToVideo(previousVideo)}
              disabled={!hasPrevious}
              className={`px-3 py-2 rounded-lg transition-colors ${
                hasPrevious 
                  ? 'bg-gray-800 hover:bg-gray-700 text-white' 
                  : 'bg-gray-900 text-gray-600 cursor-not-allowed'
              }`}
              title={previousVideo ? `Previous: ${previousVideo.name}` : 'No previous video'}
            >
              ←
            </button>
            <div className="text-sm text-gray-500 px-2">
              {currentIndex + 1} / {videoList.length}
            </div>
            <button
              onClick={() => handleNavigateToVideo(nextVideo)}
              disabled={!hasNext}
              className={`px-3 py-2 rounded-lg transition-colors ${
                hasNext 
                  ? 'bg-gray-800 hover:bg-gray-700 text-white' 
                  : 'bg-gray-900 text-gray-600 cursor-not-allowed'
              }`}
              title={nextVideo ? `Next: ${nextVideo.name}` : 'No next video'}
            >
              →
            </button>
          </div>

          <div className="border-l border-gray-700 pl-3">
            <h1 className="text-xl font-bold">{video.name}</h1>
            <div className="text-sm text-gray-400">{segments.length} segments</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <SaveStatusIndicator status={saveStatus} onForceSave={handleForceSave} />
          {saveStatus.state !== 'saving' && segments.length > 0 && (
            <button
              onClick={handleForceSave}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors text-sm"
            >
              Save Now
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      {videoUrl ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Video + Timeline */}
          <div className="flex-1 flex flex-col p-4 min-w-0">
            <VideoPlayer
              ref={videoRef}
              url={videoUrl}
              playing={playing}
              onTimeUpdate={setCurrentTime}
              onDurationChange={setDuration}
              onPlayingChange={setPlaying}
              segments={segments}
              currentTime={currentTime}
              getSegmentColor={getSegmentColor}
              onSubtitlePositionUpdate={handleSubtitlePositionUpdate}
            />
            
            <Timeline
              duration={duration}
              currentTime={currentTime}
              inPoint={inPoint}
              outPoint={outPoint}
              segments={segments}
              onSeek={seek}
              selectedSegment={selectedSegment}
              getSegmentColor={getSegmentColor}
              onSegmentUpdate={handleSegmentDragUpdate}
            />

            {/* Keyboard hints */}
            <div className="mt-4 p-3 bg-gray-900 rounded-lg text-sm text-gray-400">
              <div className="font-bold text-white mb-2">Keyboard Shortcuts:</div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-1">
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">J</kbd> or <kbd className="px-2 py-0.5 bg-gray-800 rounded">I</kbd> Mark IN</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">K</kbd> or <kbd className="px-2 py-0.5 bg-gray-800 rounded">O</kbd> Mark OUT</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">H L</kbd> Seek ±10 frames (~0.3s)</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">Shift+H L</kbd> Seek ±60 frames (~2s)</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">← →</kbd> Seek ±1s</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">Shift+← →</kbd> Seek ±5s</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">Space</kbd> Play/Pause</div>
                <div><kbd className="px-2 py-0.5 bg-gray-800 rounded">Esc</kbd> Unselect segment</div>
                <div className="col-span-2"><kbd className="px-2 py-0.5 bg-gray-800 rounded">Cmd+Z</kbd> Undo | <kbd className="px-2 py-0.5 bg-gray-800 rounded">Cmd+Shift+Z</kbd> Redo</div>
              </div>
            </div>
          </div>

          {/* Right: Segments + Form */}
          <div className="w-96 border-l border-gray-800 flex flex-col">
            <AnnotationForm
              inPoint={inPoint}
              outPoint={outPoint}
              schema={schema}
              onCommit={commitSegment}
            />
            <SegmentList
              segments={segments}
              currentTime={currentTime}
              selectedSegment={selectedSegment}
              onSelect={setSelectedSegment}
              onDelete={deleteSegment}
              onEdit={editSegment}
              onSeek={seek}
              getSegmentColor={getSegmentColor}
            />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-6xl mb-4">⏳</div>
            <h2 className="text-2xl font-bold">Loading video...</h2>
          </div>
        </div>
      )}
    </div>
  );
}
