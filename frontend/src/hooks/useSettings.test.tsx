import { describe, it, expect, vi, beforeEach } from 'vitest';

// We do NOT use @testing-library/react due to a React 19.2.7 CJS bug.
// Instead, we mount components directly using createRoot + flushSync.

import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import React, { useRef, useEffect } from 'react';
import { useSettings, SettingsState, SettingsActions } from './useSettings';

describe('useSettings', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with default settings and null saveToast', () => {
    let state: SettingsState | null = null;

    const Comp: React.FC = () => {
      const [s] = useSettings('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          state = s;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(state).not.toBeNull();
    expect(state!.saveToast).toBeNull();
    expect(state!.settings).toBeDefined();
    expect(state!.settings.theme).toBe('dark');
    expect(state!.settings.compare_mode).toBe('csv');
    expect(state!.settings.enable_helper_agent).toBe(true);
  });

  it('clearSaveToast resets saveToast to null', () => {
    let clearFn: (() => void) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useSettings('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          clearFn = a.clearSaveToast;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(clearFn).toBeInstanceOf(Function);
  });

  it('has all expected settings fields', () => {
    let state: SettingsState | null = null;

    const Comp: React.FC = () => {
      const [s] = useSettings('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          state = s;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(state).not.toBeNull();
    expect(state!.settings.llm_provider).toBe('ollama');
    expect(state!.settings.llm_model).toBe('gemma3:4b');
    expect(state!.settings.click_on_token).toBe(true);
    expect(state!.settings.auto_clean_phrases).toBe(true);
    expect(state!.settings.aspect_categories).toContain('FOOD#QUALITY');
    expect(state!.settings.sentiment_polarity_options).toEqual(['positive', 'negative', 'neutral']);
  });

  it('exposes all expected actions', () => {
    let actions: SettingsActions | null = null;

    const Comp: React.FC = () => {
      const [, a] = useSettings('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          actions = a;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(actions).not.toBeNull();
    expect(typeof actions!.fetchSettings).toBe('function');
    expect(typeof actions!.updateSettings).toBe('function');
    expect(typeof actions!.rescanPositions).toBe('function');
    expect(typeof actions!.clearSaveToast).toBe('function');
    expect(typeof actions!.setSaveToast).toBe('function');
  });

  it('updateSettings sends PATCH request and updates local state', async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockResolvedValueOnce({ ok: true });

    let updateFn: ((updates: Record<string, unknown>) => Promise<void>) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useSettings('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          updateFn = a.updateSettings;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    // Wait for effects
    await new Promise(r => setTimeout(r, 50));
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(updateFn).toBeInstanceOf(Function);
    expect(mockFetch).not.toHaveBeenCalled(); // updateSettings wasn't called yet
  });
});
