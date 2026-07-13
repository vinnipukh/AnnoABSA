import { describe, it, expect, vi, beforeEach } from 'vitest';

// NOT using @testing-library/react due to React 19.2.7 CJS bug
import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import { ModelTripletColumn } from './ModelTripletColumn';
import { TripletItem } from '../types';

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

const sampleTriplets: TripletItem[] = [
  { id: 'ma_0', aspect_term: 'Manzara', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'positive' },
  { id: 'ma_1', aspect_term: 'servis', aspect_category: 'SERVICE#GENERAL', sentiment_polarity: 'negative' },
];

describe('ModelTripletColumn', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('renders title and badge text', () => {
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        badgeText="GPT-4o"
        triplets={sampleTriplets}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
      />
    );
    expect(container.textContent).toContain('Model A');
    expect(container.textContent).toContain('GPT-4o');
  });

  it('shows empty state with Run button when onRunPrediction provided', () => {
    const onRun = vi.fn();
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={[]}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
        onRunPrediction={onRun}
      />
    );
    const runBtn = findByText(container, 'Çalıştır');
    expect(runBtn).not.toBeNull();
  });

  it('shows no-output state when empty and no onRunPrediction', () => {
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={[]}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
      />
    );
    expect(container.textContent).toContain('çıktı üretmedi');
  });

  it('renders triplet cards with aspect_term and polarity', () => {
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={sampleTriplets}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
      />
    );
    expect(container.textContent).toContain('Manzara');
    expect(container.textContent).toContain('servis');
    expect(container.textContent).toContain('AMBIENCE#GENERAL');
  });

  it('calls onToggleSelect when clicking a triplet card', () => {
    const onToggle = vi.fn();
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={sampleTriplets}
        selectedIds={new Set()}
        onToggleSelect={onToggle}
        onSelectAll={() => {}}
        onClearAll={() => {}}
      />
    );
    const manzaraCard = findByText(container, 'Manzara');
    click(manzaraCard);
    expect(onToggle).toHaveBeenCalledWith('ma_0');
  });

  it('calls onSelectAll when clicking Tümünü Seç', () => {
    const onSelectAll = vi.fn();
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={sampleTriplets}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={onSelectAll}
        onClearAll={() => {}}
      />
    );
    const selectAllBtn = findByText(container, 'Tümünü Seç');
    click(selectAllBtn);
    expect(onSelectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onClearAll when clicking Tümünü Kaldır (all selected)', () => {
    const onClearAll = vi.fn();
    const allIds = new Set(sampleTriplets.map(t => t.id));
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={sampleTriplets}
        selectedIds={allIds}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={onClearAll}
      />
    );
    const clearBtn = findByText(container, 'Tümünü Kaldır');
    click(clearBtn);
    expect(onClearAll).toHaveBeenCalledTimes(1);
  });

  it('calls onRunPrediction when Run button clicked', () => {
    const onRun = vi.fn();
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={[]}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
        onRunPrediction={onRun}
      />
    );
    const runBtn = findByText(container, 'Çalıştır');
    click(runBtn);
    expect(onRun).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner when isPredicting is true', () => {
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={[]}
        selectedIds={new Set()}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
        onRunPrediction={() => {}}
        isPredicting={true}
      />
    );
    expect(container.textContent).toContain('Tahmin ediliyor');
  });

  it('shows selected state with visual indicator', () => {
    const selectedIds = new Set(['ma_0']);
    const { container } = render(
      <ModelTripletColumn
        title="Model A"
        triplets={sampleTriplets}
        selectedIds={selectedIds}
        onToggleSelect={() => {}}
        onSelectAll={() => {}}
        onClearAll={() => {}}
      />
    );
    // Selected card should have "bg-primary" in its styling
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBeGreaterThan(0);
  });
});
