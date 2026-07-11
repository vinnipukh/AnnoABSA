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
  handleMouseUp: (container: HTMLElement) => void;
  clearSelection: () => void;
}

/* ── Helpers ──────────────────────────────────────────────────────────── */

/**
 * Walk text nodes inside `container` and find the full-text character offset
 * corresponding to the boundary of a native browser Range.
 *
 * Uses Range-based position calculation which works correctly even when the
 * text is split across multiple <span> elements (annotation highlighting).
 */
function getCharOffset(container: HTMLElement, refNode: Node, refOffset: number): number {
  const r = document.createRange();
  r.selectNodeContents(container);
  r.setEnd(refNode, refOffset);
  return r.toString().length;
}

/* ── Hook ─────────────────────────────────────────────────────────────── */

interface UseTextSelectionOptions {
  clickOnToken?: boolean;
  autoCleanPhrases?: boolean;
}

/**
 * Character-level text selection hook using native browser selection.
 *
 * Works like standard desktop text selection: click-drag-release selects text.
 * On mouseup reads `window.getSelection()` and computes character offsets
 * via DOM Range walking. Supports token snapping and phrase cleaning.
 */
export function useTextSelection(
  reviewText: string,
  options?: UseTextSelectionOptions
): [TextSelectionState, TextSelectionActions] {
  const { clickOnToken = true, autoCleanPhrases = true } = options || {};

  const [selStart, setSelStart] = useState<number | null>(null);
  const [selEnd, setSelEnd] = useState<number | null>(null);

  const handleMouseUp = useCallback((container: HTMLElement) => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
      setSelStart(null);
      setSelEnd(null);
      return;
    }

    const range = sel.getRangeAt(0);
    const rawStart = getCharOffset(container, range.startContainer, range.startOffset);
    const rawEnd = getCharOffset(container, range.endContainer, range.endOffset);

    // Range guarantees start ≤ end, so rawEnd > rawStart means non-empty
    if (rawEnd <= rawStart) {
      setSelStart(null);
      setSelEnd(null);
      return;
    }

    let s = rawStart, e = rawEnd - 1;  // convert to 0-indexed inclusive
    if (clickOnToken) {
      const st = getTokenBounds(reviewText, s);
      const et = getTokenBounds(reviewText, e);
      s = st.start;
      e = et.end;
    }
    setSelStart(s);
    setSelEnd(e);
  }, [reviewText, clickOnToken]);

  const clearSelection = useCallback(() => {
    setSelStart(null);
    setSelEnd(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  const pendingSelection = useMemo((): PendingSelection | null => {
    if (selStart === null || selEnd === null) return null;
    const s = Math.min(selStart, selEnd);
    const e = Math.max(selStart, selEnd);
    if (autoCleanPhrases) {
      const cp = getCleanedPositions(s, e, reviewText, true);
      const text = reviewText.substring(cp.start, cp.end + 1);
      return text.trim() ? { start: cp.start, end: cp.end, text } : null;
    }
    const text = reviewText.substring(s, e + 1);
    return text.trim() ? { start: s, end: e, text } : null;
  }, [selStart, selEnd, reviewText, autoCleanPhrases]);

  const selectedText = pendingSelection ? pendingSelection.text : '';

  const state: TextSelectionState = { selStart, selEnd, selectedText, pendingSelection };
  const actions: TextSelectionActions = { handleMouseUp, clearSelection };

  return [state, actions];
}
