"use client";

import React, { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Toaster } from 'react-hot-toast';
import { AtmosphericLight, Phase } from '@/components/AtmosphericLight';
import { ObsidianSlab } from '@/components/ObsidianSlab';
import { MessageThread } from '@/components/MessageThread';
import { MachinedComposer } from '@/components/MachineComposer';
import { Sidebar } from '@/components/Sidebar';
import { Message } from '../types';
import { createChatSession, streamMessage, getSession } from '@/lib/api';

export default function ObsidianEnvironment() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'ai',
      content: 'Atmospheric systems stabilized. Ready for architectural synthesis.',
    }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Derive atmospheric phase from streaming state
  const activeAiMsg = messages.find(m => m.isStreaming);
  const currentPhase: Phase = activeAiMsg
    ? (activeAiMsg.statusText ? 'thinking' : 'generating')
    : 'idle';

  // Helper: patch only the live AI message (avoids full re-render)
  const patch = useCallback((msgId: string, data: Partial<Message>) => {
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, ...data } : m));
  }, []);

  // --- Session switching: load history when user clicks a sidebar item ---
  const handleSessionSelect = useCallback(async (selectedId: string) => {
    if (selectedId === sessionId || isStreaming) return;
    try {
      const detail = await getSession(selectedId);
      setSessionId(selectedId);
      // Map backend roles to our internal type ('ai' | 'user')
      setMessages(
        detail.messages.map(msg => ({
          id: msg.id,
          role: msg.role as 'user' | 'ai',
          content: msg.content,
        }))
      );
    } catch (err) {
      console.error('[ObsidianEnvironment] Failed to load session:', err);
    }
  }, [sessionId, isStreaming]);

  // --- New chat: reset the canvas ---
  const handleNewChat = useCallback((newSessionId: string) => {
    setSessionId(newSessionId);
    setMessages([{
      id: uuidv4(),
      role: 'ai',
      content: 'New session initialized. Awaiting synthesis directive.',
    }]);
  }, []);

  // --- Send message ---
  const handleInteraction = useCallback(async (query: string) => {
    if (!query.trim() || isStreaming) return;
    setIsStreaming(true);

    // 1. User message materializes immediately
    const userMsgId = uuidv4();
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: query }]);

    // 2. Ensure we have a session — create one lazily on the first message
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        currentSessionId = await createChatSession();
        setSessionId(currentSessionId);
      } catch {
        setMessages(prev => [...prev, {
          id: uuidv4(), role: 'ai',
          content: 'Neural link severed. Backend unreachable.',
          statusText: 'Offline',
          isStreaming: false,
        }]);
        setIsStreaming(false);
        return;
      }
    }

    // 3. Placeholder AI message — enters "thinking" phase
    const aiMsgId = uuidv4();
    setMessages(prev => [...prev, {
      id: aiMsgId,
      role: 'ai',
      content: '',
      statusText: '🧠 Waking up Swarm...',
      isStreaming: true,
    }]);

    try {
      let accumulated = '';
      for await (const payload of streamMessage(currentSessionId, query)) {
        if (payload.event === 'status') {
          patch(aiMsgId, { statusText: payload.content });
        } else if (payload.event === 'token') {
          accumulated += payload.content;
          patch(aiMsgId, { content: accumulated, statusText: undefined });
        } else if (payload.event === 'error') {
          accumulated += `\n\n[System Alert]: ${payload.content}`;
          patch(aiMsgId, { content: accumulated, statusText: 'System Fault' });
        } else if (payload.event === 'done') {
          break;
        }
      }
    } catch {
      patch(aiMsgId, { content: 'Neural link severed. Backend unreachable.', statusText: 'Offline' });
    } finally {
      patch(aiMsgId, { isStreaming: false });
      setIsStreaming(false);
    }
  }, [isStreaming, sessionId, patch]);

  return (
    <div className="relative w-full h-screen bg-[#030303] overflow-hidden font-sans text-[#e5e5e5] selection:bg-indigo-900/40 flex">

      {/* Toast notifications (document uploads etc.) */}
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#111',
            color: '#e5e5e5',
            border: '1px solid rgba(255,255,255,0.06)',
            fontSize: '12px',
            fontFamily: 'monospace',
          },
        }}
      />

      {/* The Breathing Background — sits behind everything */}
      <AtmosphericLight phase={currentPhase} />

      {/* Sidebar — real sessions, frosted glass */}
      <div className="relative z-20 h-full shrink-0">
        <Sidebar
          activeSessionId={sessionId}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
        />
      </div>

      {/* Main chat column */}
      <div className="relative z-10 flex-1 flex items-center justify-center p-6 md:p-12 min-w-0">
        <ObsidianSlab phase={currentPhase}>
          <MessageThread messages={messages} />
          <div className="w-full h-px bg-gradient-to-r from-transparent via-white/[0.03] to-transparent" />
          <MachinedComposer onSend={handleInteraction} isStreaming={isStreaming} />
        </ObsidianSlab>
      </div>

    </div>
  );
}
