import { useState, useCallback } from 'react';
import { Settings } from '../types';

const DEFAULT_SETTINGS: Settings = {
  current_index: 0, max_number_of_idxs: 0, total_count: 4,
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
  compare_mode: 'csv',
  model_a_provider: null, model_a_model: null, model_a_prompt: null, model_a_temperature: 0.7,
  model_b_provider: null, model_b_model: null, model_b_prompt: null, model_b_temperature: 0.7,
  helper_agent_provider: null, helper_agent_model: null, helper_agent_prompt: null, helper_agent_temperature: 0.7,
  ai_shortcut_key: 'a',
  custom_openai_url: null, custom_openai_key: null, custom_openai_model: null,
  arrow_key_navigation: true,
};

export interface SettingsState {
  settings: Settings;
  saveToast: string | null;
}

export interface SettingsActions {
  fetchSettings: () => Promise<void>;
  updateSettings: (updates: Record<string, unknown>) => Promise<void>;
  rescanPositions: () => Promise<void>;
  clearSaveToast: () => void;
  setSaveToast: (msg: string | null) => void;
}

export function useSettings(
  backendUrl: string,
  onSettingsChanged?: (settings: Settings) => void
): [SettingsState, SettingsActions] {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saveToast, setSaveToast] = useState<string | null>(null);

  const showToast = useCallback((msg: string | null, duration: number = 2500) => {
    setSaveToast(msg);
    if (msg) {
      setTimeout(() => setSaveToast(null), duration);
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/settings`);
      if (!res.ok) return;
      const s: any = await res.json();
      const newSettings: Settings = {
        ...DEFAULT_SETTINGS,
        current_index: s.current_index ?? 0,
        max_number_of_idxs: s.max_number_of_idxs ?? 0,
        total_count: s.total_count ?? DEFAULT_SETTINGS.total_count,
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
        compare_mode: s.compare_mode ?? 'csv',
        model_a_provider: s.model_a_provider ?? null,
        model_a_model: s.model_a_model ?? null,
        model_a_prompt: s.model_a_prompt ?? null,
        model_a_temperature: s.model_a_temperature ?? 0.7,
        model_b_provider: s.model_b_provider ?? null,
        model_b_model: s.model_b_model ?? null,
        model_b_prompt: s.model_b_prompt ?? null,
        model_b_temperature: s.model_b_temperature ?? 0.7,
        helper_agent_provider: s.helper_agent_provider ?? null,
        helper_agent_model: s.helper_agent_model ?? null,
        helper_agent_prompt: s.helper_agent_prompt ?? null,
        helper_agent_temperature: s.helper_agent_temperature ?? 0.7,
        ai_shortcut_key: s.ai_shortcut_key ?? 'a',
        custom_openai_url: s.custom_openai_url ?? null,
        custom_openai_key: s.custom_openai_key ?? null,
        custom_openai_model: s.custom_openai_model ?? null,
      };
      setSettings(newSettings);
      onSettingsChanged?.(newSettings);
    } catch (_) {
      // silently fail
    }
  }, [backendUrl, onSettingsChanged]);

  const updateSettings = useCallback(async (updates: Record<string, unknown>) => {
    try {
      const res = await fetch(`${backendUrl}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error('PATCH /settings failed');
      setSettings(prev => ({ ...prev, ...updates }));
      showToast('✅ Ayarlar kaydedildi');
    } catch (_) {
      showToast('❌ Ayarlar kaydedilemedi');
    }
  }, [backendUrl, showToast]);

  const rescanPositions = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/auto-add-positions`, { method: 'POST' });
      if (!res.ok) throw new Error('auto-add-positions failed');
      showToast('✅ Pozisyonlar yeniden tarandı');
    } catch (_) {
      showToast('❌ Pozisyon taraması başarısız');
    }
  }, [backendUrl, showToast]);

  const clearSaveToast = useCallback(() => setSaveToast(null), []);

  const state: SettingsState = { settings, saveToast };
  const actions: SettingsActions = {
    fetchSettings, updateSettings, rescanPositions, clearSaveToast, setSaveToast: showToast,
  };

  return [state, actions];
}
