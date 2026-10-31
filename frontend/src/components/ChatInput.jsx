import React, { useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

export default function ChatInput({
  input,
  setInput,
  onSendMessage,
  onStopStreaming,
  isStreaming,
  disabled,
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && input.trim()) {
        onSendMessage();
      }
    }
  };

  return (
    <div className="p-3 sm:p-4 bg-[#070709] border-t border-[#18181f] shrink-0">
      <div className="max-w-3xl mx-auto flex flex-col gap-1.5">
        <div className="relative rounded-2xl bg-[#0f0f14] border border-[#23232e] focus-within:border-[#FF3038]/60 transition-colors shadow-lg p-2.5 flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={isStreaming ? 'FRIDAY is generating exploit intelligence…' : 'State your target or offensive directive…'}
            className="flex-1 bg-transparent border-0 resize-none text-xs sm:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none p-1.5 max-h-44 leading-relaxed font-sans"
          />

          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="p-2 rounded-xl bg-[#1d1d26] hover:bg-[#252533] text-[#FF555D] hover:text-white transition-colors flex items-center justify-center shrink-0 active:scale-95"
              title="Halt Generation"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={onSendMessage}
              disabled={!input.trim() || disabled}
              className={`
                p-2 rounded-xl flex items-center justify-center shrink-0 transition-all
                ${input.trim() && !disabled
                  ? 'bg-[#FF3038] hover:bg-[#ff4d54] text-white shadow-[0_0_12px_rgba(255,48,56,0.35)] active:scale-95'
                  : 'bg-[#14141a] text-zinc-600 cursor-not-allowed'}
              `}
              title="Transmit Directive"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Keyboard hints */}
        <div className="flex items-center justify-between px-2 text-[10px] font-mono text-zinc-500">
          <span>FRIDAY Cyber Intelligence &bull; Strictly Uncensored Red Team</span>
          <span className="hidden sm:inline">Return ↵ to transmit &bull; Shift+Return for newline</span>
        </div>
      </div>
    </div>
  );
}

