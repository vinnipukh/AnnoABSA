import { useState, useCallback } from 'react';

export interface CompareModeState {
  mode: 'compare' | 'manual';
  compareMode: 'csv' | 'live' | '4way';
}

export interface CompareModeActions {
  toggleMode: (mode: 'compare' | 'manual') => void;
  toggleCompareMode: (compareMode: 'csv' | 'live' | '4way') => void;
}

export function useCompareMode(): [CompareModeState, CompareModeActions] {
  const [mode, setMode] = useState<'compare' | 'manual'>('compare');
  const [compareMode, setCompareMode] = useState<'csv' | 'live' | '4way'>('4way');

  const toggleMode = useCallback((m: 'compare' | 'manual') => {
    setMode(m);
  }, []);

  const toggleCompareMode = useCallback((cm: 'csv' | 'live' | '4way') => {
    setCompareMode(cm);
  }, []);

  const state: CompareModeState = { mode, compareMode };
  const actions: CompareModeActions = { toggleMode, toggleCompareMode };

  return [state, actions];
}
