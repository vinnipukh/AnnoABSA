import React, { useState, useCallback } from 'react';
import { Settings } from '../types';

interface SettingsPanelProps {
  settings: Settings;
  onSave: (updates: Record<string, unknown>) => Promise<void>;
  onRescanPositions: () => Promise<void>;
  onClose: () => void;
}

type FormState = Record<string, unknown>;

const ALL_SENTIMENT_ELEMENTS = ['aspect_term', 'aspect_category', 'sentiment_polarity', 'opinion_term'];
const POLARITY_OPTIONS = ['positive', 'negative', 'neutral'];

// ── Helper sub-components ──

function SectionTitle({ title }: { title: string }) {
  return (
    <h3 className="text-xs font-bold text-base-content/80 uppercase tracking-wider mb-3 pb-2 border-b border-base-300">
      {title}
    </h3>
  );
}

function ToggleRow({ label, key_, form, setForm }: {
  label: string; key_: string; form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>>;
}) {
  return (
    <label className="flex items-center justify-between py-2 px-1 rounded-lg hover:bg-base-200/50 cursor-pointer select-none transition-colors">
      <span className="text-xs text-base-content">{label}</span>
      <input
        type="checkbox"
        checked={!!form[key_]}
        onChange={(e) => setForm((p) => ({ ...p, [key_]: e.target.checked }))}
        className="rounded border-base-300 bg-base-200 text-primary focus:ring-primary w-4 h-4"
      />
    </label>
  );
}

function TextRow({ label, key_, form, setForm, placeholder, type = 'text' }: {
  label: string; key_: string; form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>>;
  placeholder?: string; type?: string;
}) {
  return (
    <div className="py-1.5 px-1">
      <label className="text-xs text-base-content/60 block mb-1">{label}</label>
      <input
        type={type}
        value={(form[key_] as string) ?? ''}
        onChange={(e) => setForm((p) => ({ ...p, [key_]: e.target.value }))}
        placeholder={placeholder}
        className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-1.5 text-xs text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
      />
    </div>
  );
}

function NumberRow({ label, key_, form, setForm, min = 0 }: {
  label: string; key_: string; form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>>;
  min?: number;
}) {
  return (
    <div className="py-1.5 px-1">
      <label className="text-xs text-base-content/60 block mb-1">{label}</label>
      <input
        type="number"
        min={min}
        value={(form[key_] as number) ?? 0}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === '') {
            setForm((p) => ({ ...p, [key_]: '' }));
          } else {
            const num = parseInt(raw, 10);
            setForm((p) => ({ ...p, [key_]: isNaN(num) ? raw : num }));
          }
        }}
        className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-1.5 text-xs text-base-content focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
      />
    </div>
  );
}

function SelectRow({ label, key_, form, setForm, options }: {
  label: string; key_: string; form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>>;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="py-1.5 px-1">
      <label className="text-xs text-base-content/60 block mb-1">{label}</label>
      <select
        value={form[key_] as string}
        onChange={(e) => setForm((p) => ({ ...p, [key_]: e.target.value }))}
        className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-1.5 text-xs text-base-content focus:outline-none focus:border-primary truncate"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function ChipSelector({ label, key_, items, form, setForm, emptyLabel = 'Boş' }: {
  label: string; key_: string; items: string[]; form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>; emptyLabel?: string;
}) {
  const toggleArrayItem = (key: string, item: string) => {
    setForm((prev) => {
      const arr: string[] = [...(prev[key] as string[])];
      const idx = arr.indexOf(item);
      if (idx >= 0) arr.splice(idx, 1);
      else arr.push(item);
      return { ...prev, [key]: arr };
    });
  };

  const selected = form[key_] as string[];
  return (
    <div className="py-1.5 px-1">
      <label className="text-xs text-base-content/60 block mb-1.5">{label}</label>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => {
          const isOn = selected.includes(item);
          return (
            <button
              key={item}
              onClick={() => toggleArrayItem(key_, item)}
              className={`text-[10px] px-2 py-0.5 rounded-full border font-medium transition-all select-none ${
                isOn
                  ? 'bg-primary/20 text-primary border-primary/40'
                  : 'bg-base-200 text-base-content/50 border-base-300 hover:text-base-content hover:border-base-200'
              }`}
            >
              {item}
            </button>
          );
        })}
      </div>
      {selected.length === 0 && <span className="text-[10px] text-base-content/40 italic">{emptyLabel}</span>}
    </div>
  );
}

