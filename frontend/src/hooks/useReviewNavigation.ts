import { useState, useCallback } from 'react';
import { ReviewComparisonData, TripletItem } from '../types';

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

export interface ReviewNavigationState {
  currentIndex: number;
  currentData: ReviewComparisonData;
  totalCount: number;
  isLoading: boolean;
}

export interface ReviewNavigationActions {
  goToNext: () => void;
  goToPrev: () => void;
  setCurrentIndex: (index: number | ((prev: number) => number)) => void;
  loadReviewRow: (index: number) => Promise<void>;
  saveReview: (approved: TripletItem[]) => Promise<void>;
  getSaveToast: () => string | null;
  clearSaveToast: () => void;
  setCurrentData: (data: ReviewComparisonData | ((prev: ReviewComparisonData) => ReviewComparisonData)) => void;
  setTotalCount: (count: number | ((prev: number) => number)) => void;
  setSaveToast: (msg: string | null) => void;
}

export function useReviewNavigation(
  backendUrl: string,
  onBeforeLoadReview?: () => void
): [ReviewNavigationState, ReviewNavigationActions] {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentData, setCurrentData] = useState<ReviewComparisonData>(FALLBACK_DATA[0]);
  const [totalCount, setTotalCount] = useState(FALLBACK_DATA.length);
  const [isLoading, setIsLoading] = useState(false);
  const [saveToast, setSaveToast] = useState<string | null>(null);

  const loadReviewRow = useCallback(async (index: number) => {
    onBeforeLoadReview?.();
    setIsLoading(true);
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
          // Set manualTriplets is handled by the caller via onBeforeLoadReview
          // The caller resets manualTriplets before calling loadReviewRow
        }
      }
    } catch (e) {
      setCurrentData(FALLBACK_DATA[index % FALLBACK_DATA.length]);
    } finally {
      setIsLoading(false);
    }
  }, [backendUrl, onBeforeLoadReview]);

  const saveReview = useCallback(async (approved: TripletItem[]) => {
    try {
      const res = await fetch(`${backendUrl}/review/${currentIndex}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triplets: approved }),
      });
      if (!res.ok) throw new Error('save failed');
    } catch (_) {
      // silently fail
    }
  }, [backendUrl, currentIndex]);

  const goToNext = useCallback(() => {
    setCurrentIndex(p => (p + 1) % totalCount);
  }, [totalCount]);

  const goToPrev = useCallback(() => {
    setCurrentIndex(p => (p - 1 + totalCount) % totalCount);
  }, [totalCount]);

  const clearSaveToast = useCallback(() => setSaveToast(null), []);

  const state: ReviewNavigationState = { currentIndex, currentData, totalCount, isLoading };
  const actions: ReviewNavigationActions = {
    goToNext, goToPrev, setCurrentIndex, loadReviewRow, saveReview,
    getSaveToast: () => saveToast,
    clearSaveToast,
    setCurrentData,
    setTotalCount,
    setSaveToast,
  };

  return [state, actions];
}
