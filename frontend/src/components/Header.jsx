import React from 'react';
import { Menu, Zap, Shield, Sparkles, Download } from 'lucide-react';

const OFFICIAL_LOGO_FALLBACK = 'https://lh3.googleusercontent.com/aida-public/AB6AXuAcN1eRjJArxV6rgrKmESKWs6pNIIgghz2t08lwPHUbguzKUi6_QBkU6zT2Alm2IBhnUq5gJooHVbDYG5riYM9mTAd0ESKoFB_W7ofJEOdvKes4PoKqQ6WVDiu1mvJFhvhPDnO_TLp6O9JInIaI90cgk4l-ucK4jUIi3tQs4KaRFKhTHD-RnluE92sypzaKlZKRApmkyQVRLZX1VjzzTnzvdQZqhmEdoOHihdVh4zvOOVtYyxb5yWK1azp9GQahS68FJg';

export default function Header({
  onToggleSidebar,
  subscription,
  onOpenPricing,
  modelName = 'friday Cyber Cloud',
  onInstallApp,
  isInstallable,
  isStandalone,
}) {
  const isUnlimited = subscription?.is_unlimited;
  const remaining = subscription?.chats_remaining ?? 5;

  return (
    <header className="h-14 border-b border-[#1c1c22] bg-[#09090c]/90 backdrop-blur-md px-2.5 sm:px-4 flex items-center justify-between shrink-0 z-20">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {/* Hamburger Menu Button - Always visible on all screen sizes */}
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-xl text-zinc-300 hover:text-white bg-[#121217] hover:bg-[#1a1a24] border border-[#242432] hover:border-[#38384a] transition-all flex items-center justify-center active:scale-95 cursor-pointer shadow-sm shrink-0"
          title="Toggle Navigation Menu"
          aria-label="Toggle Navigation Menu"
        >
          <Menu className="w-4 h-4 sm:w-5 sm:h-5 text-zinc-300" />
        </button>

        {/* Official Brand Logo & Identity */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-full overflow-hidden border border-[#FF3038]/50 bg-[#0d0e11] p-0.5 flex items-center justify-center shadow-[0_0_12px_rgba(255,48,56,0.35)] shrink-0">
            <img 
              src="/logo.png" 
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = OFFICIAL_LOGO_FALLBACK;
              }}
              alt="FRIDAY AI Official Logo" 
              className="w-full h-full object-cover rounded-full"
            />
          </div>
          <div className="hidden sm:flex flex-col min-w-0">
            <span className="font-heading font-black text-sm tracking-wider text-white leading-none">
              FRIDAY AI
            </span>
            <span className="text-[9px] font-mono text-[#FF3038] tracking-widest uppercase mt-0.5 font-bold">
              Cyber Red Team
            </span>
          </div>
        </div>

        {/* Active Model Indicator Chip */}
        <div className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-2.5 py-1 rounded-lg bg-[#111116] border border-[#22222b] shrink-0">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-heading font-semibold text-[11px] sm:text-xs tracking-wide text-zinc-200">
            <span className="hidden xs:inline">{modelName}</span>
            <span className="xs:hidden">Cyber Cloud</span>
          </span>
          <span className="text-[9px] font-mono px-1 sm:px-1.5 py-0.2 bg-[#FF3038]/20 text-[#FF3038] font-bold rounded">
            GPU
          </span>
        </div>

        <div className="hidden xl:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-zinc-500">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>&lt;0.8s TTFT</span>
        </div>
      </div>

      {/* Right Actions: Install App, Quota & Upgrade */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
        {/* Install App Button on Android / PWA */}
        {!isStandalone && (
          <button
            onClick={onInstallApp}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#121219] hover:bg-[#1a1a26] border border-[#262638] hover:border-cyan-500/50 text-zinc-300 hover:text-white text-xs font-mono transition-all active:scale-95 shadow-sm"
            title="Install FRIDAY AI App on your device"
            aria-label="Install App"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="hidden md:inline font-sans">Install App</span>
          </button>
        )}

        {/* Usage pill */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#101014] border border-[#1e1e24] text-xs font-mono">
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
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#FF3038] to-[#cc141c] hover:from-[#ff4d54] hover:to-[#e61a22] text-white text-xs font-heading font-semibold shadow-[0_0_15px_rgba(255,48,56,0.3)] transition-all active:scale-95"
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden xs:inline">Get Cyber Pro</span>
            <span className="xs:hidden">Upgrade</span>
          </button>
        )}
      </div>
    </header>
  );
}
