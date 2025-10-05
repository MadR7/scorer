'use client';

import { useState } from 'react';
import type { Segment } from './VideoAnnotator';

interface SegmentListProps {
  segments: Segment[];
  currentTime: number;
  selectedSegment: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (id: string, newDescription: string) => void;
  onSeek: (time: number) => void;
  getSegmentColor?: (index: number) => string;
}

export function SegmentList({ segments, currentTime, selectedSegment, onSelect, onDelete, onEdit, onSeek, getSegmentColor }: SegmentListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startEdit = (segment: Segment) => {
    setEditingId(segment.id);
    setEditText(segment.description);
  };

  const saveEdit = (id: string) => {
    if (editText.trim()) {
      onEdit(id, editText.trim());
    }
    setEditingId(null);
    setEditText('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-bold">Segments ({segments.length})</h3>
      </div>
      
      <div className="space-y-2">
        {segments.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            <div className="text-4xl mb-2">📝</div>
            <p>No segments yet</p>
            <p className="text-sm mt-1">Press I and O to mark points, then fill the form</p>
          </div>
        ) : (
          segments.map((segment, index) => {
            const isActive = currentTime >= segment.start && currentTime <= segment.end;
            const isSelected = segment.id === selectedSegment;
            const color = getSegmentColor ? getSegmentColor(index) : '#6b7280';
            
            return (
              <div
                key={segment.id}
                onClick={() => onSelect(segment.id)}
                className={`
                  p-3 rounded-lg cursor-pointer transition-all border-2 relative
                  ${isSelected ? 'bg-blue-950' : 'bg-gray-900'}
                  ${isActive ? 'ring-2 ring-red-500' : ''}
                  hover:border-blue-400
                `}
                style={{
                  borderColor: isSelected ? color : '#374151'
                }}
              >
                {/* Color indicator bar */}
                <div 
                  className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                  style={{ backgroundColor: color }}
                />
                
                <div className="flex justify-between items-start mb-2 pl-2">
                  <div className="flex-1">
                    <div className="font-mono text-sm" style={{ color: color }}>
                      {formatTime(segment.start)} → {formatTime(segment.end)}
                      <span className="text-gray-500 ml-2">
                        ({(segment.end - segment.start).toFixed(1)}s)
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {editingId !== segment.id && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEdit(segment);
                          }}
                          className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(segment.id);
                          }}
                          className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded transition-colors"
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </div>
                
                {editingId === segment.id ? (
                  <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full px-2 py-1 text-sm bg-gray-800 border border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      rows={3}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                          saveEdit(segment.id);
                        } else if (e.key === 'Escape') {
                          cancelEdit();
                        }
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveEdit(segment.id)}
                        className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 rounded transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 rounded transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="text-sm text-gray-400 pl-2">
                      {segment.description}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSeek(segment.start);
                      }}
                      className="mt-2 ml-2 text-xs text-blue-400 hover:text-blue-300"
                    >
                      ▶ Jump to start
                    </button>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
