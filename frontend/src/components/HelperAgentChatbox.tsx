import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types';

interface HelperAgentChatboxProps {
  initialReasoning: string;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isLoading?: boolean;
}

const MIN_W = 280;
const MIN_H = 200;
const DEFAULT_W = 380;
const DEFAULT_H = 420;

type Corner = 'tl' | 'tr' | 'bl' | 'br';

export const HelperAgentChatbox: React.FC<HelperAgentChatboxProps> = ({
  initialReasoning,
  messages,
  onSendMessage,
  isLoading = false,
}) => {
  const [minimized, setMinimized] = useState(false);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Window geometry — position is controlled by inline style, not Tailwind
  const [w, setW] = useState(DEFAULT_W);
  const [h, setH] = useState(DEFAULT_H);
  const [right, setRight] = useState(16);   // px from viewport right edge
  const [bottom, setBottom] = useState(56);  // px from viewport bottom edge

  const drag = useRef<{ corner: Corner; startX: number; startY: number; r: number; b: number; w: number; h: number } | null>(null);
  const move = useRef<{ startX: number; startY: number; r: number; b: number } | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (!minimized) scrollToBottom();
  }, [messages, initialReasoning, minimized, scrollToBottom]);

  // Universal resize handler for all 4 corners
  const startResize = useCallback((corner: Corner) => (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    drag.current = { corner, startX: e.clientX, startY: e.clientY, r: right, b: bottom, w, h };
    document.body.style.userSelect = 'none';

    const cursors: Record<Corner, string> = { tl: 'nwse-resize', tr: 'nesw-resize', bl: 'nesw-resize', br: 'nwse-resize' };
    document.body.style.cursor = cursors[corner];

    const onMove = (ev: MouseEvent) => {
      if (!drag.current) return;
      const { corner, startX, startY, r, b, w, h } = drag.current;
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;

      let nw = w, nh = h, nr = r, nb = b;

      switch (corner) {
        case 'br': // bottom-right: moves right & down
          nw = Math.max(MIN_W, w + dx);
          nh = Math.max(MIN_H, h + dy);
          break;
        case 'bl': // bottom-left: left edge moves, bottom edge moves
          nw = Math.max(MIN_W, w - dx);
          nr = r + (w - Math.max(MIN_W, w - dx)); // push right offset to keep right edge fixed
          nh = Math.max(MIN_H, h + dy);
          break;
        case 'tr': // top-right: right edge moves, top edge moves
          nw = Math.max(MIN_W, w + dx);
          nh = Math.max(MIN_H, h - dy);
          nb = b + (h - Math.max(MIN_H, h - dy)); // push bottom offset to keep bottom edge fixed
          break;
        case 'tl': // top-left: left edge moves, top edge moves
          nw = Math.max(MIN_W, w - dx);
          nr = r + (w - Math.max(MIN_W, w - dx));
          nh = Math.max(MIN_H, h - dy);
          nb = b + (h - Math.max(MIN_H, h - dy));
          break;
      }

      setW(nw); setH(nh); setRight(nr); setBottom(nb);
    };

    const onUp = () => {
      drag.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [right, bottom, w, h]);

  // Window move handler (drag the header)
  const startMove = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    move.current = { startX: e.clientX, startY: e.clientY, r: right, b: bottom };
    document.body.style.cursor = 'move';
    document.body.style.userSelect = 'none';

    const onMove = (ev: MouseEvent) => {
      if (!move.current) return;
      const dx = ev.clientX - move.current.startX;
      const dy = ev.clientY - move.current.startY;
      setRight(Math.max(0, move.current.r - dx));
      setBottom(Math.max(0, move.current.b - dy));
    };

    const onUp = () => {
      move.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [right, bottom]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  // --- Minimized badge ---
  if (minimized) {
    return (
      <div className="fixed z-50" style={{ bottom, right }}>
        <button
          onClick={() => setMinimized(false)}
          className="group flex items-center gap-2 bg-slate-900 border border-indigo-500/40 rounded-full px-4 py-3 shadow-2xl hover:border-indigo-400 hover:shadow-indigo-500/20 transition-all select-none"
        >
          <div className="relative">
            <span className="text-xl">🤖</span>
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 border-2 border-slate-900 rounded-full" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
              Helper Agent
            </div>
            <div className="text-[10px] text-slate-500 truncate max-w-[140px]">
              {messages.length > 0
                ? `${messages.length} mesaj`
                : initialReasoning ? 'Analiz hazır' : 'Sohbet başlat'}
            </div>
          </div>
          <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      </div>
    );
  }

  // --- Expanded window ---
  return (
    <div
      className="fixed z-50 flex flex-col bg-slate-900/95 border border-indigo-500/40 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden"
      style={{ width: w, height: h, right, bottom }}
    >
      {/* Header — drag to move */}
      <div onMouseDown={startMove} className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-indigo-500/20 select-none flex-shrink-0 cursor-move">
        <div className="flex items-center gap-2">
          <div className="relative">
            <span className="text-base">🤖</span>
            <span className="absolute bottom-0 right-0 w-2 h-2 bg-emerald-500 border-2 border-slate-950 rounded-full" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
              <span>Helper Agent</span>
              <span className="text-[9px] bg-indigo-500/20 text-indigo-300 px-1 py-0.2 rounded border border-indigo-500/30">ABSA</span>
            </h4>
            <p className="text-[9px] text-slate-500">{w}×{h}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setMinimized(true)}
            className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors border border-slate-700" title="Küçült">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 custom-scrollbar text-xs">
        {initialReasoning && (
          <div className="bg-gradient-to-br from-indigo-950/60 to-slate-900 border border-indigo-500/20 rounded-xl p-3 shadow-sm">
            <div className="flex items-center gap-1 text-[10px] font-bold text-indigo-300 mb-1.5 pb-1 border-b border-indigo-500/10">
              <svg className="w-3 h-3 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
              </svg>
              <span>İlk Analiz</span>
            </div>
            <div className="text-slate-200 text-[11px] leading-relaxed whitespace-pre-line">{initialReasoning}</div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex items-start gap-2 ${m.sender === 'agent' ? '' : 'flex-row-reverse'}`}>
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs flex-shrink-0 ${
              m.sender === 'agent' ? 'bg-indigo-600/30 border border-indigo-500/30' : 'bg-blue-600 text-white font-bold'
            }`}>{m.sender === 'agent' ? '🤖' : 'S'}</div>
            <div className={`max-w-[80%] rounded-xl px-3 py-2 text-xs ${
              m.sender === 'agent' ? 'bg-slate-800/90 text-slate-200 border border-slate-700/80' : 'bg-blue-600 text-white'
            }`}><div className="whitespace-pre-line leading-relaxed">{m.text}</div></div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-[10px] text-indigo-400 bg-slate-950/60 w-max px-3 py-2 rounded-xl border border-indigo-500/20">
            <div className="flex gap-1"><div className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce" /><div className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce delay-100" /><div className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce delay-200" /></div>
            <span>Düşünüyor...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex items-center gap-1.5 p-2 bg-slate-950 border-t border-indigo-500/20 flex-shrink-0">
        <input type="text" value={inputText} onChange={e => setInputText(e.target.value)}
          placeholder="Asistana sor..."
          className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all" />
        <button type="submit" disabled={!inputText.trim() || isLoading}
          className="h-7 px-3 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 text-white font-bold text-[10px] tracking-wide transition-all shadow-sm flex items-center justify-center flex-shrink-0">Gönder</button>
      </form>

      {/* 4-corner resize handles */}
      {/* top-left */}
      <div onMouseDown={startResize('tl')} className="absolute top-0 left-0 w-4 h-4 cursor-nwse-resize z-10">
        <svg className="w-3 h-3 text-slate-600 absolute top-0 left-0" viewBox="0 0 12 12" fill="currentColor"><path d="M12 12V9L9 12h3zM3 12h3L0 6v3l3 3zM12 3h-3L9 0h3v3zM0 0v3l3-3H0z" /></svg>
      </div>
      {/* top-right */}
      <div onMouseDown={startResize('tr')} className="absolute top-0 right-0 w-4 h-4 cursor-nesw-resize z-10">
        <svg className="w-3 h-3 text-slate-600 absolute top-0 right-0" viewBox="0 0 12 12" fill="currentColor"><path d="M0 12V9l3 3H0zM9 12h3L6 6v3l3 3zM12 0H9l3 3V0zM0 0v3l3-3H0z" /></svg>
      </div>
      {/* bottom-left */}
      <div onMouseDown={startResize('bl')} className="absolute bottom-0 left-0 w-4 h-4 cursor-nesw-resize z-10">
        <svg className="w-3 h-3 text-slate-600 absolute bottom-0 left-0" viewBox="0 0 12 12" fill="currentColor"><path d="M12 0v3L9 0h3zM12 12h-3l3-3v3zM0 0h3L0 3V0zM3 12H0l3-3v3z" /></svg>
      </div>
      {/* bottom-right */}
      <div onMouseDown={startResize('br')} className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize z-10">
        <svg className="w-3 h-3 text-slate-600 absolute bottom-0 right-0" viewBox="0 0 12 12" fill="currentColor"><path d="M0 12V9l3 3H0zM9 12h3L6 6v3l3 3z" /></svg>
      </div>
    </div>
  );
};
