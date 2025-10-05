'use client';

import { useState, useEffect } from 'react';
import type { Schema } from './VideoAnnotator';

interface AnnotationFormProps {
  inPoint: number | null;
  outPoint: number | null;
  schema: Schema;
  onCommit: (description: string) => void;
}

export function AnnotationForm({ inPoint, outPoint, schema, onCommit }: AnnotationFormProps) {
  const [description, setDescription] = useState('');

  const formatTime = (seconds: number | null) => {
    if (seconds === null) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const canCommit = inPoint !== null && outPoint !== null && description.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canCommit) {
      onCommit(description);
      setDescription('');
    }
  };

  useEffect(() => {
    // Focus description field when both points are marked
    if (inPoint !== null && outPoint !== null) {  
      const descInput = document.getElementById('description-input') as HTMLTextAreaElement;
      if (descInput) descInput.focus();
    }
  }, [inPoint, outPoint]);

  return (
    <div className="p-4 border-b border-gray-800">
      <h3 className="text-lg font-bold mb-3">New Segment</h3>
      
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Time range */}
        <div className="p-3 bg-gray-900 rounded-lg">
          <div className="text-sm text-gray-400 mb-1">Time Range</div>
          <div className="font-mono text-lg">
            <span className={inPoint !== null ? 'text-green-400' : 'text-gray-600'}>
              {formatTime(inPoint)}
            </span>
            <span className="mx-2 text-gray-600">→</span>
            <span className={outPoint !== null ? 'text-blue-400' : 'text-gray-600'}>
              {formatTime(outPoint)}
            </span>
          </div>
          {inPoint !== null && outPoint !== null && (
            <div className="text-sm text-gray-400 mt-1">
              Duration: {Math.abs((outPoint - inPoint)).toFixed(2)}s
            </div>
          )}
          {(inPoint === null || outPoint === null) && (
            <div className="text-sm text-yellow-400 mt-1">
              Press I and O to mark IN and OUT points
            </div>
          )}
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description-input" className="block text-sm font-medium mb-1">
            Description
          </label>
          <textarea
            id="description-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what's happening..."
            rows={3}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            disabled={inPoint === null || outPoint === null}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!canCommit}
          className={`
            w-full py-2 rounded-lg font-medium transition-colors
            ${canCommit 
              ? 'bg-purple-600 hover:bg-purple-700 text-white' 
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'}
          `}
        >
          {canCommit ? '✓ Commit Segment (Enter)' : 'Mark IN and OUT first'}
        </button>
      </form>
    </div>
  );
}
