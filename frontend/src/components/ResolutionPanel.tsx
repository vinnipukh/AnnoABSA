import React, { useState, useMemo } from 'react';
import { TripletItem } from '../types';

interface ResolutionPanelProps {
  majorityVote: number;
  majorityLabel: TripletItem[];
  gtTriplets: TripletItem[];
  consensusIntersection: TripletItem[];
  originalLlmDiff: string;
  categories: string[];
  polarities: string[];
  manualTriplets: TripletItem[];
  onAddTriplet: (triplet: TripletItem) => void;
  onRemoveTriplet: (id: string) => void;
  onAcceptSuggestion: (triplets: TripletItem[]) => void;
  onEditTriplets: () => void;
}

type Tier = 1 | 2 | 3;

/* ─── Heroicons inline SVGs (no emoji) ─── */

const CheckCircleIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={`${className} text-success`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const WarningCircleIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={`${className} text-warning`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={`${className} text-error`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const PencilIcon = ({ className = "w-3.5 h-3.5" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
  </svg>
);

const ShieldIcon = ({ className = "w-3.5 h-3.5" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const DiamondIcon = ({ className = "w-3 h-3" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 2L2 12l10 10 10-10L12 2z" />
  </svg>
);

const ClipboardIcon = ({ className = "w-3.5 h-3.5" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
  </svg>
);

const CloseIcon = ({ className = "w-3 h-3" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

/* ─── Sentiment badge helper ─── */

function getSentimentBadge(polarity: string | undefined): string {
  const p = (polarity || 'neutral').toLowerCase();
  if (p === 'positive' || p === 'pos') return 'text-success bg-success/10 border-success/30';
  if (p === 'negative' || p === 'neg') return 'text-error bg-error/10 border-error/30';
  return 'text-warning bg-warning/10 border-warning/30';
}

/* ─── Component ─── */

export const ResolutionPanel: React.FC<ResolutionPanelProps> = ({
  majorityVote,
  majorityLabel,
  gtTriplets,
  consensusIntersection,
  originalLlmDiff,
  categories,
  polarities,
  manualTriplets,
  onAddTriplet,
  onRemoveTriplet,
  onAcceptSuggestion,
  onEditTriplets,
}) => {
  const [showManualForm, setShowManualForm] = useState(false);
  const [aspectTerm, setAspectTerm] = useState('');
  const [category, setCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [sentiment, setSentiment] = useState('positive');

  // Deep compare majority_label vs gt_triplets
  const gtMatchesMajority = useMemo(() => {
    if (majorityLabel.length !== gtTriplets.length) return false;
    const normalize = (t: TripletItem) => `${t.aspect_term}|${t.aspect_category}|${t.sentiment_polarity}`;
    const mlSet = new Set(majorityLabel.map(normalize));
    return gtTriplets.every(t => mlSet.has(normalize(t)));
  }, [majorityLabel, gtTriplets]);

  const tier: Tier = majorityVote >= 2 ? (gtMatchesMajority ? 1 : 2) : 3;

  const tierConfig = {
    1: {
      border: 'border-success/30',
      bg: 'bg-success/5',
      header: 'bg-success/10 border-success/30',
      icon: <CheckCircleIcon />,
      title: 'Otomatik Kabul',
      text: 'GT üçlüleri çoğunluk uzlaşmasıyla eşleşiyor',
      suggestion: 'GT üçlüleri önceden seçildi — kabul etmek için kaydedin',
      suggestionClass: 'text-success',
    },
    2: {
      border: 'border-warning/30',
      bg: 'bg-warning/5',
      header: 'bg-warning/10 border-warning/30',
      icon: <WarningCircleIcon />,
      title: 'Hızlı Fark',
      text: 'Uzlaşma bulundu ancak GT\'den farklı — doğrulayın',
      suggestion: 'Çoğunluk GT\'den farklı — aşağıdaki farkı inceleyin',
      suggestionClass: 'text-warning',
    },
    3: {
      border: 'border-error/30',
      bg: 'bg-error/5',
      header: 'bg-error/10 border-error/30',
      icon: <XCircleIcon />,
      title: 'Manuel İnceleme',
      text: 'Uzlaşma yok — manuel inceleme gerekli',
      suggestion: '4 modelin tamamını ızgarada inceleyin, doğru üçlüleri seçin',
      suggestionClass: 'text-error',
    },
  };

  const tc = tierConfig[tier];

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = aspectTerm.trim() || 'NULL';
    onAddTriplet({
      id: `res_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      aspect_term: term,
      aspect_category: category,
      sentiment_polarity: sentiment,
      isSelected: true,
    });
    setAspectTerm('');
  };

  /* ─── Reduced motion styles ─── */
  const motionStyles = `
    @media (prefers-reduced-motion: no-preference) {
      .resolution-panel-btn {
        transition: background-color 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
      }
      .resolution-panel-card {
        transition: border-color 200ms ease;
      }
    }
  `;

  return (
    <div className={`w-[280px] flex-shrink-0 flex flex-col h-full rounded-2xl border ${tc.border} ${tc.bg} p-3 shadow-xl backdrop-blur-sm overflow-hidden`}>
      <style>{motionStyles}</style>

      {/* ── Tier Header ── */}
      <div className={`flex items-start gap-2 px-3 py-2.5 rounded-xl border ${tc.header} mb-2`}>
        <span className="mt-0.5 flex-shrink-0">{tc.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-bold text-base-content">{tc.title}</div>
          <div className="text-[10px] text-base-content/70 leading-relaxed">{tc.text}</div>
        </div>
      </div>

      {/* ── Birincil Öneri Kutusu ── */}
      <div className="bg-base-200/80 border border-base-300/80 rounded-xl p-3 mb-2">
        <div className="text-[10px] font-bold text-base-content/60 uppercase tracking-wider mb-1">
          Birincil Öneri
        </div>

        {/* Tier 1 & 2: LLM-suggested labels (majority triplets) shown prominently */}
        {(tier === 1 || tier === 2) && (
          <div className="space-y-1.5">
            <div className="space-y-1">
              {majorityLabel.map(t => (
                <div key={t.id} className="flex items-center gap-1.5 text-[11px] text-base-content">
                  <DiamondIcon className={`w-2.5 h-2.5 flex-shrink-0 ${tier === 1 ? 'text-success' : 'text-warning'}`} />
                  <span className="truncate">&quot;{t.aspect_term || 'NULL'}&quot;</span>
                  <span className={`text-[10px] px-1 py-0.5 rounded uppercase font-mono border flex-shrink-0 ${getSentimentBadge(t.sentiment_polarity)}`}>
                    {t.sentiment_polarity}
                  </span>
                </div>
              ))}
              {majorityLabel.length === 0 && (
                <p className="text-[10px] text-base-content/40 italic">Uzlaşma üçlüsü yok</p>
              )}
            </div>
            <div className={`text-[10px] font-medium ${tc.suggestionClass} flex items-start gap-1.5`}>
              {tier === 1
                ? <CheckCircleIcon className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                : <WarningCircleIcon className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />}
              <span>{tc.suggestion}</span>
            </div>
          </div>
        )}

        {/* Tier 3: no consensus triplet exists */}
        {tier === 3 && (
          <div className="space-y-1.5">
            <div className="text-xs font-medium text-error flex items-start gap-1.5">
              <XCircleIcon className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>Uzlaşma sağlanamadı — tüm modelleri inceleyin</span>
            </div>
            <div className={`text-[10px] font-medium ${tc.suggestionClass}`}>
              {tc.suggestion}
            </div>
          </div>
        )}
      </div>

      {/* ── Fark Takibi Kutusu ── */}
      <div className="bg-base-200/80 border border-base-300/80 rounded-xl p-3 mb-2 flex-1 overflow-y-auto min-h-0 resolution-panel-card">
        <div className="text-[10px] font-bold text-base-content/60 uppercase tracking-wider mb-1.5">
          Fark Takibi
        </div>

        {/* Tier 1: compact GT match confirmation (labels now live in Birincil Öneri) */}
        {tier === 1 && (
          <div className="flex items-center gap-1.5 border border-success/40 bg-success/5 rounded-lg px-2 py-1.5 text-[11px] text-success font-medium">
            <CheckCircleIcon className="w-3.5 h-3.5 flex-shrink-0" />
            <span>GT ile eşleşiyor</span>
          </div>
        )}

        {/* Tier 2: side-by-side comparison first, diff text below */}
        {tier === 2 && (
          <div className="text-xs space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-[9px] text-warning font-bold uppercase mb-0.5 flex items-center gap-1">
                  <WarningCircleIcon className="w-2.5 h-2.5" />
                  Çoğunluk
                </div>
                {majorityLabel.map(t => (
                  <div key={t.id} className="text-[10px] text-base-content/80 truncate flex items-center gap-1">
                    <DiamondIcon className="w-2 h-2 text-warning flex-shrink-0" />
                    &quot;{t.aspect_term}&quot;
                  </div>
                ))}
                {majorityLabel.length === 0 && (
                  <p className="text-[10px] text-base-content/40 italic">—</p>
                )}
              </div>
              <div>
                <div className="text-[9px] text-primary font-bold uppercase mb-0.5 flex items-center gap-1">
                  <ShieldIcon className="w-2.5 h-2.5" />
                  GT (Orijinal)
                </div>
                {gtTriplets.map(t => (
                  <div key={t.id} className="text-[10px] text-base-content/80 truncate flex items-center gap-1">
                    <DiamondIcon className="w-2 h-2 text-primary flex-shrink-0" />
                    &quot;{t.aspect_term}&quot;
                  </div>
                ))}
                {gtTriplets.length === 0 && (
                  <p className="text-[10px] text-base-content/40 italic">—</p>
                )}
              </div>
            </div>
            {originalLlmDiff && (
              <div className="pt-2 border-t border-base-300">
                <div className="text-[10px] bg-base-300/50 p-2 rounded border border-base-300 font-mono text-base-content/70 leading-relaxed max-h-[60px] overflow-y-auto">
                  {originalLlmDiff}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tier 3: message about all 4 models */}
        {tier === 3 && (
          <div className="text-[11px] text-base-content/60 leading-relaxed">
            Tüm 4 model çıktısı yukarıdaki ızgarada görünüyor. Lütfen doğru tripletleri seçin.
          </div>
        )}
      </div>

      {/* ── Action Buttons ── */}
      <div className="flex flex-col gap-1.5 mb-2">
        {tier === 1 && (
          <>
            <button
              onClick={() => onAcceptSuggestion(gtTriplets)}
              className="resolution-panel-btn w-full min-h-[44px] px-3 bg-success hover:bg-success/90 text-success-content font-bold rounded-lg text-xs transition-all shadow-sm flex items-center justify-center gap-2 select-none"
            >
              <CheckCircleIcon className="w-4 h-4" />
              Kabul Et (Otomatik Kabul)
            </button>
            <button
              onClick={() => setShowManualForm(!showManualForm)}
              className="resolution-panel-btn w-full min-h-[44px] px-3 bg-base-200 hover:bg-base-300 text-base-content/70 rounded-lg text-[10px] transition-all border border-base-300 flex items-center justify-center gap-1.5 select-none"
            >
              <PencilIcon />
              {showManualForm ? 'Kapat' : 'Düzenle'}
            </button>
          </>
        )}

        {tier === 2 && (
          <>
            <button
              onClick={() => onAcceptSuggestion(majorityLabel)}
              className="resolution-panel-btn w-full min-h-[44px] px-3 bg-warning hover:bg-warning/90 text-warning-content font-bold rounded-lg text-xs transition-all shadow-sm flex items-center justify-center gap-2 select-none"
            >
              <WarningCircleIcon className="w-4 h-4" />
              Çoğunluğu Kabul Et
            </button>
            <button
              onClick={() => onAcceptSuggestion(gtTriplets)}
              className="resolution-panel-btn w-full min-h-[44px] px-3 bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-xs transition-all shadow-sm flex items-center justify-center gap-2 select-none"
            >
              <ShieldIcon className="w-4 h-4" />
              GT&apos;yi Koru
            </button>
            <button
              onClick={() => setShowManualForm(!showManualForm)}
              className="resolution-panel-btn w-full min-h-[44px] px-3 bg-base-200 hover:bg-base-300 text-base-content/70 rounded-lg text-[10px] transition-all border border-base-300 flex items-center justify-center gap-1.5 select-none"
            >
              <PencilIcon />
              {showManualForm ? 'Kapat' : 'Düzenle'}
            </button>
          </>
        )}

        {tier === 3 && (
          <button
            onClick={() => setShowManualForm(!showManualForm)}
            className="resolution-panel-btn w-full min-h-[44px] px-3 bg-error hover:bg-error/90 text-error-content font-bold rounded-lg text-xs transition-all shadow-sm flex items-center justify-center gap-2 select-none"
          >
            {showManualForm ? (
              <>
                <CloseIcon className="w-4 h-4" />
                Formu Gizle
              </>
            ) : (
              <>
                <ClipboardIcon className="w-4 h-4" />
                Manuel Giriş
              </>
            )}
          </button>
        )}
      </div>

      {/* ── Manual Entry Form (Tier 3 or toggled) ── */}
      {((tier === 3) || showManualForm) && (
        <div className="border-t border-base-300/80 pt-2 overflow-y-auto min-h-0">
          <form onSubmit={handleManualSubmit} className="space-y-2 bg-base-300/50 p-2.5 rounded-xl border border-base-300/80">
            {/* Aspect term input */}
            <div>
              <label className="text-[10px] text-base-content/50 font-mono mb-0.5 block">ASPECT TERİMİ:</label>
              <input
                type="text"
                value={aspectTerm}
                onChange={e => setAspectTerm(e.target.value)}
                placeholder="Aspect terimi (boş = NULL)"
                className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-1.5 text-xs text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary"
              />
            </div>

            {/* Category dropdown + sentiment buttons */}
            <div className="grid grid-cols-2 gap-1.5">
              <div>
                <label className="text-[10px] text-base-content/50 font-mono mb-0.5 block">KATEGORİ:</label>
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="w-full bg-base-200 border border-base-300 rounded-lg px-1.5 py-1.5 text-[10px] text-base-content focus:outline-none focus:border-primary min-h-[32px]"
                >
                  {categories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div>
                <label className="text-[10px] text-base-content/50 font-mono mb-0.5 block">KUTUP:</label>
                <div className="flex gap-1">
                  {polarities.map(p => {
                    const low = p.toLowerCase();
                    const isActive = sentiment === low;
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setSentiment(low)}
                        className={`flex-1 min-h-[32px] py-1 rounded-lg text-[10px] font-bold border transition-all select-none ${
                          isActive
                            ? `${low === 'positive' ? 'border-success/60 bg-success/15 text-success' : low === 'negative' ? 'border-error/60 bg-error/15 text-error' : 'border-warning/60 bg-warning/15 text-warning'} ring-1`
                            : 'border-base-300 text-base-content/50 hover:text-base-content hover:border-base-200'
                        }`}
                      >
                        {low === 'positive' ? '+P' : low === 'negative' ? '-N' : '=N'}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="resolution-panel-btn w-full min-h-[36px] bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-[10px] transition-all shadow-sm flex items-center justify-center gap-1.5 select-none"
            >
              + Üçlü Ekle
            </button>
          </form>

          {/* Manual triplets list */}
          {manualTriplets.length > 0 && (
            <div className="mt-2 space-y-1 max-h-[120px] overflow-y-auto">
              {manualTriplets.map(t => (
                <div
                  key={t.id}
                  className="flex items-center justify-between bg-base-300 p-1.5 rounded-lg border border-base-300/80 text-[10px]"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="font-semibold text-base-content truncate">
                      &quot;{t.aspect_term || 'NULL'}&quot;
                    </span>
                    <span className={`px-1 py-0.5 rounded text-[9px] uppercase font-mono border ${getSentimentBadge(t.sentiment_polarity)}`}>
                      {t.sentiment_polarity || 'neutral'}
                    </span>
                  </div>
                  <button
                    onClick={() => onRemoveTriplet(t.id)}
                    className="p-1 text-base-content/40 hover:text-error transition-colors flex-shrink-0"
                    title="Üçlüyü kaldır"
                  >
                    <CloseIcon className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
