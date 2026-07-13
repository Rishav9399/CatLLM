"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MessageSquare, ChevronLeft, ChevronRight, Trash2, Sparkles } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { getSessions, createChatSession, deleteChatSession } from '@/lib/api';
import type { SessionPreview } from '@/types';

interface SidebarProps {
  activeSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: (sessionId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSessionId,
  onSessionSelect,
  onNewChat,
}) => {
  const [sessions, setSessions] = useState<SessionPreview[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const LIMIT = 20;

  const loadSessions = useCallback(async (reset = false) => {
    const currentOffset = reset ? 0 : offset;
    try {
      const data = await getSessions(LIMIT, currentOffset);
      setSessions(prev => reset ? data.sessions : [...prev, ...data.sessions]);
      setTotal(data.total);
      if (!reset) setOffset(currentOffset + LIMIT);
    } catch (err) {
      console.error('[Sidebar] Failed to load sessions:', err);
    }
  }, [offset]);

  useEffect(() => {
    loadSessions(true);
    setOffset(LIMIT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || isLoadingMore) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    if (nearBottom && sessions.length < total) {
      setIsLoadingMore(true);
      loadSessions(false).finally(() => setIsLoadingMore(false));
    }
  }, [isLoadingMore, sessions.length, total, loadSessions]);

  const handleNewChat = async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      const sessionId = await createChatSession();
      const newPreview: SessionPreview = {
        id: sessionId,
        title: 'New Session',
        created_at: new Date().toISOString(),
        preview: '',
      };
      setSessions(prev => [newPreview, ...prev]);
      setTotal(t => t + 1);
      onNewChat(sessionId);
    } catch (err) {
      console.error('[Sidebar] Failed to create session:', err);
    } finally {
      setIsCreating(false);
    }
  };

  useEffect(() => {
    if (!activeSessionId) return;
    const timer = setTimeout(() => loadSessions(true).then(() => setOffset(LIMIT)), 800);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      setTotal(t => Math.max(0, t - 1));
      if (sessionId === activeSessionId) onNewChat('');
    } catch (err) {
      console.error('[Sidebar] Failed to delete session:', err);
    }
  };

  return (
    <aside
      className={`
        relative flex flex-col h-full
        transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
        ${isCollapsed ? 'w-[56px]' : 'w-[260px]'}
      `}
    >
      {/* Visible glass panel with glowing right border */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'rgba(6, 6, 14, 0.85)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          borderRight: '1px solid rgba(129,140,248,0.14)',
          boxShadow: '1px 0 20px rgba(0,0,0,0.5), inset -1px 0 0 rgba(255,255,255,0.03)',
        }}
      />

      {/* Right-edge glow */}
      <div
        className="absolute right-0 top-16 bottom-16 w-px pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, transparent, rgba(129,140,248,0.25), transparent)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full py-5 gap-3 overflow-hidden">

        {/* Logo / Brand header */}
        <div className={`px-3 shrink-0 mb-1 flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
          <div className="relative w-7 h-7 flex-shrink-0">
            <div className="absolute inset-0 rounded-lg border border-indigo-500/40 animate-spin-slow" />
            <div className="absolute inset-[2px] rounded-md border border-indigo-400/20 animate-spin-reverse" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />
            </div>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="shimmer-text text-[11px] font-semibold tracking-[0.18em] uppercase leading-none whitespace-nowrap">
                CatLLM
              </span>
              <span className="text-[8px] text-gray-700 font-mono tracking-widest mt-0.5">
                Sessions
              </span>
            </div>
          )}
        </div>

        {/* Top separator */}
        <div className="mx-3 h-px shrink-0" style={{ background: 'linear-gradient(90deg, transparent, rgba(129,140,248,0.15), transparent)' }} />

        {/* New Chat button */}
        <div className="px-3 shrink-0">
          <button
            onClick={handleNewChat}
            disabled={isCreating}
            className={`
              relative flex items-center gap-2.5 w-full rounded-xl overflow-hidden
              transition-all duration-300 group
              disabled:opacity-40 disabled:cursor-not-allowed
              ${isCollapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2.5'}
            `}
            style={{
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(129,140,248,0.2)',
              boxShadow: '0 0 15px rgba(99,102,241,0.05)',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.14)';
              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(129,140,248,0.40)';
              (e.currentTarget as HTMLElement).style.boxShadow = '0 0 20px rgba(99,102,241,0.15)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.08)';
              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(129,140,248,0.2)';
              (e.currentTarget as HTMLElement).style.boxShadow = '0 0 15px rgba(99,102,241,0.05)';
            }}
          >
            {isCreating ? (
              <Sparkles size={14} strokeWidth={1.5} className="text-indigo-400 animate-pulse shrink-0" />
            ) : (
              <Plus size={14} strokeWidth={2} className="text-indigo-400 shrink-0" />
            )}
            {!isCollapsed && (
              <span className="text-[11px] font-mono tracking-[0.12em] text-indigo-300 uppercase whitespace-nowrap">
                {isCreating ? 'Creating…' : 'New Chat'}
              </span>
            )}
          </button>
        </div>

        {/* Sessions label */}
        {!isCollapsed && sessions.length > 0 && (
          <div className="px-4 shrink-0">
            <span className="text-[9px] font-mono text-gray-700 tracking-[0.2em] uppercase">
              Recent · {total}
            </span>
          </div>
        )}

        {/* Sessions list */}
        <div
          ref={listRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-2 space-y-0.5 py-1"
        >
          {sessions.map((session, idx) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              isCollapsed={isCollapsed}
              index={idx}
              onClick={() => onSessionSelect(session.id)}
              onDelete={() => handleDeleteSession(session.id)}
            />
          ))}

          {isLoadingMore && (
            <div className="flex justify-center py-4">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1 h-1 rounded-full bg-indigo-500/50"
                    style={{ animation: `thinking-dot 1.2s ease-in-out ${i * 0.15}s infinite` }}
                  />
                ))}
              </div>
            </div>
          )}

          {sessions.length === 0 && !isLoadingMore && !isCollapsed && (
            <div className="flex flex-col items-center gap-2 pt-10 px-4">
              <MessageSquare size={22} strokeWidth={1} className="text-gray-700" />
              <p className="text-[10px] text-gray-700 font-mono text-center tracking-wide">
                No sessions yet
              </p>
              <p className="text-[9px] text-gray-800 text-center">
                Start a new chat to begin
              </p>
            </div>
          )}
        </div>

        {/* Bottom separator */}
        <div className="mx-3 h-px shrink-0" style={{ background: 'linear-gradient(90deg, transparent, rgba(129,140,248,0.10), transparent)' }} />

        {/* Collapse toggle */}
        <div className={`px-3 shrink-0 ${isCollapsed ? 'flex justify-center' : ''}`}>
          <button
            onClick={() => setIsCollapsed(c => !c)}
            className="flex items-center gap-2 px-2.5 py-2 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-white/[0.04] border border-transparent hover:border-white/[0.07] transition-all duration-200 w-full"
            style={isCollapsed ? { justifyContent: 'center' } : {}}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed
              ? <ChevronRight size={13} strokeWidth={1.5} />
              : <ChevronLeft size={13} strokeWidth={1.5} />
            }
            {!isCollapsed && (
              <span className="text-[10px] font-mono tracking-wider">Collapse</span>
            )}
          </button>
        </div>
      </div>
    </aside>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SessionItem
// ─────────────────────────────────────────────────────────────────────────────
const SessionItem = React.memo(function SessionItem({
  session,
  isActive,
  isCollapsed,
  index,
  onClick,
  onDelete,
}: {
  session: SessionPreview;
  isActive: boolean;
  isCollapsed: boolean;
  index: number;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); }
      }}
      className={`
        relative flex items-center gap-3 w-full rounded-xl text-left
        transition-all duration-250 group cursor-pointer
        ${isCollapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2.5'}
      `}
      style={{
        animationDelay: `${index * 0.04}s`,
        background: isActive ? 'rgba(99,102,241,0.10)' : 'transparent',
        border: isActive ? '1px solid rgba(129,140,248,0.25)' : '1px solid transparent',
        boxShadow: isActive ? '0 0 15px rgba(99,102,241,0.08)' : 'none',
      }}
      onMouseEnter={e => {
        if (!isActive) {
          (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
          (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.06)';
        }
      }}
      onMouseLeave={e => {
        if (!isActive) {
          (e.currentTarget as HTMLElement).style.background = 'transparent';
          (e.currentTarget as HTMLElement).style.borderColor = 'transparent';
        }
      }}
    >
      {/* Active left bar */}
      {isActive && (
        <div
          className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full"
          style={{ background: 'linear-gradient(to bottom, rgba(129,140,248,0.8), rgba(99,102,241,0.4))' }}
        />
      )}

      {/* Icon */}
      <MessageSquare
        size={13}
        strokeWidth={1.5}
        className={`shrink-0 transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-600 group-hover:text-gray-400'}`}
      />

      {!isCollapsed && (
        <>
          <div className="flex-1 min-w-0">
            <p className={`text-[12px] font-light truncate leading-tight transition-colors ${
              isActive ? 'text-gray-200' : 'text-gray-500 group-hover:text-gray-300'
            }`}>
              {session.title}
            </p>
            {session.preview && (
              <p className="text-[10px] text-gray-700 truncate mt-0.5 leading-tight group-hover:text-gray-600 transition-colors">
                {session.preview}
              </p>
            )}
            <p className="text-[9px] text-gray-800 font-mono mt-0.5">
              {formatDistanceToNow(new Date(session.created_at), { addSuffix: true })}
            </p>
          </div>

          {/* Delete button */}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 border border-transparent hover:border-red-500/20 text-gray-600 hover:text-red-400 transition-all duration-200 absolute right-2"
            aria-label="Delete chat"
          >
            <Trash2 size={11} strokeWidth={1.5} />
          </button>
        </>
      )}
    </div>
  );
});
