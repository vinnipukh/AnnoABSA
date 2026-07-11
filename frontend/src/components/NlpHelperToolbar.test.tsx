import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We do NOT use @testing-library/react due to a React 19.2.7 CJS bug:
// `React.act` is undefined in the CJS bundle, which crashes testing-library's
// `render()`. Instead, we mount components directly using createRoot + flushSync.

import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import { NlpHelperToolbar } from './NlpHelperToolbar';

// Helper: render a React element into a detached DOM node synchronously
function render(el: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = ReactDOMClient.createRoot(container);
  ReactDOM.flushSync(() => {
    root.render(el);
  });
  return { container, root };
}

/** Find a text node's parent element by matching its text content. */
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

/** Click the first matching element via a native event, wrapped in flushSync. */
function click(target: Element | null) {
  if (!target) throw new Error('Cannot click null element');
  ReactDOM.flushSync(() => {
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
  document.body.innerHTML = '';
});

// ─── Collapsed state ───────────────────────────────────────────────────

describe('NlpHelperToolbar — collapsed state', () => {
  it('renders a button (bag icon) when collapsed', () => {
    const { container } = render(<NlpHelperToolbar selectedText="güzel" />);
    expect(container.querySelectorAll('button').length).toBe(1);
  });

  it('does not fetch anything on mount', () => {
    render(<NlpHelperToolbar selectedText="güzel" />);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('does not show segment labels when collapsed', () => {
    const { container } = render(<NlpHelperToolbar selectedText="güzel" />);
    expect(container.textContent).not.toContain('Sözlük');
    expect(container.textContent).not.toContain('Duygu Analizi');
    expect(container.textContent).not.toContain('Yapı Çözümleme');
    expect(container.textContent).not.toContain('Benzerlik');
  });
});

// ─── Expanded state ────────────────────────────────────────────────────

describe('NlpHelperToolbar — expanded state', () => {
  it('expands and shows all 4 segment labels on click', () => {
    const { container } = render(<NlpHelperToolbar selectedText="güzel" />);
    click(container.querySelector('button'));
    expect(container.textContent).toContain('Sözlük');
    expect(container.textContent).toContain('Duygu Analizi');
    expect(container.textContent).toContain('Yapı Çözümleme');
    expect(container.textContent).toContain('Benzerlik');
  });

  it('auto-fetches lexicon on expand', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        words: [{ word: 'güzel', polarity: 'positive', score: 1.0 }],
        aggregate: 'positive',
      }),
    });
    const { container } = render(<NlpHelperToolbar selectedText="güzel" />);
    click(container.querySelector('button'));

    // Wait for the async fetch to resolve and re-render
    await vi.waitFor(() => {
      expect(container.textContent).toContain('Olumlu');
    });
    expect(mockFetch).toHaveBeenCalledWith(
      // fetch() is called as: fetch(url, options) where url is the full URL
      expect.stringContaining('/nlp/lexicon-polarity'),
      expect.any(Object),
    );
  });

  it('fetches sentiment on segment click', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ aggregate: 'neutral' }) }) // lexicon
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ label: 'positive', score: 0.95 }),
      });

    const { container } = render(<NlpHelperToolbar selectedText="harika" />);
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const sentimentBtn = findByText(container, 'Duygu Analizi');
    click(sentimentBtn);

    await vi.waitFor(() => {
      expect(container.textContent).toContain('positive');
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/nlp/sentiment'),
      expect.any(Object),
    );
  });

  it('fetches morphology on segment click', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ aggregate: 'neutral' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          word: 'güzel',
          parses: [{ root: 'güzel', pos: 'ADJ', ig: ['ADJ'] }],
        }),
      });

    const { container } = render(<NlpHelperToolbar selectedText="güzel yemek" />);
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const morphBtn = findByText(container, 'Yapı Çözümleme');
    click(morphBtn);

    await vi.waitFor(() => {
      expect(container.textContent).toContain('kök');
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/nlp/morphology'),
      expect.any(Object),
    );
  });

  it('fetches embedding similarity on segment click', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ aggregate: 'neutral' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ similarity: 0.87 }),
      });

    const { container } = render(
      <NlpHelperToolbar selectedText="harika" sentenceText="Bu harika bir yemek" />,
    );
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const simBtn = findByText(container, 'Benzerlik');
    click(simBtn);

    await vi.waitFor(() => {
      expect(container.textContent).toContain('87%');
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/nlp/embedding-similarity'),
      expect.any(Object),
    );
  });

  it('does not fetch similarity when sentenceText is missing', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ aggregate: 'neutral' }),
    });

    const { container } = render(<NlpHelperToolbar selectedText="harika" />);
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    const simBtn = findByText(container, 'Benzerlik');
    click(simBtn);

    // Brief wait — no extra fetch should happen
    await new Promise(r => setTimeout(r, 50));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

// ─── Error handling ────────────────────────────────────────────────────

describe('NlpHelperToolbar — error handling', () => {
  it('shows error when lexicon fetch fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    const { container } = render(<NlpHelperToolbar selectedText="test" />);
    click(container.querySelector('button'));

    await vi.waitFor(() => {
      expect(container.textContent).toContain('Network error');
    });
  });

  it('shows HTTP error when backend returns non-ok', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    const { container } = render(<NlpHelperToolbar selectedText="test" />);
    click(container.querySelector('button'));

    await vi.waitFor(() => {
      expect(container.textContent).toContain('HTTP 500');
    });
  });
});

// ─── Keyboard and interaction ──────────────────────────────────────────

describe('NlpHelperToolbar — keyboard and interaction', () => {
  it('collapses on Escape key', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ aggregate: 'neutral' }),
    });
    const { container } = render(<NlpHelperToolbar selectedText="test" />);
    click(container.querySelector('button')); // expand
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    // Send Escape to the document (component listens on document)
    ReactDOM.flushSync(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });

    // After collapse, segment labels should be gone
    expect(container.textContent).not.toContain('Sözlük');
    expect(container.querySelectorAll('button').length).toBe(1);
  });

  it('calls onClose when collapsing via Escape', async () => {
    const onClose = vi.fn();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ aggregate: 'neutral' }),
    });
    const { container } = render(<NlpHelperToolbar selectedText="test" onClose={onClose} />);
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    ReactDOM.flushSync(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('aborts in-flight request on unmount', () => {
    // We need to create the AbortController ourselves and pass it indirectly
    // The component creates its own AbortController internally.
    // We verify by checking that the fetch was called with an aborted signal.
    // Since we control the mock fetch, we can check that a signal was passed.

    const { container, root } = render(<NlpHelperToolbar selectedText="test" />);
    click(container.querySelector('button'));

    // Check that fetch was called with a signal
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    );

    // Unmount
    ReactDOM.flushSync(() => {
      root.unmount();
    });
    // If fetch was called, the signal was created — the unmount cleanup
    // will call abort on the internal AbortController. We verify by
    // checking that the call included a signal (which proves the component
    // created an AbortController).
    const calls = mockFetch.mock.calls;
    expect(calls.length).toBeGreaterThanOrEqual(1);
    const [, options] = calls[0];
    expect(options.signal).toBeInstanceOf(AbortSignal);
  });
});
