import React, { useState, useEffect } from 'react';

const STORAGE_KEY = 'annoabsa_welcome_dismissed';

interface WelcomeOverlayProps {
  totalCount: number;
  onUpload: () => void;
  onStart: () => void;
}

export const WelcomeOverlay: React.FC<WelcomeOverlayProps> = ({ totalCount, onUpload, onStart }) => {
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === 'true'; } catch { return false; }
  });

  // Auto-dismiss if real data is loaded (totalCount != FALLBACK_DATA.length=4)
  useEffect(() => {
    if (totalCount > 4 && !dismissed) {
      handleDismiss();
    }
  }, [totalCount]);

  const handleDismiss = () => {
    setDismissed(true);
    try { localStorage.setItem(STORAGE_KEY, 'true'); } catch {}
    onStart();
  };

  if (dismissed) return null;

  const SHORTCUTS = [
    { key: 'Ctrl+Shift+K', desc: 'AI Önerisi Al' },
    { key: '◀ ▶', desc: 'Önceki/Sonraki İnceleme' },
    { key: 'Sürükle-Seç', desc: 'Metin üzerinde Nlp Araçları' },
    { key: 'Escape', desc: 'Panel / Modal Kapat' },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-base-100 border border-primary/30 rounded-3xl shadow-2xl w-full max-w-xl mx-4 overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-br from-primary/10 to-base-200 px-8 pt-8 pb-6 text-center border-b border-base-300">
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <svg className="w-8 h-8 text-white" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1L2 15h3l1-3h4l1 3h3L8 1zM7.5 4.5L10 10H5l2.5-5.5z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-base-content mb-1">AnnoABSA</h1>
          <p className="text-sm text-base-content/60 leading-relaxed max-w-md mx-auto">
            Aspect-Based Sentiment Analysis etiketleme aracı
          </p>
        </div>

        {/* Body */}
        <div className="px-8 py-6 space-y-5">
          {/* Quick start */}
          <div>
            <h2 className="text-xs font-bold text-base-content/50 uppercase tracking-wider mb-3">
              ⚡ Hızlı Başlangıç
            </h2>
            <div className="space-y-2">
              <button onClick={() => { handleDismiss(); onUpload(); }}
                className="w-full flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/20 hover:bg-primary/10 hover:border-primary/40 transition-all group cursor-pointer">
                <div className="w-9 h-9 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/30 transition-colors">
                  <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-base-content group-hover:text-primary transition-colors">CSV / JSON Yükle</div>
                  <div className="text-xs text-base-content/50">Kendi veri setinizi yükleyerek etiketlemeye başlayın</div>
                </div>
              </button>
              <button onClick={handleDismiss}
                className="w-full flex items-center gap-3 p-3 rounded-xl bg-base-200 border border-base-300 hover:bg-base-300 hover:border-primary/30 transition-all group cursor-pointer">
                <div className="w-9 h-9 rounded-lg bg-base-300 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                  <svg className="w-4 h-4 text-base-content/60 group-hover:text-primary transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-base-content group-hover:text-primary transition-colors">Demo Veriyle Başla</div>
                  <div className="text-xs text-base-content/50">Örnek restoran incelemeleri ile aracı keşfedin</div>
                </div>
              </button>
            </div>
          </div>

          {/* Key features */}
          <div>
            <h2 className="text-xs font-bold text-base-content/50 uppercase tracking-wider mb-3">
              🎯 Özellikler
            </h2>
            <div className="grid grid-cols-2 gap-2">
              {[
                { icon: '🔄', title: 'Model Karşılaştırma', desc: 'İki modeli yan yana karşılaştırın' },
                { icon: '✏️', title: 'Manuel Etiketleme', desc: 'Sürükle-bırak ile hassas seçim' },
                { icon: '🤖', title: 'Yardımcı Asistan', desc: 'Yapay zeka destekli sohbet' },
                { icon: '📊', title: 'Aktif Öğrenme', desc: 'Belirsiz örnekleri önceliklendirin' },
              ].map(f => (
                <div key={f.title} className="p-3 rounded-xl bg-base-200/50 border border-base-300">
                  <div className="text-lg mb-1">{f.icon}</div>
                  <div className="text-xs font-bold text-base-content">{f.title}</div>
                  <div className="text-[10px] text-base-content/50 mt-0.5">{f.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Keyboard shortcuts */}
          <div>
            <h2 className="text-xs font-bold text-base-content/50 uppercase tracking-wider mb-3">
              ⌨️ Kısayollar
            </h2>
            <div className="space-y-1.5">
              {SHORTCUTS.map(s => (
                <div key={s.key} className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-base-200/50">
                  <span className="text-xs text-base-content/70">{s.desc}</span>
                  <kbd className="text-[10px] font-mono bg-base-300 border border-base-300 px-2 py-0.5 rounded text-base-content/70">{s.key}</kbd>
                </div>
              ))}
            </div>
          </div>

          {/* NLP tools note */}
          <div className="p-3 rounded-xl bg-gradient-to-r from-primary/5 to-base-200 border border-primary/20">
            <div className="flex items-start gap-2">
              <span className="text-sm flex-shrink-0 mt-0.5">🧠</span>
              <div>
                <div className="text-xs font-bold text-base-content mb-0.5">NLP Araçları</div>
                <div className="text-[10px] text-base-content/60 leading-relaxed">
                  Sözlük (SentiNet), Duygu Analizi (BERT), Yapı Çözümleme, ve Embedding Benzerliği — 
                  metin seçtiğinizde otomatik açılır.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 py-4 bg-base-200/50 border-t border-base-300 flex items-center justify-between">
          <span className="text-[10px] text-base-content/40">v0.1 · LREC 2026</span>
          <button onClick={handleDismiss}
            className="px-5 py-2 rounded-xl bg-primary hover:bg-primary/90 text-primary-content font-bold text-xs transition-all shadow-sm">
            Başlayalım
          </button>
        </div>
      </div>
    </div>
  );
};
