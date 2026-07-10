"use client";

import React from 'react';
import { MessageSquare, LayoutGrid, Settings, Plus } from 'lucide-react';

export const FloatingSidebar = () => {
  return (
    <aside className="group relative z-20 h-full py-12 ml-8 w-[64px] hover:w-[240px] flex flex-col transition-all duration-[800ms] ease-[cubic-bezier(0.16,1,0.3,1)]">
      
      {/* Top Action */}
      <div className="pb-8">
        <button className="flex items-center gap-5 w-full text-gray-400 hover:text-white transition-colors duration-500">
          <div className="min-w-[32px] h-[32px] flex items-center justify-center transition-all duration-500">
            <Plus size={18} strokeWidth={1.5} className="text-gray-400 group-hover:text-white" />
          </div>
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase opacity-0 group-hover:opacity-100 whitespace-nowrap transition-opacity duration-500 delay-100">
            New Synthesis
          </span>
        </button>
      </div>

      {/* History Area - Floating Nodes */}
      <div className="flex-1 flex flex-col gap-1">
        {[1, 2, 3].map((i) => (
          <button key={i} className="flex items-center gap-5 w-full p-1 rounded-lg hover:bg-white/[0.04] hover:backdrop-blur-md transition-all duration-500 group/item">
            {/* Elevated idle color to text-gray-400 for visibility */}
            <div className="min-w-[24px] h-[24px] flex items-center justify-center text-gray-400 group-hover/item:text-white transition-colors duration-500">
              <MessageSquare size={16} strokeWidth={1.5} />
            </div>
            <div className="flex flex-col items-start opacity-0 group-hover:opacity-100 whitespace-nowrap transition-all duration-500 delay-75">
              <span className="text-[12px] font-light tracking-wide text-gray-300">Archival Node {i}</span>
              <span className="text-[10px] font-mono tracking-widest text-gray-500 mt-0.5">Accessed 2h ago</span>
            </div>
          </button>
        ))}
      </div>

      {/* Bottom Actions */}
      <div className="pt-8 flex flex-col gap-4">
        <button className="flex items-center gap-5 w-full text-gray-400 hover:text-white transition-colors duration-500">
          <div className="min-w-[24px] h-[24px] flex items-center justify-center">
            <LayoutGrid size={16} strokeWidth={1.5} />
          </div>
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase opacity-0 group-hover:opacity-100 whitespace-nowrap transition-opacity duration-500 delay-100">
            Modules
          </span>
        </button>
        <button className="flex items-center gap-5 w-full text-gray-400 hover:text-white transition-colors duration-500">
          <div className="min-w-[24px] h-[24px] flex items-center justify-center">
            <Settings size={16} strokeWidth={1.5} />
          </div>
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase opacity-0 group-hover:opacity-100 whitespace-nowrap transition-opacity duration-500 delay-100">
            Parameters
          </span>
        </button>
      </div>
    </aside>
  );
};