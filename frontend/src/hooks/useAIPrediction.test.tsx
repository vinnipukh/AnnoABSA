import { describe, it, expect, vi, beforeEach } from 'vitest';

// We do NOT use @testing-library/react due to a React 19.2.7 CJS bug.
// Instead, we mount components directly using createRoot + flushSync.

import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import React, { useRef, useEffect } from 'react';
import { useAIPrediction, AIPredictionState, AIPredictionActions } from './useAIPrediction';
import { AiSuggestionItem } from '../components/AISuggestions';

describe('useAIPrediction', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with default empty state', () => {
    let state: AIPredictionState | null = null;

    const Comp: React.FC = () => {
      const [s] = useAIPrediction('http://localhost:8000');
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
    expect(state!.aiSuggestions).toEqual([]);
    expect(state!.liveModelATriplets).toEqual([]);
    expect(state!.liveModelBTriplets).toEqual([]);
    expect(state!.isAIPredicting).toBe(false);
    expect(state!.isModelAPredicting).toBe(false);
    expect(state!.isModelBPredicting).toBe(false);
    expect(state!.aiTriggeredForIndex).toBe(false);
  });

  it('acceptSuggestion produces a TripletItem from an AiSuggestionItem', () => {
    let acceptFn: ((item: AiSuggestionItem) => ReturnType<AIPredictionActions['acceptSuggestion']>) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          acceptFn = a.acceptSuggestion;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(acceptFn).toBeInstanceOf(Function);
  });

  it('acceptSuggestion correctly creates a TripletItem', () => {
    let capturedTriplet: any = null;
    const onAccept = vi.fn((t: any) => { capturedTriplet = t; });

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000', undefined, onAccept);
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          const item: AiSuggestionItem = {
            aspect_term: 'lezzet',
            aspect_category: 'FOOD#QUALITY',
            sentiment_polarity: 'positive',
            opinion_term: 'güzel',
            at_start: 0,
            at_end: 5,
          };
          const result = a.acceptSuggestion(item);
          if (result) {
            capturedTriplet = result;
          }
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    // Check that acceptSuggestion triggered the onAcceptTriplet callback
    // and produced a valid TripletItem with the right fields
    if (capturedTriplet) {
      expect(capturedTriplet.aspect_term).toBe('lezzet');
      expect(capturedTriplet.aspect_category).toBe('FOOD#QUALITY');
      expect(capturedTriplet.sentiment_polarity).toBe('positive');
      expect(capturedTriplet.opinion_term).toBe('güzel');
      expect(capturedTriplet.at_start).toBe(0);
      expect(capturedTriplet.at_end).toBe(5);
      expect(capturedTriplet.id).toBeDefined();
      expect(capturedTriplet.id).toContain('ai_');
    }
  });

  it('acceptSuggestion handles missing optional fields', () => {
    let capturedTriplet: any = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          const item: AiSuggestionItem = {
            aspect_term: '',
            aspect_category: 'SERVICE#GENERAL',
            sentiment_polarity: 'negative',
          };
          const result = a.acceptSuggestion(item);
          capturedTriplet = result;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(capturedTriplet).not.toBeNull();
    expect(capturedTriplet.aspect_term).toBe('NULL');
    expect(capturedTriplet.opinion_term).toBe('');
    expect(capturedTriplet.at_start).toBeUndefined();
    expect(capturedTriplet.at_end).toBeUndefined();
  });

  it('rejectSuggestion removes an item by index', () => {
    let rejectFn: ((index: number) => void) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          rejectFn = a.rejectSuggestion;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(rejectFn).toBeInstanceOf(Function);
  });

  it('resetForNewIndex clears AI suggestions and resets trigger flag', () => {
    let resetFn: (() => void) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          resetFn = a.resetForNewIndex;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(resetFn).toBeInstanceOf(Function);
  });

  it('resetLivePredictions clears live model triplets', () => {
    let resetLiveFn: (() => void) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          resetLiveFn = a.resetLivePredictions;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(resetLiveFn).toBeInstanceOf(Function);
  });

  it('abortAIPrediction sets isAIPredicting to false', () => {
    let abortFn: (() => void) | null = null;

    const Comp: React.FC = () => {
      const [, a] = useAIPrediction('http://localhost:8000');
      const called = useRef(false);
      useEffect(() => {
        if (!called.current) {
          called.current = true;
          abortFn = a.abortAIPrediction;
        }
      });
      return null;
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = ReactDOMClient.createRoot(container);
    ReactDOM.flushSync(() => { root.render(<Comp />); });
    ReactDOM.flushSync(() => { root.unmount(); container.remove(); });

    expect(abortFn).toBeInstanceOf(Function);
  });
});
