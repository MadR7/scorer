'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import type { Segment } from './VideoAnnotator';

interface SubtitleOverlayProps {
  segments: Segment[];
  currentTime: number;
  getSegmentColor: (index: number) => string;
  onPositionUpdate: (segmentId: string, position: { x: number; y: number }) => void;
}

interface DragState {
  segmentId: string;
  initialMouseX: number;
  initialMouseY: number;
  initialX: number;
  initialY: number;
}

export function SubtitleOverlay({ segments, currentTime, getSegmentColor, onPositionUpdate }: SubtitleOverlayProps) {
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [hoveredSegmentId, setHoveredSegmentId] = useState<string | null>(null);
  const [defaultPosition, setDefaultPosition] = useState<{ x: number; y: number }>({ x: 50, y: 80 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Find active segments at current time
  const activeSegments = useMemo(() => {
    const active = segments
      .map((seg, index) => ({ ...seg, originalIndex: index }))
      .filter(seg => currentTime >= seg.start && currentTime <= seg.end)
      .sort((a, b) => a.start - b.start); // Sort by start time for consistent stacking
    
    return active;
  }, [segments, currentTime]);

  // Handle mouse down - start dragging
  const handleMouseDown = (e: React.MouseEvent, segment: Segment & { originalIndex: number }) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const currentX = segment.subtitlePosition?.x ?? defaultPosition.x;
    const currentY = segment.subtitlePosition?.y ?? defaultPosition.y;

    setDragState({
      segmentId: segment.id,
      initialMouseX: e.clientX,
      initialMouseY: e.clientY,
      initialX: currentX,
      initialY: currentY,
    });
  };

  // Handle global mouse move during drag
  useEffect(() => {
    if (!dragState) return;

    const handleMouseMove = (e: MouseEvent) => {
      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const deltaX = e.clientX - dragState.initialMouseX;
      const deltaY = e.clientY - dragState.initialMouseY;

      // Convert pixel delta to percentage
      const deltaXPercent = (deltaX / rect.width) * 100;
      const deltaYPercent = (deltaY / rect.height) * 100;

      // Calculate new position
      let newX = dragState.initialX + deltaXPercent;
      let newY = dragState.initialY + deltaYPercent;

      // Clamp to bounds (with some margin for text)
      newX = Math.max(5, Math.min(95, newX));
      newY = Math.max(5, Math.min(95, newY));

      // Update position immediately for smooth dragging
      const segment = activeSegments.find(s => s.id === dragState.segmentId);
      if (segment) {
        segment.subtitlePosition = { x: newX, y: newY };
      }
    };

    const handleMouseUp = () => {
      if (dragState) {
        const container = containerRef.current;
        if (!container) return;

        const segment = activeSegments.find(s => s.id === dragState.segmentId);
        if (segment && segment.subtitlePosition) {
          onPositionUpdate(dragState.segmentId, segment.subtitlePosition);
          // Update default position for future segments
          setDefaultPosition(segment.subtitlePosition);
        }
      }
      setDragState(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragState, activeSegments, onPositionUpdate]);

  if (activeSegments.length === 0) return null;

  return (
    <div 
      ref={containerRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 10 }}
    >
      {activeSegments.map((segment, stackIndex) => {
        const color = getSegmentColor(segment.originalIndex);
        const isDragging = dragState?.segmentId === segment.id;
        const isHovered = hoveredSegmentId === segment.id;
        
        // Calculate stacked position - use saved position or default position
        const baseX = segment.subtitlePosition?.x ?? defaultPosition.x;
        const baseY = segment.subtitlePosition?.y ?? defaultPosition.y;
        const stackedY = baseY - (stackIndex * 8); // 8% gap between stacked subtitles
        
        return (
          <div
            key={segment.id}
            className="absolute pointer-events-auto transition-transform"
            style={{
              left: `${baseX}%`,
              top: `${stackedY}%`,
              transform: `translate(-50%, -50%) ${isDragging ? 'scale(1.05)' : isHovered ? 'scale(1.02)' : 'scale(1)'}`,
              cursor: isDragging ? 'grabbing' : 'grab',
              zIndex: isDragging ? 1000 : 100 + stackIndex,
            }}
            onMouseDown={(e) => handleMouseDown(e, segment)}
            onMouseEnter={() => setHoveredSegmentId(segment.id)}
            onMouseLeave={() => setHoveredSegmentId(null)}
          >
            <div
              className="px-2 py-1 transition-all"
              style={{
                backgroundColor: 'transparent',
                color: color,
                width: '100vw',
                maxWidth: '1400px',
                textShadow: isDragging 
                  ? `0 0 8px ${color}, 0 0 16px ${color}, 0 2px 8px rgba(0,0,0,0.9)`
                  : `0 0 4px ${color}, 0 2px 6px rgba(0,0,0,0.8)`,
              }}
            >
              <div className="text-6xl font-bold leading-tight">
                {segment.description}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
