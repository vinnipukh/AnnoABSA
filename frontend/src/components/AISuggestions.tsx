import React from 'react';
import { TripletItem } from '../types';

export interface AiSuggestionItem {
  aspect_term: string;
  aspect_category: string;
  sentiment_polarity: string;
  opinion_term?: string;
  at_start?: number | null;
  at_end?: number | null;
  ot_start?: number | null;
  ot_end?: number | null;
}

interface AISuggestionsProps {
  suggestions: AiSuggestionItem[];
  onAccept: (item: AiSuggestionItem) => void;
  onReject: (index: number) => void;
}

const getSentimentStyle = (pol: string) => {
  const p = pol.toLowerCase();
  if (p === 'positive')
    return { text: 'text-success', badge: 'bg-success/10 text-success-content border-success/30' };
  if (p === 'negative')
    return { text: 'text-error', badge: 'bg-error/10 text-error-content border-error/30' };
  return { text: 'text-warning', badge: 'bg-warning/10 text-warning-content border-warning/30' };
};

export const AISuggestions: React.FC<AISuggestionsProps> = ({
  suggestions,
  onAccept,
  onReject,
}) => {
  if (suggestions.length === 0) return null;

  return (
    <div className="border-t border-primary/20 bg-base-200/60 px-4 py-3">
      <div className="flex items-center gap-1.5 mb-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
          AI Önerileri ({suggestions.length})
        </span>
      </div>
      <div className="space-y-1.5">
        {suggestions.map((s, i) => {
          const style = getSentimentStyle(s.sentiment_polarity);
          return (
            <div
              key={i}
              className="flex items-center justify-between bg-base-100/80 border border-primary/20 rounded-lg px-3 py-2 text-xs group hover:border-primary/40 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className="text-[10px] text-primary font-mono w-4 flex-shrink-0">
                  #{i + 1}
                </span>
                <span className="font-semibold text-base-content truncate">
                  "{s.aspect_term === 'NULL' ? (
                    <span className="italic text-base-content/50">NULL</span>
                  ) : (
                    s.aspect_term
                  )}"
                </span>
                <span className="text-base-content/40 hidden sm:inline">|</span>
                <span className="text-base-content/60 truncate text-[10px] hidden sm:inline">
                  {s.aspect_category}
                </span>
                <span className={`px-1 py-0.5 rounded text-[10px] uppercase font-mono border ${style.badge}`}>
                  {s.sentiment_polarity}
                </span>
                {s.opinion_term && s.opinion_term !== 'NULL' && (
                  <span className="text-base-content/50 text-[10px] hidden sm:inline">
                    gr: "{s.opinion_term}"
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                <button
                  onClick={() => onAccept(s)}
                  className="w-6 h-6 rounded-md bg-success/20 hover:bg-success/40 text-success-content hover:text-success flex items-center justify-center transition-colors border border-success/30"
                  title="Kabul et"
                >
                  <span className="text-xs leading-none">✓</span>
                </button>
                <button
                  onClick={() => onReject(i)}
                  className="w-6 h-6 rounded-md bg-base-200 hover:bg-error/30 text-base-content/50 hover:text-error flex items-center justify-center transition-colors border border-base-300"
                  title="Reddet"
                >
                  <span className="text-xs leading-none">✗</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
