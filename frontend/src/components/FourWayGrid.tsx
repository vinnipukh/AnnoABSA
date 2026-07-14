import React from 'react';
import { TripletItem } from '../types';
import { CompactTripletChip } from './CompactTripletChip';

interface FourWayGridProps {
  gtTriplets: TripletItem[];
  gemmaTriplets: TripletItem[];
  qwenTriplets: TripletItem[];
  gptTriplets: TripletItem[];
  majorityVote: number;
  selectedIds: Record<string, Set<string>>;
  onToggleSelect: (column: string, id: string) => void;
  onSelectAll: (column: string) => void;
  onClearAll: (column: string) => void;
  modelNames?: { gemma: string; qwen: string; gpt: string };
  csvColumnNames?: { gemma: string; qwen: string; gpt: string; gt?: string };
}

const defaultModelNames = { gemma: 'Gemma', qwen: 'Qwen', gpt: 'GPT' };

function ColumnCard({
  title,
  csvColumnName,
  triplets,
  selectedIds,
  columnKey,
  onToggleSelect,
  onSelectAll,
  onClearAll,
}: {
  title: string;
  csvColumnName?: string;
  triplets: TripletItem[];
  selectedIds: Set<string>;
  columnKey: string;
  onToggleSelect: (column: string, id: string) => void;
  onSelectAll: (column: string) => void;
  onClearAll: (column: string) => void;
}) {
  const allSelected =
    triplets.length > 0 && triplets.every((t) => selectedIds.has(t.id));

  return (
    <div className="bg-base-200/80 border border-base-300 rounded-xl p-3 shadow-sm flex flex-col">
      {/* Column header */}
      <div className="flex items-start justify-between mb-2 min-h-[32px]">
        <div className="flex flex-col min-w-0">
          <h4 className="text-sm font-bold text-base-content tracking-tight">
            {title}
          </h4>
          {csvColumnName && (
            <div className="text-[10px] text-base-content/40 font-mono truncate leading-tight">
              {csvColumnName}
            </div>
          )}
        </div>
        {triplets.length > 0 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() =>
                allSelected ? onClearAll(columnKey) : onSelectAll(columnKey)
              }
              className="text-[10px] px-2.5 py-1 rounded-lg bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300 min-h-[28px] flex items-center select-none"
            >
              {allSelected ? 'Temizle' : 'Tümünü Seç'}
            </button>
          </div>
        )}
      </div>

      {/* Triplet list */}
      <div className="space-y-1.5 flex-1 overflow-y-auto min-h-0">
        {triplets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-4 text-base-content/40">
            {/* Heroicons document SVG — no emoji */}
            <svg
              className="w-8 h-8 mx-auto text-base-content/20"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-[10px] mt-1">Boş</p>
          </div>
        ) : (
          triplets.map((t) => (
            <CompactTripletChip
              key={t.id}
              triplet={t}
              isSelected={selectedIds.has(t.id)}
              onToggle={(id) => onToggleSelect(columnKey, id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ConsensusDiamond({ majorityVote }: { majorityVote: number }) {
  let colorClasses: string;
  if (majorityVote >= 3) {
    colorClasses = 'border-success bg-success/20 text-success';
  } else if (majorityVote >= 2) {
    colorClasses = 'border-warning bg-warning/20 text-warning';
  } else {
    colorClasses = 'border-error bg-error/20 text-error';
  }

  return (
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
      <div
        className={`w-9 h-9 rotate-45 border-2 rounded-md shadow-lg flex items-center justify-center ${colorClasses}`}
      >
        <span className="-rotate-45 text-sm font-bold select-none">
          {majorityVote}
        </span>
      </div>
    </div>
  );
}

export const FourWayGrid: React.FC<FourWayGridProps> = ({
  gtTriplets,
  gemmaTriplets,
  qwenTriplets,
  gptTriplets,
  majorityVote,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onClearAll,
  modelNames,
  csvColumnNames,
}) => {
  const names = { ...defaultModelNames, ...modelNames };

  // Reduce motion — wrap hover transitions
  const motionStyles = `
    @media (prefers-reduced-motion: no-preference) {
      .fourway-column-card {
        transition: box-shadow 200ms ease, border-color 200ms ease;
      }
      .fourway-column-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      }
    }
  `;

  return (
    <div className="relative">
      <style>{motionStyles}</style>

      <div className="grid grid-cols-2 gap-3">
        {/* GT — top-left */}
        <ColumnCard
          title="GT"
          csvColumnName={csvColumnNames?.gt}
          triplets={gtTriplets}
          selectedIds={selectedIds['gt'] || new Set()}
          columnKey="gt"
          onToggleSelect={onToggleSelect}
          onSelectAll={onSelectAll}
          onClearAll={onClearAll}
        />

        {/* Gemma — top-right */}
        <ColumnCard
          title={names.gemma}
          csvColumnName={csvColumnNames?.gemma}
          triplets={gemmaTriplets}
          selectedIds={selectedIds['gemma'] || new Set()}
          columnKey="gemma"
          onToggleSelect={onToggleSelect}
          onSelectAll={onSelectAll}
          onClearAll={onClearAll}
        />

        {/* Qwen — bottom-left */}
        <ColumnCard
          title={names.qwen}
          csvColumnName={csvColumnNames?.qwen}
          triplets={qwenTriplets}
          selectedIds={selectedIds['qwen'] || new Set()}
          columnKey="qwen"
          onToggleSelect={onToggleSelect}
          onSelectAll={onSelectAll}
          onClearAll={onClearAll}
        />

        {/* GPT — bottom-right */}
        <ColumnCard
          title={names.gpt}
          csvColumnName={csvColumnNames?.gpt}
          triplets={gptTriplets}
          selectedIds={selectedIds['gpt'] || new Set()}
          columnKey="gpt"
          onToggleSelect={onToggleSelect}
          onSelectAll={onSelectAll}
          onClearAll={onClearAll}
        />
      </div>

      {/* Consensus diamond at center intersection */}
      <ConsensusDiamond majorityVote={majorityVote} />
    </div>
  );
};
