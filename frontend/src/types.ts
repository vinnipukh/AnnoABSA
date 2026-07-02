// Type definitions for AnnoABSA

export interface TripletItem {
  id: string;
  aspect_term: string;
  aspect_category: string;
  sentiment_polarity: 'positive' | 'negative' | 'neutral' | string;
  isSelected?: boolean;
}

export interface ReviewComparisonData {
  id: number;
  text: string;
  review_text: string;
  translation?: string;
  label?: TripletItem[];
  aspect_category_list: string[];
  deepseek_triplets: TripletItem[];
  qwen_triplets: TripletItem[];
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
}
