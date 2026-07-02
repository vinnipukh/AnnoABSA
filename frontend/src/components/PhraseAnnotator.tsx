import React, { useState, useCallback, useMemo } from 'react';
import { TripletItem } from '../types';
import { getColorByIndex } from '../phraseColoring';

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
}

interface PendingAnnotation { start: number; end: number; text: string }

const SENTIMENT_STYLES: Record<string, { border: string; bg: string; text: string; ring: string }> = {
  positive: { border: 'border-emerald-500/60', bg: 'bg-emerald-500/15', text: 'text-emerald-300', ring: 'ring-emerald-500/40' },
  negative: { border: 'border-rose-500/60', bg: 'bg-rose-500/15', text: 'text-rose-300', ring: 'ring-rose-500/40' },
  neutral:  { border: 'border-amber-500/60', bg: 'bg-amber-500/15', text: 'text-amber-300', ring: 'ring-amber-500/40' },
};

function getTokenBounds(text: string, ci: number): { start: number; end: number } {
  if (!text || ci < 0 || ci >= text.length) return { start: ci, end: ci };
  const isB = (c: string) => /[\s.,;:!?¡¿"'`´''""„«»()\[\]{}]+/.test(c);
  let s = ci, e = ci;
  while (s > 0 && !isB(text[s - 1])) s--;
  while (e < text.length - 1 && !isB(text[e + 1])) e++;
  return { start: s, end: e };
}

function cleanPhrase(p: string): string {
  return p.replace(/^[.,;:!?¡¿"'`´''""„«»()\[\]{}]+|[.,;:!?¡¿"'`´''""„«»()\[\]{}]+$/g, '').trim();
}

function getCleanedPositions(os: number, oe: number, txt: string, clean: boolean): { start: number; end: number } {
  if (!clean) return { start: os, end: oe };
  const r = txt.substring(os, oe + 1), c = cleanPhrase(r);
  if (c === r) return { start: os, end: oe };
  const i = r.indexOf(c);
  return i === -1 ? { start: os, end: oe } : { start: os + i, end: os + i + c.length - 1 };
}

export const PhraseAnnotator: React.FC<PhraseAnnotatorProps> = ({
  reviewText, categories, polarities, clickOnToken,
  implicitAspectAllowed, implicitOpinionAllowed, autoCleanPhrases,
  annotations, onAddAnnotation, onRemoveAnnotation,
}) => {
  const [selStart, setSelStart] = useState<number | null>(null);
  const [selEnd, setSelEnd] = useState<number | null>(null);
  const [pending, setPending] = useState<PendingAnnotation | null>(null);
  const [formAspectTerm, setFormAspectTerm] = useState('');
  const [formOpinionTerm, setFormOpinionTerm] = useState('');
  const [formCategory, setFormCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [formPolarity, setFormPolarity] = useState('positive');
  const [formImplicitAspect, setFormImplicitAspect] = useState(false);
  const [formImplicitOpinion, setFormImplicitOpinion] = useState(false);

  const handleCharClick = useCallback((charIndex: number) => {
    let start = charIndex, end = charIndex;
    if (clickOnToken) {
      const tb = getTokenBounds(reviewText, charIndex);
      if (selStart === null) start = tb.start;
      else end = tb.end;
    }
    if (selStart === null) {
      setSelStart(start);
    } else if (selEnd === null && (clickOnToken ? end : charIndex) >= selStart) {
      setSelEnd(clickOnToken ? end : charIndex);
    } else {
      setSelStart(start);
      setSelEnd(null);
    }
  }, [reviewText, clickOnToken, selStart, selEnd]);

  const pendingFromSelection = useMemo((): PendingAnnotation | null => {
    if (selStart === null || selEnd === null) return null;
    let s = selStart, e = selEnd, t = reviewText.substring(s, e + 1);
    if (autoCleanPhrases) {
      const cp = getCleanedPositions(s, e, reviewText, true);
      s = cp.start; e = cp.end; t = reviewText.substring(s, e + 1);
    }
    return t.trim() ? { start: s, end: e, text: t } : null;
  }, [selStart, selEnd, reviewText, autoCleanPhrases]);

  const prevEndRef = React.useRef<number | null>(null);
  if (pendingFromSelection && pendingFromSelection !== pending && selEnd !== prevEndRef.current) {
    setPending(pendingFromSelection);
    setFormAspectTerm(pendingFromSelection.text);
    setFormOpinionTerm('');
    setFormCategory(categories[0] || 'RESTAURANT#GENERAL');
    setFormPolarity('positive');
    setFormImplicitAspect(false);
    setFormImplicitOpinion(false);
    prevEndRef.current = selEnd;
  }

  const handleCancel = useCallback(() => { setPending(null); setSelStart(null); setSelEnd(null); }, []);
  const handleAdd = useCallback(() => {
    if (!pending) return;
    const aT = formImplicitAspect ? 'NULL' : formAspectTerm.trim() || 'NULL';
    const oT = formImplicitOpinion ? 'NULL' : formOpinionTerm.trim() || 'NULL';

    // Duplicate detection: same span range + same category = skip
    const isDuplicate = annotations.some(ann =>
      ann.at_start !== null && ann.at_start === pending.start &&
      ann.at_end !== null && ann.at_end === pending.end &&
      ann.aspect_category === formCategory
    );
    if (isDuplicate) {
      setPending(null); setSelStart(null); setSelEnd(null);
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
    setPending(null); setSelStart(null); setSelEnd(null);
  }, [pending, formImplicitAspect, formAspectTerm, formImplicitOpinion, formOpinionTerm, formCategory, formPolarity, reviewText, autoCleanPhrases, onAddAnnotation]);

  // Build rendered text with continuous runs (no per-char border artifacts)
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
        cls[i] = (cls[i]||'') + ' ring-1 ring-blue-400/60';
      }
    }

    // Group into continuous runs to avoid per-char border artifacts
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
        className={`cursor-pointer select-none rounded-sm ${r.bg ? r.cls : 'hover:bg-blue-500/20'}`}
        style={r.bg ? { backgroundColor: r.bg } : undefined}
      >
        {reviewText.slice(r.start, r.end + 1)}
      </span>
    ));
  }, [reviewText, annotations, selStart, selEnd, handleCharClick]);

  const getSentimentBadge = (pol: string) => {
    const p = pol.toLowerCase();
    if (p === 'positive') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (p === 'negative') return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  };

  const tripletCount = annotations.length;

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-slate-100">Manuel Etiketleme</h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30">
            {clickOnToken ? 'TOKEN' : 'KARAKTER'}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {selStart !== null && (
            <span className="text-blue-400 font-mono text-[10px]">
              {selEnd !== null ? `[${selStart}-${selEnd}]` : `Başlangıç:${selStart} — bitiş için tıkla`}
            </span>
          )}
          <span className="font-mono text-slate-400">{tripletCount} etiket</span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Text area */}
        <div className="bg-slate-950/80 border-b border-slate-800 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              Metinden seçmek için tıkla (1. tık başlangıç, 2. tık bitiş)
            </span>
          </div>
          <div className="text-base md:text-lg font-medium text-slate-100 leading-relaxed font-sans select-none whitespace-pre-wrap">
            {renderedRuns || reviewText}
          </div>
        </div>

        {/* Selection popup - centered fixed, scrollable */}
        {pending && (
          <>
            {/* backdrop */}
            <div className="fixed inset-0 z-40 bg-black/40" onClick={handleCancel} />
            <div className="fixed z-50 inset-x-4 top-1/2 -translate-y-1/2 mx-auto max-w-sm bg-slate-900 border border-blue-500/50 rounded-2xl shadow-2xl overflow-hidden">
              {/* header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <span className="text-xs font-bold text-blue-300 uppercase tracking-wider">Yeni Etiket</span>
                <button onClick={handleCancel} className="text-slate-500 hover:text-slate-300 text-sm p-1">✕</button>
              </div>
              {/* body */}
              <div className="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
                <div className="bg-slate-950 rounded-lg p-2.5 border border-slate-700">
                  <span className="text-[10px] text-slate-500 font-mono block mb-1">SEÇİLEN:</span>
                  <span className="text-sm text-slate-200 font-medium">"{pending.text}"</span>
                </div>

                {/* Aspect Term */}
                <div>
                  <label className="flex items-center justify-between text-[10px] text-slate-400 font-mono mb-1">
                    <span>GÖRÜNÜŞ TERİMİ (aspect term):</span>
                    {implicitAspectAllowed && (
                      <label className="flex items-center gap-1 text-[10px] cursor-pointer">
                        <input type="checkbox" checked={formImplicitAspect}
                          onChange={e => setFormImplicitAspect(e.target.checked)}
                          className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500" />
                        <span className="text-slate-500">NULL</span>
                      </label>
                    )}
                  </label>
                  <input type="text" value={formImplicitAspect ? 'NULL' : formAspectTerm}
                    onChange={e => setFormAspectTerm(e.target.value)}
                    disabled={formImplicitAspect}
                    placeholder="Metinden seç veya yaz..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50" />
                </div>

                {/* Opinion Term */}
                <div>
                  <label className="flex items-center justify-between text-[10px] text-slate-400 font-mono mb-1">
                    <span>GÖRÜŞ TERİMİ (opinion term):</span>
                    {implicitOpinionAllowed && (
                      <label className="flex items-center gap-1 text-[10px] cursor-pointer">
                        <input type="checkbox" checked={formImplicitOpinion}
                          onChange={e => setFormImplicitOpinion(e.target.checked)}
                          className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500" />
                        <span className="text-slate-500">NULL</span>
                      </label>
                    )}
                  </label>
                  <input type="text" value={formImplicitOpinion ? 'NULL' : formOpinionTerm}
                    onChange={e => setFormOpinionTerm(e.target.value)}
                    disabled={formImplicitOpinion}
                    placeholder="Görüş terimini yaz..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50" />
                </div>

                {/* Category + Polarity */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400 font-mono mb-1 block">KATEGORİ:</label>
                    <select value={formCategory} onChange={e => setFormCategory(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500">
                      {categories.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 font-mono mb-1 block">KUTUP:</label>
                    <div className="flex gap-1">
                      {polarities.map(p => {
                        const low = p.toLowerCase();
                        const s = SENTIMENT_STYLES[low] || SENTIMENT_STYLES.neutral;
                        return (
                          <button key={p} onClick={() => setFormPolarity(low)}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                              formPolarity === low
                                ? `${s.border} ${s.bg} ${s.text} ring-1 ${s.ring}`
                                : 'border-slate-700 text-slate-500 hover:text-slate-300 hover:border-slate-600'
                            }`}>
                            {low === 'positive' ? '+P' : low === 'negative' ? '-N' : '=N'}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button onClick={handleAdd}
                  className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-lg text-xs tracking-wider transition-all shadow-md">
                  + Etiket Ekle
                </button>
              </div>
            </div>
          </>
        )}

        {/* Annotation list */}
        <div className="flex-1 overflow-y-auto px-4 py-2 custom-scrollbar min-h-0">
          {tripletCount === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-600 py-8">
              <p className="text-xs font-medium">Henüz etiket eklenmedi</p>
              <p className="text-[10px] text-slate-700 mt-1">Metinden bir bölüm seçerek başlayın</p>
            </div>
          ) : (
            <>
              <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider block mb-1.5">
                Etiketler ({tripletCount}):
              </span>
              <div className="space-y-1">
                {annotations.map((ann, idx) => {
                  const ce = getColorByIndex(idx);
                  return (
                    <div key={ann.id}
                      className="flex items-center justify-between bg-slate-950 p-2 rounded-lg border border-slate-800/80 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: `rgb(${ce.aspectRgb.join(',')})` }} />
                        <span className="font-semibold text-slate-200 truncate">
                          "{ann.aspect_term === 'NULL' ? <span className="italic text-slate-500">NULL</span> : ann.aspect_term}"
                        </span>
                        <span className="text-slate-600 hidden sm:inline">|</span>
                        <span className="text-slate-400 truncate text-[10px] hidden sm:inline">{ann.aspect_category}</span>
                        <span className={`px-1 py-0.5 rounded text-[10px] uppercase font-mono border ${getSentimentBadge(ann.sentiment_polarity)}`}>
                          {ann.sentiment_polarity}
                        </span>
                        {ann.opinion_term && ann.opinion_term !== 'NULL' && (
                          <span className="text-slate-500 text-[10px] hidden sm:inline">gr: "{ann.opinion_term}"</span>
                        )}
                      </div>
                      <button onClick={() => onRemoveAnnotation(ann.id)}
                        className="text-slate-600 hover:text-rose-400 p-1 transition-colors flex-shrink-0" title="Sil">✕</button>
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
