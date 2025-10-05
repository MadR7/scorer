'use client';

import { useState, useEffect } from 'react';
import type { VideoInfo, GCSAnnotation } from '@/types/gcs';

interface AnnotationPreviewProps {
  video: VideoInfo;
  onEdit: (video: VideoInfo) => void;
  onDeleted: () => void;
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

export function AnnotationPreview({ video, onEdit, onDeleted }: AnnotationPreviewProps) {
  const [annotation, setAnnotation] = useState<GCSAnnotation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (video.hasAnnotations) {
      loadAnnotation();
    } else {
      setAnnotation(null);
    }
  }, [video.path]);

  const loadAnnotation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/gcs/annotations?videoPath=${encodeURIComponent(video.path)}`);
      if (!response.ok) {
        throw new Error('Failed to load annotations');
      }
      const data = await response.json();
      setAnnotation(data.annotation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete all annotations for this video?')) {
      return;
    }

    try {
      // Save empty annotations
      const response = await fetch('/api/gcs/annotations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          videoPath: video.path,
          annotation: { segments: [] }
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to delete annotations');
      }

      onDeleted();
    } catch (err) {
      alert(`Failed to delete: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-gray-500">
          <div className="text-4xl mb-2">↻</div>
          <div>Loading annotations...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-500">
          <div className="text-4xl mb-2">⚠️</div>
          <div>Error: {error}</div>
        </div>
      </div>
    );
  }

  if (!video.hasAnnotations || !annotation || annotation.segments.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-6xl mb-4">📝</div>
          <h2 className="text-2xl font-bold mb-2">{video.name}</h2>
          <p className="text-gray-400 mb-6">No annotations yet</p>
          <button
            onClick={() => onEdit(video)}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-lg font-medium"
          >
            Start Labeling
          </button>
        </div>
      </div>
    );
  }

  const segments = annotation.segments;
  const totalDuration = segments.reduce((sum, seg) => {
    const [startMin, startSec] = seg.start.split(':').map(Number);
    const [endMin, endSec] = seg.end.split(':').map(Number);
    const start = startMin * 60 + startSec;
    const end = endMin * 60 + endSec;
    return sum + (end - start);
  }, 0);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-4xl w-full p-8">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">{video.name}</h2>
        <div className="flex items-center gap-4 text-gray-400">
          <span>{segments.length} segments</span>
          <span>•</span>
          <span>{formatDuration(totalDuration)} total duration</span>
        </div>
      </div>

      {/* Timeline Visualization */}
      <div className="mb-6 h-16 bg-gray-900 rounded-lg overflow-hidden relative">
        {segments.map((seg, idx) => {
          const color = getSegmentColor(idx);
          
          return (
            <div
              key={idx}
              className="absolute top-0 h-full opacity-80"
              style={{
                left: `${(idx / segments.length) * 100}%`,
                width: `${(1 / segments.length) * 100}%`,
                backgroundColor: color,
              }}
              title={`${seg.start} - ${seg.end}`}
            />
          );
        })}
      </div>

      {/* Segment List */}
      <div className="space-y-3 mb-6 max-h-96 overflow-y-auto">
        {segments.map((seg, idx) => {
          const color = getSegmentColor(idx);
          return (
            <div key={idx} className="p-4 bg-gray-900 rounded-lg border relative" style={{ borderColor: color + '44' }}>
              {/* Color indicator bar */}
              <div 
                className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                style={{ backgroundColor: color }}
              />
              
              <div className="flex justify-between items-start mb-2 pl-2">
                <div className="flex items-center gap-3">
                  <div className="text-xl font-bold" style={{ color: color + '99' }}>#{idx + 1}</div>
                  <div>
                    <div className="font-mono text-sm" style={{ color: color }}>{seg.start} → {seg.end}</div>
                  </div>
                </div>
              </div>
              <div className="text-sm text-gray-400 pl-2">{seg.description}</div>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => onEdit(video)}
          className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
        >
          Edit Annotations
        </button>
        <button
          onClick={handleDelete}
          className="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg transition-colors font-medium"
        >
          Delete All
        </button>
      </div>
    </div>
  );
}
