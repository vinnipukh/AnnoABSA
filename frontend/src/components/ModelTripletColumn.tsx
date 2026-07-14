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
  // Phase 4: Live Compare Mode
  onRunPrediction?: () => void;
  isPredicting?: boolean;
}

export const ModelTripletColumn: React.FC<ModelTripletColumnProps> = ({
  title,
  subtitle,
  badgeText,
  badgeColor = "bg-primary/20 text-primary border-primary/30",
  triplets,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onClearAll,
  onRunPrediction,
  isPredicting = false,
}) => {
  const getSentimentStyle = (polarity: string) => {
    const pol = polarity.toLowerCase();
    if (pol === 'positive' || pol === 'pos' || pol === 'olumlu') {
      return {
        text: 'text-success font-medium',
        badge: 'bg-success/10 text-success border-success/30',
        cardSelected: 'bg-success/5 border-success/60 shadow-success/10',
        cardHover: 'hover:border-success/40',
        icon: '◆'
      };
    } else if (pol === 'negative' || pol === 'neg' || pol === 'olumsuz') {
      return {
        text: 'text-error font-medium',
        badge: 'bg-error/10 text-error border-error/30',
        cardSelected: 'bg-error/5 border-error/60 shadow-error/10',
        cardHover: 'hover:border-error/40',
        icon: '◆'
      };
    } else {
      return {
        text: 'text-warning font-medium',
        badge: 'bg-warning/10 text-warning border-warning/30',
        cardSelected: 'bg-warning/5 border-warning/60 shadow-warning/10',
        cardHover: 'hover:border-warning/40',
        icon: '◆'
      };
    }
  };

  const allSelected = triplets.length > 0 && triplets.every(t => selectedIds.has(t.id));

  return (
    <div className="flex flex-col h-full bg-base-200/80 border border-base-300 rounded-2xl p-4 shadow-xl backdrop-blur-sm overflow-hidden">
      <div className="flex items-center justify-between pb-3 border-b border-base-300 mb-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-base-content tracking-tight">{title}</h3>
            {badgeText && (
              <span className={`text-xs px-2 py-0.5 rounded-full border ${badgeColor}`}>
                {badgeText}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-base-content/60 mt-0.5">{subtitle}</p>}
        </div>

        {triplets.length > 0 && (
          <div className="flex items-center space-x-1.5">
            <button
              onClick={allSelected ? onClearAll : onSelectAll}
              className="text-xs px-2.5 py-1 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300 select-none"
            >
              {allSelected ? 'Tümünü Kaldır' : 'Tümünü Seç'}
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar">
        {triplets.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-base-content/50 py-8">
            {onRunPrediction ? (
              <>
                <button
                  onClick={onRunPrediction}
                  disabled={isPredicting}
                  className="px-6 py-3 rounded-xl bg-primary hover:bg-primary/90 text-primary-content font-bold text-sm transition-all shadow-lg flex items-center gap-2 disabled:opacity-50"
                >
                  {isPredicting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-primary-content border-t-transparent rounded-full animate-spin" />
                      Tahmin ediliyor...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {title} Çalıştır
                    </>
                  )}
                </button>
                <p className="text-xs text-base-content/40 mt-3">
                  {isPredicting ? 'Lütfen bekleyin...' : 'Canlı tahmin için tıklayın'}
                </p>
              </>
            ) : (
              <>
                <svg className="w-8 h-8 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <p className="text-sm font-medium">Bu model çıktı üretmedi</p>
                <p className="text-xs text-base-content/40 mt-1">Eksikleri manuel girebilirsiniz</p>
              </>
            )}
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
                    : `bg-base-100/60 border-base-300/80 ${style.cardHover}`
                }`}
              >
                <div className="pt-0.5 flex-shrink-0">
                  <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                    isSelected
                      ? 'bg-primary border-primary text-primary-content shadow-sm'
                      : 'border-base-300 bg-base-200 group-hover:border-base-200 text-transparent'
                  }`}>
                    <span className="text-xs leading-none transform -translate-y-[0.5px]">◆</span>
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-base font-semibold text-base-content truncate block">
                      "{t.aspect_term || 'NULL'}"
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-md border flex-shrink-0 uppercase tracking-wider ${style.badge}`}>
                      {t.sentiment_polarity}
                    </span>
                  </div>
                  
                  <div className="mt-1.5 flex items-center text-xs text-base-content/60 font-mono tracking-tight">
                    <span className="text-base-content/50 mr-1.5">KATEGORİ:</span>
                    <span className="bg-base-200 px-1.5 py-0.5 rounded text-base-content/80 border border-base-300">
                      {t.aspect_category || 'GENEL'}
                    </span>
                  </div>
                </div>

                {isSelected && (
                  <div className="absolute left-0 top-3 bottom-3 w-1 bg-primary rounded-r-full"></div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
