import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TripletItem, ReviewComparisonData, ChatMessage, Settings } from './types';
import { ModelTripletColumn } from './components/ModelTripletColumn';
import { ManualInputForm } from './components/ManualInputForm';
import { HelperAgentChatbox } from './components/HelperAgentChatbox';
import { PhraseAnnotator } from './components/PhraseAnnotator';
import { AISuggestions, AiSuggestionItem } from './components/AISuggestions';
import { SettingsPanel } from './components/SettingsPanel';
import { EditReviewTextModal } from './components/EditReviewTextModal';
import { NlpHelperToolbar } from './components/NlpHelperToolbar';

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

const DEFAULT_SETTINGS: Settings = {
  current_index: 0, max_number_of_idxs: 0, total_count: FALLBACK_DATA.length,
  session_id: null, sentiment_elements: ['aspect_term','aspect_category','sentiment_polarity','opinion_term'],
  sentiment_polarity_options: ['positive','negative','neutral'],
  aspect_categories: ['RESTAURANT#GENERAL','FOOD#QUALITY','SERVICE#GENERAL','AMBIENCE#GENERAL','FOOD#PRICES','FOOD#STYLE_OPTIONS'],
  implicit_aspect_term_allowed: true, implicit_opinion_term_allowed: false,
  auto_clean_phrases: true, save_phrase_positions: true, click_on_token: true,
  enable_pre_prediction: false, disable_ai_automatic_prediction: false,
  enable_helper_agent: true,
  llm_provider: 'ollama', llm_model: 'gemma3:4b', vllm_model: '',
  openai_key: null, anthropic_key: null, vllm_url: null,
  n_few_shot: 10, compare_model_a_name: null, compare_model_b_name: null,
  theme: 'dark',
};

