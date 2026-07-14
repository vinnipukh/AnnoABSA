import React from 'react';
import { TripletItem } from '../types';

interface CompactTripletChipProps {
  triplet: TripletItem;
  isSelected: boolean;
  onToggle: (id: string) => void;
}

const getSentimentStyle = (polarity: string) => {
  const pol = polarity.toLowerCase();
  if (pol === 'positive' || pol === 'pos' || pol === 'olumlu') {
    return {
      badge: 'bg-success/10 text-success border-success/30',
      selectedBg: 'bg-success/5',
      selectedBorder: 'border-l-success',
    };
  } else if (pol === 'negative' || pol === 'neg' || pol === 'olumsuz') {
    return {
      badge: 'bg-error/10 text-error border-error/30',
      selectedBg: 'bg-error/5',
      selectedBorder: 'border-l-error',
    };
  } else {
    return {
      badge: 'bg-warning/10 text-warning border-warning/30',
      selectedBg: 'bg-warning/5',
      selectedBorder: 'border-l-warning',
    };
  }
};

export const CompactTripletChip: React.FC<CompactTripletChipProps> = ({
  triplet,
  isSelected,
  onToggle,
}) => {
  const style = getSentimentStyle(triplet.sentiment_polarity);

  return (
    <div
      onClick={() => onToggle(triplet.id)}
      className={`flex items-center h-8 px-2 rounded-lg text-xs border transition-all cursor-pointer select-none gap-2 min-w-0 ${
        isSelected
          ? `border-l-2 ${style.selectedBorder} ${style.selectedBg} bg-base-100 border-base-200 shadow-sm`
          : 'border-base-300/80 bg-base-100/40 hover:bg-base-200/60 hover:border-base-200'
      }`}
    >
      {/* Diamond indicator — Heroicons diamond SVG */}
      <svg
        className={`w-3 h-3 flex-shrink-0 ${
          isSelected ? 'text-primary' : 'text-base-content/30'
        }`}
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path d="M12 2L2 12l10 10 10-10L12 2z" />
      </svg>

      {/* Aspect term */}
      <span className="font-semibold text-base-content truncate min-w-0">
        &quot;{triplet.aspect_term || 'NULL'}&quot;
      </span>

      {/* Sentiment badge */}
      <span
        className={`px-1 py-0.5 rounded text-[10px] uppercase font-mono border flex-shrink-0 ${style.badge}`}
      >
        {triplet.sentiment_polarity}
      </span>

      {/* Category */}
      <span className="text-base-content/50 text-[10px] truncate hidden sm:inline flex-shrink-0">
        {triplet.aspect_category}
      </span>
    </div>
  );
};
