import React from 'react';
import { Phase } from './AtmosphericLight';

interface ObsidianSlabProps {
  children: React.ReactNode;
  phase: Phase;
}

export const ObsidianSlab: React.FC<ObsidianSlabProps> = ({ children, phase }) => {
  return (
    <div className="relative z-10 flex flex-col h-full w-full max-w-5xl mx-auto p-4 md:py-8 md:px-6 perspective-1000">
      
      {/* Precision-Engineered Header */}
      <header className="flex items-center justify-between mb-8 px-6 pb-4 border-b border-white/[0.03]">
        <div className="flex items-baseline gap-4 opacity-70 hover:opacity-100 transition-opacity duration-700 cursor-default">
          {/* Replaced logo with pure, confident typography */}
          <h1 className="text-[13px] font-medium tracking-[0.15em] text-gray-200">
            OBSIDIAN
          </h1>
          {/* Serialized technical metric instead of a generic subtitle */}
          <span className="text-[9px] text-gray-500 font-mono tracking-widest uppercase">
            S.01 — NX.3
          </span>
        </div>
        
        {/* Silent Status Indicator (Replaces "STANDBY") 
            This acts like a physical LED embedded in the glass. 
            When thinking/generating, the line expands and brightens. 
        */}
        <div className="flex items-center gap-3 opacity-60">
          <div className={`h-px transition-all duration-[1500ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
            phase === 'idle' ? 'w-4 bg-gray-700' : 'w-12 bg-indigo-400'
          }`} />
          <div className={`w-1 h-1 rounded-full transition-all duration-1000 ${
            phase === 'idle' ? 'bg-gray-700 shadow-none' : 'bg-indigo-300 shadow-[0_0_8px_rgba(165,180,252,0.8)]'
          }`} />
        </div>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden rounded-[24px] bg-[#0c0c0c]/60 backdrop-blur-[60px] shadow-[0_40px_80px_rgba(0,0,0,1),0_0_0_1px_rgba(255,255,255,0.06),inset_0_1px_1px_rgba(255,255,255,0.2)] transition-all duration-700">
        {children}
      </main>
    </div>
  );
};