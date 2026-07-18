import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TripletItem, ReviewComparisonData, ChatMessage, Settings, AppActions } from './types';
import { ModelTripletColumn } from './components/ModelTripletColumn';
import { ManualInputForm } from './components/ManualInputForm';
import { HelperAgentChatbox } from './components/HelperAgentChatbox';
import { PhraseAnnotator } from './components/PhraseAnnotator';
import { AISuggestions } from './components/AISuggestions';
import { SettingsPanel } from './components/SettingsPanel';
import { EditReviewTextModal } from './components/EditReviewTextModal';
import { NlpHelperToolbar } from './components/NlpHelperToolbar';
import { WelcomeOverlay } from './components/WelcomeOverlay';
import { ReviewHeader } from './components/ReviewHeader';
import { FourWayGrid } from './components/FourWayGrid';
import { ResolutionPanel } from './components/ResolutionPanel';
import { useReviewNavigation } from './hooks/useReviewNavigation';
import { useAnnotationState } from './hooks/useAnnotationState';
import { useAIPrediction } from './hooks/useAIPrediction';
import { useSettings } from './hooks/useSettings';
import { useCompareMode } from './hooks/useCompareMode';
import { DEMO_DATA } from './data/demoData';

export default function App() {
  const backendUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';

  // ── Hook 1: Review Navigation ──
  const [navState, navActions] = useReviewNavigation(backendUrl);
  const { currentIndex, currentData, totalCount } = navState;
  const { goToNext, goToPrev, setCurrentIndex, loadReviewRow, saveReview, clearSaveToast, setCurrentData, setTotalCount, setSaveToast: navSetSaveToast } = navActions;

  // ── Hook 2: Annotation State ──
  const [annotState, annotActions] = useAnnotationState();
  const { manualTriplets, selectedIds, selectedModelAIds, selectedModelBIds } = annotState;
  const { addTriplet, removeTriplet, toggleTriplet, selectAllInColumn, clearAllInColumn, clearAll, resetAll, setManualTriplets } = annotActions;

  // ── Hook 3: AI Prediction ──
  const [aiState, aiActions] = useAIPrediction(backendUrl,
    // onSaveToast
    (msg: string | null) => setSaveToast(msg),
    // onAcceptTriplet
    (triplet: TripletItem) => setManualTriplets(p => [...p, triplet]),
  );
  const { aiSuggestions, liveModelATriplets, liveModelBTriplets, isAIPredicting, isModelAPredicting, isModelBPredicting, aiTriggeredForIndex } = aiState;
  const { fetchAIPrediction, fetchLivePrediction, acceptSuggestion, rejectSuggestion, abortAIPrediction, resetForNewIndex, setAiTriggeredForIndex, setAiSuggestions, resetLivePredictions } = aiActions;

  // ── Hook 4: Settings ──
  const [settingsState, settingsActions] = useSettings(backendUrl, (newSettings: Settings) => {
    setEnablePrePrediction(newSettings.enable_pre_prediction === true);
    setDisableAiAutomaticPrediction(newSettings.disable_ai_automatic_prediction === true);
  });
  const { settings, saveToast } = settingsState;
  const { updateSettings, rescanPositions, setSaveToast } = settingsActions;

  // ── Hook 5: Compare Mode ──
  const [modeState, modeActions] = useCompareMode();
  const { mode, compareMode } = modeState;
  const { toggleMode, toggleCompareMode } = modeActions;

  // ── Local state not in hooks ──
  const [enablePrePrediction, setEnablePrePrediction] = useState(false);
  const [disableAiAutomaticPrediction, setDisableAiAutomaticPrediction] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [showFloatingChat, setShowFloatingChat] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [showEditReview, setShowEditReview] = useState(false);
  const [autopilotLoading, setAutopilotLoading] = useState(false);
  const [tierFilter, setTierFilter] = useState<'all' | 2 | 3>('all');
  const [demoMode, setDemoMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // NLP Toolbar state
  const [nlpToolbarSelection, setNlpToolbarSelection] = useState<{
    text: string; sentence: string; rect?: DOMRect
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Effects ──

  // Fetch settings on mount
  useEffect(() => {
    fetchAIPredictionRef.current = fetchAIPrediction;
  });

  // Apply DaisyUI theme to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme);
  }, [settings.theme]);

  // Load review row when index changes
  useEffect(() => {
    const loadRow = async () => {
      resetAll();
      resetForNewIndex();
      resetLivePredictions();
      setChatMessages([]);

      // Demo mode: use local DEMO_DATA instead of fetching from backend
      if (demoMode) {
        setCurrentData(DEMO_DATA[currentIndex % DEMO_DATA.length]);
        setTotalCount(DEMO_DATA.length);
        return;
      }

      // Load from backend
      try {
        const res = await fetch(`${backendUrl}/data/${currentIndex}`);
        if (res.ok) {
          const data: ReviewComparisonData = await res.json();
          setCurrentData(data);
          return;
        }
        // Backend responded but has no data — auto-start demo
        setDemoMode(true);
      } catch {
        // Backend unavailable — auto-start demo mode
        setDemoMode(true);
      }
    };
    loadRow();
  }, [currentIndex, demoMode]);

  // Auto-trigger AI prediction
  useEffect(() => {
    const shouldAutoTrigger =
      enablePrePrediction &&
      !disableAiAutomaticPrediction &&
      manualTriplets.length === 0 &&
      !aiTriggeredForIndex &&
      !isAIPredicting;
    if (shouldAutoTrigger) {
      setAiTriggeredForIndex(true);
      fetchAIPrediction(currentIndex);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, enablePrePrediction, disableAiAutomaticPrediction, manualTriplets.length, aiTriggeredForIndex]);

  // ── Tier filter helper ──

  const getReviewTier = useCallback((data: ReviewComparisonData): 1 | 2 | 3 | null => {
    const vote = data.majority_vote ?? 0;
    if (vote >= 2) {
      const origLabel = (data as any).original_label;
      const majLabel = (data as any).majority_label;
      if (majLabel === origLabel) return 1;
      return 2;
    }
    if (vote === 1) return 3;
    return null;
  }, []);

  const findNextFilteredIndex = useCallback(async (direction: 1 | -1): Promise<number | null> => {
    if (tierFilter === 'all') return currentIndex + direction;
    let candidate = currentIndex + direction;
    let iterations = 0;
    while (candidate >= 0 && candidate < totalCount && iterations < 50) {
      try {
        let tier: number | null = null;
        if (demoMode) {
          const d = DEMO_DATA[candidate % DEMO_DATA.length];
          tier = getReviewTier(d);
        } else {
          const res = await fetch(`${backendUrl}/data/${candidate}`);
          if (res.ok) {
            const data: ReviewComparisonData = await res.json();
            tier = getReviewTier(data);
          }
        }
        if (tier === tierFilter) return candidate;
      } catch {
        // skip indices that fail to load
      }
      candidate += direction;
      iterations++;
    }
    return null;
  }, [backendUrl, currentIndex, tierFilter, totalCount, getReviewTier, demoMode]);

  // ── Navigation handlers ──

  const handleNextReview = async () => {
    abortAIPrediction();
    setAiSuggestions([]);
    setAiTriggeredForIndex(false);
    const approved: any[] = [];
    const columnKeys = ['model_a', 'model_b', 'gt', 'gemma', 'qwen', 'gpt'] as const;
    const colDataMap: Record<string, TripletItem[] | undefined> = {
      model_a: currentData.model_a_triplets,
      model_b: currentData.model_b_triplets,
      gt: currentData.gt_triplets,
      gemma: currentData.gemma_triplets,
      qwen: currentData.qwen_triplets,
      gpt: currentData.gpt_triplets,
    };
    for (const key of columnKeys) {
      const colSet = selectedIds[key] || new Set();
      (colDataMap[key] || []).forEach(t => { if (colSet.has(t.id)) approved.push(t); });
    }
    manualTriplets.forEach(t => approved.push(t));
    await saveReview(approved);
    setSaveToast(`İnceleme #${currentIndex + 1} kaydedildi (${approved.length} etiket).`);
    setTimeout(() => setSaveToast(null), 2500);
    if (tierFilter === 'all') {
      goToNext();
    } else {
      const nextIdx = await findNextFilteredIndex(1);
      if (nextIdx !== null) {
        setCurrentIndex(nextIdx);
      } else {
        setSaveToast('Bu filtrede daha fazla inceleme yok');
        setTimeout(() => setSaveToast(null), 3000);
      }
    }
  };

  const handlePrevReview = async () => {
    abortAIPrediction();
    setAiSuggestions([]);
    setAiTriggeredForIndex(false);
    // Save current review before navigating
    const approved: any[] = [];
    const columnKeys = ['model_a', 'model_b', 'gt', 'gemma', 'qwen', 'gpt'] as const;
    const colDataMap: Record<string, TripletItem[] | undefined> = {
      model_a: currentData.model_a_triplets,
      model_b: currentData.model_b_triplets,
      gt: currentData.gt_triplets,
      gemma: currentData.gemma_triplets,
      qwen: currentData.qwen_triplets,
      gpt: currentData.gpt_triplets,
    };
    for (const key of columnKeys) {
      const colSet = selectedIds[key] || new Set();
      (colDataMap[key] || []).forEach(t => { if (colSet.has(t.id)) approved.push(t); });
    }
    manualTriplets.forEach(t => approved.push(t));
    if (approved.length > 0) {
      await saveReview(approved);
      setSaveToast(`İnceleme #${currentIndex + 1} kaydedildi (${approved.length} etiket).`);
      setTimeout(() => setSaveToast(null), 2500);
    }
    if (tierFilter === 'all') {
      goToPrev();
    } else {
      const prevIdx = await findNextFilteredIndex(-1);
      if (prevIdx !== null) {
        setCurrentIndex(prevIdx);
      } else {
        setSaveToast('Bu filtrede daha fazla inceleme yok');
        setTimeout(() => setSaveToast(null), 3000);
      }
    }
  };

  // ── Save-only (no advance) ──

  const handleSaveNoAdvance = useCallback(async () => {
    if (demoMode) {
      setSaveToast('Yüklemediğiniz veriyi kaydedemezsiniz');
      setTimeout(() => setSaveToast(null), 3000);
      return;
    }
    if (isSaving) return;
    setIsSaving(true);
    const approved: any[] = [];
    const columnKeys = ['model_a', 'model_b', 'gt', 'gemma', 'qwen', 'gpt'] as const;
    const colDataMap: Record<string, TripletItem[] | undefined> = {
      model_a: currentData.model_a_triplets,
      model_b: currentData.model_b_triplets,
      gt: currentData.gt_triplets,
      gemma: currentData.gemma_triplets,
      qwen: currentData.qwen_triplets,
      gpt: currentData.gpt_triplets,
    };
    for (const key of columnKeys) {
      const colSet = selectedIds[key] || new Set();
      (colDataMap[key] || []).forEach(t => { if (colSet.has(t.id)) approved.push(t); });
    }
    manualTriplets.forEach(t => approved.push(t));
    try {
      await saveReview(approved);
      setSaveToast(`İnceleme #${currentIndex + 1} kaydedildi (${approved.length} etiket).`);
      setTimeout(() => setSaveToast(null), 2500);
    } catch (e) {
      setSaveToast('Kayıt başarısız');
      setTimeout(() => setSaveToast(null), 4000);
    } finally {
      setIsSaving(false);
    }
  }, [currentData, selectedIds, manualTriplets, saveReview, currentIndex, isSaving, demoMode]);

  // ── Arrow key navigation ──

  useEffect(() => {
    if (!settings.arrow_key_navigation) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        e.preventDefault();
        if (e.key === 'ArrowLeft') handlePrevReview();
        else handleNextReview();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [settings.arrow_key_navigation, handleNextReview, handlePrevReview]);

  // ── Per-review ML Prediction ──

  const handlePredictReview = useCallback(async () => {
    if (autopilotLoading) return;
    setAutopilotLoading(true);
    try {
      // Train on labeled data, predict for current review
      const res = await fetch(`${backendUrl}/learning/predict/${currentIndex}`);
      if (!res.ok) {
        if (res.status === 400) {
          const err = await res.json().catch(() => ({ detail: '' }));
          setSaveToast(err.detail || 'Yetersiz etiketlenmis inceleme');
        } else {
          setSaveToast('Tahmin alinamadi');
        }
        setTimeout(() => setSaveToast(null), 3000);
        return;
      }
      const predictions = await res.json();
      if (!predictions || predictions.length === 0) {
        setSaveToast('Guvenli tahmin bulunamadi');
        setTimeout(() => setSaveToast(null), 3000);
        return;
      }

      // Match predictions to existing triplets in the 4-way grid columns
      let selected = 0;
      const columns: { key: string; triplets: TripletItem[] }[] = [
        { key: 'gt', triplets: currentData.gt_triplets || [] },
        { key: 'gemma', triplets: currentData.gemma_triplets || [] },
        { key: 'qwen', triplets: currentData.qwen_triplets || [] },
        { key: 'gpt', triplets: currentData.gpt_triplets || [] },
      ];

      for (const pred of predictions) {
        const targetCat = pred.aspect_category;
        const targetPol = pred.sentiment_polarity;
        for (const col of columns) {
          for (const t of col.triplets) {
            if (t.aspect_category === targetCat && t.sentiment_polarity === targetPol) {
              toggleTriplet(col.key, t.id);
              selected++;
            }
          }
        }
      }

      if (selected > 0) {
        setSaveToast(`${selected} etiket secildi — kaydetmek icin "Kaydet & Gec" kullanin`);
      } else {
        setSaveToast('Eslesen etiket bulunamadi — manuel secim yapin');
      }
      setTimeout(() => setSaveToast(null), 3500);
    } catch {
      setSaveToast('Tahmin alinamadi — sunucuya baglanilamiyor');
      setTimeout(() => setSaveToast(null), 3000);
    } finally {
      setAutopilotLoading(false);
    }
  }, [backendUrl, currentIndex, autopilotLoading, currentData, toggleTriplet]);

  // ── Batch Autopilot (Plan 7.5) ──

  const handleRunAutopilot = useCallback(async () => {
    if (autopilotLoading) return;
    setAutopilotLoading(true);
    const count = 10;
    try {
      const res = await fetch(`${backendUrl}/learning/autopilot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count, confidence_threshold: 0.5 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '' }));
        setSaveToast(err.detail || 'Otomatik etiketleme basarisiz');
        setTimeout(() => setSaveToast(null), 3000);
        return;
      }
      const data = await res.json();
      if (data.annotated > 0) {
        setSaveToast(`${data.annotated} inceleme etiketlendi (${data.total_unlabeled} kaldi)`);
        // Reload current review data
        loadReviewRow(currentIndex);
      } else {
        setSaveToast(data.message || 'Etiketlenecek inceleme bulunamadi');
      }
      setTimeout(() => setSaveToast(null), 3500);
    } catch {
      setSaveToast('Otomatik etiketleme basarisiz — sunucuya baglanilamiyor');
      setTimeout(() => setSaveToast(null), 3000);
    } finally {
      setAutopilotLoading(false);
    }
  }, [backendUrl, currentIndex, autopilotLoading, loadReviewRow]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${backendUrl}/upload-data`, { method: 'POST', body: formData });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.total_count) setTotalCount(data.total_count);
      setCurrentIndex(0);
      setDemoMode(false);
      setSaveToast(`${data.message}`);
      setTimeout(() => setSaveToast(null), 3000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'bilinmeyen hata';
      setSaveToast(`Yükleme başarısız: ${msg}`);
      setTimeout(() => setSaveToast(null), 5000);
    }
    e.target.value = '';
  };

  // ── Chat handlers ──

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

  // ── NLP Toolbar selection callback ──

  const handleNlpSelectionChange = useCallback((text: string, rect?: DOMRect) => {
    if (text) {
      setNlpToolbarSelection({ text, sentence: currentData.review_text, rect });
    } else {
      setNlpToolbarSelection(null);
    }
  }, [currentData.review_text]);

  // ── Review text update ──

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
      setSaveToast('İnceleme metni güncellendi');
      setTimeout(() => setSaveToast(null), 2500);
    } catch (_) {
      setSaveToast('Metin güncellenemedi');
      setTimeout(() => setSaveToast(null), 2500);
    }
  };

  // ── Keyboard shortcuts ──

  // Keep refs for use in event handlers (avoids stale closures)
  const fetchAIPredictionRef = useRef(fetchAIPrediction);
  fetchAIPredictionRef.current = fetchAIPrediction;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const shortcutKey = (settings.ai_shortcut_key || 'a').toLowerCase();
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key.toLowerCase() === shortcutKey)) {
        e.preventDefault();
        if (enablePrePrediction && !isAIPredicting) {
          fetchAIPredictionRef.current(currentIndex);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enablePrePrediction, isAIPredicting, settings.ai_shortcut_key, currentIndex]);

  // ── Autopilot action registry ──
  // Exposes every core action so the Helper Agent can drive the app programmatically.

  const appActions = React.useMemo<AppActions>(() => ({
    navigateTo: (index: number) => setCurrentIndex(index),
    nextReview: goToNext,
    prevReview: handlePrevReview,
    switchMode: (m: 'compare' | 'manual') => toggleMode(m),
    toggleChat: (show?: boolean) => setShowFloatingChat(p => show ?? !p),
    selectTriplet: (role, id) => toggleTriplet(role, id),
    selectAllTriplets: (role) => {
      const ids = role === 'model_a' ? (currentData.model_a_triplets || [])
        : role === 'model_b' ? (currentData.model_b_triplets || [])
        : role === 'gt' ? (currentData.gt_triplets || [])
        : role === 'gemma' ? (currentData.gemma_triplets || [])
        : role === 'qwen' ? (currentData.qwen_triplets || [])
        : role === 'gpt' ? (currentData.gpt_triplets || [])
        : [];
      selectAllInColumn(role, ids);
    },
    clearAllTriplets: (role) => clearAllInColumn(role),
    addManualTriplet: (triplet) => setManualTriplets(p => [...p, triplet]),
    addTriplet: (term, category, polarity) => {
      const triplet: TripletItem = {
        id: `auto_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        aspect_term: term,
        aspect_category: category,
        sentiment_polarity: polarity,
      };
      addTriplet(triplet);
    },
    removeManualTriplet: (id) => setManualTriplets(p => p.filter(m => m.id !== id)),
    saveAndNext: handleNextReview,
    triggerAIPrediction: () => fetchAIPrediction(currentIndex),
    triggerLivePrediction: (role) => fetchLivePrediction(role, currentIndex),
    clearAll: () => { setManualTriplets([]); clearAll(); },
    openSettings: () => setShowSettings(true),
    annotateAll: handlePredictReview,
    runAutopilot: handleRunAutopilot,
  }), [goToNext, goToPrev, toggleMode, toggleTriplet, selectAllInColumn, clearAllInColumn, handleNextReview, handlePrevReview, fetchAIPrediction, fetchLivePrediction, currentIndex, clearAll, handlePredictReview, handleRunAutopilot, currentData.model_a_triplets, currentData.model_b_triplets, currentData.gt_triplets, currentData.gemma_triplets, currentData.qwen_triplets, currentData.gpt_triplets]);

  const tripletCount = mode === 'compare'
    ? (selectedIds.model_a?.size || 0) + (selectedIds.model_b?.size || 0) + (selectedIds.gt?.size || 0) + (selectedIds.gemma?.size || 0) + (selectedIds.qwen?.size || 0) + (selectedIds.gpt?.size || 0) + manualTriplets.length
    : manualTriplets.length;

  // Backward-compat aliases for CSV/Live mode
  const toggleModelA = (id: string) => toggleTriplet('model_a', id);
  const toggleModelB = (id: string) => toggleTriplet('model_b', id);
  const selectAllModelA = () => selectAllInColumn('model_a', currentData.model_a_triplets || []);
  const clearAllModelA = () => clearAllInColumn('model_a');
  const selectAllModelB = () => selectAllInColumn('model_b', currentData.model_b_triplets || []);
  const clearAllModelB = () => clearAllInColumn('model_b');

  return (
    <div className="bg-base-300 text-base-content min-h-screen flex flex-col font-sans selection:bg-primary selection:text-primary-content">
      <header className="h-12 bg-base-200/90 border-b border-base-300 px-4 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shadow-sm">
            <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1L2 15h3l1-3h4l1 3h3L8 1zM7.5 4.5L10 10H5l2.5-5.5z" />
            </svg>
          </div>
          <h1 className="text-sm font-bold text-base-content">AnnoABSA</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-base-300/80 border border-base-300 rounded-lg p-0.5">
            <button onClick={() => toggleMode('compare')}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                mode === 'compare' ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
              }`}>Karşılaştır</button>
            <button onClick={() => toggleMode('manual')}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                mode === 'manual' ? 'bg-warning text-warning-content shadow' : 'text-base-content/60 hover:text-base-content'
              }`}>Manuel</button>
          </div>
          {mode === 'compare' && (
            <div className="flex bg-base-300/80 border border-base-300 rounded-lg p-0.5">
              <button onClick={() => updateSettings({ compare_mode: 'csv' })}
                className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                  settings.compare_mode === 'csv' ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
                }`}>Standard</button>
              <button onClick={() => updateSettings({ compare_mode: '4way' })}
                className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                  settings.compare_mode === '4way' ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
                }`}>4-Yönlü</button>
              <button onClick={() => updateSettings({ compare_mode: 'live' })}
                className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none ${
                  settings.compare_mode === 'live' ? 'bg-primary text-primary-content shadow' : 'text-base-content/60 hover:text-base-content'
                }`}>Canlı</button>
            </div>
          )}
          <select
            className="select select-bordered select-sm min-w-[110px]"
            aria-label="İnceleme filtresi"
            value={tierFilter}
            onChange={e => {
              const val = e.target.value;
              setTierFilter(val === 'all' ? 'all' : (Number(val) as 2 | 3));
            }}
          >
            <option value="all">Tümü</option>
            <option value="2">Tier 2</option>
            <option value="3">Tier 3</option>
          </select>
          <div aria-live="polite" aria-atomic="true" className="text-[10px] font-medium text-base-content/60 min-w-[100px]">
            {tierFilter !== 'all' ? `Tier ${tierFilter} filtreleniyor` : ''}
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
            <button onClick={() => fetchAIPrediction(currentIndex)} disabled={isAIPredicting}
              className={`p-1.5 rounded-lg transition-all border text-xs font-bold ${
                isAIPredicting
                  ? 'bg-primary/20 text-primary border-primary/30 animate-pulse'
                  : aiSuggestions.length > 0
                  ? 'bg-success/20 text-success border-success/30 hover:bg-success/30'
                  : 'bg-base-200 text-base-content/50 border-base-300 hover:text-primary hover:border-primary/40'
              }`}
              title={isAIPredicting ? 'AI tahmin ediyor...' : `AI Önerisi Al (Ctrl+Shift+${(settings.ai_shortcut_key || 'A').toUpperCase()})`}>
              {isAIPredicting ? (
                <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          )}
          <button
            onClick={() => handlePredictReview()}
            disabled={autopilotLoading}
            className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none flex items-center gap-1 ${
              autopilotLoading
                ? 'opacity-50 cursor-not-allowed bg-base-200 text-primary'
                : 'bg-base-200 text-base-content/70 hover:text-primary hover:border-primary/40 border border-base-300'
            }`}
            title="Etiketli verilerle ML modeli egit ve bu inceleme icin tahmin yap"
          >
            {autopilotLoading ? (
              <>
                <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Tahmin Ediliyor...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Tahmin Et
              </>
            )}
          </button>
          <button
            onClick={() => handleRunAutopilot()}
            disabled={autopilotLoading}
            className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all select-none flex items-center gap-1 ${
              autopilotLoading
                ? 'opacity-50 cursor-not-allowed bg-base-200 text-success'
                : 'bg-base-200 text-base-content/70 hover:text-success hover:border-success/40 border border-base-300'
            }`}
            title="Etiketlenmemis tum incelemeleri ML ile otomatik etiketle"
          >
            {autopilotLoading ? (
              <>
                <div className="w-3 h-3 border-2 border-success border-t-transparent rounded-full animate-spin" />
                Etiketleniyor...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Otomatik Etiketle
              </>
            )}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv,.json" onChange={handleFileUpload} className="hidden" />
          <button onClick={() => fileInputRef.current?.click()}
            className="p-1.5 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 hover:text-base-content transition-colors border border-base-300"
            title="CSV/JSON Yükle">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </button>
          <button
            onClick={async () => {
              const res = await fetch(`${backendUrl}/data/export-4way`);
              if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Hata' }));
                setSaveToast(err.detail || 'Dışa aktarma başarısız');
                setTimeout(() => setSaveToast(null), 3000);
                return;
              }
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = 'export-4way.csv'; a.click();
              URL.revokeObjectURL(url);
            }}
            className="p-1.5 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 hover:text-base-content transition-colors border border-base-300"
            aria-label="Dışa Aktar"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <span className="text-base-content/50">Satır:</span>
            <span className="bg-base-200 px-2 py-0.5 rounded text-primary font-bold border border-base-300">#{currentIndex + 1}/{totalCount}</span>
            <button onClick={handlePrevReview}
              className="p-1 rounded hover:bg-base-300 text-base-content/50 hover:text-base-content transition-colors text-xs" title="Önceki">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button onClick={goToNext}
              className="p-1 rounded hover:bg-base-300 text-base-content/50 hover:text-base-content transition-colors text-xs" title="Sonraki">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-3 flex flex-col max-w-[1700px] w-full mx-auto h-[calc(100vh-3rem)] overflow-hidden">
        {!currentData ? (
          <div className="flex-1 flex items-center justify-center text-base-content/40 text-sm">
            Veri yükleniyor...
          </div>
        ) : (
        <section className="flex-1 min-h-0">
          {mode === 'compare' ? (
            settings.compare_mode === '4way' && currentData.gt_triplets ? (
              <div className="h-full flex flex-col gap-3">
                <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                  <ReviewHeader
                    reviewText={currentData.review_text}
                    translation={currentData.translation}
                    onEditReview={() => setShowEditReview(true)}
                    onSelectionChange={handleNlpSelectionChange}
                  />
                  <div className="flex-1 min-h-0">
                    <FourWayGrid
                      gtTriplets={currentData.gt_triplets || []}
                      gemmaTriplets={currentData.gemma_triplets || []}
                      qwenTriplets={currentData.qwen_triplets || []}
                      gptTriplets={currentData.gpt_triplets || []}
                      majorityVote={currentData.majority_vote || 0}
                      selectedIds={selectedIds}
                      onToggleSelect={toggleTriplet}
                      onSelectAll={(col) => selectAllInColumn(col, [])}
                      onClearAll={(col) => clearAllInColumn(col)}
                      csvColumnNames={demoMode ? {
                        gt: 'GT',
                        gemma: 'gemma_triplets',
                        qwen: 'qwen_triplets',
                        gpt: 'gpt_triplets',
                      } : undefined}
                    />
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <ResolutionPanel
                    majorityVote={currentData.majority_vote || 0}
                    majorityLabel={(currentData as any).majority_label || []}
                    gtTriplets={currentData.gt_triplets || []}
                    consensusIntersection={(currentData as any).consensus_intersection || []}
                    originalLlmDiff={(currentData as any).original_llm_diff || ''}
                    categories={currentData.aspect_category_list}
                    polarities={['positive', 'negative', 'neutral']}
                    manualTriplets={manualTriplets}
                    onAddTriplet={t => setManualTriplets(p => [...p, t])}
                    onRemoveTriplet={id => setManualTriplets(p => p.filter(m => m.id !== id))}
                    onAcceptSuggestion={(triplets) => {
                      if (triplets.length === 0) return;
                      triplets.forEach(t => {
                        setManualTriplets(p => [...p, { ...t, isSelected: true }]);
                        toggleTriplet('gt', t.id);
                      });
                      const names = triplets.map(t =>
                        `${t.aspect_term || 'NULL'} → ${t.aspect_category} (${t.sentiment_polarity})`
                      ).join('; ');
                      setSaveToast(`Eklendi: ${names}`);
                      setTimeout(() => setSaveToast(null), 4000);
                    }}
                    onEditTriplets={() => {}}
                  />
                </div>
              </div>
            ) : (
              <div className="h-full grid grid-cols-1 md:grid-cols-3 gap-3">
                {(() => {
                  const isLiveMode = settings.compare_mode === 'live';
                  return (
                    <>
                      <ModelTripletColumn title={currentData.model_a_name ? `Model A - ${currentData.model_a_name}` : "Model A"}
                        subtitle="" badgeText={currentData.model_a_name || "MODEL A"}
                        badgeColor="bg-secondary/10 text-secondary border-secondary/30"
                        triplets={isLiveMode ? liveModelATriplets : currentData.model_a_triplets}
                        selectedIds={selectedModelAIds}
                        onToggleSelect={toggleModelA} onSelectAll={selectAllModelA} onClearAll={clearAllModelA}
                        onRunPrediction={isLiveMode ? () => fetchLivePrediction('model_a', currentIndex) : undefined}
                        isPredicting={isModelAPredicting} />
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
                          <AISuggestions suggestions={aiSuggestions}
                            onAccept={(item) => { acceptSuggestion(item); }}
                            onReject={rejectSuggestion} />
                        )}
                      </div>
                      <ModelTripletColumn title={currentData.model_b_name ? `Model B - ${currentData.model_b_name}` : "Model B"}
                        subtitle="" badgeText={currentData.model_b_name || "MODEL B"}
                        badgeColor="bg-accent/10 text-accent border-accent/30"
                        triplets={isLiveMode ? liveModelBTriplets : currentData.model_b_triplets}
                        selectedIds={selectedModelBIds}
                        onToggleSelect={toggleModelB} onSelectAll={selectAllModelB} onClearAll={clearAllModelB}
                        onRunPrediction={isLiveMode ? () => fetchLivePrediction('model_b', currentIndex) : undefined}
                        isPredicting={isModelBPredicting} />
                    </>
                  );
                })()}
              </div>
            )
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
                <AISuggestions suggestions={aiSuggestions} onAccept={(item) => { acceptSuggestion(item); }} onReject={rejectSuggestion} />
              )}
            </div>
          )}
        </section>)}
      </main>

      {settings.enable_helper_agent && showFloatingChat && (
        <HelperAgentChatbox
          initialReasoning={currentData.agent_initial_reasoning}
          messages={chatMessages}
          onSendMessage={handleSendMessage}
          isLoading={isChatLoading}
          appActions={appActions}
        />
      )}

      <footer className="h-10 bg-base-200/90 border-t border-base-300 px-4 flex items-center justify-between flex-shrink-0 z-20">
        <span className="text-[10px] text-base-content/40 font-mono">
          {tripletCount} etiket seçildi · {mode === 'manual' ? 'Manuel' : 'Karşılaştırma'} modu
        </span>
        <div className="flex items-center gap-2">
          <button onClick={() => { setManualTriplets([]); clearAll(); }}
            className="text-[10px] px-2.5 py-1 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/60 transition-colors border border-base-300 select-none">
            Temizle
          </button>
          <button onClick={handleNextReview}
            className="text-[11px] px-4 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-content font-bold transition-all shadow-sm select-none flex items-center gap-1.5">
            <span>Kaydet & Geç</span>
            <svg className="w-3 h-3 text-primary-content/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </footer>

      {showSettings && (
        <SettingsPanel
          settings={settings}
          onSave={updateSettings}
          onRescanPositions={rescanPositions}
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

      <WelcomeOverlay
        totalCount={totalCount}
        onUpload={() => fileInputRef.current?.click()}
        onStart={() => {}}
      />
    </div>
  );
}

// ── FALLBACK_DATA (kept for offline mode) ──
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

