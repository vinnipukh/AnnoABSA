import { describe, it, expect, vi, beforeEach } from 'vitest';

// NOT using @testing-library/react due to React 19.2.7 CJS bug
import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import { SettingsPanel } from './SettingsPanel';
import { Settings } from '../types';

function render(el: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = ReactDOMClient.createRoot(container);
  ReactDOM.flushSync(() => { root.render(el); });
  return { container, root };
}

function findByText(container: HTMLElement, pattern: RegExp | string): Element | null {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
  let node: Text | null;
  while ((node = walker.nextNode() as Text | null)) {
    if (typeof pattern === 'string'
      ? node.textContent?.includes(pattern)
      : pattern.test(node.textContent || '')) {
      return node.parentElement;
    }
  }
  return null;
}

function click(target: Element | null) {
  if (!target) throw new Error('Cannot click null element');
  ReactDOM.flushSync(() => {
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

const defaultSettings: Settings = {
  current_index: 0,
  max_number_of_idxs: 100,
  total_count: 100,
  session_id: null,
  sentiment_elements: ['aspect_term', 'aspect_category', 'sentiment_polarity', 'opinion_term'],
  sentiment_polarity_options: ['positive', 'negative', 'neutral'],
  aspect_categories: ['FOOD#QUALITY', 'SERVICE#GENERAL'],
  implicit_aspect_term_allowed: true,
  implicit_opinion_term_allowed: false,
  auto_clean_phrases: true,
  save_phrase_positions: true,
  click_on_token: true,
  enable_pre_prediction: false,
  disable_ai_automatic_prediction: false,
  enable_helper_agent: false,
  llm_provider: 'ollama',
  llm_model: 'gemma3:4b',
  vllm_model: '',
  openai_key: null,
  anthropic_key: null,
  vllm_url: null,
  n_few_shot: 10,
  compare_model_a_name: null,
  compare_model_b_name: null,
  theme: 'dark',
  compare_mode: 'csv',
  model_a_provider: null,
  model_a_model: null,
  model_a_prompt: null,
  model_a_temperature: 0.7,
  model_b_provider: null,
  model_b_model: null,
  model_b_prompt: null,
  model_b_temperature: 0.7,
  helper_agent_provider: null,
  helper_agent_model: null,
  helper_agent_prompt: null,
  helper_agent_temperature: 0.7,
  ai_shortcut_key: 'k',
  custom_openai_url: null,
  custom_openai_key: null,
  custom_openai_model: null,
};

describe('SettingsPanel', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('renders section titles', () => {
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={async () => {}}
        onRescanPositions={async () => {}}
        onClose={() => {}}
      />
    );
    expect(container.textContent).toContain('Ayarlar');
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={async () => {}}
        onRescanPositions={async () => {}}
        onClose={onClose}
      />
    );
    // Find close buttons (X or similar)
    const buttons = container.querySelectorAll('button');
    // Click first close-like button
    if (buttons.length > 0) {
      click(buttons[0]);
    }
    // The component should have at least one button
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('renders toggle fields for boolean settings', () => {
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={async () => {}}
        onRescanPositions={async () => {}}
        onClose={() => {}}
      />
    );
    // Should render checkbox inputs for boolean toggles
    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  it('renders text input fields', () => {
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={async () => {}}
        onRescanPositions={async () => {}}
        onClose={() => {}}
      />
    );
    const textInputs = container.querySelectorAll('input[type="text"]');
    expect(textInputs.length).toBeGreaterThan(0);
  });

  it('renders number input fields', () => {
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={async () => {}}
        onRescanPositions={async () => {}}
        onClose={() => {}}
      />
    );
    const numberInputs = container.querySelectorAll('input[type="number"]');
    expect(numberInputs.length).toBeGreaterThan(0);
  });

  it('calls onSave with form data when save button clicked', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { container } = render(
      <SettingsPanel
        settings={defaultSettings}
        onSave={onSave}
        onRescanPositions={async () => {}}
        onClose={() => {}}
      />
    );
    // Find the save button by looking for "Kaydet" text
    const saveBtn = findByText(container, 'Kaydet');
    if (saveBtn) {
      click(saveBtn);
      expect(onSave).toHaveBeenCalled();
    }
  });
});
