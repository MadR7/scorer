'use client';

import { forwardRef, useEffect } from 'react';
import { SubtitleOverlay } from './SubtitleOverlay';
import type { Segment } from './VideoAnnotator';

interface VideoPlayerProps {
  url: string;
  playing: boolean;
  onTimeUpdate: (time: number) => void;
  onDurationChange: (duration: number) => void;
  onPlayingChange: (playing: boolean) => void;
  segments?: Segment[];
  currentTime?: number;
  getSegmentColor?: (index: number) => string;
  onSubtitlePositionUpdate?: (segmentId: string, position: { x: number; y: number }) => void;
}

export const VideoPlayer = forwardRef<HTMLVideoElement, VideoPlayerProps>(
  ({ url, playing, onTimeUpdate, onDurationChange, onPlayingChange, segments, currentTime, getSegmentColor, onSubtitlePositionUpdate }, ref) => {
    useEffect(() => {
      const video = (ref as React.RefObject<HTMLVideoElement>).current;
      if (!video) return;

      if (playing) {
        video.play().catch(() => onPlayingChange(false));
      } else {
        video.pause();
      }
    }, [playing, ref, onPlayingChange]);

    return (
      <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
        <video
          ref={ref}
          src={url}
          className="w-full h-full"
          onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
          onLoadedMetadata={(e) => onDurationChange(e.currentTarget.duration)}
          onPlay={() => onPlayingChange(true)}
          onPause={() => onPlayingChange(false)}
          onEnded={() => onPlayingChange(false)}
        />
        {segments && currentTime !== undefined && getSegmentColor && onSubtitlePositionUpdate && (
          <SubtitleOverlay
            segments={segments}
            currentTime={currentTime}
            getSegmentColor={getSegmentColor}
            onPositionUpdate={onSubtitlePositionUpdate}
          />
        )}
      </div>
    );
  }
);

VideoPlayer.displayName = 'VideoPlayer';
