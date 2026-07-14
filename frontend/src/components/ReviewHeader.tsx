import React, { useState, useRef, useEffect } from 'react';
import { useTextSelection } from '../hooks/useTextSelection';

interface ReviewHeaderProps {
  reviewText: string;
  translation?: string;
  onEditReview?: () => void;
  onSelectionChange?: (text: string, rect?: DOMRect) => void;
}

export const ReviewHeader: React.FC<ReviewHeaderProps> = ({
  reviewText,
  translation,
  onEditReview,
  onSelectionChange,
}) => {
  const [showTranslation, setShowTranslation] = useState(false);
  const textContainerRef = useRef<HTMLDivElement>(null);

  const [{ selStart, selEnd }, { handleMouseUp }] = useTextSelection(
    reviewText,
    { clickOnToken: true, autoCleanPhrases: true }
  );

  // Notify parent of selection changes (for NLP toolbar)
  useEffect(() => {
    if (onSelectionChange) {
      if (selStart !== null && selEnd !== null) {
        const text = reviewText.substring(selStart, selEnd + 1);
        const sel = window.getSelection();
        let rect: DOMRect | undefined;
        if (sel && sel.rangeCount > 0) {
          rect = sel.getRangeAt(0).getBoundingClientRect();
        }
        onSelectionChange(text, rect);
      } else {
        onSelectionChange('');
      }
    }
  }, [selStart, selEnd, reviewText, onSelectionChange]);

  return (
    <div className="bg-base-300/80 border border-base-300 rounded-xl p-4 mb-4 relative shadow-inner">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-base-300/80">
        <span className="text-xs font-bold text-base-content/60 uppercase tracking-wider flex items-center">
          <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-pulse"></span>
          İnceleme Metni (Raw Review)
        </span>
        <div className="flex items-center gap-1">
          {onEditReview && (
            <button
              onClick={onEditReview}
              className="p-1 rounded-md bg-base-200 hover:bg-base-300 text-base-content/50 hover:text-primary transition-all border border-base-300 min-w-[28px] min-h-[28px] flex items-center justify-center"
              title="Metni Düzenle"
              aria-label="Metni Düzenle"
            >
              {/* Heroicons pencil SVG — no emoji */}
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          {translation && (
            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="text-xs px-2 py-0.5 rounded bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300 min-w-[28px] min-h-[28px]"
            >
              {showTranslation ? 'Orijinali Göster' : 'İngilizce Çeviri'}
            </button>
          )}
        </div>
      </div>

      <div
        ref={textContainerRef}
        onMouseUp={() => { if (textContainerRef.current) handleMouseUp(textContainerRef.current); }}
        className="text-lg md:text-xl font-medium text-base-content leading-relaxed font-sans whitespace-pre-wrap"
      >
        {showTranslation && translation ? translation : reviewText || "Metin bulunamadı."}
      </div>
    </div>
  );
};
