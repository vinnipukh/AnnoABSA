import React, { useState } from 'react';
import { TripletItem } from '../types';

interface ManualInputFormProps {
  reviewText: string;
  translation?: string;
  categories: string[];
  polarities: string[];
  manualTriplets: TripletItem[];
  onAddTriplet: (triplet: TripletItem) => void;
  onRemoveTriplet: (id: string) => void;
}

export const ManualInputForm: React.FC<ManualInputFormProps> = ({
  reviewText,
  translation,
  categories,
  polarities,
  manualTriplets,
  onAddTriplet,
  onRemoveTriplet
}) => {
  const [aspectTerm, setAspectTerm] = useState('');
  const [category, setCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [sentiment, setSentiment] = useState('positive');
  const [showTranslation, setShowTranslation] = useState(false);

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
          {translation && (
            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="text-xs px-2 py-0.5 rounded bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300"
            >
              {showTranslation ? 'Orijinali Göster' : 'İngilizce Çeviri'}
            </button>
          )}
        </div>

        <p className="text-lg md:text-xl font-medium text-base-content leading-relaxed font-sans tracking-wide">
          {showTranslation && translation ? translation : reviewText || "Metin bulunamadı."}
        </p>
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
              className="w-full bg-base-200 border border-base-300 rounded-lg px-3 py-2 text-sm text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="text-[11px] text-base-content/60 font-mono mb-1 block">ASPECT CATEGORY:</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-2 text-xs text-base-content focus:outline-none focus:border-primary truncate"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-base-content/60 font-mono mb-1 block">POLARITY:</label>
              <select
                value={sentiment}
                onChange={(e) => setSentiment(e.target.value)}
                className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-2 text-xs text-base-content focus:outline-none focus:border-primary font-medium"
              >
                <option value="positive" className="text-success">Positive (+)</option>
                <option value="negative" className="text-error">Negative (-)</option>
                <option value="neutral" className="text-warning">Neutral (•)</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-2 px-4 bg-base-200 hover:bg-base-300 active:bg-base-200 text-base-content font-semibold rounded-lg text-xs tracking-wider transition-all border border-base-300 flex items-center justify-center space-x-1.5 shadow-sm"
          >
            <span>+ MANUEL TRİPLET EKLE</span>
          </button>
        </form>

        {manualTriplets.length > 0 && (
          <div className="mt-3 flex-1 overflow-y-auto pr-1 custom-scrollbar">
            <span className="text-[10px] font-mono text-base-content/50 uppercase tracking-wider block mb-1.5">
              Eklenen Özel Tripletler ({manualTriplets.length}):
            </span>
            <div className="space-y-1.5">
              {manualTriplets.map((m) => (
                <div key={m.id} className="flex items-center justify-between bg-base-300 p-2 rounded-lg border border-base-300 text-xs">
                  <div className="flex items-center space-x-2 min-w-0 pr-2">
                    <span className="font-bold text-base-content truncate">"{m.aspect_term}"</span>
                    <span className="text-base-content/50 hidden sm:inline">|</span>
                    <span className="text-base-content/60 truncate text-[11px] hidden sm:inline">{m.aspect_category}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono border ${getSentimentBadge(m.sentiment_polarity)}`}>
                      {m.sentiment_polarity}
                    </span>
                  </div>
                  <button
                    onClick={() => onRemoveTriplet(m.id)}
                    className="text-base-content/50 hover:text-error p-1 transition-colors flex-shrink-0"
                    title="Sil"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
