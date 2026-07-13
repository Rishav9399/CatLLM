"use client";

import React from 'react';
import dynamic from 'next/dynamic';

const MagicRings = dynamic(() => import('./MagicRings'), { ssr: false });

export type Phase = 'idle' | 'thinking' | 'generating';

interface AtmosphericLightProps {
  phase: Phase;
}

export const AtmosphericLight: React.FC<AtmosphericLightProps> = ({ phase }) => {
  const ringStates = {
    idle: {
      speed: 0.12,
      opacity: 0.75,
      blur: 14,
      color: "#4f46e5",
      colorTwo: "#1e1b4b",
    },
    thinking: {
      speed: 0.7,
      opacity: 1,
      blur: 6,
      color: "#7c3aed",
      colorTwo: "#4f46e5",
    },
    generating: {
      speed: 0.28,
      opacity: 0.88,
      blur: 18,
      color: "#4338ca",
      colorTwo: "#312e81",
    },
  };

  const current = ringStates[phase];

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden" style={{ background: '#050508' }}>

      {/* 1. WebGL Ring shader */}
      <div
        className="absolute inset-0 flex items-center justify-center scale-[2.2] mix-blend-screen"
        style={{ opacity: current.opacity * 0.38, transition: 'opacity 2s ease' }}
      >
        <MagicRings
          color={current.color}
          colorTwo={current.colorTwo}
          speed={current.speed}
          opacity={current.opacity}
          blur={current.blur}
          ringCount={4}
          attenuation={7}
          lineThickness={14}
          baseRadius={0.1}
          radiusStep={0.15}
          scaleRate={0.05}
          noiseAmount={0.35}
          followMouse={true}
          mouseInfluence={0.04}
        />
      </div>

      {/* 2. Deep ambient blobs for richness */}
      <div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: '55vmax',
          height: '55vmax',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -60%)',
          background: phase === 'thinking'
            ? 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)'
            : 'radial-gradient(circle, rgba(67,56,202,0.10) 0%, transparent 70%)',
          transition: 'background 2s ease',
          filter: 'blur(40px)',
        }}
      />
      <div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: '40vmax',
          height: '40vmax',
          bottom: '-10%',
          right: '-5%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />

      {/* 3. Radial vignette — darkens the edges so UI elements pop */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 80% 80% at 50% 40%, transparent 15%, rgba(5,5,8,0.88) 75%, rgba(5,5,8,1) 100%)',
        }}
      />

      {/* 4. Bottom fade so composer area feels grounded */}
      <div
        className="absolute bottom-0 left-0 right-0 h-40 pointer-events-none"
        style={{
          background: 'linear-gradient(to top, rgba(5,5,8,0.96), transparent)',
        }}
      />
    </div>
  );
};