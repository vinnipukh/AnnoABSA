import { describe, it, expect, vi, beforeEach } from 'vitest';

// NOT using @testing-library/react due to React 19.2.7 CJS bug
import React from 'react';
import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import { FourWayGrid } from './FourWayGrid';
import { TripletItem } from '../types';

function render(el: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = ReactDOMClient.createRoot(container);
  ReactDOM.flushSync(() => { root.render(el); });
  return { container, root };
}

function click(target: Element | null) {
  if (!target) throw new Error('Cannot click null element');
  ReactDOM.flushSync(() => {
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

const sampleTriplets: TripletItem[] = [
  { id: 'gt_0', aspect_term: 'NULL', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
  { id: 'gm_0', aspect_term: 'NULL', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
  { id: 'qw_0', aspect_term: 'NULL', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
  { id: 'gpt_0', aspect_term: 'NULL', aspect_category: 'FOOD#QUALITY', sentiment_polarity: 'positive' },
];

/**
 * Simulate the header toolbar with an autopilot button + toast area,
 * matching the App.tsx pattern (lines 682-705, 950-954).
 */
function AutopilotWrapper({
  autopilotLoading = false,
  onRunAutopilot = () => Promise.resolve({ annotated: 5, total_unlabeled: 3 }),
}: {
  autopilotLoading?: boolean;
  onRunAutopilot?: () => Promise<{ annotated: number; total_unlabeled: number }>;
}) {
  const [isLoading, setIsLoading] = React.useState(autopilotLoading);
  const [toast, setToast] = React.useState<string | null>(null);

  const handleRun = async () => {
    setIsLoading(true);
    try {
      const data = await onRunAutopilot();
      if (data.annotated > 0) {
        setToast(`${data.annotated} inceleme etiketlendi (${data.total_unlabeled} kaldi)`);
      } else {
        setToast('Etiketlenecek inceleme kalmadi');
      }
    } catch {
      setToast('Hata');
    } finally {
      setIsLoading(false);
    }
  };

  return React.createElement('div', null,
    // Header section with autopilot button (matching App.tsx lines 682-705)
    React.createElement('div', { className: 'flex items-center gap-2' },
      React.createElement('button',
        {
          onClick: handleRun,
          disabled: isLoading,
          className: isLoading
            ? 'opacity-50 cursor-not-allowed bg-base-200 text-primary'
            : 'bg-base-200 text-base-content/70 hover:text-primary',
          title: 'Etiketlenmemis incelemeleri ML ile otomatik etiketle',
          'data-testid': 'autopilot-btn',
        },
        isLoading
          ? React.createElement(React.Fragment, null,
              React.createElement('div', { className: 'w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin' }),
              ' Etiketleniyor...'
            )
          : React.createElement(React.Fragment, null,
              React.createElement('svg', { className: 'w-3.5 h-3.5' }),
              ' Otomatik Etiketle'
            )
      ),
    ),
    // FourWayGrid below
    React.createElement(FourWayGrid, {
      gtTriplets: sampleTriplets,
      gemmaTriplets: sampleTriplets,
      qwenTriplets: sampleTriplets,
      gptTriplets: sampleTriplets,
      majorityVote: 4,
      selectedIds: { gt: new Set<string>(), gemma: new Set<string>(), qwen: new Set<string>(), gpt: new Set<string>() },
      onToggleSelect: () => {},
      onSelectAll: () => {},
      onClearAll: () => {},
    }),
    // Toast area (matching App.tsx lines 950-954)
    toast
      ? React.createElement('div', {
          className: 'fixed bottom-14 left-1/2 -translate-x-1/2 bg-base-100 border border-success/50 text-success px-4 py-2 rounded-xl',
          'data-testid': 'autopilot-toast',
        }, toast)
      : null,
  );
}

describe('FourWayGrid', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('renders GT, Gemma, Qwen, and GPT columns', () => {
    const { container, root } = render(
      React.createElement(FourWayGrid, {
        gtTriplets: sampleTriplets,
        gemmaTriplets: sampleTriplets,
        qwenTriplets: sampleTriplets,
        gptTriplets: sampleTriplets,
        majorityVote: 3,
        selectedIds: { gt: new Set<string>(), gemma: new Set<string>(), qwen: new Set<string>(), gpt: new Set<string>() },
        onToggleSelect: () => {},
        onSelectAll: () => {},
        onClearAll: () => {},
      })
    );
    expect(container.textContent).toContain('GT');
    expect(container.textContent).toContain('Gemma');
    expect(container.textContent).toContain('Qwen');
    expect(container.textContent).toContain('GPT');
    expect(container.textContent).toContain('FOOD#QUALITY');
    root.unmount();
    document.body.removeChild(container);
  });

  it('renders consensus diamond with vote count', () => {
    const { container, root } = render(
      React.createElement(FourWayGrid, {
        gtTriplets: sampleTriplets,
        gemmaTriplets: sampleTriplets,
        qwenTriplets: sampleTriplets,
        gptTriplets: sampleTriplets,
        majorityVote: 4,
        selectedIds: { gt: new Set<string>(), gemma: new Set<string>(), qwen: new Set<string>(), gpt: new Set<string>() },
        onToggleSelect: () => {},
        onSelectAll: () => {},
        onClearAll: () => {},
      })
    );
    expect(container.textContent).toContain('4');
    root.unmount();
    document.body.removeChild(container);
  });

  it('shows empty state when no triplets', () => {
    const { container, root } = render(
      React.createElement(FourWayGrid, {
        gtTriplets: [],
        gemmaTriplets: [],
        qwenTriplets: [],
        gptTriplets: [],
        majorityVote: 0,
        selectedIds: { gt: new Set<string>(), gemma: new Set<string>(), qwen: new Set<string>(), gpt: new Set<string>() },
        onToggleSelect: () => {},
        onSelectAll: () => {},
        onClearAll: () => {},
      })
    );
    // Each column shows "Boş" (empty) when no triplets
    const emptyCount = container.textContent!.match(/Boş/g)?.length || 0;
    expect(emptyCount).toBe(4);
    root.unmount();
    document.body.removeChild(container);
  });
});

describe('Autopilot in 4-way mode', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('renders autopilot button in 4-way mode', () => {
    const { container, root } = render(
      React.createElement(AutopilotWrapper, {})
    );
    const btn = container.querySelector('[data-testid="autopilot-btn"]');
    expect(btn).not.toBeNull();
    expect(container.textContent).toContain('Otomatik Etiketle');
    root.unmount();
    document.body.removeChild(container);
  });

  it('disables button during execution', async () => {
    // Create a promise that never resolves during the test
    const neverResolve = vi.fn().mockImplementation(
      () => new Promise<{ annotated: number; total_unlabeled: number }>(() => {
        // Never resolves — button stays disabled
      })
    );

    const { container, root } = render(
      React.createElement(AutopilotWrapper, {
        onRunAutopilot: neverResolve,
      })
    );

    const btn = container.querySelector('[data-testid="autopilot-btn"]') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.disabled).toBe(false);

    // Click to trigger loading state
    click(btn);
    // After click, the loading state should enable the spinner text
    await new Promise(r => setTimeout(r, 50));
    ReactDOM.flushSync(() => {}); // flush pending state updates
    expect(container.textContent).toContain('Etiketleniyor');
    // Button should be disabled during execution
    expect(btn.disabled).toBe(true);
    root.unmount();
    document.body.removeChild(container);
  });

  it('shows success toast after completion', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ annotated: 5, total_unlabeled: 3 });

    const { container, root } = render(
      React.createElement(AutopilotWrapper, {
        onRunAutopilot: mockFetch,
      })
    );

    const btn = container.querySelector('[data-testid="autopilot-btn"]') as HTMLButtonElement;
    click(btn);

    // Wait for async completion
    await new Promise(r => setTimeout(r, 100));
    ReactDOM.flushSync(() => {}); // flush pending state updates

    const toast = container.querySelector('[data-testid="autopilot-toast"]');
    expect(toast).not.toBeNull();
    expect(toast?.textContent).toContain('5 inceleme etiketlendi');
    root.unmount();
    document.body.removeChild(container);
  });
});
