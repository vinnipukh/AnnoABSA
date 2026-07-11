import React, { useState, useMemo, useEffect, useRef } from 'react';
import { TripletItem } from '../types';
import { useTextSelection } from '../hooks/useTextSelection';

interface ManualInputFormProps {
  reviewText: string;
  translation?: string;
  categories: string[];
  polarities: string[];
  manualTriplets: TripletItem[];
  onAddTriplet: (triplet: TripletItem) => void;
  onRemoveTriplet: (id: string) => void;
  onEditReview?: () => void;
  clickOnToken?: boolean;
  onSelectionChange?: (text: string, rect?: DOMRect) => void;
}

export const ManualInputForm: React.FC<ManualInputFormProps> = ({
  reviewText,
  translation,
  categories,
  polarities,
  manualTriplets,
  onAddTriplet,
  onRemoveTriplet,
  onEditReview,
  clickOnToken = true,
  onSelectionChange,
}) => {
  const [aspectTerm, setAspectTerm] = useState('');
  const [category, setCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [sentiment, setSentiment] = useState('positive');
  const [showTranslation, setShowTranslation] = useState(false);

  const [{ selStart, selEnd }, { handleMouseUp }] = useTextSelection(
    reviewText,
    { clickOnToken, autoCleanPhrases: true }
  );

  const textContainerRef = useRef<HTMLDivElement>(null);

  // Notify parent of selection changes (for NLP toolbar)
  useEffect(() => {
    if (onSelectionChange) {
      if (selStart !== null && selEnd !== null) {
        const text = reviewText.substring(selStart, selEnd + 1);
        const sel = window.getSelection();
        let rect: DOMRect | undefined;
        if (sel && sel.rangeCount > 0) {
          rect = sel.getRangeAt(0).getBoundingClientRect();
        }
        onSelectionChange(text, rect);
      } else {
        onSelectionChange('');
      }
    }
  }, [selStart, selEnd, reviewText, onSelectionChange]);

  // Build character-level runs for annotation coloring (selection is native)
  const renderedRuns = useMemo(() => {
    if (!reviewText) return null;
    const n = reviewText.length;
    const bg: (string | null)[] = new Array(n).fill(null);
    const cls: string[] = new Array(n).fill('');

    const runs: { start: number; end: number; bg: string | null; cls: string }[] = [];
    let i = 0;
    while (i < n) {
      const curBg = bg[i];
      const curCls = cls[i];
      const start = i;
      while (i < n && bg[i] === curBg && cls[i] === curCls) i++;
      runs.push({ start, end: i - 1, bg: curBg, cls: curCls });
    }

    return runs.map((r) => (
      <span
        key={r.start}
        className={`cursor-pointer rounded-sm ${r.bg ? r.cls : 'hover:bg-primary/20'}`}
        style={r.bg ? { backgroundColor: r.bg } : undefined}
      >
        {reviewText.slice(r.start, r.end + 1)}
      </span>
    ));
  }, [reviewText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = aspectTerm.trim() || 'NULL';
    const newId = `man_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

    onAddTriplet({
      id: newId,
      aspect_term: term,
      aspect_category: category,
      sentiment_polarity: sentiment,
      isSelected: true
    });

    setAspectTerm('');
  };

  const getSentimentBadge = (pol: string) => {
    const p = pol.toLowerCase();
    if (p === 'positive') return 'text-success bg-success/10 border-success/30';
    if (p === 'negative') return 'text-error bg-error/10 border-error/30';
    return 'text-warning bg-warning/10 border-warning/30';
  };

  return (
    <div className="flex flex-col h-full bg-base-200/80 border border-base-300 rounded-2xl p-4 shadow-xl backdrop-blur-sm overflow-hidden">
      <div className="bg-base-300/80 border border-base-300 rounded-xl p-4 mb-4 relative shadow-inner">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-base-300/80">
          <span className="text-xs font-bold text-base-content/60 uppercase tracking-wider flex items-center">
            <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-pulse"></span>
            İnceleme Metni (Raw Review)
          </span>
          <div className="flex items-center gap-1">
            {onEditReview && (
              <button onClick={onEditReview}
                className="p-1 rounded-md bg-base-200 hover:bg-base-300 text-base-content/50 hover:text-primary transition-all border border-base-300"
                title="Metni Düzenle">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
            )}
            {translation && (
            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="text-xs px-2 py-0.5 rounded bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300"
            >
              {showTranslation ? 'Orijinali Göster' : 'İngilizce Çeviri'}
            </button>
          )}
          </div>
        </div>

        <div ref={textContainerRef} className="text-lg md:text-xl font-medium text-base-content leading-relaxed font-sans whitespace-pre-wrap"
          onMouseUp={() => { if (textContainerRef.current) handleMouseUp(textContainerRef.current); }}>
          {renderedRuns || (showTranslation && translation ? translation : reviewText || "Metin bulunamadı.")}
        </div>
      </div>

      <div className="border-t border-base-300 pt-3 flex-1 flex flex-col overflow-hidden">
        <label className="text-xs font-bold text-base-content/80 uppercase tracking-wider mb-2.5 block flex items-center justify-between">
          <span>Üçlülerinizi girin veya doğru olanları seçin</span>
          <span className="text-[10px] font-normal text-base-content/50 lowercase">(Her iki model de eksikse)</span>
        </label>

        <form onSubmit={handleSubmit} className="space-y-3 bg-base-300/50 p-3.5 rounded-xl border border-base-300/80">
          <div>
            <label className="text-[11px] text-base-content/60 font-mono mb-1 block">ASPECT TERM (Sözcük Öbeği):</label>
            <input
              type="text"
              value={aspectTerm}
              onChange={(e) => setAspectTerm(e.target.value)}
              placeholder="Örn: manzara (boş bırakılırsa NULL)"
              className="w-full bg-base-200 border border-base-300 rounded-lg px-3 py-1.5 text-sm text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-base-content/60 font-mono mb-1 block">KATEGORİ:</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-base-200 border border-base-300 rounded-lg px-2 py-1.5 text-xs text-base-content focus:outline-none focus:border-primary">
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-base-content/60 font-mono mb-1 block">KUTUP:</label>
              <div className="flex gap-1">
                {polarities.map(p => {
                  const low = p.toLowerCase();
                  const isActive = sentiment === low;
                  return (
                    <button key={p} type="button" onClick={() => setSentiment(low)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                        isActive
                          ? `${low === 'positive' ? 'border-success/60 bg-success/15 text-success' : low === 'negative' ? 'border-error/60 bg-error/15 text-error' : 'border-warning/60 bg-warning/15 text-warning'} ring-1`
                          : 'border-base-300 text-base-content/50 hover:text-base-content hover:border-base-200'
                      }`}>
                      {low === 'positive' ? '+P' : low === 'negative' ? '-N' : '=N'}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <button type="submit"
            className="w-full py-2.5 px-4 bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-xs tracking-wider transition-all shadow-md">
            + Triplet Ekle
          </button>
        </form>

        {/* Show existing manual triplets */}
        {manualTriplets.length > 0 && (
          <div className="mt-3 flex-1 overflow-y-auto min-h-0">
            <span className="text-[10px] font-mono text-base-content/40 uppercase tracking-wider block mb-1.5">
              Eklenen Özel Tripletler ({manualTriplets.length}):
            </span>
            <div className="space-y-1">
              {manualTriplets.map((t) => (
                <div key={t.id}
                  className="flex items-center justify-between bg-base-300 p-2 rounded-lg border border-base-300/80 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-semibold text-base-content truncate">"{t.aspect_term}"</span>
                    <span className="text-base-content/40">|</span>
                    <span className="text-base-content/60 truncate text-[10px]">{t.aspect_category}</span>
                    <span className={`px-1 py-0.5 rounded text-[10px] uppercase font-mono border ${getSentimentBadge(t.sentiment_polarity)}`}>
                      {t.sentiment_polarity}
                    </span>
                  </div>
                  <button onClick={() => onRemoveTriplet(t.id)}
                    className="text-base-content/40 hover:text-error p-1 transition-colors flex-shrink-0">✕</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
