'use client';

import { useState } from 'react';
import { VideoBrowser } from '@/components/VideoBrowser';
import { VideoAnnotator } from '@/components/VideoAnnotator';
import type { VideoInfo } from '@/types/gcs';

export default function Home() {
  const [mode, setMode] = useState<'browse' | 'edit'>('browse');
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null);
  const [videoList, setVideoList] = useState<VideoInfo[]>([]);

  const handleSelectVideo = (video: VideoInfo, allVideos: VideoInfo[]) => {
    setSelectedVideo(video);
    setVideoList(allVideos);
    setMode('edit');
  };

  const handleBackToBrowse = () => {
    setMode('browse');
    setSelectedVideo(null);
  };

  const handleNavigate = (video: VideoInfo) => {
    setSelectedVideo(video);
  };

  return (
    <main className="min-h-screen bg-black">
      {mode === 'browse' ? (
        <VideoBrowser onSelectVideo={handleSelectVideo} />
      ) : (
        <VideoAnnotator
          video={selectedVideo}
          videoList={videoList}
          onBack={handleBackToBrowse}
          onNavigate={handleNavigate}
        />
      )}
    </main>
  );
}