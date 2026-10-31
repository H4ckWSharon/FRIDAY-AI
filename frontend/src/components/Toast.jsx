import React from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const isError = toast.type === 'error';
  const isSuccess = toast.type === 'success';

  return (
    <div className="fixed bottom-20 right-4 z-50 max-w-sm animate-bounce-once">
      <div className={`
        flex items-center gap-3 p-3.5 rounded-xl border shadow-2xl backdrop-blur-md text-xs font-mono
        ${isError 
          ? 'bg-[#180a0a]/95 border-rose-800/80 text-rose-200' 
          : isSuccess 
            ? 'bg-[#0a180f]/95 border-emerald-800/80 text-emerald-200' 
            : 'bg-[#101017]/95 border-[#282836] text-zinc-200'}
      `}>
        {isError && <AlertCircle className="w-4 h-4 text-[#FF3038] shrink-0" />}
        {isSuccess && <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />}
        {!isError && !isSuccess && <Info className="w-4 h-4 text-cyan-400 shrink-0" />}

        <span className="flex-1 leading-normal">{toast.message}</span>

        <button onClick={onClose} className="p-1 hover:text-white transition-colors">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

