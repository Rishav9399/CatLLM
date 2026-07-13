"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, X, ArrowUp, Loader2 } from 'lucide-react';
import { uploadImage } from '@/lib/api';
import toast from 'react-hot-toast';

interface MachinedComposerProps {
  onSend: (query: string, attachments?: string[]) => void;
  isStreaming: boolean;
}

export const MachinedComposer: React.FC<MachinedComposerProps> = ({ onSend, isStreaming }) => {
  const [input, setInput] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [stagedImage, setStagedImage] = useState<File | null>(null);
  const [stagedPreview, setStagedPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isActive = !isStreaming && !isUploading;
  const hasContent = input.trim().length > 0;

  // Auto-resize textarea
  useEffect(() => {
    const ta = inputRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  // Auto-focus
  useEffect(() => {
    if (isActive && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isActive]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Only images are supported for vision analysis.');
        return;
      }
      setStagedImage(file);
      setStagedPreview(URL.createObjectURL(file));
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeStagedImage = () => {
    setStagedImage(null);
    setStagedPreview(null);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!hasContent || !isActive) return;

    let attachments: string[] | undefined;

    if (stagedImage) {
      setIsUploading(true);
      try {
        const { file_path } = await uploadImage(stagedImage);
        attachments = [file_path];
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Image upload failed.';
        toast.error(msg);
        setIsUploading(false);
        return;
      }
      setIsUploading(false);
    }

    onSend(input, attachments);
    setInput('');
    removeStagedImage();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const borderColor = isFocused
    ? 'rgba(129,140,248,0.55)'
    : hasContent
    ? 'rgba(129,140,248,0.3)'
    : 'rgba(255,255,255,0.08)';

  const boxShadow = isFocused
    ? '0 0 0 1px rgba(129,140,248,0.4), 0 0 30px rgba(99,102,241,0.15), inset 0 1px 0 rgba(255,255,255,0.06)'
    : hasContent
    ? '0 0 0 1px rgba(129,140,248,0.2), 0 0 15px rgba(99,102,241,0.07)'
    : '0 0 0 1px rgba(255,255,255,0.05)';

  return (
    <div className="px-5 pb-5 pt-3 w-full max-w-4xl mx-auto shrink-0 flex flex-col gap-3">

      {/* Staged image preview */}
      {stagedPreview && (
        <div className="flex items-center gap-3 px-2 animate-fade-up">
          <div className="relative group w-fit">
            <img
              src={stagedPreview}
              alt="Staged"
              className="w-14 h-14 object-cover rounded-lg border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
            />
            <button
              onClick={removeStagedImage}
              type="button"
              className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-gray-900 border border-white/10 flex items-center justify-center text-gray-400 hover:text-red-400 hover:border-red-400/40 transition-colors"
            >
              <X size={10} />
            </button>
          </div>
          <span className="text-[10px] text-gray-600 font-mono tracking-wider">
            {stagedImage?.name}
          </span>
        </div>
      )}

      {/* Composer panel */}
      <div
        className="relative rounded-xl transition-all duration-300"
        style={{
          background: 'rgba(10, 10, 20, 0.85)',
          border: `1px solid ${borderColor}`,
          boxShadow,
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Top edge glow when focused */}
        <div
          className="absolute top-0 left-6 right-6 h-px rounded-full transition-opacity duration-500"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(129,140,248,0.5), transparent)',
            opacity: isFocused ? 1 : 0,
          }}
        />

        <div className="flex items-end gap-3 px-4 py-3">

          {/* Attach button */}
          <input
            type="file"
            accept="image/*"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileSelect}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={!isActive}
            className="shrink-0 mb-0.5 p-1.5 rounded-lg text-gray-600 hover:text-indigo-400 hover:bg-indigo-500/10 border border-transparent hover:border-indigo-500/20 transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Attach image"
          >
            <Paperclip size={15} strokeWidth={1.5} />
          </button>

          {/* Textarea */}
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={!isActive}
            placeholder={
              isStreaming
                ? 'Generating response…'
                : isUploading
                ? 'Uploading image…'
                : 'Ask anything… (Shift+Enter for new line)'
            }
            className="flex-1 bg-transparent py-1 text-[13.5px] text-gray-100 placeholder-gray-600 tracking-[0.015em] font-light focus:outline-none resize-none leading-relaxed disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ minHeight: '24px', maxHeight: '160px' }}
          />

          {/* Send / Loading button */}
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!hasContent || !isActive}
            className={`shrink-0 mb-0.5 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-300 ${
              isStreaming
                ? 'bg-indigo-900/40 border border-indigo-600/30 cursor-not-allowed'
                : hasContent && isActive
                ? 'bg-indigo-600 hover:bg-indigo-500 border border-indigo-400/50 shadow-[0_0_20px_rgba(99,102,241,0.4)] hover:shadow-[0_0_30px_rgba(99,102,241,0.6)] hover:scale-110 active:scale-95'
                : 'bg-gray-800/50 border border-white/[0.05] opacity-40 cursor-not-allowed'
            }`}
          >
            {isStreaming || isUploading ? (
              <Loader2 size={14} className="text-indigo-400 animate-spin" />
            ) : (
              <ArrowUp size={14} className="text-white" strokeWidth={2} />
            )}
          </button>
        </div>

        {/* Bottom helper row */}
        <div className="flex items-center justify-between px-4 pb-2.5 pt-0">
          <span className="text-[9px] text-gray-700 font-mono tracking-wider">
            {isStreaming ? (
              <span className="text-indigo-500/70 flex items-center gap-1.5">
                <span className="inline-block w-1 h-1 rounded-full bg-indigo-500 animate-ping" />
                Streaming…
              </span>
            ) : (
              'Enter to send  ·  Shift+Enter for new line'
            )}
          </span>
          <span className={`text-[9px] font-mono transition-all duration-300 ${
            input.length > 800 ? 'text-orange-400' : 'text-gray-700'
          }`}>
            {input.length > 0 ? `${input.length} chars` : ''}
          </span>
        </div>
      </div>
    </div>
  );
};