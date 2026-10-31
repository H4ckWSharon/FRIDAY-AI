import React from 'react';
import { Menu, Zap, Shield, Sparkles, Terminal } from 'lucide-react';

export default function Header({
  onToggleSidebar,
  subscription,
  onOpenPricing,
  modelName = 'friday Cyber Cloud',
}) {
  const isUnlimited = subscription?.is_unlimited;
  const remaining = subscription?.chats_remaining ?? 5;

  return (
    <header className="h-14 border-b border-[#1c1c22] bg-[#09090c]/90 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-20">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-[#18181f] md:hidden transition-colors"
          title="Toggle Sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Brand & Model Chip */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#111116] border border-[#22222b]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-heading font-semibold text-xs tracking-wide text-zinc-200">
              {modelName}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 bg-[#FF3038]/20 text-[#FF3038] font-bold rounded">
              GPU
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-zinc-500">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>&lt;0.8s TTFT</span>
          </div>
        </div>
      </div>

      {/* Right Actions: Quota & Upgrade */}
      <div className="flex items-center gap-2.5">
        {/* Usage pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#101014] border border-[#1e1e24] text-xs font-mono">
          <Shield className="w-3.5 h-3.5 text-[#FF3038]" />
          <span className="text-zinc-400">Quota:</span>
          <span className="text-zinc-200 font-semibold">
            {isUnlimited ? 'Unlimited Pro' : `${remaining} left today`}
          </span>
        </div>

        {/* Upgrade Button */}
        {!isUnlimited && (
          <button
            onClick={onOpenPricing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#FF3038] to-[#cc141c] hover:from-[#ff4d54] hover:to-[#e61a22] text-white text-xs font-heading font-semibold shadow-[0_0_15px_rgba(255,48,56,0.3)] transition-all active:scale-95"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Get Cyber Pro</span>
          </button>
        )}
      </div>
    </header>
  );
}

