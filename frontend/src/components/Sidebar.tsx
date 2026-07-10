"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MessageSquare, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
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

  // Initial load
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

  // Infinite scroll — load next page when user reaches the bottom
  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || isLoadingMore) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    if (nearBottom && sessions.length < total) {
      setIsLoadingMore(true);
      loadSessions(false).finally(() => setIsLoadingMore(false));
    }
  }, [isLoadingMore, sessions.length, total, loadSessions]);

  // New chat
  const handleNewChat = async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      const sessionId = await createChatSession();
      // Prepend the new session to the list immediately (optimistic update)
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

  // After streaming a message, refresh the session list so preview updates
  // (called by parent via a ref if needed — for now we do a soft refresh on
  // activeSessionId change, which covers the "first message sent" case)
  useEffect(() => {
    if (!activeSessionId) return;
    // Give the backend 800ms to commit the message before re-fetching previews
    const timer = setTimeout(() => loadSessions(true).then(() => setOffset(LIMIT)), 800);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      setTotal(t => Math.max(0, t - 1));
      
      // If we deleted the active session, reset state by calling onNewChat
      if (sessionId === activeSessionId) {
        onNewChat('');
      }
    } catch (err) {
      console.error('[Sidebar] Failed to delete session:', err);
    }
  };

  return (
    <aside
      className={`
        relative flex flex-col h-full
        transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
        ${isCollapsed ? 'w-[52px]' : 'w-[260px]'}
      `}
    >
      {/* Frosted glass panel — same token family as ObsidianSlab */}
      <div className="
        absolute inset-0
        bg-white/[0.02] backdrop-blur-md
        border-r border-white/[0.04]
      " />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full py-6 gap-4 overflow-hidden">

        {/* Collapse toggle */}
        <button
          onClick={() => setIsCollapsed(c => !c)}
          className="
            absolute -right-3 top-8 z-20
            w-6 h-6 rounded-full flex items-center justify-center
            bg-[#0c0c0c] border border-white/[0.08]
            text-gray-500 hover:text-white
            transition-colors duration-300
          "
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed
            ? <ChevronRight size={12} strokeWidth={1.5} />
            : <ChevronLeft size={12} strokeWidth={1.5} />
          }
        </button>

        {/* New Chat button */}
        <div className="px-3 shrink-0">
          <button
            onClick={handleNewChat}
            disabled={isCreating}
            className="
              flex items-center gap-3 w-full px-3 py-2.5 rounded-lg
              border border-white/[0.06] hover:border-white/[0.12]
              text-gray-400 hover:text-white
              hover:bg-white/[0.04]
              transition-all duration-300
              disabled:opacity-40
            "
          >
            <Plus size={15} strokeWidth={1.5} className="shrink-0" />
            {!isCollapsed && (
              <span className="text-[11px] font-mono tracking-[0.15em] uppercase whitespace-nowrap">
                New Chat
              </span>
            )}
          </button>
        </div>

        {/* Separator */}
        {!isCollapsed && (
          <div className="mx-3 h-px bg-white/[0.04] shrink-0" />
        )}

        {/* Sessions list */}
        <div
          ref={listRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-2 space-y-0.5"
        >
          {sessions.map(session => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              isCollapsed={isCollapsed}
              onClick={() => onSessionSelect(session.id)}
              onDelete={() => handleDeleteSession(session.id)}
            />
          ))}

          {/* Load-more indicator */}
          {isLoadingMore && (
            <div className="flex justify-center py-3">
              <div className="w-1 h-1 rounded-full bg-gray-600 animate-pulse" />
            </div>
          )}

          {sessions.length === 0 && !isLoadingMore && (
            <p className={`
              text-[10px] text-gray-600 font-mono text-center pt-8
              ${isCollapsed ? 'hidden' : 'block'}
            `}>
              No sessions yet
            </p>
          )}
        </div>
      </div>
    </aside>
  );
};

// ---------------------------------------------------------------------------
// SessionItem — memoized to prevent re-renders during streaming
// ---------------------------------------------------------------------------
const SessionItem = React.memo(function SessionItem({
  session,
  isActive,
  isCollapsed,
  onClick,
  onDelete,
}: {
  session: SessionPreview;
  isActive: boolean;
  isCollapsed: boolean;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`
        relative flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-left
        transition-all duration-300 group
        ${isActive
          ? 'bg-white/[0.06] text-gray-200'
          : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
        }
      `}
    >
      {/* Active indicator bar */}
      {isActive && (
        <div className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-indigo-400/70" />
      )}

      <MessageSquare size={14} strokeWidth={1.5} className="shrink-0" />

      {!isCollapsed && (
        <>
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-light truncate leading-tight">
              {session.title}
            </p>
            {session.preview ? (
              <p className="text-[10px] text-gray-600 truncate mt-0.5 leading-tight">
                {session.preview}
              </p>
            ) : null}
            <p className="text-[9px] text-gray-700 font-mono mt-1">
              {formatDistanceToNow(new Date(session.created_at), { addSuffix: true })}
            </p>
          </div>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-white/[0.08] text-gray-500 hover:text-red-400 transition-all absolute right-2"
            aria-label="Delete chat"
          >
            <Trash2 size={13} strokeWidth={1.5} />
          </button>
        </>
      )}
    </div>
  );
});
