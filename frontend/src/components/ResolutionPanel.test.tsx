import { describe, it, expect, vi, beforeEach } from 'vitest';

// NOT using @testing-library/react due to React 19.2.7 CJS bug
import ReactDOMClient from 'react-dom/client';
import ReactDOM from 'react-dom';
import { ResolutionPanel } from './ResolutionPanel';
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

/* ─── Sample data ─── */

const majorityTriplets: TripletItem[] = [
  { id: 'maj_1', aspect_term: 'Manzara', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'positive' },
  { id: 'maj_2', aspect_term: 'servis', aspect_category: 'SERVICE#GENERAL', sentiment_polarity: 'negative' },
];

const gtTriplets: TripletItem[] = [
  { id: 'gt_1', aspect_term: 'Manzara', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'positive' },
  { id: 'gt_2', aspect_term: 'servis', aspect_category: 'SERVICE#GENERAL', sentiment_polarity: 'negative' },
];

const gtTripletsDiff: TripletItem[] = [
  { id: 'gt_1', aspect_term: 'manzara', aspect_category: 'AMBIENCE#GENERAL', sentiment_polarity: 'neutral' },
  { id: 'gt_2', aspect_term: 'yemek', aspect_category: 'FOOD#GENERAL', sentiment_polarity: 'positive' },
];

const categories = ['AMBIENCE#GENERAL', 'SERVICE#GENERAL', 'FOOD#GENERAL'];
const polarities = ['positive', 'negative', 'neutral'];

const defaultProps = {
  majorityVote: 3,
  majorityLabel: majorityTriplets,
  gtTriplets: gtTriplets,
  consensusIntersection: majorityTriplets,
  originalLlmDiff: '',
  categories,
  polarities,
  manualTriplets: [] as TripletItem[],
  onAddTriplet: vi.fn(),
  onRemoveTriplet: vi.fn(),
  onAcceptSuggestion: vi.fn(),
  onEditTriplets: vi.fn(),
};