function arraysEqual(a: unknown[], b: unknown[]): boolean {
  const sa = [...a].sort();
  const sb = [...b].sort();
  return JSON.stringify(sa) === JSON.stringify(sb);
}

// ── Main component ──

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  onSave,
  onRescanPositions,
  onClose,
}) => {
  const [form, setForm] = useState<FormState>(() => {
    const initial: FormState = {};
    initial.sentiment_elements = [...(settings.sentiment_elements || ALL_SENTIMENT_ELEMENTS)];
    initial.sentiment_polarity_options = [...(settings.sentiment_polarity_options || POLARITY_OPTIONS)];
    initial.aspect_categories = (settings.aspect_categories || []).join(', ');
    initial.implicit_aspect_term_allowed = settings.implicit_aspect_term_allowed ?? true;
    initial.implicit_opinion_term_allowed = settings.implicit_opinion_term_allowed ?? false;
    initial.click_on_token = settings.click_on_token ?? true;
    initial.save_phrase_positions = settings.save_phrase_positions ?? true;
    initial.auto_clean_phrases = settings.auto_clean_phrases ?? true;
    initial.enable_pre_prediction = settings.enable_pre_prediction ?? false;
    initial.disable_ai_automatic_prediction = settings.disable_ai_automatic_prediction ?? false;
    initial.enable_helper_agent = settings.enable_helper_agent ?? true;
    initial.llm_provider = settings.llm_provider || 'ollama';
    initial.llm_model = settings.llm_model || 'gemma3:4b';
    initial.vllm_model = settings.vllm_model || '';
    initial.openai_key = settings.openai_key || '';
    initial.anthropic_key = settings.anthropic_key || '';
    initial.vllm_url = settings.vllm_url || '';
    initial.n_few_shot = settings.n_few_shot ?? 10;
    initial.compare_model_a_name = settings.compare_model_a_name || '';
    initial.compare_model_b_name = settings.compare_model_b_name || '';
    initial.theme = settings.theme || 'dark';
    return initial;
  });

  const [saving, setSaving] = useState(false);
  const [rescanned, setRescanned] = useState(false);

  const hasChanged = useCallback(() => {
    for (const key of Object.keys(form)) {
      const current = (settings as any)[key];
      const next = form[key];
      if (Array.isArray(current) && Array.isArray(next)) {
        if (!arraysEqual(current, next)) return true;
      } else if (current !== next) {
        return true;
      }
    }
    return false;
  }, [form, settings]);

  const handleSave = async () => {
    setSaving(true);
    const changed: Record<string, unknown> = {};
    for (const key of Object.keys(form)) {
      const current = (settings as any)[key];
      let next = form[key];
      if (Array.isArray(current) && Array.isArray(next)) {
        if (!arraysEqual(current, next)) {
          changed[key] = next;
        }
      } else if (current !== next) {
        if (key === 'aspect_categories' && typeof next === 'string') {
          next = next.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
        if (key === 'n_few_shot' && typeof next === 'string') {
          next = next === '' ? 0 : parseInt(next as string, 10) || 0;
        }
        changed[key] = next;
      }
    }
    if (changed.openai_key === '') changed.openai_key = null;
    if (changed.anthropic_key === '') changed.anthropic_key = null;
    if (changed.vllm_url === '') changed.vllm_url = null;
    if (changed.compare_model_a_name === '') changed.compare_model_a_name = null;
    if (changed.compare_model_b_name === '') changed.compare_model_b_name = null;
    if (changed.vllm_model === '') changed.vllm_model = null;

    await onSave(changed);
    setSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-10 pb-10">
      <div className="absolute inset-0 bg-neutral/60" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-base-100 border border-base-300 rounded-2xl shadow-2xl overflow-hidden max-h-[calc(100vh-5rem)] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-base-300 bg-base-100/90 flex-shrink-0">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <h2 className="text-sm font-bold text-base-content">Ayarlar</h2>
          </div>
          <button onClick={onClose} className="text-base-content/50 hover:text-base-content p-1 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 px-5 py-4 space-y-5 custom-scrollbar">
          <section>
            <SectionTitle title="0. Görünüm" />
            <SelectRow label="Tema" key_="theme" form={form} setForm={setForm}
              options={[
                { value: 'light', label: 'Açık' },
                { value: 'dark', label: 'Koyu' },
                { value: 'coffee', label: 'Kahve' },
                { value: 'forest', label: 'Orman' },
                { value: 'cupcake', label: 'Pastel' },
                { value: 'aqua', label: 'Su' },
                { value: 'lemonade', label: 'Limonata' },
              ]}
            />
          </section>

          <section>
            <SectionTitle title="1. Ek Açıklama" />
            <ChipSelector label="Duygu Öğeleri (Sentiment Elements)" key_="sentiment_elements"
              items={ALL_SENTIMENT_ELEMENTS} form={form} setForm={setForm} emptyLabel="En az bir öğe seçin" />
            <ChipSelector label="Kutuplar (Polarities)" key_="sentiment_polarity_options"
              items={POLARITY_OPTIONS} form={form} setForm={setForm} />
            <TextRow label="Kategori Listesi (virgülle ayırın)" key_="aspect_categories"
              form={form} setForm={setForm} placeholder="location general, food prices, food quality, ..." />
            <div className="mt-1 space-y-0.5">
              <ToggleRow label="Örtük görünüş terimine izin ver" key_="implicit_aspect_term_allowed" form={form} setForm={setForm} />
              <ToggleRow label="Örtük görüş terimine izin ver" key_="implicit_opinion_term_allowed" form={form} setForm={setForm} />
              <ToggleRow label="Token'a tıkla (Click-on-Token)" key_="click_on_token" form={form} setForm={setForm} />
              <ToggleRow label="Pozisyonları kaydet" key_="save_phrase_positions" form={form} setForm={setForm} />
              <ToggleRow label="İfadeleri otomatik temizle" key_="auto_clean_phrases" form={form} setForm={setForm} />
            </div>
          </section>

          <section>
            <SectionTitle title="2. Yapay Zeka / Dil Modeli" />
            <div className="space-y-0.5">
              <ToggleRow label="AI önerilerini etkinleştir" key_="enable_pre_prediction" form={form} setForm={setForm} />
              <ToggleRow label="Otomatik AI tahminini devre dışı bırak" key_="disable_ai_automatic_prediction" form={form} setForm={setForm} />
              <ToggleRow label="Yardımcı Asistanı etkinleştir" key_="enable_helper_agent" form={form} setForm={setForm} />
            </div>
            <SelectRow label="LLM Sağlayıcı" key_="llm_provider" form={form} setForm={setForm}
              options={[
                { value: 'ollama', label: 'Ollama (yerel)' },
                { value: 'openai', label: 'OpenAI' },
                { value: 'anthropic', label: 'Anthropic' },
                { value: 'vllm', label: 'vLLM' },
              ]}
            />
            <TextRow label="LLM Modeli" key_="llm_model" form={form} setForm={setForm} placeholder="gemma3:4b" />
            <TextRow label="vLLM Modeli" key_="vllm_model" form={form} setForm={setForm} placeholder="(opsiyonel, aksi halde LLM modeli kullanılır)" />
            <TextRow label="OpenAI Anahtarı" key_="openai_key" form={form} setForm={setForm} placeholder="sk-..." type="password" />
            <TextRow label="Anthropic Anahtarı" key_="anthropic_key" form={form} setForm={setForm} placeholder="sk-ant-..." type="password" />
            <TextRow label="vLLM URL" key_="vllm_url" form={form} setForm={setForm} placeholder="http://localhost:8001/v1" />
            <NumberRow label="Few-Shot Örnek Sayısı" key_="n_few_shot" form={form} setForm={setForm} min={0} />
          </section>

          <section>
            <SectionTitle title="4. Veri" />
            <TextRow label="Model A Adı" key_="compare_model_a_name" form={form} setForm={setForm} placeholder="Model A" />
            <TextRow label="Model B Adı" key_="compare_model_b_name" form={form} setForm={setForm} placeholder="Model B" />
          </section>

          <section>
            <SectionTitle title="5. Araçlar" />
            <button
              onClick={async () => {
                setRescanned(true);
                await onRescanPositions();
                setRescanned(false);
              }}
              disabled={rescanned}
              className="w-full py-2 px-3 rounded-lg bg-base-200 hover:bg-base-300 active:bg-base-200 text-base-content/80 text-xs font-semibold border border-base-300 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {rescanned ? (
                <>
                  <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  Taranıyor...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Pozisyonları Yeniden Tara
                </>
              )}
            </button>
          </section>
        </div>

        <div className="flex items-center justify-between px-5 py-3 border-t border-base-300 bg-base-100/90 flex-shrink-0">
          <span className="text-[10px] text-base-content/40">
            {hasChanged() ? '⚡ Kaydedilmemiş değişiklikler var' : '✓ Tüm ayarlar güncel'}
          </span>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-3 py-1.5 text-xs rounded-lg bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300">
              İptal
            </button>
            <button onClick={handleSave} disabled={!hasChanged() || saving}
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
    </div>
  );
};
