import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';

interface HelperAgentChatboxProps {
  initialReasoning: string;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isLoading?: boolean;
}

export const HelperAgentChatbox: React.FC<HelperAgentChatboxProps> = ({
  initialReasoning,
  messages,
  onSendMessage,
  isLoading = false
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (!isCollapsed) {
      scrollToBottom();
    }
  }, [messages, initialReasoning, isCollapsed]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  if (isCollapsed) {
    return (
      <div
        onClick={() => setIsCollapsed(false)}
        className="h-full bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-2xl p-4 cursor-pointer hover:border-indigo-400 transition-all flex items-center justify-between shadow-lg group select-none"
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-xl shadow-inner group-hover:scale-105 transition-transform">
            🤖
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
              Helper Agent Chatbox (Yardımcı AI Asistan)
            </h4>
            <p className="text-xs text-slate-400 line-clamp-1 max-w-md">
              {initialReasoning || "Akıl yürütme analizi hazır. Açmak için tıklayın."}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2 text-xs text-indigo-400 font-semibold bg-indigo-500/10 px-3 py-1.5 rounded-lg border border-indigo-500/20">
          <span>Sohbeti Genişlet</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900/90 border border-indigo-500/30 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-md">
      {/* Top Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-indigo-500/20 select-none">
        <div className="flex items-center space-x-2.5">
          <div className="relative">
            <span className="text-xl">🤖</span>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-slate-950 rounded-full"></span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
              <span>Helper Agent</span>
              <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded border border-indigo-500/30">ABSA EXPERT</span>
            </h4>
            <p className="text-[10px] text-slate-400 tracking-tight">Model akıl yürütmesi & Karar rehberi</p>
          </div>
        </div>

        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors border border-slate-700 flex items-center gap-1 text-xs"
          title="Küçült (Minimize)"
        >
          <span className="text-[11px] hidden sm:inline font-medium">Küçült</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar text-sm">
        {/* Initial Reasoning Card */}
        {initialReasoning && (
          <div className="bg-gradient-to-br from-indigo-950/60 to-slate-900 border border-indigo-500/30 rounded-xl p-3.5 shadow-md">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-300 mb-1.5 pb-1 border-b border-indigo-500/20">
              <svg className="w-3.5 h-3.5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
              </svg>
              <span>İlk Akıl Yürütme Analizi (Initial Reasoning)</span>
            </div>
            <div className="text-slate-200 text-xs sm:text-sm whitespace-pre-line leading-relaxed">
              {initialReasoning}
            </div>
          </div>
        )}

        {/* Chat Conversation History */}
        {messages.map((m) => {
          const isAgent = m.sender === 'agent';
          return (
            <div
              key={m.id}
              className={`flex items-start gap-2.5 ${isAgent ? 'justify-start' : 'justify-end'}`}
            >
              {isAgent && (
                <div className="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
                  🤖
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-xl px-3.5 py-2.5 text-xs sm:text-sm ${
                  isAgent
                    ? 'bg-slate-800/90 text-slate-200 border border-slate-700/80 shadow'
                    : 'bg-blue-600 text-white shadow-md font-medium'
                }`}
              >
                <div className="whitespace-pre-line leading-relaxed">{m.text}</div>
              </div>

              {!isAgent && (
                <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-xs text-white font-bold flex-shrink-0 mt-0.5">
                  SİZ
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div className="flex items-center space-x-2 text-xs text-indigo-400 bg-slate-950/60 w-max px-3 py-2 rounded-xl border border-indigo-500/20">
            <div className="flex space-x-1">
              <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-100"></div>
              <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-200"></div>
            </div>
            <span>Asistan düşünüyor...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bottom Bar */}
      <form onSubmit={handleSend} className="p-3 bg-slate-950 border-t border-indigo-500/20 flex items-center gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Etiket hakkında asistanla tartışın... (Örn: Model A niye eksi vermiş?)"
          className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
        />

        <button
          type="submit"
          disabled={!inputText.trim() || isLoading}
          className="h-10 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 text-white font-bold text-xs tracking-wide transition-all shadow-md flex items-center justify-center flex-shrink-0"
        >
          <span>Gönder</span>
        </button>
      </form>
    </div>
  );
};
