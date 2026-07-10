import React, { useState, useRef, useEffect } from 'react';
import { Plus, Paperclip, X } from 'lucide-react';
import { uploadImage } from '@/lib/api';
import toast from 'react-hot-toast';

interface MachinedComposerProps {
  onSend: (query: string, attachments?: string[]) => void;
  isStreaming: boolean;
}

export const MachinedComposer: React.FC<MachinedComposerProps> = ({ onSend, isStreaming }) => {
  const [input, setInput] = useState('');
  const [stagedImage, setStagedImage] = useState<File | null>(null);
  const [stagedPreview, setStagedPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || isUploading) return;

    let attachments: string[] | undefined = undefined;
    
    if (stagedImage) {
      setIsUploading(true);
      try {
        const { file_path } = await uploadImage(stagedImage);
        attachments = [file_path];
      } catch (err: any) {
        toast.error(err.message || 'Image upload failed.');
        setIsUploading(false);
        return;
      }
      setIsUploading(false);
    }

    onSend(input, attachments);
    setInput('');
    removeStagedImage();
  };

  // Auto-focus the structural command line
  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  return (
    <div className="px-8 md:px-12 pb-8 pt-4 w-full max-w-4xl mx-auto shrink-0 flex flex-col gap-3">
      
      {/* Staging Area */}
      {stagedPreview && (
        <div className="bg-white/[0.02] border border-white/[0.05] rounded-lg p-2 flex items-center gap-3 w-fit self-start ml-12">
           <img src={stagedPreview} alt="Staged" className="w-12 h-12 object-cover rounded-md opacity-80" />
           <button 
             onClick={removeStagedImage} 
             type="button"
             className="p-1 hover:bg-white/[0.05] rounded-full text-gray-500 hover:text-white transition-colors"
           >
             <X size={14} />
           </button>
        </div>
      )}
      
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
            isStreaming || isUploading ? 'bg-gray-700' : 'bg-indigo-400/80 shadow-[0_0_12px_rgba(129,140,248,0.5)] animate-pulse'
          }`} />
        </div>

        {/* The Paperclip */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isStreaming || isUploading}
          className="p-1.5 mr-3 text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-50"
        >
          <Paperclip size={16} strokeWidth={1.5} />
        </button>
        <input 
          type="file" 
          accept="image/*" 
          className="hidden" 
          ref={fileInputRef} 
          onChange={handleFileSelect} 
        />

        {/* The Typographic Input Layer */}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming || isUploading}
          placeholder={isStreaming || isUploading ? "" : "Initiate synthesis sequence..."}
          className="flex-1 bg-transparent py-2 text-[14px] text-gray-100 placeholder-gray-500 tracking-[0.02em] font-light focus:outline-none disabled:opacity-50"
        />
        
        {/* 
          The Action Node (Replaces the giant Send Button)
          It is completely invisible until the user types, maintaining the void.
          When it appears, it is a microscopic crosshair/plus, not a paper airplane.
        */}
        <button
          type="submit"
          disabled={!input.trim() || isStreaming || isUploading}
          className={`ml-4 p-1.5 flex items-center justify-center transition-all duration-500 ${
            input.trim() && !(isStreaming || isUploading) 
              ? 'opacity-100 text-gray-400 hover:text-white' 
              : 'opacity-0 text-gray-800 pointer-events-none'
          }`}
        >
          <Plus size={16} strokeWidth={1} className={input.trim() && !(isStreaming || isUploading) ? "rotate-90 transition-transform duration-700" : ""} />
        </button>

      </form>
    </div>
  );
};