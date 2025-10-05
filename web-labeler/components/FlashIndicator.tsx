'use client';

interface FlashIndicatorProps {
  text: string;
  color: string;
}

export function FlashIndicator({ text, color }: FlashIndicatorProps) {
  return (
    <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50">
      <div
        className="text-8xl font-bold animate-ping opacity-80"
        style={{ color }}
      >
        {text}
      </div>
    </div>
  );
}
