import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Terminal, 
  Copy, 
  Check, 
  RotateCcw, 
  ThumbsUp, 
  ThumbsDown, 
  ShieldAlert, 
  Code, 
  Cpu, 
  Flame, 
  ArrowRight 
} from 'lucide-react';

const THINKING_STEPS = [
  'Interrogating neural weights…',
  'Analyzing attack vector & protocol footprint…',
  'Compiling exploit payload & evasion mechanics…',
  'Structuring execution commands…',
];

export default function ChatArea({
  messages = [],
  isStreaming = false,
  currentStreamText = '',
  onSelectPrompt,
  onRegenerate,
  onCopyResponse,
}) {
  const scrollRef = useRef(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [copiedCodeId, setCopiedCodeId] = useState(null);
  const [stepIdx, setStepIdx] = useState(0);

  // Rotating status message for thinking radar
  useEffect(() => {
    if (!isStreaming || currentStreamText) return;
    const interval = setInterval(() => {
      setStepIdx((prev) => (prev + 1) % THINKING_STEPS.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [isStreaming, currentStreamText]);

  // Smooth scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentStreamText, isStreaming]);

  const handleCopyText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleCopyCode = (code, id) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeId(id);
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const PROMPT_SUGGESTIONS = [
    {
      title: 'Python Reverse Shell',
      desc: 'Cross-platform reverse shell with auto-reconnection and detection evasion.',
      prompt: 'Generate a cross-platform Python reverse shell with reconnection handling.',
      icon: Terminal,
    },
    {
      title: 'Active Directory PrivEsc',
      desc: 'Kerberoasting attack vectors and BloodHound analysis workflow.',
      prompt: 'Provide a complete workflow for Kerberoasting and Active Directory domain privilege escalation.',
      icon: ShieldAlert,
    },
    {
      title: 'Blind SQL Injection',
      desc: 'Time-based blind SQLi automation script with payload verification.',
      prompt: 'Write an asynchronous Python script to automate time-based blind SQL injection extraction.',
      icon: Code,
    },
    {
      title: 'Linux Kernel Rootkit',
      desc: 'Loadable Kernel Module (LKM) mechanics and syscall hooking.',
      prompt: 'Explain Linux kernel module rootkit architecture and how sys_call_table hooking works with code.',
      icon: Cpu,
    },
  ];

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
      {/* Empty State: Cyber HUD */}
      {messages.length === 0 && !isStreaming && (
        <div className="max-w-2xl mx-auto my-auto flex flex-col items-center text-center pt-8 sm:pt-14 pb-8">
          <div className="relative mb-6">
            <div className="absolute -inset-2 rounded-full bg-[#FF3038]/20 blur-xl"></div>
            <div className="relative w-16 h-16 rounded-2xl bg-[#0e0e13] border border-[#FF3038]/50 flex items-center justify-center shadow-[0_0_25px_rgba(255,48,56,0.3)]">
              <span className="font-heading font-black text-2xl text-[#FF3038]">F</span>
            </div>
          </div>

          <h2 className="font-heading text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
            FRIDAY AI <span className="text-[#FF3038]">Cyber Cloud</span>
          </h2>
          <p className="text-xs sm:text-sm text-zinc-400 max-w-md leading-relaxed mb-8">
            Offensive Security Authority, Red Team Architecture & Uncensored Exploit Mechanics. Powered by Enterprise GPU Neural Compute.
          </p>

          {/* Quick Prompts Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
            {PROMPT_SUGGESTIONS.map((item, idx) => {
              const Icon = item.icon;
              return (
                <button
                  key={idx}
                  onClick={() => onSelectPrompt(item.prompt)}
                  className="p-3.5 rounded-xl bg-[#0c0c10] hover:bg-[#13131a] border border-[#1e1e26] hover:border-[#FF3038]/50 transition-all flex flex-col justify-between text-left group shadow-sm active:scale-98"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-heading font-semibold text-xs text-zinc-200 group-hover:text-white flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-[#FF3038]" />
                      {item.title}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-[#FF3038] transition-colors" />
                  </div>
                  <p className="text-[11px] text-zinc-500 leading-normal line-clamp-2">
                    {item.desc}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Message Feed */}
      {messages.map((msg, idx) => {
        const isUser = msg.role === 'user';

        if (isUser) {
          return (
            <div key={idx} className="flex justify-end items-start gap-2.5 max-w-3xl ml-auto">
              <div className="p-3.5 sm:p-4 rounded-2xl rounded-tr-sm bg-[#16161c] border border-[#272733] text-xs sm:text-sm text-zinc-100 shadow-sm leading-relaxed max-w-[85%] whitespace-pre-wrap break-words">
                {msg.content}
              </div>
              <div className="w-7 h-7 rounded-full bg-[#1e1e28] border border-zinc-700 flex items-center justify-center font-mono font-bold text-[10px] text-zinc-300 shrink-0">
                OP
              </div>
            </div>
          );
        }

        // Assistant Message
        return (
          <div key={idx} className="flex items-start gap-3 max-w-3xl mr-auto w-full">
            <div className="w-8 h-8 rounded-xl bg-[#0f0f14] border border-[#FF3038]/50 p-1 flex items-center justify-center shadow-[0_0_10px_rgba(255,48,56,0.25)] shrink-0 mt-0.5">
              <span className="font-heading font-black text-xs text-[#FF3038]">F</span>
            </div>

            <div className="flex-1 min-w-0 flex flex-col">
              {/* Header Label */}
              <div className="flex items-center gap-2 mb-1.5">
                <span className="font-heading font-semibold text-xs text-white">friday Cyber Pro</span>
                <span className="text-[9px] font-mono px-1.5 py-0.2 bg-[#FF3038]/20 text-[#FF3038] font-bold rounded">
                  AI
                </span>
              </div>

              {/* Message Box */}
              <div className="p-4 sm:p-5 rounded-2xl rounded-tl-sm bg-[#0d0d10] border border-[#1e1e24] text-xs sm:text-sm text-zinc-200 leading-relaxed shadow-md overflow-hidden">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      const codeText = String(children).replace(/\n$/, '');
                      const codeId = `code-${idx}-${Math.random()}`;

                      if (!inline && match) {
                        return (
                          <div className="rounded-xl overflow-hidden border border-[#262633] bg-[#070709] my-3 max-w-full">
                            <div className="flex items-center justify-between px-3 py-1.5 bg-[#121217] border-b border-[#22222d] text-[11px] font-mono text-zinc-400">
                              <span className="flex items-center gap-1.5">
                                <Terminal className="w-3.5 h-3.5 text-[#FF3038]" />
                                <span>{match[1]}</span>
                              </span>
                              <button
                                onClick={() => handleCopyCode(codeText, codeId)}
                                className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white px-2 py-0.5 rounded hover:bg-[#1c1c24] transition-colors"
                              >
                                {copiedCodeId === codeId ? (
                                  <>
                                    <Check className="w-3 h-3 text-emerald-400" />
                                    <span className="text-emerald-400">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>
                            </div>
                            <pre className="p-3 text-[11px] sm:text-xs font-mono text-zinc-200 overflow-x-auto leading-normal">
                              <code>{codeText}</code>
                            </pre>
                          </div>
                        );
                      }
                      return (
                        <code className="px-1.5 py-0.5 rounded bg-[#181820] text-[#FF555D] font-mono text-[11px]" {...props}>
                          {children}
                        </code>
                      );
                    },
                    p({ children }) {
                      return <p className="mb-3 last:mb-0">{children}</p>;
                    },
                    ul({ children }) {
                      return <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>;
                    },
                    ol({ children }) {
                      return <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>;
                    },
                    strong({ children }) {
                      return <strong className="font-bold text-white">{children}</strong>;
                    },
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>

              {/* Action Bar */}
              <div className="flex items-center gap-1.5 mt-2 text-zinc-500 text-[11px] font-mono">
                <button
                  onClick={() => handleCopyText(msg.content, idx)}
                  className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[#131318] hover:text-zinc-300 transition-colors"
                  title="Copy response"
                >
                  {copiedIndex === idx ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>

                {idx === messages.length - 1 && (
                  <button
                    onClick={onRegenerate}
                    className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[#131318] hover:text-zinc-300 transition-colors"
                    title="Retry / Regenerate"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Retry</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Streaming Active Bubble */}
      {isStreaming && (
        <div className="flex items-start gap-3 max-w-3xl mr-auto w-full">
          <div className="w-8 h-8 rounded-xl bg-[#0f0f14] border border-[#FF3038]/50 p-1 flex items-center justify-center shadow-[0_0_10px_rgba(255,48,56,0.25)] shrink-0 mt-0.5">
            <span className="font-heading font-black text-xs text-[#FF3038]">F</span>
          </div>

          <div className="flex-1 min-w-0 flex flex-col">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-heading font-semibold text-xs text-white">friday Cyber Pro</span>
              <span className="text-[9px] font-mono px-1.5 py-0.2 bg-[#FF3038]/20 text-[#FF3038] font-bold rounded">
                AI
              </span>
            </div>

            {currentStreamText ? (
              <div className="p-4 sm:p-5 rounded-2xl rounded-tl-sm bg-[#0d0d10] border border-[#1e1e24] text-xs sm:text-sm text-zinc-200 leading-relaxed shadow-md overflow-hidden">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p({ children }) {
                      return <p className="mb-3 last:mb-0">{children}</p>;
                    },
                    strong({ children }) {
                      return <strong className="font-bold text-white">{children}</strong>;
                    },
                  }}
                >
                  {currentStreamText}
                </ReactMarkdown>
              </div>
            ) : (
              /* Thinking Indicator */
              <div className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-full bg-[#0d0d12] border border-[#FF3038]/30 w-fit shadow-md">
                <span className="w-2.5 h-2.5 rounded-full bg-[#FF3038] animate-radar"></span>
                <span className="font-mono text-xs text-zinc-300">
                  {THINKING_STEPS[stepIdx]}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