export default function App() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentData, setCurrentData] = useState<ReviewComparisonData>(FALLBACK_DATA[0]);
  const [totalCount, setTotalCount] = useState(FALLBACK_DATA.length);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);

  const [selectedModelAIds, setSelectedModelAIds] = useState<Set<string>>(new Set());
  const [selectedModelBIds, setSelectedModelBIds] = useState<Set<string>>(new Set());
  const [manualTriplets, setManualTriplets] = useState<TripletItem[]>([]);

  const [mode, setMode] = useState<'compare' | 'manual'>('compare');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [showFloatingChat, setShowFloatingChat] = useState(true);
  const [saveToast, setSaveToast] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showEditReview, setShowEditReview] = useState(false);

  // AI Suggestions state
  const [aiSuggestions, setAiSuggestions] = useState<AiSuggestionItem[]>([]);
  const [isAIPredicting, setIsAIPredicting] = useState(false);
  const [aiTriggeredForIndex, setAiTriggeredForIndex] = useState(false);
  const [enablePrePrediction, setEnablePrePrediction] = useState(false);
  const [disableAiAutomaticPrediction, setDisableAiAutomaticPrediction] = useState(false);
  const aiAbortRef = useRef<AbortController | null>(null);

  // NLP Toolbar state
  const [nlpToolbarSelection, setNlpToolbarSelection] = useState<{
    text: string; sentence: string
  } | null>(null);

  const backendUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${backendUrl}/upload-data`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('upload failed');
      const data = await res.json();
      if (data.total_count) setTotalCount(data.total_count);
      setCurrentIndex(0);
      setSaveToast(`✅ ${data.message}`);
      setTimeout(() => setSaveToast(null), 3000);
    } catch (_) {
      setSaveToast('❌ Yükleme başarısız — backend çalışıyor mu?');
      setTimeout(() => setSaveToast(null), 3000);
    }
    e.target.value = '';
  };

  const loadReviewRow = async (index: number) => {
    setSelectedModelAIds(new Set());
    setSelectedModelBIds(new Set());
    setManualTriplets([]);
    setChatMessages([]);
    try {
      const res = await fetch(`${backendUrl}/data/${index}`);
      if (!res.ok) throw new Error("API Offline");
      const data = await res.json();
      setCurrentData(data);
      if (data.label) {
        let parsed: unknown;
        if (typeof data.label === 'string') {
          try { parsed = JSON.parse(data.label); } catch { parsed = null; }
        } else {
          parsed = data.label;
        }
        if (Array.isArray(parsed) && parsed.length > 0) {
          setManualTriplets(parsed as TripletItem[]);
        }
      }
    } catch (e) {
      setCurrentData(FALLBACK_DATA[index % FALLBACK_DATA.length]);
    }
  };

  useEffect(() => {
    fetch(`${backendUrl}/settings`)
      .then(r => r.json())
      .then((s: any) => {
        setSettings({
          current_index: s.current_index ?? 0,
          max_number_of_idxs: s.max_number_of_idxs ?? 0,
          total_count: s.total_count ?? FALLBACK_DATA.length,
          session_id: s.session_id ?? null,
          sentiment_elements: s['sentiment elements'] ?? DEFAULT_SETTINGS.sentiment_elements,
          sentiment_polarity_options: s['sentiment_polarity options'] ?? DEFAULT_SETTINGS.sentiment_polarity_options,
          aspect_categories: s.aspect_categories ?? DEFAULT_SETTINGS.aspect_categories,
          implicit_aspect_term_allowed: s.implicit_aspect_term_allowed ?? true,
          implicit_opinion_term_allowed: s.implicit_opinion_term_allowed ?? false,
          auto_clean_phrases: s.auto_clean_phrases ?? true,
          save_phrase_positions: s.save_phrase_positions ?? true,
          click_on_token: s.click_on_token ?? true,
          enable_pre_prediction: s.enable_pre_prediction ?? false,
          disable_ai_automatic_prediction: s.disable_ai_automatic_prediction ?? false,
          enable_helper_agent: s.enable_helper_agent ?? true,
          llm_provider: s.llm_provider ?? 'ollama',
          llm_model: s.llm_model ?? 'gemma3:4b',
          vllm_model: s.vllm_model ?? '',
          openai_key: s.openai_key ?? null,
          anthropic_key: s.anthropic_key ?? null,
          vllm_url: s.vllm_url ?? null,
          n_few_shot: s.n_few_shot ?? 10,
          compare_model_a_name: s.compare_model_a_name ?? null,
          compare_model_b_name: s.compare_model_b_name ?? null,
          theme: s.theme ?? 'dark',
        });
        setEnablePrePrediction(s.enable_pre_prediction === true);
        setDisableAiAutomaticPrediction(s.disable_ai_automatic_prediction === true);
        if (s.total_count) setTotalCount(s.total_count);
      })
      .catch(() => {});
  }, []);

  // Apply DaisyUI theme to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme);
  }, [settings.theme]);

  useEffect(() => {
    loadReviewRow(currentIndex);
  }, [currentIndex]);

  const toggleModelA = (id: string) => {
    const n = new Set(selectedModelAIds);
    n.has(id) ? n.delete(id) : n.add(id);
    setSelectedModelAIds(n);
  };
  const toggleModelB = (id: string) => {
    const n = new Set(selectedModelBIds);
    n.has(id) ? n.delete(id) : n.add(id);
    setSelectedModelBIds(n);
  };
  const selectAllModelA = () => setSelectedModelAIds(new Set(currentData.model_a_triplets.map(t => t.id)));
  const clearAllModelA = () => setSelectedModelAIds(new Set());
  const selectAllModelB = () => setSelectedModelBIds(new Set(currentData.model_b_triplets.map(t => t.id)));
  const clearAllModelB = () => setSelectedModelBIds(new Set());

  const handleNextReview = async () => {
    abortAIPrediction();
    setAiSuggestions([]);
    setAiTriggeredForIndex(false);
    const approved: any[] = [];
    currentData.model_a_triplets.forEach(t => { if (selectedModelAIds.has(t.id)) approved.push(t); });
    currentData.model_b_triplets.forEach(t => { if (selectedModelBIds.has(t.id)) approved.push(t); });
    manualTriplets.forEach(t => approved.push(t));
    try {
      await fetch(`${backendUrl}/review/${currentIndex}/save`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triplets: approved }),
      });
    } catch (_) {}
    setSaveToast(`✅ İnceleme #${currentIndex + 1} kaydedildi (${approved.length} etiket).`);
    setTimeout(() => setSaveToast(null), 2500);
    setCurrentIndex(p => (p + 1) % totalCount);
  };

  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = { id: `u_${Date.now()}`, sender: 'user', text };
    const nextHistory = [...chatMessages, userMsg];
    setChatMessages(nextHistory);
    setIsChatLoading(true);
    try {
      const res = await fetch(`${backendUrl}/agent/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_text: currentData.review_text, model_a_triplets: currentData.model_a_triplets, model_b_triplets: currentData.model_b_triplets, user_message: text, chat_history: nextHistory }),
      });
      if (!res.ok) throw new Error("offline");
      const d = await res.json();
      setChatMessages(p => [...p, { id: `a_${Date.now()}`, sender: 'agent', text: d.reply }]);
    } catch (_) {
      setTimeout(() => {
        const q = text.toLowerCase();
        let reply = "Helper agent: ";
        if (q.includes("neden") || q.includes("niye") || q.includes("hangisi"))
          reply += `'${currentData.review_text}' cümlesinde bağlam çok önemli. Benim önerim sol kolondaki tutarlı etiketleri seçip eksikleri orta formdan eklemeniz.`;
        else
          reply += `Sorunuzu anladım. Bu incelemede hem Model A hem Model B çıktısını karşılaştırıp onayladıklarınızı sağ alttaki butonla kaydedebilirsiniz.`;
        setChatMessages(p => [...p, { id: `a_${Date.now()}`, sender: 'agent', text: reply }]);
      }, 600);
    } finally { setIsChatLoading(false); }
  };

  // ── AI Suggestions ──

  const abortAIPrediction = () => {
    if (aiAbortRef.current) {
      aiAbortRef.current.abort();
      aiAbortRef.current = null;
    }
    setIsAIPredicting(false);
  };

  const fetchAIPrediction = async () => {
    abortAIPrediction();
    const controller = new AbortController();
    aiAbortRef.current = controller;
    setIsAIPredicting(true);
    try {
      const res = await fetch(`${backendUrl}/ai_prediction/${currentIndex}`, {
        signal: controller.signal,
      });
      const predictions: AiSuggestionItem[] = await res.json();
      if (Array.isArray(predictions)) {
        setAiSuggestions(predictions);
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        // Aborted — expected on rapid navigation
      } else {
        console.error('AI prediction error:', e);
      }
    } finally {
      setIsAIPredicting(false);
      aiAbortRef.current = null;
    }
  };

  const handleAcceptSuggestion = (item: AiSuggestionItem) => {
    const newId = `ai_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const triplet: TripletItem = {
      id: newId,
      aspect_term: item.aspect_term || 'NULL',
      aspect_category: item.aspect_category,
      sentiment_polarity: item.sentiment_polarity || 'neutral',
      opinion_term: item.opinion_term || '',
    };
    if (item.at_start !== undefined && item.at_start !== null) triplet.at_start = item.at_start;
    if (item.at_end !== undefined && item.at_end !== null) triplet.at_end = item.at_end;
    if (item.ot_start !== undefined && item.ot_start !== null) triplet.ot_start = item.ot_start;
    if (item.ot_end !== undefined && item.ot_end !== null) triplet.ot_end = item.ot_end;
    setManualTriplets(p => [...p, triplet]);
  };

  const handleRejectSuggestion = (index: number) => {
    setAiSuggestions(p => p.filter((_, i) => i !== index));
  };

  useEffect(() => {
    setAiSuggestions([]);
    setAiTriggeredForIndex(false);
    abortAIPrediction();
  }, [currentIndex]);

  useEffect(() => {
    const shouldAutoTrigger =
      enablePrePrediction &&
      !disableAiAutomaticPrediction &&
      manualTriplets.length === 0 &&
      !aiTriggeredForIndex &&
      !isAIPredicting;
    if (shouldAutoTrigger) {
      setAiTriggeredForIndex(true);
      fetchAIPrediction();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, enablePrePrediction, disableAiAutomaticPrediction, manualTriplets.length, aiTriggeredForIndex]);

  // ── Settings Panel ──

  const handleSaveSettings = async (updates: Record<string, unknown>) => {
    try {
      const res = await fetch(`${backendUrl}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error('PATCH /settings failed');
      setSettings(prev => ({ ...prev, ...updates }));
      if (typeof updates.enable_pre_prediction === 'boolean') {
        setEnablePrePrediction(updates.enable_pre_prediction);
      }
      if (typeof updates.disable_ai_automatic_prediction === 'boolean') {
        setDisableAiAutomaticPrediction(updates.disable_ai_automatic_prediction);
      }
      setSaveToast('✅ Ayarlar kaydedildi');
      setTimeout(() => setSaveToast(null), 2500);
    } catch (_) {
      setSaveToast('❌ Ayarlar kaydedilemedi');
      setTimeout(() => setSaveToast(null), 2500);
    }
  };

  const handleRescanPositions = async () => {
    try {
      const res = await fetch(`${backendUrl}/auto-add-positions`, { method: 'POST' });
      if (!res.ok) throw new Error('auto-add-positions failed');
      setSaveToast('✅ Pozisyonlar yeniden tarandı');
      setTimeout(() => setSaveToast(null), 2500);
    } catch (_) {
      setSaveToast('❌ Pozisyon taraması başarısız');
      setTimeout(() => setSaveToast(null), 2500);
    }
  };

  // NLP Toolbar selection callback
  const handleNlpSelectionChange = useCallback((text: string, rect?: DOMRect) => {
    if (text) {
      setNlpToolbarSelection({ text, sentence: currentData.review_text, rect });
    } else {
      setNlpToolbarSelection(null);
    }
  }, [currentData.review_text]);

  const handleUpdateReviewText = async (newText: string) => {
    try {
      const res = await fetch(`${backendUrl}/review/${currentIndex}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triplets: [], review_text: newText }),
      });
      if (!res.ok) throw new Error('save failed');
      setCurrentData(prev => ({ ...prev, review_text: newText, text: newText }));
      setShowEditReview(false);
      setSaveToast('✅ İnceleme metni güncellendi');
      setTimeout(() => setSaveToast(null), 2500);
    } catch (_) {
      setSaveToast('❌ Metin güncellenemedi');
      setTimeout(() => setSaveToast(null), 2500);
    }
  };

  const tripletCount = mode === 'compare'
    ? selectedModelAIds.size + selectedModelBIds.size + manualTriplets.length
    : manualTriplets.length;

  return (
    <div className="bg-base-300 text-base-content min-h-screen flex flex-col font-sans selection:bg-primary selection:text-primary-content">
      <header className="h-12 bg-base-200/90 border-b border-base-300 px-4 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center font-black text-primary-content shadow text-sm">A</div>
          <h1 className="text-sm font-bold text-base-content">AnnoABSA</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-base-300/80 border border-base-300 rounded-lg p-0.5">
            <button onClick={() => setMode('compare')}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                mode === 'compare' ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
              }`}>Karşılaştır</button>
            <button onClick={() => setMode('manual')}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                mode === 'manual' ? 'bg-warning text-warning-content shadow' : 'text-base-content/60 hover:text-base-content'
              }`}>Manuel</button>
          </div>
          <button onClick={() => setShowSettings(true)}
            className="p-1.5 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 hover:text-base-content transition-colors border border-base-300"
            title="Ayarlar">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          {settings.enable_helper_agent && (
          <button onClick={() => setShowFloatingChat(p => !p)}
            className={`p-1.5 rounded-lg transition-all border ${
              showFloatingChat ? 'bg-primary/20 text-primary border-primary/30' : 'bg-base-200 text-base-content/50 border-base-300 hover:text-base-content'
            }`} title={showFloatingChat ? 'Sohbeti Kapat' : 'Sohbeti Aç'}>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </button>
          )}
          {enablePrePrediction && (
            <button onClick={fetchAIPrediction} disabled={isAIPredicting}
              className={`p-1.5 rounded-lg transition-all border text-xs font-bold ${
                isAIPredicting
                  ? 'bg-primary/20 text-primary border-primary/30 animate-pulse'
                  : aiSuggestions.length > 0
                  ? 'bg-success/20 text-success border-success/30 hover:bg-success/30'
                  : 'bg-base-200 text-base-content/50 border-base-300 hover:text-primary hover:border-primary/40'
              }`}
              title={isAIPredicting ? 'AI tahmin ediyor...' : 'AI Önerisi Al'}>
              {isAIPredicting ? (
                <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          )}
          <input ref={fileInputRef} type="file" accept=".csv,.json" onChange={handleFileUpload} className="hidden" />
          <button onClick={() => fileInputRef.current?.click()}
            className="p-1.5 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 hover:text-base-content transition-colors border border-base-300"
            title="CSV/JSON Yükle">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </button>
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <span className="text-base-content/50">Satır:</span>
            <span className="bg-base-200 px-2 py-0.5 rounded text-primary font-bold border border-base-300">#{currentIndex + 1}/{totalCount}</span>
            <button onClick={() => setCurrentIndex(p => (p - 1 + totalCount) % totalCount)}
              className="p-1 rounded hover:bg-base-300 text-base-content/50 hover:text-base-content transition-colors text-xs" title="Önceki">◀</button>
            <button onClick={() => setCurrentIndex(p => (p + 1) % totalCount)}
              className="p-1 rounded hover:bg-base-300 text-base-content/50 hover:text-base-content transition-colors text-xs" title="Sonraki">▶</button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-3 flex flex-col max-w-[1700px] w-full mx-auto h-[calc(100vh-3rem)] overflow-hidden">
        <section className="flex-1 min-h-0">
          {mode === 'compare' ? (
            <div className="h-full grid grid-cols-1 md:grid-cols-3 gap-3">
              <ModelTripletColumn title={currentData.model_a_name ? `Model A - ${currentData.model_a_name}` : "Model A"}
                subtitle="" badgeText={currentData.model_a_name || "MODEL A"}
                badgeColor="bg-secondary/10 text-secondary border-secondary/30"
                triplets={currentData.model_a_triplets} selectedIds={selectedModelAIds}
                onToggleSelect={toggleModelA} onSelectAll={selectAllModelA} onClearAll={clearAllModelA} />
              <div className="flex flex-col h-full overflow-hidden">
                <div className="flex-1 min-h-0">
                  <ManualInputForm reviewText={currentData.review_text} translation={currentData.translation}
                    categories={currentData.aspect_category_list} polarities={['positive','negative','neutral']}
                    manualTriplets={manualTriplets}
                    onAddTriplet={t => setManualTriplets(p => [...p, t])}
                    onRemoveTriplet={id => setManualTriplets(p => p.filter(m => m.id !== id))}
                    onEditReview={() => setShowEditReview(true)}
                    clickOnToken={settings.click_on_token}
                    onSelectionChange={handleNlpSelectionChange} />
                </div>
                {aiSuggestions.length > 0 && (
                  <AISuggestions suggestions={aiSuggestions} onAccept={handleAcceptSuggestion} onReject={handleRejectSuggestion} />
                )}
              </div>
              <ModelTripletColumn title={currentData.model_b_name ? `Model B - ${currentData.model_b_name}` : "Model B"}
                subtitle="" badgeText={currentData.model_b_name || "MODEL B"}
                badgeColor="bg-accent/10 text-accent border-accent/30"
                triplets={currentData.model_b_triplets} selectedIds={selectedModelBIds}
                onToggleSelect={toggleModelB} onSelectAll={selectAllModelB} onClearAll={clearAllModelB} />
            </div>
          ) : (
            <div className="h-full flex flex-col overflow-hidden">
              <div className="flex-1 min-h-0">
                <PhraseAnnotator reviewText={currentData.review_text}
                  categories={currentData.aspect_category_list}
                  polarities={settings.sentiment_polarity_options}
                  clickOnToken={settings.click_on_token}
                  implicitAspectAllowed={settings.implicit_aspect_term_allowed}
                  implicitOpinionAllowed={settings.implicit_opinion_term_allowed}
                  autoCleanPhrases={settings.auto_clean_phrases}
                  annotations={manualTriplets}
                  onAddAnnotation={t => setManualTriplets(p => [...p, t])}
                  onRemoveAnnotation={id => setManualTriplets(p => p.filter(m => m.id !== id))}
                  onEditReview={() => setShowEditReview(true)}
                  onSelectionChange={handleNlpSelectionChange} />
              </div>
              {aiSuggestions.length > 0 && (
                <AISuggestions suggestions={aiSuggestions} onAccept={handleAcceptSuggestion} onReject={handleRejectSuggestion} />
              )}
            </div>
          )}
        </section>
      </main>

      {settings.enable_helper_agent && showFloatingChat && (
        <HelperAgentChatbox
          initialReasoning={currentData.agent_initial_reasoning}
          messages={chatMessages}
          onSendMessage={handleSendMessage}
          isLoading={isChatLoading}
        />
      )}

      <footer className="h-10 bg-base-200/90 border-t border-base-300 px-4 flex items-center justify-between flex-shrink-0 z-20">
        <span className="text-[10px] text-base-content/40 font-mono">
          {tripletCount} etiket seçildi · {mode === 'manual' ? 'Manuel' : 'Karşılaştırma'} modu
        </span>
        <div className="flex items-center gap-2">
          <button onClick={() => { setManualTriplets([]); setSelectedModelAIds(new Set()); setSelectedModelBIds(new Set()); }}
            className="text-[10px] px-2.5 py-1 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 transition-colors border border-base-300 select-none">
            Temizle
          </button>
          <button onClick={handleNextReview}
            className="text-[11px] px-4 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-content font-bold transition-all shadow-sm select-none flex items-center gap-1.5">
            <span>Kaydet & Geç</span>
            <span className="text-primary-content/80">▶</span>
          </button>
        </div>
      </footer>

      {showSettings && (
        <SettingsPanel
          settings={settings}
          onSave={handleSaveSettings}
          onRescanPositions={handleRescanPositions}
          onClose={() => setShowSettings(false)}
        />
      )}
      {showEditReview && (
        <EditReviewTextModal
          currentText={currentData.review_text}
          reviewIndex={currentIndex}
          onSave={handleUpdateReviewText}
          onClose={() => setShowEditReview(false)}
        />
      )}
      {saveToast && (
        <div className="fixed bottom-14 left-1/2 -translate-x-1/2 bg-base-100 border border-success/50 text-success px-4 py-2 rounded-xl shadow-2xl z-50 flex items-center text-xs font-semibold backdrop-blur-md">
          {saveToast}
        </div>
      )}

      {/* NLP Helper Toolbar */}
      {nlpToolbarSelection && (
        <NlpHelperToolbar
          selectedText={nlpToolbarSelection.text}
          sentenceText={nlpToolbarSelection.sentence}
          onClose={() => setNlpToolbarSelection(null)}
        />
      )}
    </div>
  );
}
