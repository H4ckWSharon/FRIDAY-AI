import React, { useState } from 'react';
import { Lock, RefreshCw, Terminal, ShieldAlert } from 'lucide-react';

export default function MaintenanceView() {
  const [checking, setChecking] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Server maintenance active. All systems will resume tomorrow.');
  const [isOnline, setIsOnline] = useState(false);

  const handleCheckStatus = async () => {
    setChecking(true);
    setStatusMsg('Contacting infrastructure cluster…');
    try {
      const res = await fetch('/health', { cache: 'no-store' });
      if (res.ok) {
        setStatusMsg('Server backend online. Maintenance window active — resuming tomorrow.');
        setIsOnline(true);
      } else {
        setStatusMsg('Maintenance mode active. Upgrades in progress.');
        setIsOnline(false);
      }
    } catch (e) {
      setStatusMsg('Server maintenance active. All systems will resume tomorrow.');
      setIsOnline(false);
    } finally {
      setTimeout(() => setChecking(false), 800);
    }
  };

  return (
    <div className="min-h-screen w-screen flex flex-col justify-between bg-[#050507] text-[#F5F5F5] font-sans selection:bg-[#FF3038] selection:text-white relative overflow-x-hidden">
      {/* Background Cyber Grid */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-40 z-0"
        style={{
          backgroundImage: 'linear-gradient(to right, rgba(255, 48, 56, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 48, 56, 0.05) 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}
      />
      
      {/* Ambient Crimson Glow */}
      <div 
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: 'radial-gradient(circle at 50% 35%, rgba(255, 48, 56, 0.12) 0%, rgba(5, 5, 7, 0) 70%)'
        }}
      />

      {/* Header */}
      <header className="relative z-10 w-full border-b border-[#1c1c22] bg-[#08080a]/80 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#0e0e12] border border-[#FF3038]/40 flex items-center justify-center shadow-[0_0_12px_rgba(255,48,56,0.25)]">
            <span className="font-heading font-black text-sm text-[#FF3038]">F</span>
          </div>
          <div className="flex flex-col text-left">
            <span className="font-heading font-bold text-sm tracking-wide text-white">FRIDAY AI</span>
            <span className="font-mono text-[10px] text-[#71717A] tracking-wider uppercase">Offensive Security Architecture</span>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#160b0c] border border-[#FF3038]/40 shadow-[0_0_12px_rgba(255,48,56,0.2)]">
          <span className="w-2 h-2 rounded-full bg-[#FF3038] animate-ping"></span>
          <span className="font-mono text-[11px] font-semibold text-[#FF3038] tracking-wider uppercase">SERVER MAINTENANCE ACTIVE</span>
        </div>
      </header>

      {/* Main Lock Card */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-xl mx-auto flex flex-col items-center text-center">
          
          {/* Glowing Lock Emblem */}
          <div className="relative mb-8">
            <div className="absolute -inset-2 rounded-full bg-gradient-to-r from-[#FF3038]/30 to-[#990000]/20 blur-xl"></div>
            <div className="relative w-24 h-24 rounded-2xl bg-[#0b0b0e] border border-[#FF3038]/50 p-2 flex items-center justify-center shadow-[0_0_35px_rgba(255,48,56,0.35)] animate-pulse">
              <Lock className="w-12 h-12 text-[#FF3038]" />
            </div>
          </div>

          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#160b0c] border border-[#FF3038]/40 text-[#FF555D] text-xs font-mono font-medium mb-5 shadow-[0_0_15px_rgba(255,48,56,0.15)]">
            <ShieldAlert className="w-3.5 h-3.5 text-[#FF3038]" />
            <span>SCHEDULED INFRASTRUCTURE UPGRADE</span>
          </div>

          {/* Headline */}
          <h1 className="font-heading text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            Website Temporarily Locked
          </h1>

          {/* Notice */}
          <p className="text-sm sm:text-base text-[#A1A1AA] leading-relaxed max-w-md mb-8">
            We are performing scheduled maintenance and full system upgrades across all nodes. Chat sessions and operator consoles are locked. <strong className="text-white">We will be fully back online tomorrow.</strong>
          </p>

          {/* Diagnostics Box */}
          <div className="w-full rounded-xl bg-[#09090c] border border-[#222228] p-4 text-left font-mono text-xs shadow-2xl mb-8">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1c1c22]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#FF3038]"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-700"></span>
                <span className="text-[11px] text-[#71717A] ml-2 font-medium">MAINTENANCE_LOCKDOWN.SYS</span>
              </div>
              <span className="text-[10px] text-[#FF555D] font-bold">STATUS: LOCKED</span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#71717A]">Access Barrier:</span>
                <span className="text-[#FF3038] font-semibold">100% Locked Out (Maintenance Mode)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#71717A]">Operations Status:</span>
                <span className="text-amber-400 font-semibold">Offline for Upgrades</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#71717A]">Resuming:</span>
                <span className="text-emerald-400 font-semibold">Tomorrow</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#71717A]">Active Node:</span>
                <span className="text-zinc-400">213.133.97.141</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mt-4 pt-3 border-t border-[#1c1c22]">
              <div className="flex justify-between text-[10px] text-[#71717A] mb-1.5">
                <span>UPGRADE PIPELINE</span>
                <span className="text-zinc-400">IN PROGRESS &bull; RESUMING TOMORROW</span>
              </div>
              <div className="w-full h-1.5 bg-[#141419] rounded-full overflow-hidden relative">
                <div 
                  className="h-full bg-gradient-to-r from-[#FF3038] via-rose-500 to-[#FF3038] rounded-full"
                  style={{ width: '65%' }}
                />
              </div>
            </div>
          </div>

          {/* Action Button */}
          <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
            <button
              onClick={handleCheckStatus}
              disabled={checking}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[#131318] hover:bg-[#1a1a22] border border-[#2b2b36] hover:border-[#FF3038]/60 text-xs font-mono font-semibold text-zinc-200 hover:text-white transition-all flex items-center justify-center gap-2 shadow-lg active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
              <span>Check Node Status</span>
            </button>
          </div>

          {/* Feedback */}
          <p className={`text-[11px] font-mono mt-4 min-h-[18px] ${isOnline ? 'text-amber-400' : 'text-[#71717A]'}`}>
            {statusMsg}
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full border-t border-[#1c1c22] bg-[#08080a]/80 backdrop-blur-md px-6 py-3 flex flex-col sm:flex-row items-center justify-between gap-2 text-center">
        <span className="font-mono text-[11px] text-[#52525B]">
          FRIDAY AI &copy; 2026 &bull; Advanced Cyber Defense & Offensive Operations
        </span>
        <span className="font-mono text-[10px] text-[#3F3F46]">
          AUTH NODE: 213.133.97.141 &bull; PROTOCOL 2.0
        </span>
      </footer>
    </div>
  );
}

