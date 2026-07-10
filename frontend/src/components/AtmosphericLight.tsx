"use client";

import React from 'react';
import dynamic from 'next/dynamic';

const MagicRings = dynamic(() => import('./MagicRings'), { ssr: false });

export type Phase = 'idle' | 'thinking' | 'generating';

interface AtmosphericLightProps {
  phase: Phase;
}

export const AtmosphericLight: React.FC<AtmosphericLightProps> = ({ phase }) => {
  // We feed the shader brighter colors so its internal alpha calculation survives,
  // then we tame the brightness using CSS opacity and blending.
  const ringStates = {
    idle: {
      speed: 0.15,
      opacity: 0.8, 
      blur: 12,
      color: "#4f46e5", // Indigo 500 - Brighter base for solid alpha
      colorTwo: "#1e1b4b" // Indigo 900
    },
    thinking: {
      speed: 0.6,
      opacity: 1,
      blur: 8, // Less blur, light gathers inward
      color: "#6366f1", // Indigo 400
      colorTwo: "#4338ca" // Indigo 700
    },
    generating: {
      speed: 0.3,
      opacity: 0.9,
      blur: 15,
      color: "#3730a3", // Indigo 800
      colorTwo: "#312e81" // Indigo 900
    }
  };

  const current = ringStates[phase];

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden bg-[#030303]">
      
      {/* 1. scale-[2] pushes the edges of the rings outside the viewport so we only see the core.
        2. opacity-40 dims the overall WebGL output.
        3. mix-blend-screen ensures the dark parts of the shader disappear, leaving only pure light.
      */}
      <div className="absolute inset-0 flex items-center justify-center scale-[2] opacity-40 mix-blend-screen">
        <MagicRings
          color={current.color}
          colorTwo={current.colorTwo}
          speed={current.speed}
          opacity={current.opacity}
          blur={current.blur}
          ringCount={4} // Reduced count for less "ribbed" texture, more "cloud" texture
          attenuation={8} 
          lineThickness={12} // Extremely thick lines turn into rolling waves
          baseRadius={0.1}
          radiusStep={0.15}
          scaleRate={0.05}
          noiseAmount={0.3} // Higher noise makes it feel organic and misty
          followMouse={true} 
          mouseInfluence={0.03} 
        />
      </div>

      {/* The Physical Vignette: 
        Replaced mix-blend-multiply with a standard alpha gradient (rgba). 
        This smoothly fades the edges into the absolute black of the background 
        without crushing the center light.
      */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_20%,_rgba(3,3,3,1)_70%)]" />
    </div>
  );
};