import React, { useState, useCallback } from 'react';

export interface LearningSuggestion {
  index: number;
  text: string;
  uncertainty_score: number;
  uncertainty_rank: number;
}

interface ActiveLearningSuggestionsProps {
  backendUrl: string;
  onNavigate: (index: number) => void;
}

export const ActiveLearningSuggestions: React.FC<ActiveLearningSuggestionsProps> = ({
  backendUrl,
  onNavigate,
}) => {
  const [suggestions, setSuggestions] = useState<LearningSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/learning/suggestions?n=5`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Bağlantı hatası' }));
        setError(err.detail || 'Hata');
        return;
      }
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      if (data.message) {
        setError(data.message);
      }
    } catch {
      setError('Sunucuya bağlanılamadı');
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  const formatScore = (score: number) => {
    // Normalize to percentage-like display
    const pct = Math.min(100, Math.round(score * 25));
    return `${pct}%`;
  };

  const getUncertaintyBar = (score: number) => {
    const pct = Math.min(100, Math.round(score * 25));
    let color = 'bg-success';
    if (pct > 40) color = 'bg-warning';
    if (pct > 70) color = 'bg-error';
    return (
      <div className="w-16 h-1.5 bg-base-300 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    );
  };

  return (
    <div className="border-t border-primary/20 bg-base-200/60 px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${loading ? 'bg-primary animate-pulse' : suggestions.length > 0 ? 'bg-warning' : 'bg-base-300'}`} />
          <span className="text-[10px] font-bold text-base-content/70 uppercase tracking-wider">
            Aktif Öğrenme
          </span>
          {suggestions.length > 0 && (
            <span className="text-[10px] text-warning font-mono bg-warning/10 px-1.5 py-0.5 rounded border border-warning/30">
              {suggestions.length} belirsiz
            </span>
          )}
        </div>
        <button
          onClick={fetchSuggestions}
          disabled={loading}
          className="text-[10px] px-2 py-1 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 hover:text-primary transition-colors border border-base-300 disabled:opacity-50 flex items-center gap-1"
        >
          {loading ? (
            <div className="w-2.5 h-2.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          {loading ? 'Taranıyor...' : 'Tara'}
        </button>
      </div>

      {error && suggestions.length === 0 && (
        <div className="text-[10px] text-base-content/50 bg-base-100/50 rounded-lg px-3 py-2 border border-base-300">
          {error}
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="space-y-1.5">
          {suggestions.map((s) => (
            <div
              key={s.index}
              onClick={() => onNavigate(s.index)}
              className="flex items-center gap-3 bg-base-100/80 border border-warning/20 rounded-lg px-3 py-2 text-xs group hover:border-warning/50 hover:bg-warning/5 transition-all cursor-pointer"
            >
              <span className="text-[10px] text-warning font-mono w-5 flex-shrink-0 font-bold">
                #{s.uncertainty_rank}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-base-content font-medium truncate">
                  "{s.text.length > 50 ? s.text.slice(0, 50) + '...' : s.text}"
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[9px] text-base-content/40 font-mono">
                    Satır #{s.index}
                  </span>
                  {getUncertaintyBar(s.uncertainty_score)}
                  <span className="text-[9px] text-base-content/50 font-mono">
                    {formatScore(s.uncertainty_score)}
                  </span>
                </div>
              </div>
              <svg className="w-3 h-3 text-base-content/30 group-hover:text-primary transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
