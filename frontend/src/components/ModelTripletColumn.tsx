import React from 'react';
import { TripletItem } from '../types';

interface ModelTripletColumnProps {
  title: string;
  subtitle?: string;
  badgeText?: string;
  badgeColor?: string;
  triplets: TripletItem[];
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
}

export const ModelTripletColumn: React.FC<ModelTripletColumnProps> = ({
  title,
  subtitle,
  badgeText,
  badgeColor = "bg-blue-500/20 text-blue-300 border-blue-500/30",
  triplets,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onClearAll
}) => {
  const getSentimentStyle = (polarity: string) => {
    const pol = polarity.toLowerCase();
    if (pol === 'positive' || pol === 'pos' || pol === 'olumlu') {
      return {
        text: 'text-emerald-400 font-medium',
        badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
        cardSelected: 'bg-emerald-950/40 border-emerald-500/60 shadow-emerald-950/50',
        cardHover: 'hover:border-emerald-500/40',
        icon: '◆'
      };
    } else if (pol === 'negative' || pol === 'neg' || pol === 'olumsuz') {
      return {
        text: 'text-rose-400 font-medium',
        badge: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
        cardSelected: 'bg-rose-950/40 border-rose-500/60 shadow-rose-950/50',
        cardHover: 'hover:border-rose-500/40',
        icon: '◆'
      };
    } else {
      return {
        text: 'text-amber-400 font-medium',
        badge: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
        cardSelected: 'bg-amber-950/40 border-amber-500/60 shadow-amber-950/50',
        cardHover: 'hover:border-amber-500/40',
        icon: '◆'
      };
    }
  };

  const allSelected = triplets.length > 0 && triplets.every(t => selectedIds.has(t.id));

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-slate-100 tracking-tight">{title}</h3>
            {badgeText && (
              <span className={`text-xs px-2 py-0.5 rounded-full border ${badgeColor}`}>
                {badgeText}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>

        {triplets.length > 0 && (
          <div className="flex items-center space-x-1.5">
            <button
              onClick={allSelected ? onClearAll : onSelectAll}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700 select-none"
            >
              {allSelected ? 'Tümünü Kaldır' : 'Tümünü Seç'}
            </button>
          </div>
        )}
      </div>

      {/* Triplet List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar">
        {triplets.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 py-8">
            <svg className="w-8 h-8 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-sm font-medium">Bu model çıktı üretmedi</p>
            <p className="text-xs text-slate-600 mt-1">Eksikleri manuel girebilirsiniz</p>
          </div>
        ) : (
          triplets.map((t) => {
            const isSelected = selectedIds.has(t.id);
            const style = getSentimentStyle(t.sentiment_polarity);

            return (
              <div
                key={t.id}
                onClick={() => onToggleSelect(t.id)}
                className={`group relative p-3.5 rounded-xl border transition-all duration-200 cursor-pointer select-none flex items-start space-x-3 shadow-md ${
                  isSelected
                    ? style.cardSelected
                    : `bg-slate-950/60 border-slate-800/80 ${style.cardHover}`
                }`}
              >
                {/* Clickable Diamond / Checkbox Icon */}
                <div className="pt-0.5 flex-shrink-0">
                  <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                    isSelected
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-600 border-blue-400 text-white shadow-sm'
                      : 'border-slate-700 bg-slate-900 group-hover:border-slate-600 text-transparent'
                  }`}>
                    <span className="text-xs leading-none transform -translate-y-[0.5px]">◆</span>
                  </div>
                </div>

                {/* Triplet Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-base font-semibold text-slate-100 truncate block">
                      "{t.aspect_term || 'NULL'}"
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-md border flex-shrink-0 uppercase tracking-wider ${style.badge}`}>
                      {t.sentiment_polarity}
                    </span>
                  </div>
                  
                  <div className="mt-1.5 flex items-center text-xs text-slate-400 font-mono tracking-tight">
                    <span className="text-slate-500 mr-1.5">KATEGORİ:</span>
                    <span className="bg-slate-900 px-1.5 py-0.5 rounded text-slate-300 border border-slate-800">
                      {t.aspect_category || 'GENEL'}
                    </span>
                  </div>
                </div>

                {/* Selected Accent Indicator */}
                {isSelected && (
                  <div className="absolute left-0 top-3 bottom-3 w-1 bg-blue-500 rounded-r-full"></div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
