import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';

/* ── Types ──────────────────────────────────────────────────────────── */

interface SegmentResult {
  loading: boolean;
  data: any;
  error: string | null;
}

interface NlpHelperToolbarProps {
  selectedText: string;
  sentenceText?: string;
  onClose?: () => void;
}

/* ── API helper ─────────────────────────────────────────────────────── */

const BACKEND_URL = 'http://localhost:8000';

async function fetchSegment(
  endpoint: string,
  params: Record<string, string>,
  setResult: (r: SegmentResult) => void,
  abortRef: React.MutableRefObject<AbortController | null>
) {
  if (abortRef.current) abortRef.current.abort();
  const controller = new AbortController();
  abortRef.current = controller;

  setResult({ loading: true, data: null, error: null });
  try {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${BACKEND_URL}${endpoint}?${query}`, {
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!controller.signal.aborted) {
      setResult({ loading: false, data, error: null });
    }
  } catch (e: any) {
    if (e.name === 'AbortError') return;
    if (!controller.signal.aborted) {
      setResult({ loading: false, data: null, error: e.message });
    }
  }
}

/* ── Result display ────────────────────────────────────────────────── */

function ResultDisplay({ data }: { data: any }) {
  // Polarity (lexicon)
  if (data?.aggregate) {
    const pol = data.aggregate;
    const color = pol === 'positive' ? 'text-success'
      : pol === 'negative' ? 'text-error' : 'text-warning';
    return (
      <span className={color + ' font-bold'}>
        {pol === 'positive' ? <><svg className="w-4 h-4 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M8 14s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg> Olumlu</> : pol === 'negative' ? <><svg className="w-4 h-4 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M16 16s-1.5-2-4-2-4 2-4 2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg> Olumsuz</> : <><svg className="w-4 h-4 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="8" y1="14" x2="16" y2="14" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg> Nötr</>}
        {' · '}
        {data.words?.filter((w: any) => w.polarity !== 'unknown').length || 0} kelime
      </span>
    );
  }
  // Sentence sentiment
  if (data?.label) {
    const col = data.label === 'positive' ? 'text-success'
      : data.label === 'negative' ? 'text-error' : 'text-warning';
    return <span className={col + ' font-bold'}>{data.label} ({(data.score * 100).toFixed(0)}%)</span>;
  }
  // Morphology
  if (data?.parses) {
    return (
      <span>
        {data.parses.length} çözümleme · kök: {data.parses[0]?.root || '?'}
      </span>
    );
  }
  // Embedding similarity
  if (data?.similarity !== undefined) {
    const pct = (data.similarity * 100).toFixed(0);
    return <span>Benzerlik: <strong>{pct}%</strong></span>;
  }
  return <span>Yanıt alındı</span>;
}

/* ── Segment button ─────────────────────────────────────────────────── */

interface SegmentButtonProps {
  emoji: React.ReactNode;
  label: string;
  loading: boolean;
  data: any;
  error: string | null;
  onClick: () => void;
}

function SegmentButton({ emoji, label, loading, data, error, onClick }: SegmentButtonProps) {
  return (
    <button onClick={onClick} disabled={loading}
      className="flex items-center gap-2 w-full px-3 py-2 rounded-lg
        hover:bg-base-200 cursor-pointer transition-colors text-left
        disabled:opacity-60 disabled:cursor-wait"
    >
      <span className="text-base">{emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-base-content">{label}</div>
        <div className="text-[10px] text-base-content/50 truncate">
          {loading && 'Yükleniyor…'}
          {error && `❌ ${error}`}
          {data && !loading && !error && <ResultDisplay data={data} />}
          {!loading && !data && !error && 'Tıkla ve çalıştır'}
        </div>
      </div>
    </button>
  );
}

/* ── Toolbox icon SVG (always red, ignores theme) ────────────────────── */

function ToolboxIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="#DC2626" viewBox="0 0 24 24" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round">
      {/* Handle */}
      <rect x="5" y="3" width="14" height="3" rx="1" fill="#DC2626" />
      {/* Body */}
      <path d="M2 8h20l-1.5 13H3.5L2 8z" fill="#DC2626" />
      {/* Divider lines */}
      <line x1="8" y1="8" x2="8" y2="21" stroke="white" strokeWidth={0.5} />
      <line x1="12" y1="8" x2="12" y2="21" stroke="white" strokeWidth={0.5} />
      <line x1="16" y1="8" x2="16" y2="21" stroke="white" strokeWidth={0.5} />
    </svg>
  );
}

/* ── Main component ─────────────────────────────────────────────────── */

export const NlpHelperToolbar: React.FC<NlpHelperToolbarProps> = ({
  selectedText,
  sentenceText,
  onClose,
}) => {
  const [expanded, setExpanded] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);

  const [lexiconResult, setLexiconResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
  const [sentimentResult, setSentimentResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
  const [morphologyResult, setMorphologyResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
  const [similarityResult, setSimilarityResult] = useState<SegmentResult>({ loading: false, data: null, error: null });

  // Clear results when selection changes
  useEffect(() => {
    setLexiconResult({ loading: false, data: null, error: null });
    setSentimentResult({ loading: false, data: null, error: null });
    setMorphologyResult({ loading: false, data: null, error: null });
    setSimilarityResult({ loading: false, data: null, error: null });
    setExpanded(false);
  }, [selectedText]);

  // Auto-fetch lexicon on expand
  useEffect(() => {
    if (expanded && selectedText) {
      fetchSegment('/nlp/lexicon-polarity', { text: selectedText }, setLexiconResult, abortRef);
    }
  }, [expanded, selectedText]);

  // Collapse on Escape
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      setExpanded(false);
      onClose?.();
    }
  }, [onClose]);

  useEffect(() => {
    if (expanded) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [expanded, handleKeyDown]);

  // Collapse on click outside
  useEffect(() => {
    if (!expanded) return;
    const handleClick = (e: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) {
        setExpanded(false);
        onClose?.();
      }
    };
    // Delay to avoid immediate collapse from the click that opened it
    const timer = setTimeout(() => document.addEventListener('mousedown', handleClick), 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [expanded, onClose]);

  // Position: centered horizontally above the footer
  const toolbarStyle: React.CSSProperties = useMemo(() => {
    return {
      position: 'fixed',
      bottom: '64px',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 45,
    };
  }, []);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return (
    <div
      ref={toolbarRef}
      style={toolbarStyle}
      className="bg-base-100/95 backdrop-blur-md border border-base-300 rounded-xl shadow-2xl
        min-w-[280px] max-w-[360px] overflow-hidden"
    >
      {!expanded ? (
        <button onClick={() => setExpanded(true)}
          className="p-2 hover:bg-base-200 rounded-xl transition-colors" title="NLP Araçları">
          <ToolboxIcon />
        </button>
      ) : (
        <div className="p-2 space-y-1">
          {/* Lexicon — auto-loaded */}
          <SegmentButton emoji={<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>} label="Sözlük (SentiNet)"
            loading={lexiconResult.loading} data={lexiconResult.data} error={lexiconResult.error}
            onClick={() => {}} />
          <div className="border-t border-base-300 my-1" />
          {/* Sentiment — on click */}
          <SegmentButton emoji={<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" /><path d="M12 7v4" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" /></svg>} label="Duygu Analizi (BERT)"
            loading={sentimentResult.loading} data={sentimentResult.data} error={sentimentResult.error}
            onClick={() => fetchSegment('/nlp/sentiment', { text: selectedText }, setSentimentResult, abortRef)} />
          {/* Morphology — on click */}
          <SegmentButton emoji={<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg>} label="Yapı Çözümleme (NlpToolkit)"
            loading={morphologyResult.loading} data={morphologyResult.data} error={morphologyResult.error}
            onClick={() => fetchSegment('/nlp/morphology',
              { word: selectedText.split(/\s+/)[0] }, setMorphologyResult, abortRef)} />
          {/* Similarity — on click */}
          <SegmentButton emoji={<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>} label="Benzerlik Karşılaştırması"
            loading={similarityResult.loading} data={similarityResult.data} error={similarityResult.error}
            onClick={() => {
              if (!sentenceText) return;
              fetchSegment('/nlp/embedding-similarity',
                { selection: selectedText, sentence: sentenceText }, setSimilarityResult, abortRef);
            }} />
        </div>
      )}
    </div>
  );
};
