import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { TripletItem } from '../types';
import { getColorByIndex } from '../phraseColoring';
import { useTextSelection, getCleanedPositions } from '../hooks/useTextSelection';

interface PhraseAnnotatorProps {
  reviewText: string;
  categories: string[];
  polarities: string[];
  clickOnToken: boolean;
  implicitAspectAllowed: boolean;
  implicitOpinionAllowed: boolean;
  autoCleanPhrases: boolean;
  annotations: TripletItem[];
  onAddAnnotation: (triplet: TripletItem) => void;
  onRemoveAnnotation: (id: string) => void;
  onEditReview?: () => void;
  onSelectionChange?: (text: string, rect?: DOMRect) => void;
}

interface PendingAnnotation { start: number; end: number; text: string }

const SENTIMENT_STYLES: Record<string, { border: string; bg: string; text: string; ring: string }> = {
  positive: { border: 'border-success/60', bg: 'bg-success/15', text: 'text-success', ring: 'ring-success/40' },
  negative: { border: 'border-error/60', bg: 'bg-error/15', text: 'text-error', ring: 'ring-error/40' },
  neutral:  { border: 'border-warning/60', bg: 'bg-warning/15', text: 'text-warning', ring: 'ring-warning/40' },
};

export const PhraseAnnotator: React.FC<PhraseAnnotatorProps> = ({
  reviewText, categories, polarities, clickOnToken,
  implicitAspectAllowed, implicitOpinionAllowed, autoCleanPhrases,
  annotations, onAddAnnotation, onRemoveAnnotation, onEditReview,
  onSelectionChange,
}) => {
  const [{ selStart, selEnd, pendingSelection }, { handleCharClick, clearSelection }] = useTextSelection(
    reviewText,
    { clickOnToken, autoCleanPhrases }
  );

  const [pending, setPending] = useState<PendingAnnotation | null>(null);
  const [formAspectTerm, setFormAspectTerm] = useState('');
  const [formOpinionTerm, setFormOpinionTerm] = useState('');
  const [formCategory, setFormCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [formPolarity, setFormPolarity] = useState('positive');
  const [formImplicitAspect, setFormImplicitAspect] = useState(false);
  const [formImplicitOpinion, setFormImplicitOpinion] = useState(false);

  // Bridge: hook's pendingSelection → component's form state
  const prevEndRef = useRef<number | null>(null);
  useEffect(() => {
    if (pendingSelection && selEnd !== prevEndRef.current) {
      setPending(pendingSelection);
      setFormAspectTerm(pendingSelection.text);
      setFormOpinionTerm('');
      setFormCategory(categories[0] || 'RESTAURANT#GENERAL');
      setFormPolarity('positive');
      setFormImplicitAspect(false);
      setFormImplicitOpinion(false);
      prevEndRef.current = selEnd;
    }
  }, [pendingSelection, selEnd, categories]);

  // Notify parent of selection changes (for NLP toolbar)
  useEffect(() => {
    if (onSelectionChange) {
      if (selStart !== null && selEnd !== null && pendingSelection) {
        const sel = window.getSelection();
        let rect: DOMRect | undefined;
        if (sel && sel.rangeCount > 0) {
          rect = sel.getRangeAt(0).getBoundingClientRect();
        }
        onSelectionChange(pendingSelection.text, rect);
      } else {
        onSelectionChange('');
      }
    }
  }, [selStart, selEnd, pendingSelection, onSelectionChange]);

  const handleCancel = useCallback(() => { setPending(null); clearSelection(); }, [clearSelection]);
  const handleAdd = useCallback(() => {
    if (!pending) return;
    const aT = formImplicitAspect ? 'NULL' : formAspectTerm.trim() || 'NULL';
    const oT = formImplicitOpinion ? 'NULL' : formOpinionTerm.trim() || 'NULL';

    const isDuplicate = annotations.some(ann =>
      ann.at_start !== null && ann.at_start === pending.start &&
      ann.at_end !== null && ann.at_end === pending.end &&
      ann.aspect_category === formCategory
    );
    if (isDuplicate) {
      setPending(null); clearSelection();
      return;
    }

    const triplet: TripletItem = {
      id: `ph_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      aspect_term: aT, aspect_category: formCategory,
      sentiment_polarity: formPolarity, opinion_term: oT,
    };
    if (aT !== 'NULL') {
      const cp = getCleanedPositions(pending.start, pending.end, reviewText, autoCleanPhrases);
      triplet.at_start = cp.start; triplet.at_end = cp.end;
    } else { triplet.at_start = null; triplet.at_end = null; }
    if (oT !== 'NULL') {
      const i = reviewText.indexOf(oT);
      if (i !== -1) { triplet.ot_start = i; triplet.ot_end = i + oT.length - 1; }
      else { triplet.ot_start = null; triplet.ot_end = null; }
    } else { triplet.ot_start = null; triplet.ot_end = null; }
    onAddAnnotation(triplet);
    setPending(null); clearSelection();
  }, [pending, formImplicitAspect, formAspectTerm, formImplicitOpinion, formOpinionTerm, formCategory, formPolarity, reviewText, autoCleanPhrases, onAddAnnotation, clearSelection]);

  const renderedRuns = useMemo(() => {
    if (!reviewText) return null;
    const n = reviewText.length;
    const bg: (string | null)[] = new Array(n).fill(null);
    const cls: string[] = new Array(n).fill('');

    annotations.forEach((ann, idx) => {
      const ce = getColorByIndex(idx);
      if (ann.aspect_term && ann.aspect_term !== 'NULL' && ann.at_start !== null && ann.at_end !== null) {
        for (let i = ann.at_start; i <= ann.at_end && i < n; i++) {
          bg[i] = `rgba(${ce.aspectRgb.join(',')},0.55)`;
          cls[i] = 'font-bold';
        }
      }
      if (ann.opinion_term && ann.opinion_term !== 'NULL' && ann.ot_start !== null && ann.ot_end !== null) {
        for (let i = ann.ot_start; i <= ann.ot_end && i < n; i++) {
          bg[i] = `rgba(${ce.opinionRgb.join(',')},0.4)`;
          cls[i] = (cls[i]||'') + ' underline decoration-dotted';
        }
      }
    });
    if (selStart !== null) {
      const effE = selEnd ?? selStart;
      for (let i = selStart; i <= effE && i < n; i++) {
        bg[i] = 'rgba(59,130,246,0.4)';
        cls[i] = (cls[i]||'') + ' ring-1 ring-primary/60';
      }
    }

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
        onClick={() => handleCharClick(r.start)}
        className={`cursor-pointer select-none rounded-sm ${r.bg ? r.cls : 'hover:bg-primary/20'}`}
        style={r.bg ? { backgroundColor: r.bg } : undefined}
      >
        {reviewText.slice(r.start, r.end + 1)}
      </span>
    ));
  }, [reviewText, annotations, selStart, selEnd, handleCharClick]);

  const getSentimentBadge = (pol: string) => {
    const p = pol.toLowerCase();
    if (p === 'positive') return 'text-success bg-success/10 border-success/30';
    if (p === 'negative') return 'text-error bg-error/10 border-error/30';
    return 'text-warning bg-warning/10 border-warning/30';
  };

  const tripletCount = annotations.length;

  return (
    <div className="flex flex-col h-full bg-base-200/80 border border-base-300 rounded-2xl shadow-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-base-300 bg-base-200/60">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-base-content">Manuel Etiketleme</h3>
          {onEditReview && (
            <button onClick={onEditReview}
              className="p-1 rounded-md bg-base-200 hover:bg-base-300 text-base-content/50 hover:text-primary transition-all border border-base-300"
              title="Metni Düzenle">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          </div>
          <div className="flex items-center gap-2 text-xs text-base-content/50">
          {selStart !== null && (
            <span className="text-primary font-mono text-[10px]">
              {selEnd !== null ? `[${selStart}-${selEnd}]` : `Başlangıç:${selStart} — bitiş için tıkla`}
            </span>
          )}
          <span className="font-mono text-base-content/60">{tripletCount} etiket</span>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        <div className="bg-base-300/80 border-b border-base-300 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-base-content/50 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              Metinden seçmek için tıkla (1. tık başlangıç, 2. tık bitiş)
            </span>
          </div>
          <div className="text-base md:text-lg font-medium text-base-content leading-relaxed font-sans select-none whitespace-pre-wrap">
            {renderedRuns || reviewText}
          </div>
        </div>

        {pending && (
          <>
            <div className="fixed inset-0 z-40 bg-neutral/40" onClick={handleCancel} />
            <div className="fixed z-50 inset-x-4 top-1/2 -translate-y-1/2 mx-auto max-w-sm bg-base-100 border border-primary/50 rounded-2xl shadow-2xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-base-300">
                <span className="text-xs font-bold text-primary uppercase tracking-wider">Yeni Etiket</span>
                <button onClick={handleCancel} className="text-base-content/50 hover:text-base-content text-sm p-1">✕</button>
              </div>
              <div className="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
                <div className="bg-base-200 rounded-lg p-2.5 border border-base-300">
                  <span className="text-[10px] text-base-content/50 font-mono block mb-1">SEÇİLEN:</span>
                  <span className="text-sm text-base-content font-medium">"{pending.text}"</span>
                </div>

                <div>
                  <label className="flex items-center justify-between text-[10px] text-base-content/60 font-mono mb-1">
                    <span>GÖRÜNÜŞ TERİMİ (aspect term):</span>
                    {implicitAspectAllowed && (
                      <label className="flex items-center gap-1 text-[10px] cursor-pointer">
                        <input type="checkbox" checked={formImplicitAspect}
                          onChange={e => setFormImplicitAspect(e.target.checked)}
                          className="rounded border-base-300 bg-base-200 text-primary focus:ring-primary" />
                        <span className="text-base-content/50">NULL</span>
                      </label>
                    )}
                  </label>
                  <input type="text" value={formImplicitAspect ? 'NULL' : formAspectTerm}
                    onChange={e => setFormAspectTerm(e.target.value)}
                    disabled={formImplicitAspect}
                    placeholder="Metinden seç veya yaz..."
                    className="w-full bg-base-200 border border-base-300 rounded-lg px-3 py-1.5 text-sm text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary disabled:opacity-50" />
                </div>

                <div>
                  <label className="flex items-center justify-between text-[10px] text-base-content/60 font-mono mb-1">
                    <span>GÖRÜŞ TERİMİ (opinion term):</span>
                    {implicitOpinionAllowed && (
                      <label className="flex items-center gap-1 text-[10px] cursor-pointer">
                        <input type="checkbox" checked={formImplicitOpinion}
                          onChange={e => setFormImplicitOpinion(e.target.checked)}
                          className="rounded border-base-300 bg-base-200 text-primary focus:ring-primary" />
                        <span className="text-base-content/50">NULL</span>
                      </label>
                    )}
                  </label>
                  <input type="text" value={formImplicitOpinion ? 'NULL' : formOpinionTerm}
                    onChange={e => setFormOpinionTerm(e.target.value)}
                    disabled={formImplicitOpinion}
                    placeholder="Görüş terimini yaz..."
                    className="w-full bg-base-200 border border-base-300 rounded-lg px-3 py-1.5 text-sm text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary disabled:opacity-50" />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-base-content/60 font-mono mb-1 block">KATEGORİ:</label>
                    <select value={formCategory} onChange={e => setFormCategory(e.target.value)}
                      className="w-full bg-base-200 border border-base-300 rounded-lg px-2 py-1.5 text-xs text-base-content focus:outline-none focus:border-primary">
                      {categories.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-base-content/60 font-mono mb-1 block">KUTUP:</label>
                    <div className="flex gap-1">
                      {polarities.map(p => {
                        const low = p.toLowerCase();
                        const s = SENTIMENT_STYLES[low] || SENTIMENT_STYLES.neutral;
                        return (
                          <button key={p} onClick={() => setFormPolarity(low)}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                              formPolarity === low
                                ? `${s.border} ${s.bg} ${s.text} ring-1 ${s.ring}`
                                : 'border-base-300 text-base-content/50 hover:text-base-content hover:border-base-200'
                            }`}>
                            {low === 'positive' ? '+P' : low === 'negative' ? '-N' : '=N'}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button onClick={handleAdd}
                  className="w-full py-2.5 px-4 bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-xs tracking-wider transition-all shadow-md">
                  + Etiket Ekle
                </button>
              </div>
            </div>
          </>
        )}

        <div className="flex-1 overflow-y-auto px-4 py-2 custom-scrollbar min-h-0">
          {tripletCount === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-base-content/40 py-8">
              <p className="text-xs font-medium">Henüz etiket eklenmedi</p>
              <p className="text-[10px] text-base-content/30 mt-1">Metinden bir bölüm seçerek başlayın</p>
            </div>
          ) : (
            <>
              <span className="text-[10px] font-mono text-base-content/40 uppercase tracking-wider block mb-1.5">
                Etiketler ({tripletCount}):
              </span>
              <div className="space-y-1">
                {annotations.map((ann, idx) => {
                  const ce = getColorByIndex(idx);
                  return (
                    <div key={ann.id}
                      className="flex items-center justify-between bg-base-300 p-2 rounded-lg border border-base-300/80 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: `rgb(${ce.aspectRgb.join(',')})` }} />
                        <span className="font-semibold text-base-content truncate">
                          "{ann.aspect_term === 'NULL' ? <span className="italic text-base-content/50">NULL</span> : ann.aspect_term}"
                        </span>
                        <span className="text-base-content/40 hidden sm:inline">|</span>
                        <span className="text-base-content/60 truncate text-[10px] hidden sm:inline">{ann.aspect_category}</span>
                        <span className={`px-1 py-0.5 rounded text-[10px] uppercase font-mono border ${getSentimentBadge(ann.sentiment_polarity)}`}>
                          {ann.sentiment_polarity}
                        </span>
                        {ann.opinion_term && ann.opinion_term !== 'NULL' && (
                          <span className="text-base-content/50 text-[10px] hidden sm:inline">gr: "{ann.opinion_term}"</span>
                        )}
                      </div>
                      <button onClick={() => onRemoveAnnotation(ann.id)}
                        className="text-base-content/40 hover:text-error p-1 transition-colors flex-shrink-0" title="Sil">✕</button>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