describe('ResolutionPanel', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  /* ─── Tier 1: Auto-Accept (green) ─── */

  it('renders Tier 1 Auto-Accept with green header', () => {
    const { container } = render(<ResolutionPanel {...defaultProps} />);

    // Should show tier title
    expect(container.textContent).toContain('Auto-Accept');
    // Should show suggestion text
    expect(container.textContent).toContain('GT triplets match majority consensus');
    // Should show green-ish header (bg-success class applied)
    const headerDiv = container.querySelector('.bg-success\\/10');
    expect(headerDiv).not.toBeNull();
    // Should show "Tüm modeller uyumlu" badge
    expect(container.textContent).toContain('Tüm modeller uyumlu');
    // Should show majority triplets in diff tracker
    expect(container.textContent).toContain('Manzara');
    expect(container.textContent).toContain('servis');
  });

  it('shows Accept and Edit buttons in Tier 1', () => {
    const { container } = render(<ResolutionPanel {...defaultProps} />);

    const acceptBtn = findByText(container, /Kabul Et/);
    expect(acceptBtn).not.toBeNull();

    const editBtn = findByText(container, /Düzenle/);
    expect(editBtn).not.toBeNull();
  });

  /* ─── Tier 2: Quick Diff (yellow) ─── */

  it('renders Tier 2 Quick Diff with yellow header', () => {
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={2}
        majorityLabel={majorityTriplets}
        gtTriplets={gtTripletsDiff}
        originalLlmDiff="Majority says positive, GT says neutral"
      />
    );

    // Should show tier title
    expect(container.textContent).toContain('Quick Diff');
    // Should show suggestion text
    expect(container.textContent).toContain('Consensus found but differs from GT');
    // Should show yellow-ish header
    const headerDiv = container.querySelector('.bg-warning\\/10');
    expect(headerDiv).not.toBeNull();
    // Should show diff text
    expect(container.textContent).toContain('Majority says positive');
    // Should show both sides: Majority and GT
    expect(container.textContent).toContain('Majority');
    expect(container.textContent).toContain('GT (Original)');
  });

  it('shows three action buttons in Tier 2', () => {
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={2}
        majorityLabel={majorityTriplets}
        gtTriplets={gtTripletsDiff}
      />
    );

    // All three button labels should be present
    expect(container.textContent).toContain('Majority Kabul Et');
    expect(container.textContent).toContain('GT\'yi Koru');
    expect(container.textContent).toContain('Düzenle');
  });

  /* ─── Tier 3: Manual Review (red) ─── */

  it('renders Tier 3 Manual Review with red header', () => {
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={1}
        majorityLabel={[]}
        gtTriplets={[]}
      />
    );

    // Should show tier title
    expect(container.textContent).toContain('Manual Review');
    // Should show suggestion text
    expect(container.textContent).toContain('No consensus');
    // Should show red-ish header
    const headerDiv = container.querySelector('.bg-error\\/10');
    expect(headerDiv).not.toBeNull();
    // Should show Turkish message about all 4 models
    expect(container.textContent).toContain('Tüm 4 model');
    expect(container.textContent).toContain('ızgarada');
    // Should show Manuel Giris button
    expect(container.textContent).toContain('Manuel Giris');
  });

  it('shows manual form when Manuel Giris button clicked in Tier 3', () => {
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={1}
        majorityLabel={[]}
        gtTriplets={[]}
      />
    );

    // Click Manuel Giris button
    const manualBtn = findByText(container, /Manuel Giris/);
    click(manualBtn);

    // Form should now be visible with input fields
    expect(container.textContent).toContain('ASPECT TERM');
    expect(container.textContent).toContain('KATEGORI');
    expect(container.textContent).toContain('KUTUP');
    // Form should have +P, -N, =N buttons
    expect(container.textContent).toContain('+P');
    expect(container.textContent).toContain('-N');
    expect(container.textContent).toContain('=N');
  });

  /* ─── Callback tests ─── */

  it('calls onAcceptSuggestion with GT triplets when Accept clicked in Tier 1', () => {
    const onAccept = vi.fn();
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        onAcceptSuggestion={onAccept}
      />
    );

    const acceptBtn = findByText(container, /Kabul Et/);
    click(acceptBtn);

    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(onAccept).toHaveBeenCalledWith(gtTriplets);
  });

  it('calls onAcceptSuggestion with majorityLabel when Majority Kabul Et clicked in Tier 2', () => {
    const onAccept = vi.fn();
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={2}
        majorityLabel={majorityTriplets}
        gtTriplets={gtTripletsDiff}
        onAcceptSuggestion={onAccept}
      />
    );

    // Find "Majority Kabul Et" button specifically
    const majorityBtn = findByText(container, /^Majority Kabul Et$/);
    click(majorityBtn);

    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(onAccept).toHaveBeenCalledWith(majorityTriplets);
  });

  it('calls onAcceptSuggestion with GT triplets when GT yi Koru clicked in Tier 2', () => {
    const onAccept = vi.fn();
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={2}
        majorityLabel={majorityTriplets}
        gtTriplets={gtTripletsDiff}
        onAcceptSuggestion={onAccept}
      />
    );

    const gtBtn = findByText(container, 'GT\'yi Koru');
    click(gtBtn);

    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(onAccept).toHaveBeenCalledWith(gtTripletsDiff);
  });

  it('calls onEditTriplets when Düzenle clicked', () => {
    const onEdit = vi.fn();
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        onEditTriplets={onEdit}
      />
    );

    const editBtn = findByText(container, /Düzenle/);
    click(editBtn);

    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  /* ─── Manual form functionality ─── */

  it('calls onAddTriplet when manual form submitted in Tier 3', () => {
    const onAdd = vi.fn();
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={1}
        majorityLabel={[]}
        gtTriplets={[]}
        onAddTriplet={onAdd}
      />
    );

    // Open manual form
    const manualBtn = findByText(container, /Manuel Giris/);
    click(manualBtn);

    // Find aspect term input and type in it
    const input = container.querySelector('input[type="text"]') as HTMLInputElement;
    expect(input).not.toBeNull();

    // Set value via native input
    Object.defineProperty(input, 'value', { value: 'yemek', writable: true });
    input.dispatchEvent(new Event('input', { bubbles: true }));

    // Find submit button and click
    const submitBtn = findByText(container, '+ Triplet Ekle');
    click(submitBtn);

    expect(onAdd).toHaveBeenCalledTimes(1);
    const added = onAdd.mock.calls[0][0] as TripletItem;
    expect(added.aspect_term).toBe('yemek');
    expect(added.sentiment_polarity).toBe('positive');
  });

  /* ─── Diff tracker text ─── */

  it('shows original_llm_diff text in Tier 2 Diff Tracker', () => {
    const diffText = 'Majority says Manzara=positive vs GT=neutral — aspect mismatch detected';
    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={2}
        majorityLabel={majorityTriplets}
        gtTriplets={gtTripletsDiff}
        originalLlmDiff={diffText}
      />
    );

    expect(container.textContent).toContain('Majority says Manzara');
    expect(container.textContent).toContain('aspect mismatch detected');
  });

  it('shows manual triplets list with remove button', () => {
    const onRemove = vi.fn();
    const manualTriplets: TripletItem[] = [
      { id: 'man_1', aspect_term: 'yemek', aspect_category: 'FOOD#GENERAL', sentiment_polarity: 'positive' },
    ];

    const { container } = render(
      <ResolutionPanel
        {...defaultProps}
        majorityVote={1}
        majorityLabel={[]}
        gtTriplets={[]}
        manualTriplets={manualTriplets}
        onRemoveTriplet={onRemove}
      />
    );

    // Open manual form
    const manualBtn = findByText(container, /Manuel Giris/);
    click(manualBtn);

    // Manual triplet should be visible
    expect(container.textContent).toContain('yemek');

    // Find and click remove button (close icon area)
    const removeBtn = container.querySelector('button[title="Remove triplet"]');
    expect(removeBtn).not.toBeNull();
    click(removeBtn);

    expect(onRemove).toHaveBeenCalledWith('man_1');
  });
});
