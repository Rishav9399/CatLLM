import React, { useState, useRef, useEffect } from 'react';
import { Plus } from 'lucide-react';

interface MachinedComposerProps {
  onSend: (query: string) => void;
  isStreaming: boolean;
}

export const MachinedComposer: React.FC<MachinedComposerProps> = ({ onSend, isStreaming }) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSend(input);
    setInput('');
  };

  // Auto-focus the structural command line
  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  return (
    <div className="px-8 md:px-12 pb-8 pt-4 w-full max-w-4xl mx-auto shrink-0">
      
      {/* 
        Notice: NO background color, NO border radius, NO box shadow on the form.
        It is purely a typographic input layer resting on the glass.
      */}
      <form 
        onSubmit={handleSubmit} 
        className="relative flex items-center group cursor-text"
        onClick={() => inputRef.current?.focus()}
      >
        
        {/* The Prompt Block (Replaces the Paperclip) 
            Acts as a physical cursor resting state, showing system readiness.
        */}
        <div className="w-4 shrink-0 flex flex-col items-center pt-0.5 mr-6">
          <div className={`w-2 h-3 transition-all duration-700 ${
            isStreaming ? 'bg-gray-700' : 'bg-indigo-400/80 shadow-[0_0_12px_rgba(129,140,248,0.5)] animate-pulse'
          }`} />
        </div>

        {/* The Typographic Input Layer */}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
          placeholder={isStreaming ? "" : "Initiate synthesis sequence..."}
          className="flex-1 bg-transparent py-2 text-[14px] text-gray-100 placeholder-gray-500 tracking-[0.02em] font-light focus:outline-none disabled:opacity-50"
        />
        
        {/* 
          The Action Node (Replaces the giant Send Button)
          It is completely invisible until the user types, maintaining the void.
          When it appears, it is a microscopic crosshair/plus, not a paper airplane.
        */}
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          className={`ml-4 p-1.5 flex items-center justify-center transition-all duration-500 ${
            input.trim() && !isStreaming 
              ? 'opacity-100 text-gray-400 hover:text-white' 
              : 'opacity-0 text-gray-800 pointer-events-none'
          }`}
        >
          <Plus size={16} strokeWidth={1} className={input.trim() && !isStreaming ? "rotate-90 transition-transform duration-700" : ""} />
        </button>

      </form>
    </div>
  );
};