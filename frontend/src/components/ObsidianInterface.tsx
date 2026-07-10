"use client";

import React, { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { AtmosphericLight, Phase } from '@/components/AtmosphericLight';
import { ObsidianSlab } from '@/components/ObsidianSlab';
import { MessageThread } from '@/components/MessageThread';
import { MachinedComposer } from '@/components/MachineComposer';

// Extracted from original file for cleanliness
type Role = 'user' | 'ai';
export interface Message {
  id: string;
  role: Role;
  content: string;
  statusText?: string;
  isStreaming?: boolean;
}

export default function ObsidianInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'ai',
      content: 'Atmospheric systems stabilized. Ready for architectural synthesis.',
    }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Derive phase from state
  const activeAiMsg = messages.find(m => m.isStreaming);
  const currentPhase: Phase = activeAiMsg 
    ? (activeAiMsg.statusText ? 'thinking' : 'generating') 
    : 'idle';

  const handleInteraction = async (query: string) => {
    setIsStreaming(true);
    
    // 1. User Message Materializes
    const userMsgId = uuidv4();
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: query }]);

    // 2. AI Intelligence Engages (The system "breathes" before acting)
    const aiMsgId = uuidv4();
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        id: aiMsgId, 
        role: 'ai', 
        content: '', 
        statusText: 'Realigning vector matrices...', 
        isStreaming: true 
      }]);
      simulateIntelligence(aiMsgId);
    }, 600); // 600ms intentional delay for physical weight
  };

  const simulateIntelligence = async (msgId: string) => {
    const delay = (ms: number) => new Promise(res => setTimeout(res, ms));
    const update = (data: Partial<Message>) => {
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, ...data } : m));
    };

    // The Thinking Phase
    await delay(1500); 
    update({ statusText: 'Formulating architectural response...' });
    await delay(1200); 
    
    // The Generating Phase
    const text = "The environment has been decoupled into modular spatial components. The atmospheric lighting now renders on an isolated DOM layer, preventing layout thrashing during the 5000ms volumetric transitions.\n\nNotice how the machined input composer absorbs light differently than the primary frosted slab. This is intentional. We are treating pixels as physical materials.";
    
    update({ statusText: undefined, content: '' }); // Clear status, begin etching
    
    const words = text.split(/( )/);
    let currentText = '';
    
    for (const word of words) {
      // Intentional, slightly variable speed to mimic processing, not a robot loop.
      await delay(25 + Math.random() * 35); 
      currentText += word;
      update({ content: currentText });
    }
    
    update({ isStreaming: false });
    setIsStreaming(false);
  };

  return (
    <div className="relative w-full h-screen bg-[#030303] overflow-hidden font-sans text-[#e5e5e5] selection:bg-indigo-900/40">
      <AtmosphericLight phase={currentPhase} />
      
      <ObsidianSlab phase={currentPhase}>
        <MessageThread messages={messages} />
        <div className="w-full h-px bg-gradient-to-r from-transparent via-white/[0.05] to-transparent" />
        <MachinedComposer onSend={handleInteraction} isStreaming={isStreaming} />
      </ObsidianSlab>
    </div>
  );
}