import { useState, useCallback, useRef } from 'react';
import { TripletItem } from '../types';
import { AiSuggestionItem } from '../components/AISuggestions';

export interface AIPredictionState {
  aiSuggestions: AiSuggestionItem[];
  liveModelATriplets: TripletItem[];
  liveModelBTriplets: TripletItem[];
  isAIPredicting: boolean;
  isModelAPredicting: boolean;
  isModelBPredicting: boolean;
  aiTriggeredForIndex: boolean;
}

export interface AIPredictionActions {
  fetchAIPrediction: (currentIndex: number) => Promise<void>;
  fetchLivePrediction: (role: 'model_a' | 'model_b', currentIndex: number) => Promise<void>;
  acceptSuggestion: (item: AiSuggestionItem) => TripletItem | null;
  rejectSuggestion: (index: number) => void;
  abortAIPrediction: () => void;
  resetForNewIndex: () => void;
  setAiTriggeredForIndex: (val: boolean) => void;
  setAiSuggestions: (suggestions: AiSuggestionItem[]) => void;
  resetLivePredictions: () => void;
}

export function useAIPrediction(
  backendUrl: string,
  onSaveToast?: (msg: string | null) => void,
  onAcceptTriplet?: (triplet: TripletItem) => void,
): [AIPredictionState, AIPredictionActions] {
  const [aiSuggestions, setAiSuggestions] = useState<AiSuggestionItem[]>([]);
  const [isAIPredicting, setIsAIPredicting] = useState(false);
  const [aiTriggeredForIndex, setAiTriggeredForIndex] = useState(false);
  const [liveModelATriplets, setLiveModelATriplets] = useState<TripletItem[]>([]);
  const [liveModelBTriplets, setLiveModelBTriplets] = useState<TripletItem[]>([]);
  const [isModelAPredicting, setIsModelAPredicting] = useState(false);
  const [isModelBPredicting, setIsModelBPredicting] = useState(false);

  const aiAbortRef = useRef<AbortController | null>(null);

  const showToast = useCallback((msg: string | null) => {
    onSaveToast?.(msg);
  }, [onSaveToast]);

  const abortAIPrediction = useCallback(() => {
    if (aiAbortRef.current) {
      aiAbortRef.current.abort();
      aiAbortRef.current = null;
    }
    setIsAIPredicting(false);
  }, []);

  const fetchAIPrediction = useCallback(async (currentIndex: number) => {
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
  }, [backendUrl, abortAIPrediction]);

  const fetchLivePrediction = useCallback(async (role: 'model_a' | 'model_b', currentIndex: number) => {
    const setter = role === 'model_a' ? setLiveModelATriplets : setLiveModelBTriplets;
    const loader = role === 'model_a' ? setIsModelAPredicting : setIsModelBPredicting;

    loader(true);
    try {
      const res = await fetch(`${backendUrl}/live_prediction/${currentIndex}?role=${role}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Bilinmeyen hata' }));
        showToast(`${role}: ${err.detail || 'Hata'}`);
        setTimeout(() => showToast(null), 3000);
        return;
      }
      const predictions: TripletItem[] = await res.json();
      setter(predictions);
      showToast(`${role} tamamlandı (${predictions.length} etiket)`);
      setTimeout(() => showToast(null), 2500);
    } catch (e) {
      showToast(`${role}: Sunucu hatası`);
      setTimeout(() => showToast(null), 3000);
    } finally {
      loader(false);
    }
  }, [backendUrl, showToast]);

  const acceptSuggestion = useCallback((item: AiSuggestionItem): TripletItem | null => {
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
    onAcceptTriplet?.(triplet);
    return triplet;
  }, [onAcceptTriplet]);

  const rejectSuggestion = useCallback((index: number) => {
    setAiSuggestions(p => p.filter((_, i) => i !== index));
  }, []);

  const resetForNewIndex = useCallback(() => {
    setAiSuggestions([]);
    setAiTriggeredForIndex(false);
    abortAIPrediction();
  }, [abortAIPrediction]);

  const resetLivePredictions = useCallback(() => {
    setLiveModelATriplets([]);
    setLiveModelBTriplets([]);
  }, []);

  const state: AIPredictionState = {
    aiSuggestions, liveModelATriplets, liveModelBTriplets,
    isAIPredicting, isModelAPredicting, isModelBPredicting,
    aiTriggeredForIndex,
  };
  const actions: AIPredictionActions = {
    fetchAIPrediction, fetchLivePrediction, acceptSuggestion, rejectSuggestion,
    abortAIPrediction, resetForNewIndex, setAiTriggeredForIndex, setAiSuggestions,
    resetLivePredictions,
  };

  return [state, actions];
}
