import { describe, it, expect } from 'vitest';
import { getTokenBounds, cleanPhrase, getCleanedPositions } from './useTextSelection';

describe('getTokenBounds', () => {
  it('returns full word boundaries for middle of word', () => {
    const { start, end } = getTokenBounds('güzel yemek', 3);
    expect(start).toBe(0);
    expect(end).toBe(4);
  });

  it('expands to full word when clicking punctuation at word edge', () => {
    const { start, end } = getTokenBounds('güzel,', 5);  // comma at end
    expect(start).toBe(0);
    expect(end).toBe(5);  // includes the comma as part of the word span
  });

  it('handles first char of text', () => {
    const { start, end } = getTokenBounds('Merhaba dünya', 0);
    expect(start).toBe(0);
    expect(end).toBe(6);
  });

  it('handles last char of text', () => {
    const { start, end } = getTokenBounds('hello world', 10);
    expect(start).toBe(6);
    expect(end).toBe(10);
  });

  it('handles empty text gracefully', () => {
    const r = getTokenBounds('', 0);
    expect(r.start).toBe(0);
    expect(r.end).toBe(0);
  });
});

describe('cleanPhrase', () => {
  it('strips leading punctuation', () => {
    expect(cleanPhrase('"güzel"')).toBe('güzel');
  });

  it('strips trailing punctuation', () => {
    expect(cleanPhrase('güzel!')).toBe('güzel');
  });

  it('strips both sides', () => {
    expect(cleanPhrase('(güzel)')).toBe('güzel');
  });

  it('leaves clean text unchanged', () => {
    expect(cleanPhrase('güzel')).toBe('güzel');
  });

  it('handles Turkish characters', () => {
    expect(cleanPhrase('«şahane»')).toBe('şahane');
  });
});

describe('getCleanedPositions', () => {
  it('returns original positions when no cleaning needed', () => {
    const r = getCleanedPositions(0, 5, 'güzel yemek', true);
    expect(r.start).toBe(0);
    expect(r.end).toBe(4);  // position 5 is a space, which gets trimmed; actual text ends at 4
  });

  it('adjusts positions when leading punctuation stripped', () => {
    // text: '"güzel" yemek', positions 0-6 → '"güzel"'
    // cleaned: 'güzel' → positions 1-5
    const r = getCleanedPositions(0, 6, '"güzel" yemek', true);
    expect(r.start).toBe(1);
    expect(r.end).toBe(5);
  });

  it('returns original when autoCleanPhrases is false', () => {
    const r = getCleanedPositions(0, 6, '"güzel" yemek', false);
    expect(r.start).toBe(0);
    expect(r.end).toBe(6);
  });
});
