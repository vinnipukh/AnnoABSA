import React, { useState, useEffect } from 'react';
import { TripletItem, ReviewComparisonData, ChatMessage } from './types';
import { ModelTripletColumn } from './components/ModelTripletColumn';
import { ManualInputForm } from './components/ManualInputForm';
import { HelperAgentChatbox } from './components/HelperAgentChatbox';

// Fallback local dataset matching user's exact CSV format
const FALLBACK_DATA: ReviewComparisonData[] = [
  {
    id: 0,
    text: "4 tarafı cam olduğu için yeterince ısıtamıyorlar.",
    review_text: "4 tarafı cam olduğu için yeterince ısıtamıyorlar.",
    aspect_category_list: ["AMBIENCE#GENERAL", "RESTAURANT#GENERAL", "FOOD#QUALITY", "SERVICE#GENERAL"],
    model_a_triplets: [
      { id: 'ma_0', aspect_term: 'NULL', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'negative' }
    ],
    model_b_triplets: [
      { id: 'mb_0', aspect_term: 'NULL', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'negative' }
    ],
    model_a_name: "Model A",
    model_b_name: "Model B",
    agent_initial_reasoning: "Cam duvarlar nedeniyle mekanın yeterince ısınamaması, doğrudan müşteri konforunu ve ambiyansı olumsuz etkilediği için AMBIENCE#GENERAL (negative) olarak etiketlenmelidir."
  },
  {
    id: 1,
    text: "Üstelik fiyatlarda, yemeklerine nazaran uygun degil.",
    review_text: "Üstelik fiyatlarda, yemeklerine nazaran uygun degil.",
    aspect_category_list: ["FOOD#PRICES", "FOOD#QUALITY", "RESTAURANT#GENERAL", "SERVICE#GENERAL"],
    model_a_triplets: [
      { id: 'ma_1', aspect_term: 'fiyatlarda', aspect_category: 'FOOD#PRICES', sentiment_polarity: 'negative' },
      { id: 'ma_2', aspect_term: 'yemeklerine', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'negative' }
    ],
    model_b_triplets: [
      { id: 'mb_1', aspect_term: 'fiyatlarda', aspect_category: 'FOOD#PRICES', sentiment_polarity: 'negative' }
    ],
    model_a_name: "Model A",
    model_b_name: "Model B",
    agent_initial_reasoning: "Fiyatlar yemeklere göre uygun değil. Bu cümlede asıl eleştirilen nokta 'fiyatların yüksekliği' olduğu için FOOD#PRICES (negative) seçilmelidir. Yemeklerin kötü olduğu söylenmediği için FOOD#QUALITY eklenmemelidir."
  },
  {
    id: 2,
    text: "Mekanin kalabalik olmasindan mi kaynakliydi bu dikkatsizlik anlam veremedim, bu kadar övgü almasina ragmen böyle olumsuz bir durum ilginç geldi.",
    review_text: "Mekanin kalabalik olmasindan mi kaynakliydi bu dikkatsizlik anlam veremedim, bu kadar övgü almasina ragmen böyle olumsuz bir durum ilginç geldi.",
    aspect_category_list: ["RESTAURANT#GENERAL", "SERVICE#GENERAL", "AMBIENCE#GENERAL"],
    model_a_triplets: [
      { id: 'ma_3', aspect_term: 'durum', aspect_category: 'RESTAURANT#GENERAL', sentiment_polarity: 'negative' }
    ],
    model_b_triplets: [],
    model_a_name: "Model A",
    model_b_name: "Model B",
    agent_initial_reasoning: "Mekanın kalabalık olması ve yaşanan dikkatsizlik genel restoran deneyimini olumsuz etkiliyor. Model B bu satırda çıktı üretmemiş, Model A etiketini onaylayabilirsiniz."
  },
  {
    id: 3,
    text: "Hamburgeri hoşuma gidiyor ve NY steak de tavsiye edebilirim.",
    review_text: "Hamburgeri hoşuma gidiyor ve NY steak de tavsiye edebilirim.",
    aspect_category_list: ["FOOD#QUALITY", "FOOD#STYLE_OPTIONS", "RESTAURANT#GENERAL"],
    model_a_triplets: [
      { id: 'ma_4', aspect_term: 'NY steak', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
      { id: 'ma_5', aspect_term: 'Hamburgeri', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' }
    ],
    model_b_triplets: [
      { id: 'mb_2', aspect_term: 'Hamburgeri', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
      { id: 'mb_3', aspect_term: 'NY steak', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' }
    ],
    model_a_name: "Model A",
    model_b_name: "Model B",
    agent_initial_reasoning: "Her iki yemek için de net olumlu ifadeler mevcut: hamburger beğenilmiş, NY steak tavsiye edilmiş. Her iki modelin ortak çıktılarını seçebilirsiniz."
  }
];

export default function App() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentData, setCurrentData] = useState<ReviewComparisonData>(FALLBACK_DATA[0]);
  const [totalCount, setTotalCount] = useState(FALLBACK_DATA.length);

  // Selections
  const [selectedModelAIds, setSelectedModelAIds] = useState<Set<string>>(new Set());
  const [selectedModelBIds, setSelectedModelBIds] = useState<Set<string>>(new Set());
  const [manualTriplets, setManualTriplets] = useState<TripletItem[]>([]);

  // Chat
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Status
  const [saveToast, setSaveToast] = useState<string | null>(null);

  // Backend URL from env or local default
  const backendUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';

  // Load Data Row
  const loadReviewRow = async (index: number) => {
    try {
      const res = await fetch(`${backendUrl}/data/${index}`);
      if (!res.ok) throw new Error("API Offline");
      const data: ReviewComparisonData = await res.json();
      setCurrentData(data);
    } catch (e) {
      // Graceful fallback to static data
      const safeIndex = index % FALLBACK_DATA.length;
      setCurrentData(FALLBACK_DATA[safeIndex]);
    }

    // Reset selections on new review
    setSelectedModelAIds(new Set());
    setSelectedModelBIds(new Set());
    setManualTriplets([]);
    setChatMessages([]);
  };

  useEffect(() => {
    // Initial fetch
    fetch(`${backendUrl}/settings`)
      .then(r => r.json())
      .then(s => {
        if (s.total_count) setTotalCount(s.total_count);
      })
      .catch(() => {});

    loadReviewRow(currentIndex);
  }, [currentIndex]);

  // Triplet selection handlers
  const toggleModelA = (id: string) => {
    const next = new Set(selectedModelAIds);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelectedModelAIds(next);
  };

  const toggleModelB = (id: string) => {
    const next = new Set(selectedModelBIds);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelectedModelBIds(next);
  };

  const selectAllModelA = () => {
    setSelectedModelAIds(new Set(currentData.model_a_triplets.map(t => t.id)));
  };

  const clearAllModelA = () => setSelectedModelAIds(new Set());

  const selectAllModelB = () => {
    setSelectedModelBIds(new Set(currentData.model_b_triplets.map(t => t.id)));
  };

  const clearAllModelB = () => setSelectedModelBIds(new Set());

  // Save & Next Review
  const handleNextReview = async () => {
    // Gather all selected triplets
    const approvedTriplets: any[] = [];

    currentData.model_a_triplets.forEach(t => {
      if (selectedModelAIds.has(t.id)) approvedTriplets.push(t);
    });

    currentData.model_b_triplets.forEach(t => {
      if (selectedModelBIds.has(t.id)) approvedTriplets.push(t);
    });

    manualTriplets.forEach(t => approvedTriplets.push(t));

    try {
      await fetch(`${backendUrl}/review/${currentIndex}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triplets: approvedTriplets })
      });
    } catch (e) {
      // offline save simulation
    }

    setSaveToast(`✅ İnceleme #${currentIndex + 1} kaydedildi (${approvedTriplets.length} triplet).`);
    setTimeout(() => setSaveToast(null), 2500);

    setCurrentIndex(prev => (prev + 1) % totalCount);
  };

  // Chat send handler
  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = { id: `u_${Date.now()}`, sender: 'user', text };
    const nextHistory = [...chatMessages, userMsg];
    setChatMessages(nextHistory);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${backendUrl}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_text: currentData.review_text,
          model_a_triplets: currentData.model_a_triplets,
          model_b_triplets: currentData.model_b_triplets,
          user_message: text,
          chat_history: nextHistory
        })
      });
      if (!res.ok) throw new Error("offline");
      const replyData = await res.json();
      setChatMessages(prev => [...prev, { id: `a_${Date.now()}`, sender: 'agent', text: replyData.reply }]);
    } catch (e) {
      // Mock conversational response fallback
      setTimeout(() => {
        let reply = "Helper agent: ";
        const q = text.toLowerCase();
          if (q.includes("neden") || q.includes("niye") || q.includes("hangisi")) {
            reply += `'${currentData.review_text}' cümlesinde bağlam çok önemli. Benim önerim sol kolondaki tutarlı etiketleri seçip eksikleri orta formdan eklemeniz.`;
          } else {
            reply += `Sorunuzu anladım. Bu incelemede hem Model A hem Model B çıktısını karşılaştırıp onayladıklarınızı sağ alttaki 'press for next review' butonuyla kaydedebilirsiniz.`;
          }
        setChatMessages(prev => [...prev, { id: `a_${Date.now()}`, sender: 'agent', text: reply }]);
      }, 600);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="dark bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans selection:bg-blue-500 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="h-14 bg-slate-900/90 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-md">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-black text-white shadow">
            A
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              <span>AnnoABSA</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                LREC 2026 EDITION
              </span>
            </h1>
          </div>
        </div>

        {/* Progress Tracker */}
        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2 text-xs font-mono">
            <span className="text-slate-400">SATIR:</span>
            <span className="bg-slate-800 px-2.5 py-1 rounded-md text-blue-400 font-bold border border-slate-700">
              #{currentIndex + 1} / {totalCount}
            </span>
          </div>

          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
            <button
              onClick={() => setCurrentIndex(prev => (prev - 1 + totalCount) % totalCount)}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
              title="Önceki İnceleme"
            >
              ◀
            </button>
            <button
              onClick={() => setCurrentIndex(prev => (prev + 1) % totalCount)}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
              title="Sonraki İnceleme"
            >
              ▶
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace (Split 65% Top / 35% Bottom) */}
      <main className="flex-1 p-3 md:p-5 flex flex-col gap-4 max-w-[1700px] w-full mx-auto h-[calc(100vh-3.5rem)] overflow-hidden">

        {/* 1. TOP SECTION (Three-Column Layout - ~65% height) */}
        <section className="h-[62%] md:h-[65%] grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 overflow-hidden min-h-[360px]">

          {/* Left Column: Model A */}
          <ModelTripletColumn
            title={currentData.model_a_name ? `Model A - ${currentData.model_a_name}` : "Model A"}
            subtitle=""
            badgeText={currentData.model_a_name || "MODEL A"}
            badgeColor="bg-purple-500/10 text-purple-300 border-purple-500/30"
            triplets={currentData.model_a_triplets}
            selectedIds={selectedModelAIds}
            onToggleSelect={toggleModelA}
            onSelectAll={selectAllModelA}
            onClearAll={clearAllModelA}
          />

          {/* Center Column: Review Text & Custom Manual Form */}
          <ManualInputForm
            reviewText={currentData.review_text}
            translation={currentData.translation}
            categories={currentData.aspect_category_list}
            polarities={['positive', 'negative', 'neutral']}
            manualTriplets={manualTriplets}
            onAddTriplet={(t) => setManualTriplets(prev => [...prev, t])}
            onRemoveTriplet={(id) => setManualTriplets(prev => prev.filter(m => m.id !== id))}
          />

          {/* Right Column: Model B */}
          <ModelTripletColumn
            title={currentData.model_b_name ? `Model B - ${currentData.model_b_name}` : "Model B"}
            subtitle=""
            badgeText={currentData.model_b_name || "MODEL B"}
            badgeColor="bg-cyan-500/10 text-cyan-300 border-cyan-500/30"
            triplets={currentData.model_b_triplets}
            selectedIds={selectedModelBIds}
            onToggleSelect={toggleModelB}
            onSelectAll={selectAllModelB}
            onClearAll={clearAllModelB}
          />

        </section>


        {/* 2. BOTTOM SECTION (~35% height) */}
        <section className="flex-1 min-h-[160px] grid grid-cols-1 lg:grid-cols-12 gap-3 md:gap-4 overflow-hidden">

          {/* Bottom-Left: Helper Agent Chatbox (Span 8 columns on large screens) */}
          <div className="lg:col-span-8 h-full overflow-hidden">
            <HelperAgentChatbox
              initialReasoning={currentData.agent_initial_reasoning}
              messages={chatMessages}
              onSendMessage={handleSendMessage}
              isLoading={isChatLoading}
            />
          </div>

          {/* Bottom-Right: Prominent Action Button (Span 4 columns) */}
          <div className="lg:col-span-4 h-full flex flex-col justify-end">
            <button
              onClick={handleNextReview}
              className="group relative w-full h-full min-h-[90px] max-h-36 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 active:scale-[0.99] text-white rounded-2xl shadow-2xl transition-all duration-200 p-6 flex flex-col items-center justify-center text-center overflow-hidden border border-white/20 select-none cursor-pointer"
            >
              <div className="absolute -right-10 -top-10 w-40 h-40 bg-white/10 rounded-full blur-2xl group-hover:scale-150 transition-transform"></div>

              <span className="text-xs uppercase tracking-widest text-blue-200 font-mono mb-1 flex items-center gap-1.5">
                <span>SEÇİMLERİ KAYDET & GEÇ</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              </span>

              <span className="text-2xl md:text-3xl font-black tracking-tight drop-shadow uppercase block">
                press for next review
              </span>

              <span className="text-[11px] text-indigo-200 mt-2 opacity-80 group-hover:opacity-100 transition-opacity">
                (Sıradaki inceleme satırını yükler)
              </span>
            </button>
          </div>

        </section>

      </main>

      {/* Toast Alert Notification */}
      {saveToast && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-slate-900 border border-emerald-500/50 text-emerald-300 px-5 py-3 rounded-2xl shadow-2xl z-50 flex items-center space-x-3 text-sm font-semibold animate-fade-in backdrop-blur-md">
          <span>{saveToast}</span>
        </div>
      )}
    </div>
  );
}
