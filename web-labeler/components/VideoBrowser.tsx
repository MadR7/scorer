'use client';

import { useState } from 'react';
import useSWR from 'swr';
import type { VideoInfo, VideoBrowserFilter } from '@/types/gcs';
import { AnnotationPreview } from './AnnotationPreview';

interface VideoBrowserProps {
  onSelectVideo: (video: VideoInfo, allVideos: VideoInfo[]) => void;
}

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function VideoBrowser({ onSelectVideo }: VideoBrowserProps) {
  const [gcsPath, setGcsPath] = useState('finetune_dataset');
  const [filter, setFilter] = useState<VideoBrowserFilter['status']>('all');
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null);

  const { data, error, isLoading, mutate } = useSWR(
    `/api/gcs/list-videos?path=${encodeURIComponent(gcsPath)}`,
    fetcher,
    {
      revalidateOnFocus: true,
      refreshInterval: 30000, // Refresh every 30s
    }
  );

  const videos: VideoInfo[] = data?.videos || [];

  // Apply filter
  const filteredVideos = videos.filter(video => {
    if (filter === 'all') return true;
    if (filter === 'labeled') return video.annotationStatus === 'labeled';
    if (filter === 'unlabeled') return video.annotationStatus === 'not_started';
    if (filter === 'in_progress') return video.annotationStatus === 'in_progress';
    return true;
  });

  // Calculate stats
  const labeledCount = videos.filter(v => v.annotationStatus === 'labeled').length;
  const totalCount = videos.length;
  const percentage = totalCount > 0 ? Math.round((labeledCount / totalCount) * 100) : 0;

  const handleRefresh = () => {
    mutate();
  };

  const handleNextUnlabeled = () => {
    const unlabeled = videos.find(v => v.annotationStatus === 'not_started');
    if (unlabeled) {
      handleSelectVideo(unlabeled);
    }
  };

  const handleSelectVideo = (video: VideoInfo) => {
    setSelectedVideo(video);
  };

  const handleEdit = (video: VideoInfo) => {
    onSelectVideo(video, videos);
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold mb-2">Error Loading Videos</h2>
          <p className="text-gray-400 mb-4">{error.error || 'Failed to fetch videos from GCS'}</p>
          {error.details && (
            <p className="text-sm text-gray-500 mb-4">{error.details}</p>
          )}
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-black text-white">
      {/* Left Sidebar: Video List */}
      <div className="w-96 border-r border-gray-800 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-2xl font-bold mb-3">Video Browser</h1>
          
          {/* GCS Path Input */}
          <div className="mb-3">
            <label className="block text-sm text-gray-400 mb-1">GCS Path</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={gcsPath}
                onChange={(e) => setGcsPath(e.target.value)}
                placeholder="finetune_dataset/test"
                className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
              <button
                onClick={handleRefresh}
                className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                title="Refresh"
              >
                ↻
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {!isLoading && totalCount > 0 && (
            <div className="mb-3">
              <div className="flex justify-between text-sm text-gray-400 mb-1">
                <span>{labeledCount} of {totalCount} labeled</span>
                <span>{percentage}%</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-600 transition-all duration-300"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Filter Buttons */}
          <div className="flex gap-2 text-sm">
            {(['all', 'unlabeled', 'labeled', 'in_progress'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`
                  px-2 py-1 rounded transition-colors
                  ${filter === f ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}
                `}
              >
                {f === 'all' && 'All'}
                {f === 'labeled' && 'Labeled'}
                {f === 'unlabeled' && 'Unlabeled'}
                {f === 'in_progress' && 'Draft'}
              </button>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="p-4 border-b border-gray-800 flex gap-2">
          <button
            onClick={handleNextUnlabeled}
            className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-sm font-medium"
            disabled={!videos.some(v => v.annotationStatus === 'not_started')}
          >
            Next Unlabeled
          </button>
        </div>

        {/* Video List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-4xl mb-2">↻</div>
              <div>Loading videos...</div>
            </div>
          ) : filteredVideos.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-4xl mb-2">📂</div>
              <div>No videos found</div>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredVideos.map(video => {
                const isSelected = selectedVideo?.path === video.path;
                let statusColor = 'bg-gray-700';
                let statusIcon = '○';
                
                if (video.annotationStatus === 'labeled') {
                  statusColor = 'bg-green-600';
                  statusIcon = '✓';
                } else if (video.annotationStatus === 'in_progress') {
                  statusColor = 'bg-yellow-600';
                  statusIcon = '●';
                }

                return (
                  <button
                    key={video.path}
                    onClick={() => handleSelectVideo(video)}
                    className={`
                      w-full p-3 rounded-lg text-left transition-all border-2
                      ${isSelected 
                        ? 'border-blue-500 bg-blue-950' 
                        : 'border-gray-800 bg-gray-900 hover:border-gray-700'}
                    `}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="font-medium truncate flex-1">{video.name}</div>
                      <div className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusColor} ml-2`}>
                        {statusIcon}
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">
                      {video.annotationStatus === 'labeled' && 'Labeled'}
                      {video.annotationStatus === 'in_progress' && 'In Progress'}
                      {video.annotationStatus === 'not_started' && 'Not Started'}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel: Preview or Instructions */}
      <div className="flex-1 flex items-center justify-center">
        {selectedVideo ? (
          <AnnotationPreview
            video={selectedVideo}
            onEdit={handleEdit}
            onDeleted={() => {
              mutate();
              setSelectedVideo(null);
            }}
          />
        ) : (
          <div className="text-center text-gray-500">
            <div className="text-6xl mb-4">👈</div>
            <h2 className="text-2xl font-bold mb-2">Select a Video</h2>
            <p>Choose a video from the list to preview or edit annotations</p>
            <div className="mt-6 text-sm text-gray-600">
              <div className="mb-2">
                <span className="inline-block w-6 h-6 rounded-full bg-green-600 mr-2">✓</span>
                Labeled - Has complete annotations
              </div>
              <div className="mb-2">
                <span className="inline-block w-6 h-6 rounded-full bg-yellow-600 mr-2">●</span>
                In Progress - Has draft annotations
              </div>
              <div>
                <span className="inline-block w-6 h-6 rounded-full bg-gray-700 mr-2">○</span>
                Not Started - No annotations yet
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
