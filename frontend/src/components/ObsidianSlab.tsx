"use client";

import React, { useEffect, useRef } from 'react';
import { Phase } from './AtmosphericLight';

interface ObsidianSlabProps {
  children: React.ReactNode;
  phase: Phase;
}

export const ObsidianSlab: React.FC<ObsidianSlabProps> = ({ children, phase }) => {
  const slabRef = useRef<HTMLDivElement>(null);

  // Mouse-tracking glow on the slab edges
  useEffect(() => {
    const el = slabRef.current;
    if (!el) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty('--mouse-x', `${x}%`);
      el.style.setProperty('--mouse-y', `${y}%`);
    };

    el.addEventListener('mousemove', handleMouseMove);
    return () => el.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const phaseColors = {
    idle:       { glow: 'rgba(99,102,241,0.12)',   border: 'rgba(129,140,248,0.22)' },
    thinking:   { glow: 'rgba(167,139,250,0.2)',   border: 'rgba(196,181,253,0.4)'  },
    generating: { glow: 'rgba(99,102,241,0.15)',   border: 'rgba(129,140,248,0.30)' },
  };
  const pc = phaseColors[phase];

  return (
    <div className="relative z-10 flex flex-col h-full w-full max-w-5xl mx-auto p-4 md:py-6 md:px-4 perspective-1000">

      {/* ── Header ── */}
      <header className="flex items-center justify-between mb-5 px-5 pb-4 shrink-0">
        {/* Left: branding */}
        <div className="flex items-center gap-4 group cursor-default">
          {/* Animated logo mark */}
          <div className="relative w-8 h-8 flex items-center justify-center">
            <div
              className="absolute inset-0 rounded-md border border-indigo-500/40 animate-spin-slow"
              style={{ borderRadius: '6px' }}
            />
            <div
              className="absolute inset-[3px] rounded-[4px] border border-indigo-400/25 animate-spin-reverse"
            />
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_10px_rgba(129,140,248,0.9)]" />
          </div>

          <div className="flex flex-col">
            <h1 className="shimmer-text text-[13px] font-semibold tracking-[0.2em] uppercase leading-none">
              CatLLM
            </h1>
            <span className="text-[9px] text-gray-600 font-mono tracking-widest mt-0.5">
              Neural Interface · v2.0
            </span>
          </div>
        </div>

        {/* Right: phase indicator */}
        <div className="flex items-center gap-3">
          {/* Ring indicator */}
          <div className="relative flex items-center justify-center w-6 h-6">
            <div className={`absolute inset-0 rounded-full border transition-all duration-1000 ${
              phase !== 'idle'
                ? 'border-indigo-400/50 animate-pulse-ring'
                : 'border-gray-800'
            }`} />
            <div className={`w-2 h-2 rounded-full transition-all duration-700 ${
              phase === 'idle'       ? 'bg-gray-700'
              : phase === 'thinking' ? 'bg-violet-400 shadow-[0_0_12px_rgba(196,181,253,0.8)]'
              :                        'bg-indigo-400 shadow-[0_0_12px_rgba(129,140,248,0.8)]'
            }`} />
          </div>

          {/* Status text */}
          <span className={`text-[9px] font-mono tracking-[0.18em] uppercase transition-all duration-500 ${
            phase === 'idle'        ? 'text-gray-700'
            : phase === 'thinking'  ? 'text-violet-400/80'
            :                         'text-indigo-400/80'
          }`}>
            {phase === 'idle' ? 'STANDBY' : phase === 'thinking' ? 'THINKING' : 'GENERATING'}
          </span>
        </div>
      </header>

      {/* ── Main Glass Slab ── */}
      <main
        ref={slabRef}
        className="flex-1 flex flex-col overflow-hidden rounded-2xl relative transition-all duration-700"
        style={{
          background: 'rgba(8, 8, 16, 0.80)',
          backdropFilter: 'blur(60px) saturate(160%)',
          WebkitBackdropFilter: 'blur(60px) saturate(160%)',
          border: `1px solid ${pc.border}`,
          boxShadow: [
            `0 0 0 1px ${pc.border}`,
            `0 0 40px ${pc.glow}`,
            `0 40px 80px rgba(0,0,0,0.9)`,
            `0 0 120px rgba(0,0,0,0.6)`,
            `inset 0 1px 0 rgba(255,255,255,0.06)`,
            `inset 0 0 80px rgba(0,0,0,0.3)`,
          ].join(', '),
        }}
      >
        {/* Mouse-following internal highlight */}
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 hover:opacity-100 transition-opacity duration-500"
          style={{
            background: `radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(129,140,248,0.04), transparent 60%)`,
          }}
        />

        {/* Top edge glow line */}
        <div
          className="absolute top-0 left-8 right-8 h-px rounded-full"
          style={{
            background: `linear-gradient(90deg, transparent, ${pc.border}, transparent)`,
            opacity: phase !== 'idle' ? 1 : 0.5,
            transition: 'opacity 1s',
          }}
        />

        {/* Corner accent — top left */}
        <div className="absolute top-0 left-0 w-12 h-12 rounded-tl-2xl overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-indigo-500/50 to-transparent" />
          <div className="absolute top-0 left-0 h-full w-px bg-gradient-to-b from-indigo-500/50 to-transparent" />
        </div>

        {/* Corner accent — top right */}
        <div className="absolute top-0 right-0 w-12 h-12 rounded-tr-2xl overflow-hidden pointer-events-none">
          <div className="absolute top-0 right-0 w-full h-px bg-gradient-to-l from-indigo-500/50 to-transparent" />
          <div className="absolute top-0 right-0 h-full w-px bg-gradient-to-b from-indigo-500/50 to-transparent" />
        </div>

        {/* Bottom edge glow line */}
        <div
          className="absolute bottom-0 left-8 right-8 h-px rounded-full"
          style={{
            background: `linear-gradient(90deg, transparent, rgba(99,102,241,0.2), transparent)`,
          }}
        />

        {children}
      </main>
    </div>
  );
};