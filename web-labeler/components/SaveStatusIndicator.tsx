'use client';

import type { SaveStatus } from '@/types/gcs';

interface SaveStatusIndicatorProps {
  status: SaveStatus;
  onForceSave?: () => void;
}

export function SaveStatusIndicator({ status, onForceSave }: SaveStatusIndicatorProps) {
  const getStatusDisplay = () => {
    switch (status.state) {
      case 'idle':
        return {
          icon: '',
          text: '',
          color: 'text-gray-600',
        };
      case 'pending':
        return {
          icon: '●',
          text: 'Unsaved changes',
          color: 'text-yellow-400',
        };
      case 'saving':
        return {
          icon: '↻',
          text: status.error || 'Saving...',
          color: 'text-blue-400',
        };
      case 'saved':
        return {
          icon: '✓',
          text: status.lastSaved 
            ? `Saved at ${status.lastSaved.toLocaleTimeString()}`
            : 'All changes saved',
          color: 'text-green-400',
        };
      case 'error':
        return {
          icon: '⚠',
          text: status.error || 'Save failed',
          color: 'text-red-400',
        };
    }
  };

  const display = getStatusDisplay();

  if (!display.text) return null;

  return (
    <div className="flex items-center gap-2">
      <span className={`${display.color} text-sm flex items-center gap-1`}>
        <span className={status.state === 'saving' ? 'animate-spin' : ''}>
          {display.icon}
        </span>
        <span>{display.text}</span>
      </span>
      {status.state === 'error' && onForceSave && (
        <button
          onClick={onForceSave}
          className="px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-xs transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
