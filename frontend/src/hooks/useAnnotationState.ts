import { useState, useCallback } from 'react';
import { TripletItem } from '../types';

export type ColumnKey = 'model_a' | 'model_b' | 'gt' | 'gemma' | 'qwen' | 'gpt';

function makeEmptySelectedIds(): Record<ColumnKey, Set<string>> {
  return {
    model_a: new Set(),
    model_b: new Set(),
    gt: new Set(),
    gemma: new Set(),
    qwen: new Set(),
    gpt: new Set(),
  };
}

export interface AnnotationState {
  manualTriplets: TripletItem[];
  selectedIds: Record<ColumnKey, Set<string>>;
  selectedModelAIds: Set<string>;
  selectedModelBIds: Set<string>;
}

export interface AnnotationActions {
  addTriplet: (triplet: TripletItem) => void;
  removeTriplet: (id: string) => void;
  toggleTriplet: (column: string, id: string) => void;
  selectAllInColumn: (column: string, ids: TripletItem[]) => void;
  clearAllInColumn: (column: string) => void;
  clearAll: () => void;
  resetAll: () => void;
  setManualTriplets: (triplets: TripletItem[] | ((prev: TripletItem[]) => TripletItem[])) => void;
}

export function useAnnotationState(): [AnnotationState, AnnotationActions] {
  const [manualTriplets, setManualTriplets] = useState<TripletItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Record<ColumnKey, Set<string>>>(makeEmptySelectedIds());

  const addTriplet = useCallback((triplet: TripletItem) => {
    setManualTriplets(p => [...p, triplet]);
  }, []);

  const removeTriplet = useCallback((id: string) => {
    setManualTriplets(p => p.filter(m => m.id !== id));
  }, []);

  const toggleTriplet = useCallback((column: string, id: string) => {
    setSelectedIds(prev => {
      const next = { ...prev };
      const colKey = column as ColumnKey;
      const set = new Set(next[colKey] || []);
      set.has(id) ? set.delete(id) : set.add(id);
      next[colKey] = set;
      return next;
    });
  }, []);

  const selectAllInColumn = useCallback((column: string, ids: TripletItem[]) => {
    setSelectedIds(prev => ({ ...prev, [column]: new Set(ids.map(t => t.id)) }));
  }, []);

  const clearAllInColumn = useCallback((column: string) => {
    setSelectedIds(prev => ({ ...prev, [column]: new Set() }));
  }, []);

  const clearAll = useCallback(() => {
    setManualTriplets([]);
    setSelectedIds(makeEmptySelectedIds());
  }, []);

  const resetAll = useCallback(() => {
    setManualTriplets([]);
    setSelectedIds(makeEmptySelectedIds());
  }, []);

  const state: AnnotationState = {
    manualTriplets,
    selectedIds,
    selectedModelAIds: selectedIds.model_a || new Set(),
    selectedModelBIds: selectedIds.model_b || new Set(),
  };

  const actions: AnnotationActions = {
    addTriplet, removeTriplet, toggleTriplet,
    selectAllInColumn, clearAllInColumn, clearAll, resetAll,
    setManualTriplets,
  };

  return [state, actions];
}
