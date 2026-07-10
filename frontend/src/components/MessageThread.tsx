import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Activity } from 'lucide-react';
import { Message } from '../types';

interface MessageThreadProps {
  messages: Message[];
}

// Memoized — only re-renders when messages array reference changes.
// This prevents the sidebar and thread from thrashing during token streaming.
export const MessageThread = React.memo(function MessageThread({ messages }: MessageThreadProps) {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-8 md:px-12 pt-8 pb-4 scroll-smooth scrollbar-hide">
      <style>{`
        @keyframes materialize {
          0% { opacity: 0; transform: translateY(6px); filter: blur(4px); }
          100% { opacity: 1; transform: translateY(0); filter: blur(0); }
        }
        .msg-enter { animation: materialize 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>

      <div className="space-y-10 pb-8 max-w-3xl mx-auto">
        {messages.map((msg) => (
          <div key={msg.id} className="relative flex gap-6 msg-enter origin-left">

            {/* The Precision Gutter */}
            <div className="w-4 shrink-0 flex flex-col items-center pt-2">
              {msg.role === 'ai' ? (
                <div className="w-1.5 h-1.5 rotate-45 bg-white border border-white/[0.2] shadow-[0_0_12px_rgba(255,255,255,0.4)]" />
              ) : (
                <div className="w-1 h-1 rounded-full bg-white/[0.15]" />
              )}
            </div>

            {/* The Content Stage */}
            <div className="flex-1 pl-2 min-w-0">

              {/* Status text — thinking indicator */}
              {msg.role === 'ai' && msg.statusText && (
                <div className="text-[9px] text-indigo-300/60 font-mono tracking-[0.2em] uppercase mb-2 flex items-center gap-3">
                  <Activity size={10} strokeWidth={2} className="text-indigo-400/50 animate-pulse" />
                  {msg.statusText}
                </div>
              )}

              {/* Message content */}
              {msg.content && (
                msg.role === 'user' ? (
                  // User messages: plain etched text, recedes into glass
                  <div className="text-[13px] text-gray-500 leading-[1.9] tracking-[0.015em] font-light antialiased">
                    {msg.content}
                  </div>
                ) : (
                  // AI messages: markdown rendered inside Obsidian typography
                  <div className="text-[14px] text-gray-200 leading-[1.9] tracking-[0.015em] font-light antialiased">
                    <ReactMarkdown
                      components={{
                        // Paragraphs — inherit parent size/weight
                        p: ({ children }) => (
                          <p className="mb-3 last:mb-0">{children}</p>
                        ),
                        // Bold
                        strong: ({ children }) => (
                          <strong className="font-semibold text-white/90">{children}</strong>
                        ),
                        // Italic
                        em: ({ children }) => (
                          <em className="italic text-gray-300">{children}</em>
                        ),
                        // Unordered list
                        ul: ({ children }) => (
                          <ul className="list-disc list-inside space-y-1 mb-3 text-gray-300">{children}</ul>
                        ),
                        // Ordered list
                        ol: ({ children }) => (
                          <ol className="list-decimal list-inside space-y-1 mb-3 text-gray-300">{children}</ol>
                        ),
                        // H1–H3
                        h1: ({ children }) => (
                          <h1 className="text-[16px] font-semibold text-white mt-4 mb-2 tracking-tight">{children}</h1>
                        ),
                        h2: ({ children }) => (
                          <h2 className="text-[14px] font-semibold text-white/90 mt-3 mb-1.5 tracking-tight">{children}</h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className="text-[13px] font-medium text-white/80 mt-2 mb-1">{children}</h3>
                        ),
                        // Inline code
                        code: ({ children, className }) => {
                          const isBlock = className?.startsWith('language-');
                          if (!isBlock) {
                            return (
                              <code className="text-[12px] font-mono bg-white/[0.06] text-indigo-300 px-1.5 py-0.5 rounded">
                                {children}
                              </code>
                            );
                          }
                          const lang = className?.replace('language-', '') ?? '';
                          return (
                            <SyntaxHighlighter
                              style={oneDark}
                              language={lang}
                              PreTag="div"
                              customStyle={{
                                margin: '12px 0',
                                borderRadius: '8px',
                                fontSize: '12px',
                                border: '1px solid rgba(255,255,255,0.06)',
                                background: 'rgba(0,0,0,0.5)',
                              }}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          );
                        },
                        // Horizontal rule
                        hr: () => (
                          <hr className="border-white/[0.06] my-4" />
                        ),
                        // Blockquote
                        blockquote: ({ children }) => (
                          <blockquote className="border-l-2 border-indigo-400/40 pl-4 text-gray-400 italic my-3">
                            {children}
                          </blockquote>
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>

                    {/* Streaming cursor — only shows while tokens are arriving */}
                    {msg.isStreaming && !msg.statusText && (
                      <span className="inline-block w-[3px] h-[14px] ml-2 align-middle bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        ))}
        <div ref={scrollRef} className="h-4" />
      </div>
    </div>
  );
});