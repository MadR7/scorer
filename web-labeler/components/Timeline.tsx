'use client';

import { useRef, useEffect, useState } from 'react';
import type { Segment } from './VideoAnnotator';

interface TimelineProps {
  duration: number;
  currentTime: number;
  inPoint: number | null;
  outPoint: number | null;
  segments: Segment[];
  onSeek: (time: number) => void;
  selectedSegment: string | null;
  getSegmentColor?: (index: number) => string;
  onSegmentUpdate?: (segmentId: string, newStart: number, newEnd: number) => void;
}

type DragState = {
  type: 'resize-start' | 'resize-end' | 'move';
  segmentId: string;
  segment: Segment;
  initialMouseX: number;
  initialStart: number;
  initialEnd: number;
} | null;

export function Timeline({ duration, currentTime, inPoint, outPoint, segments, onSeek, selectedSegment, getSegmentColor, onSegmentUpdate }: TimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hovering, setHovering] = useState(false);
  const [hoverTime, setHoverTime] = useState(0);
  const [dragState, setDragState] = useState<DragState>(null);
  const [dragPreview, setDragPreview] = useState<{ start: number; end: number } | null>(null);
  const [cursorStyle, setCursorStyle] = useState<string>('pointer');

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Helper: Get segment at position with drag zone detection
  const getSegmentAtPosition = (x: number, canvasWidth: number): { segment: Segment; index: number; zone: 'start' | 'end' | 'body' } | null => {
    const EDGE_THRESHOLD_PX = 8;
    
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const startX = (seg.start / duration) * canvasWidth;
      const endX = (seg.end / duration) * canvasWidth;
      
      if (x >= startX && x <= endX) {
        // Check if near start edge
        if (x <= startX + EDGE_THRESHOLD_PX) {
          return { segment: seg, index: i, zone: 'start' };
        }
        // Check if near end edge
        if (x >= endX - EDGE_THRESHOLD_PX) {
          return { segment: seg, index: i, zone: 'end' };
        }
        // Must be in body
        return { segment: seg, index: i, zone: 'body' };
      }
    }
    return null;
  };

  // Handle mouse down - start drag
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || duration === 0 || !onSegmentUpdate) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const segmentInfo = getSegmentAtPosition(x, rect.width);

    if (segmentInfo) {
      e.preventDefault();
      const { segment, zone } = segmentInfo;
      
      let dragType: 'resize-start' | 'resize-end' | 'move';
      if (zone === 'start') dragType = 'resize-start';
      else if (zone === 'end') dragType = 'resize-end';
      else dragType = 'move';

      setDragState({
        type: dragType,
        segmentId: segment.id,
        segment: segment,
        initialMouseX: x,
        initialStart: segment.start,
        initialEnd: segment.end,
      });
      setDragPreview({ start: segment.start, end: segment.end });
    }
  };

  // Handle click to seek (only when not dragging)
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragState) return; // Don't seek if we were dragging
    
    const canvas = canvasRef.current;
    if (!canvas || duration === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = (x / rect.width) * duration;
    onSeek(time);
  };

  // Handle mouse move for hover and drag
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || duration === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = (x / rect.width) * duration;
    
    // Handle dragging
    if (dragState) {
      const deltaX = x - dragState.initialMouseX;
      const deltaTime = (deltaX / rect.width) * duration;
      
      let newStart = dragState.initialStart;
      let newEnd = dragState.initialEnd;
      
      if (dragState.type === 'resize-start') {
        // Resize from start edge
        newStart = Math.max(0, Math.min(dragState.initialEnd - 0.1, dragState.initialStart + deltaTime));
      } else if (dragState.type === 'resize-end') {
        // Resize from end edge
        newEnd = Math.min(duration, Math.max(dragState.initialStart + 0.1, dragState.initialEnd + deltaTime));
      } else if (dragState.type === 'move') {
        // Move entire segment
        const segmentDuration = dragState.initialEnd - dragState.initialStart;
        newStart = dragState.initialStart + deltaTime;
        newEnd = dragState.initialEnd + deltaTime;
        
        // Clamp to bounds
        if (newStart < 0) {
          newStart = 0;
          newEnd = segmentDuration;
        }
        if (newEnd > duration) {
          newEnd = duration;
          newStart = duration - segmentDuration;
        }
      }
      
      setDragPreview({ start: newStart, end: newEnd });
      setHoverTime(time);
      return;
    }
    
    // Update cursor based on hover zone
    const segmentInfo = getSegmentAtPosition(x, rect.width);
    if (segmentInfo && onSegmentUpdate) {
      if (segmentInfo.zone === 'start' || segmentInfo.zone === 'end') {
        setCursorStyle('ew-resize');
      } else {
        setCursorStyle('grab');
      }
    } else {
      setCursorStyle('pointer');
    }
    
    setHoverTime(time);
  };

  // Handle mouse up - finalize drag
  const handleMouseUp = () => {
    if (dragState && dragPreview && onSegmentUpdate) {
      onSegmentUpdate(dragState.segmentId, dragPreview.start, dragPreview.end);
    }
    setDragState(null);
    setDragPreview(null);
    setCursorStyle('pointer');
  };

  // Add global mouse up listener for when mouse is released outside canvas
  useEffect(() => {
    if (dragState) {
      const handleGlobalMouseMove = (e: MouseEvent) => {
        const canvas = canvasRef.current;
        if (!canvas || duration === 0) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const deltaX = x - dragState.initialMouseX;
        const deltaTime = (deltaX / rect.width) * duration;
        
        let newStart = dragState.initialStart;
        let newEnd = dragState.initialEnd;
        
        if (dragState.type === 'resize-start') {
          newStart = Math.max(0, Math.min(dragState.initialEnd - 0.1, dragState.initialStart + deltaTime));
        } else if (dragState.type === 'resize-end') {
          newEnd = Math.min(duration, Math.max(dragState.initialStart + 0.1, dragState.initialEnd + deltaTime));
        } else if (dragState.type === 'move') {
          const segmentDuration = dragState.initialEnd - dragState.initialStart;
          newStart = dragState.initialStart + deltaTime;
          newEnd = dragState.initialEnd + deltaTime;
          
          if (newStart < 0) {
            newStart = 0;
            newEnd = segmentDuration;
          }
          if (newEnd > duration) {
            newEnd = duration;
            newStart = duration - segmentDuration;
          }
        }
        
        setDragPreview({ start: newStart, end: newEnd });
      };

      window.addEventListener('mousemove', handleGlobalMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        window.removeEventListener('mousemove', handleGlobalMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [dragState, duration, onSegmentUpdate]);

  // Draw timeline
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || duration === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#1f2937';
    ctx.fillRect(0, 0, width, height);

    // Segments
    segments.forEach((seg, index) => {
      // Use drag preview if this segment is being dragged
      const isDragging = dragState?.segmentId === seg.id;
      const displayStart = isDragging && dragPreview ? dragPreview.start : seg.start;
      const displayEnd = isDragging && dragPreview ? dragPreview.end : seg.end;
      
      const startX = (displayStart / duration) * width;
      const endX = (displayEnd / duration) * width;
      const isSelected = seg.id === selectedSegment;
      
      // Get color for this segment
      const color = getSegmentColor ? getSegmentColor(index) : '#6b7280';
      
      // Draw segment with color (brighter when dragging)
      if (isDragging) {
        ctx.fillStyle = color + 'DD'; // Brighter during drag
      } else {
        ctx.fillStyle = isSelected ? color : color + '99'; // 99 = 60% opacity when not selected
      }
      ctx.fillRect(startX, 0, endX - startX, height);
      
      // Segment border (thicker when dragging)
      ctx.strokeStyle = isDragging ? color : (isSelected ? color : color + 'CC');
      ctx.lineWidth = isDragging ? 4 : (isSelected ? 3 : 2);
      ctx.strokeRect(startX, 0, endX - startX, height);
    });

    // IN/OUT range
    if (inPoint !== null && outPoint !== null) {
      const startX = (Math.min(inPoint, outPoint) / duration) * width;
      const endX = (Math.max(inPoint, outPoint) / duration) * width;
      
      ctx.fillStyle = 'rgba(168, 85, 247, 0.3)';
      ctx.fillRect(startX, 0, endX - startX, height);
    }

    // IN marker
    if (inPoint !== null) {
      const x = (inPoint / duration) * width;
      ctx.fillStyle = '#10b981';
      ctx.fillRect(x - 2, 0, 4, height);
    }

    // OUT marker
    if (outPoint !== null) {
      const x = (outPoint / duration) * width;
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(x - 2, 0, 4, height);
    }

    // Playhead
    const playheadX = (currentTime / duration) * width;
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(playheadX - 1.5, 0, 3, height);

    // Hover line
    if (hovering) {
      const hoverX = (hoverTime / duration) * width;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(hoverX, 0);
      ctx.lineTo(hoverX, height);
      ctx.stroke();
    }
  }, [duration, currentTime, inPoint, outPoint, segments, selectedSegment, hovering, hoverTime, dragState, dragPreview, getSegmentColor]);

  return (
    <div className="mt-4">
      <div className="flex justify-between text-sm text-gray-400 mb-1">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
      <canvas
        ref={canvasRef}
        width={1200}
        height={60}
        className="w-full h-16 rounded-lg"
        style={{ cursor: cursorStyle }}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
      />
      {dragState && dragPreview && (
        <div className="text-xs text-blue-400 mt-1 font-medium">
          Dragging: {formatTime(dragPreview.start)} - {formatTime(dragPreview.end)} (duration: {formatTime(dragPreview.end - dragPreview.start)})
        </div>
      )}
      {!dragState && hovering && (
        <div className="text-xs text-gray-400 mt-1">
          Click to seek to {formatTime(hoverTime)}
        </div>
      )}
    </div>
  );
}
