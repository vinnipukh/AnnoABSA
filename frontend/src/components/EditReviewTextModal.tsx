import React, { useState } from 'react';

interface EditReviewTextModalProps {
  currentText: string;
  reviewIndex: number;
  onSave: (newText: string) => Promise<void>;
  onClose: () => void;
}

export const EditReviewTextModal: React.FC<EditReviewTextModalProps> = ({
  currentText,
  reviewIndex,
  onSave,
  onClose,
}) => {
  const [text, setText] = useState(currentText);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (text.trim() === currentText) {
      onClose();
      return;
    }
    setSaving(true);
    try {
      await onSave(text.trim());
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-neutral/60" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-base-100 border border-base-300 rounded-2xl shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-base-300">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <h2 className="text-sm font-bold text-base-content">
              İnceleme Metnini Düzenle — #{reviewIndex + 1}
            </h2>
          </div>
          <button onClick={onClose} className="text-base-content/50 hover:text-base-content p-1 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            className="w-full h-48 bg-base-200 border border-base-300 rounded-xl px-4 py-3 text-sm text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-y font-sans leading-relaxed"
            placeholder="İnceleme metnini buraya yazın..."
          />
          <p className="text-[10px] text-base-content/40 mt-1.5">
            {text.length} karakter · Mevcut etiket konumları (at_start/at_end) güncelliğini yitirebilir,
            «Pozisyonları Yeniden Tara» butonu ile düzeltebilirsiniz.
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-base-300">
          <button onClick={onClose}
            className="px-4 py-1.5 text-xs rounded-lg bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300">
            İptal
          </button>
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-1.5 text-xs font-bold rounded-lg bg-primary hover:bg-primary/90 text-primary-content transition-all shadow-sm disabled:opacity-40 flex items-center gap-1.5">
            {saving ? (
              <>
                <div className="w-3 h-3 border-2 border-primary-content border-t-transparent rounded-full animate-spin" />
                Kaydediliyor...
              </>
            ) : 'Kaydet'}
          </button>
        </div>
      </div>
    </div>
  );
};