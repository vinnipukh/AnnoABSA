// Type definitions for AnnoABSA

export interface TripletItem {
  id: string;
  aspect_term: string;
  aspect_category: string;
  sentiment_polarity: 'positive' | 'negative' | 'neutral' | string;
  opinion_term?: string;
  at_start?: number | null;
  at_end?: number | null;
  ot_start?: number | null;
  ot_end?: number | null;
  isSelected?: boolean;
}

/** AspectItem used by phraseColoring.tsx for highlighted inline annotations */
export interface AspectItem {
  aspect_term?: string;
  opinion_term?: string;
  sentiment_polarity?: string;
  aspect_category?: string;
  at_start?: number;
  at_end?: number;
  ot_start?: number;
  ot_end?: number;
  colorIndex?: number;
}

/** ColorClasses placeholder — used by phraseColoring.tsx import, resolved at runtime */
export type ColorClasses = string;

export interface ReviewComparisonData {
  id: number;
  text: string;
  review_text: string;
  translation?: string;
  label?: TripletItem[];
  aspect_category_list: string[];
  model_a_triplets: TripletItem[];
  model_b_triplets: TripletItem[];
  model_a_name?: string;
  model_b_name?: string;
  agent_initial_reasoning: string;
}

export interface ChatMessage {
  id: string;
  sender: 'agent' | 'user';
  text: string;
  timestamp?: string;
}

export interface Settings {
  current_index: number;
  max_number_of_idxs: number;
  total_count: number;
  session_id: string | null;
  sentiment_elements: string[];
  sentiment_polarity_options: string[];
  aspect_categories: string[];
  implicit_aspect_term_allowed: boolean;
  implicit_opinion_term_allowed: boolean;
  auto_clean_phrases: boolean;
  save_phrase_positions: boolean;
  click_on_token: boolean;
  enable_pre_prediction: boolean;
  disable_ai_automatic_prediction: boolean;
  enable_helper_agent: boolean;
  llm_provider: string;
  llm_model: string;
  vllm_model: string;
  openai_key: string | null;
  anthropic_key: string | null;
  vllm_url: string | null;
  n_few_shot: number;
  compare_model_a_name: string | null;
  compare_model_b_name: string | null;
  theme: string;
  // Phase 4: Live Compare Mode
  compare_mode: 'csv' | 'live';
  model_a_provider: string | null;
  model_a_model: string | null;
  model_a_prompt: string | null;
  model_a_temperature: number;
  model_b_provider: string | null;
  model_b_model: string | null;
  model_b_prompt: string | null;
  model_b_temperature: number;
  helper_agent_provider: string | null;
  helper_agent_model: string | null;
  helper_agent_prompt: string | null;
  helper_agent_temperature: number;
  ai_shortcut_key: string;
  // Phase 6: Custom OpenAI-compatible API provider
  custom_openai_url: string | null;
  custom_openai_key: string | null;
  custom_openai_model: string | null;
}

/**
 * AppActions — programmatic action interface for the Helper Agent autopilot.
 *
 * Exposes every core UI action so an agent can drive the app (navigate,
 * switch modes, select/deselect, save, trigger predictions).
 * Passed to HelperAgentChatbox so the agent's structured responses can
 * trigger these actions directly.
 *
 * Extend this interface when adding new interactive features.
 */
export interface AppActions {
  navigateTo: (index: number) => void;
  nextReview: () => void;
  prevReview: () => void;
  switchMode: (mode: 'compare' | 'manual') => void;
  toggleChat: (show?: boolean) => void;
  selectTriplet: (role: 'model_a' | 'model_b', id: string) => void;
  selectAllTriplets: (role: 'model_a' | 'model_b') => void;
  clearAllTriplets: (role: 'model_a' | 'model_b') => void;
  addManualTriplet: (triplet: TripletItem) => void;
  removeManualTriplet: (id: string) => void;
  saveAndNext: () => Promise<void>;
  triggerAIPrediction: () => Promise<void>;
  triggerLivePrediction: (role: 'model_a' | 'model_b') => Promise<void>;
  clearAll: () => void;
  openSettings: () => void;
}
