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
    if (p === 'positive') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (p === 'negative') return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-sm overflow-hidden">
      {/* Top Box: Review Text Card */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 mb-4 relative shadow-inner">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/80">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center">
            <span className="w-2 h-2 rounded-full bg-blue-500 mr-2 animate-pulse"></span>
            İnceleme Metni (Raw Review)
          </span>
          {translation && (
            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="text-xs px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
            >
              {showTranslation ? 'Orijinali Göster' : 'İngilizce Çeviri'}
            </button>
          )}
        </div>

        <p className="text-lg md:text-xl font-medium text-slate-100 leading-relaxed font-sans tracking-wide">
          {showTranslation && translation ? translation : reviewText || "Metin bulunamadı."}
        </p>
      </div>

      {/* Form Section */}
      <div className="border-t border-slate-800 pt-3 flex-1 flex flex-col overflow-hidden">
        <label className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5 block flex items-center justify-between">
          <span>Enter your triplets or choose the correct ones</span>
          <span className="text-[10px] font-normal text-slate-500 lowercase">(Her iki model de eksikse)</span>
        </label>

        <form onSubmit={handleSubmit} className="space-y-3 bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
          <div>
            <label className="text-[11px] text-slate-400 font-mono mb-1 block">ASPECT TERM (Sözcük Öbeği):</label>
            <input
              type="text"
              value={aspectTerm}
              onChange={(e) => setAspectTerm(e.target.value)}
              placeholder="Örn: manzara (boş bırakılırsa NULL)"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="text-[11px] text-slate-400 font-mono mb-1 block">ASPECT CATEGORY:</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 truncate"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-slate-400 font-mono mb-1 block">POLARITY:</label>
              <select
                value={sentiment}
                onChange={(e) => setSentiment(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 font-medium"
              >
                <option value="positive" className="text-emerald-400">Positive (+)</option>
                <option value="negative" className="text-rose-400">Negative (-)</option>
                <option value="neutral" className="text-amber-400">Neutral (•)</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-2 px-4 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-slate-100 font-semibold rounded-lg text-xs tracking-wider transition-all border border-slate-700 flex items-center justify-center space-x-1.5 shadow-sm"
          >
            <span>+ MANUEL TRİPLET EKLE</span>
          </button>
        </form>

        {/* Manually Added List Preview */}
        {manualTriplets.length > 0 && (
          <div className="mt-3 flex-1 overflow-y-auto pr-1 custom-scrollbar">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              Eklenen Özel Tripletler ({manualTriplets.length}):
            </span>
            <div className="space-y-1.5">
              {manualTriplets.map((m) => (
                <div key={m.id} className="flex items-center justify-between bg-slate-950 p-2 rounded-lg border border-slate-800 text-xs">
                  <div className="flex items-center space-x-2 min-w-0 pr-2">
                    <span className="font-bold text-slate-200 truncate">"{m.aspect_term}"</span>
                    <span className="text-slate-500 hidden sm:inline">|</span>
                    <span className="text-slate-400 truncate text-[11px] hidden sm:inline">{m.aspect_category}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono border ${getSentimentBadge(m.sentiment_polarity)}`}>
                      {m.sentiment_polarity}
                    </span>
                  </div>
                  <button
                    onClick={() => onRemoveTriplet(m.id)}
                    className="text-slate-500 hover:text-rose-400 p-1 transition-colors flex-shrink-0"
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
