"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Cpu, User, Zap } from 'lucide-react';
import { Message } from '../types';

interface MessageThreadProps {
  messages: Message[];
}

export const MessageThread = React.memo(function MessageThread({ messages }: MessageThreadProps) {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-5 md:px-8 pt-6 pb-3 scroll-smooth">
      <style>{`
        @keyframes msg-in {
          0%   { opacity: 0; transform: translateY(8px) scale(0.99); filter: blur(3px); }
          100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        @keyframes thinking-dot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
          30%            { transform: translateY(-4px); opacity: 1; }
        }
        @keyframes cursor-blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
        .msg-enter { animation: msg-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) both; }
        .thinking-dot { animation: thinking-dot 1.2s ease-in-out infinite; }
        .thinking-dot:nth-child(2) { animation-delay: 0.15s; }
        .thinking-dot:nth-child(3) { animation-delay: 0.30s; }
        .cursor-blink { animation: cursor-blink 0.85s step-start infinite; }
        
        /* Code block scrollbar */
        .code-scroll::-webkit-scrollbar { height: 3px; }
        .code-scroll::-webkit-scrollbar-thumb { background: rgba(129,140,248,0.3); border-radius: 2px; }
        
        /* Hover effect on messages */
        .msg-bubble { transition: background 0.25s; }
      `}</style>

      <div className="space-y-6 pb-4 max-w-3xl mx-auto">
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className="relative flex gap-4 msg-enter"
            style={{ animationDelay: `${idx * 0.03}s` }}
          >
            {/* Avatar */}
            <div className="shrink-0 flex flex-col items-center gap-2 pt-0.5">
              {msg.role === 'ai' ? (
                <div className="relative">
                  {/* Outer ring — pulses while streaming */}
                  <div className={`absolute -inset-1 rounded-full border transition-all duration-700 ${
                    msg.isStreaming
                      ? 'border-indigo-400/40 animate-pulse'
                      : 'border-indigo-500/15'
                  }`} />
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-600 to-violet-700 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.35)]">
                    <Cpu size={12} className="text-white/90" strokeWidth={1.5} />
                  </div>
                </div>
              ) : (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-700 to-gray-800 border border-white/10 flex items-center justify-center">
                  <User size={12} className="text-gray-400" strokeWidth={1.5} />
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pt-0.5">

              {/* Role label */}
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-[10px] font-mono tracking-[0.15em] uppercase font-medium ${
                  msg.role === 'ai' ? 'text-indigo-400/80' : 'text-gray-500'
                }`}>
                  {msg.role === 'ai' ? 'Assistant' : 'You'}
                </span>
                {msg.isStreaming && !msg.statusText && (
                  <span className="text-[9px] text-indigo-400/50 font-mono flex items-center gap-1">
                    <Zap size={8} className="text-indigo-400/50" />
                    streaming
                  </span>
                )}
              </div>

              {/* Thinking indicator */}
              {msg.role === 'ai' && msg.statusText && (
                <div className="flex items-center gap-3 px-3 py-2 mb-3 rounded-lg border border-violet-500/15 bg-violet-500/[0.04]">
                  <div className="flex items-center gap-1">
                    <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-violet-400 inline-block" />
                    <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-violet-400 inline-block" />
                    <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-violet-400 inline-block" />
                  </div>
                  <span className="text-[10px] text-violet-300/70 font-mono tracking-[0.12em]">
                    {msg.statusText}
                  </span>
                </div>
              )}

              {/* Message body */}
              {msg.content && (
                msg.role === 'user' ? (
                  /* User message bubble */
                  <div className="msg-bubble px-4 py-3 rounded-xl rounded-tl-sm bg-white/[0.04] border border-white/[0.07] hover:border-white/[0.10] hover:bg-white/[0.05]">
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex gap-2 flex-wrap mb-3">
                        {msg.attachments.map((url, i) => (
                          <img
                            key={i}
                            src={`http://localhost:8000${url}`}
                            alt="Attachment"
                            className="w-40 h-auto rounded-lg border border-white/[0.08] opacity-85 hover:opacity-100 transition-opacity"
                          />
                        ))}
                      </div>
                    )}
                    <p className="text-[13.5px] text-gray-300 leading-relaxed tracking-[0.01em] font-light">
                      {msg.content}
                    </p>
                  </div>
                ) : (
                  /* AI message — rich markdown */
                  <div className="text-[13.5px] text-gray-200 leading-[1.85] tracking-[0.01em] font-light antialiased">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => (
                          <p className="mb-3 last:mb-0 text-gray-200">{children}</p>
                        ),
                        strong: ({ children }) => (
                          <strong className="font-semibold text-white">{children}</strong>
                        ),
                        em: ({ children }) => (
                          <em className="italic text-gray-300">{children}</em>
                        ),
                        ul: ({ children }) => (
                          <ul className="my-2 space-y-1 pl-4 list-disc list-outside marker:text-indigo-500">
                            {children}
                          </ul>
                        ),
                        ol: ({ children }) => (
                          <ol className="my-2 space-y-1 pl-4 list-decimal list-outside marker:text-indigo-500">
                            {children}
                          </ol>
                        ),
                        li: ({ children }) => (
                          <li className="text-gray-300">{children}</li>
                        ),
                        h1: ({ children }) => (
                          <h1 className="text-[18px] font-semibold text-white mt-5 mb-2.5 tracking-tight pb-2 border-b border-white/[0.07]">
                            {children}
                          </h1>
                        ),
                        h2: ({ children }) => (
                          <h2 className="text-[15px] font-semibold text-white/90 mt-4 mb-2 tracking-tight">
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className="text-[13px] font-semibold text-indigo-300/90 mt-3 mb-1.5 tracking-[0.05em] uppercase">
                            {children}
                          </h3>
                        ),
                        code: ({ children, className }) => {
                          const isBlock = className?.startsWith('language-');
                          if (!isBlock) {
                            return (
                              <code className="text-[12px] font-mono bg-indigo-500/[0.12] text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-500/20">
                                {children}
                              </code>
                            );
                          }
                          const lang = className?.replace('language-', '') ?? '';
                          return (
                            <div className="relative my-3 rounded-xl overflow-hidden border border-white/[0.08] group/code">
                              {/* Code block header */}
                              <div className="flex items-center justify-between px-4 py-2 bg-white/[0.03] border-b border-white/[0.06]">
                                <span className="text-[10px] font-mono text-gray-500 tracking-widest uppercase">
                                  {lang || 'code'}
                                </span>
                                <div className="flex gap-1.5">
                                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/30 border border-red-500/20" />
                                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/30 border border-yellow-500/20" />
                                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/30 border border-green-500/20" />
                                </div>
                              </div>
                              <SyntaxHighlighter
                                style={oneDark}
                                language={lang}
                                PreTag="div"
                                className="code-scroll"
                                customStyle={{
                                  margin: 0,
                                  borderRadius: 0,
                                  fontSize: '12px',
                                  background: 'rgba(0,0,0,0.55)',
                                  padding: '16px',
                                }}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            </div>
                          );
                        },
                        hr: () => (
                          <hr className="border-none h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-5" />
                        ),
                        blockquote: ({ children }) => (
                          <blockquote className="my-3 pl-4 border-l-2 border-indigo-400/50 bg-indigo-500/[0.04] rounded-r-lg py-2 pr-3">
                            <span className="text-gray-400 italic text-[13px]">{children}</span>
                          </blockquote>
                        ),
                        table: ({ children }) => (
                          <div className="my-3 overflow-x-auto rounded-xl border border-white/[0.08]">
                            <table className="w-full text-[12px]">{children}</table>
                          </div>
                        ),
                        th: ({ children }) => (
                          <th className="px-4 py-2.5 text-left text-[11px] font-mono text-gray-400 tracking-wider uppercase bg-white/[0.03] border-b border-white/[0.08]">
                            {children}
                          </th>
                        ),
                        td: ({ children }) => (
                          <td className="px-4 py-2.5 text-gray-300 border-b border-white/[0.04]">
                            {children}
                          </td>
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>

                    {/* Blinking cursor while streaming */}
                    {msg.isStreaming && !msg.statusText && (
                      <span className="cursor-blink inline-block w-[2.5px] h-[15px] ml-1 align-middle bg-indigo-400 rounded-sm shadow-[0_0_8px_rgba(129,140,248,0.9)]" />
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        ))}

        <div ref={scrollRef} className="h-1" />
      </div>
    </div>
  );
});