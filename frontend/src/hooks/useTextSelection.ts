import { useState, useCallback, useMemo } from 'react';

/* ── Pure functions (exported for testing, no React dependency) ─────── */

export function getTokenBounds(text: string, ci: number): { start: number; end: number } {
  if (!text || ci < 0 || ci >= text.length) return { start: ci, end: ci };
  const isB = (c: string) => /[\s.,;:!?¡¿"'`''""„«»()\[\]{}]+/.test(c);
  let s = ci, e = ci;
  while (s > 0 && !isB(text[s - 1])) s--;
  while (e < text.length - 1 && !isB(text[e + 1])) e++;
  return { start: s, end: e };
}

export function cleanPhrase(p: string): string {
  return p.replace(/^[.,;:!?¡¿"'`''""„«»()\[\]{}]+|[.,;:!?¡¿"'`''""„«»()\[\]{}]+$/g, '').trim();
}

export function getCleanedPositions(os: number, oe: number, txt: string, clean: boolean): { start: number; end: number } {
  if (!clean) return { start: os, end: oe };
  const r = txt.substring(os, oe + 1), c = cleanPhrase(r);
  if (c === r) return { start: os, end: oe };
  const i = r.indexOf(c);
  return i === -1 ? { start: os, end: oe } : { start: os + i, end: os + i + c.length - 1 };
}

/* ── Type definitions ────────────────────────────────────────────────── */

export interface PendingSelection {
  start: number;
  end: number;
  text: string;
}

export interface TextSelectionState {
  selStart: number | null;
  selEnd: number | null;
  selectedText: string;
  pendingSelection: PendingSelection | null;
}

export interface TextSelectionActions {
  handleCharClick: (charIndex: number) => void;
  clearSelection: () => void;
}

/* ── Hook ─────────────────────────────────────────────────────────────── */

interface UseTextSelectionOptions {
  clickOnToken?: boolean;
  autoCleanPhrases?: boolean;
}

/**
 * Character-level text selection hook.
 *
 * Click cycle: first click sets start, second click sets end,
 * third click resets. Supports token snapping and phrase cleaning.
 */
export function useTextSelection(
  reviewText: string,
  options?: UseTextSelectionOptions
): [TextSelectionState, TextSelectionActions] {
  const { clickOnToken = true, autoCleanPhrases = true } = options || {};

  const [selStart, setSelStart] = useState<number | null>(null);
  const [selEnd, setSelEnd] = useState<number | null>(null);

  const handleCharClick = useCallback((charIndex: number) => {
    let start = charIndex, end = charIndex;
    if (clickOnToken) {
      const tb = getTokenBounds(reviewText, charIndex);
      if (selStart === null) start = tb.start;
      else end = tb.end;
    }
    if (selStart === null) {
      setSelStart(start);
    } else if (selEnd === null && (clickOnToken ? end : charIndex) >= selStart) {
      setSelEnd(clickOnToken ? end : charIndex);
    } else {
      setSelStart(start);
      setSelEnd(null);
    }
  }, [reviewText, clickOnToken, selStart, selEnd]);

  const clearSelection = useCallback(() => {
    setSelStart(null);
    setSelEnd(null);
  }, []);

  const pendingSelection = useMemo((): PendingSelection | null => {
    if (selStart === null || selEnd === null) return null;
    let s = selStart, e = selEnd, t = reviewText.substring(s, e + 1);
    if (autoCleanPhrases) {
      const cp = getCleanedPositions(s, e, reviewText, true);
      s = cp.start; e = cp.end; t = reviewText.substring(s, e + 1);
    }
    return t.trim() ? { start: s, end: e, text: t } : null;
  }, [selStart, selEnd, reviewText, autoCleanPhrases]);

  const selectedText = pendingSelection ? pendingSelection.text : '';

  const state: TextSelectionState = { selStart, selEnd, selectedText, pendingSelection };
  const actions: TextSelectionActions = { handleCharClick, clearSelection };

  return [state, actions];
}
