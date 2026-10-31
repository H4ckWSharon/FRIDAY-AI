maintenance_html = '''
<!-- FRIDAY Full-Screen Stealth Black Maintenance Shield -->
<div id="friday-maintenance-screen" class="fixed inset-0 z-[999999] bg-[#070709] flex flex-col items-center justify-center p-4 sm:p-6 select-none overflow-hidden" style="background-image: radial-gradient(circle at 50% 38%, rgba(255, 48, 56, 0.08) 0%, transparent 65%);">
  <!-- Cyber Background Grid -->
  <div class="absolute inset-0 pointer-events-none opacity-20" style="background-size: 32px 32px; background-image: linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);"></div>

  <div class="relative z-10 flex flex-col items-center max-w-lg w-full text-center gap-6 animate-fadeIn">
    <!-- Emblem -->
    <div class="relative w-20 h-20 rounded-2xl bg-[#121215] border border-[#FF3038]/40 flex items-center justify-center shadow-[0_0_35px_rgba(255,48,56,0.35)]">
      <img alt="FRIDAY" class="w-12 h-12 object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAcN1eRjJArxV6rgrKmESKWs6pNIIgghz2t08lwPHUbguzKUi6_QBkU6zT2Alm2IBhnUq5gJooHVbDYG5riYM9mTAd0ESKoFB_W7ofJEOdvKes4PoKqQ6WVDiu1mvJFhvhPDnO_TLp6O9JInIaI90cgk4l-ucK4jUIi3tQs4KaRFKhTHD-RnluE92sypzaKlZKRApmkyQVRLZX1VjzzTnzvdQZqhmEdoOHihdVh4zvOOVtYyxb5yWK1azp9GQahS68FJg">
      <span class="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#FF3038] animate-ping"></span>
      <span class="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#FF3038] border-2 border-[#070709]"></span>
    </div>

    <!-- Badge -->
    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#FF3038]/10 border border-[#FF3038]/30 text-[#FF3038] font-mono text-xs font-semibold tracking-wider uppercase">
      <span class="w-2 h-2 rounded-full bg-[#FF3038] animate-pulse"></span>
      Server Maintenance & Frontend Upgrade
    </div>

    <!-- Headlines -->
    <div class="flex flex-col gap-2">
      <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F5F5F5] font-heading">
        Core Systems Upgrading
      </h1>
      <p class="text-xs sm:text-sm text-[#A1A1AA] leading-relaxed max-w-md mx-auto">
        FRIDAY AI is currently undergoing scheduled infrastructure upgrades and frontend modernization. High-speed neural clusters are being primed. Systems will return to service shortly.
      </p>
    </div>

    <!-- Telemetry Block -->
    <div class="w-full rounded-2xl bg-[#0D0D10]/90 border border-[#27272A] p-4 sm:p-5 flex flex-col gap-3 font-mono text-xs shadow-2xl backdrop-blur-md text-left">
      <div class="flex justify-between items-center pb-2.5 border-b border-[#1A1A1F]">
        <span class="text-[#71717A]">SYSTEM STATUS</span>
        <span class="text-amber-400 font-bold flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span> MAINTENANCE IN PROGRESS
        </span>
      </div>
      <div class="flex justify-between items-center pb-2.5 border-b border-[#1A1A1F]">
        <span class="text-[#71717A]">ACTIVE CLUSTER</span>
        <span class="text-[#F5F5F5] font-semibold">friday Cyber Cloud (Uncensored)</span>
      </div>
      <div class="flex justify-between items-center pb-2.5 border-b border-[#1A1A1F]">
        <span class="text-[#71717A]">DEPLOYMENT TARGET</span>
        <span class="text-[#A1A1AA]">Modern MERN / React Architecture</span>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-[#71717A]">ESTIMATED DOWNTIME</span>
        <span class="text-[#FF3038] font-semibold">Brief Maintenance Window</span>
      </div>
    </div>

    <!-- Animated Progress Bar -->
    <div class="w-full h-1.5 rounded-full bg-[#1A1A1F] overflow-hidden relative">
      <div class="h-full bg-gradient-to-r from-[#FF3038] via-rose-400 to-[#FF3038] w-1/2 animate-pulse rounded-full"></div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 pt-2">
      <button onclick="location.reload()" class="px-5 py-2.5 rounded-xl bg-[#141417] hover:bg-[#1C1C22] border border-[#27272A] hover:border-[#FF3038]/50 text-xs font-mono text-[#F5F5F5] flex items-center gap-2 transition-all cursor-pointer shadow-md active:scale-95">
        <span class="material-symbols-outlined text-[16px] text-[#FF3038]">refresh</span>
        Check System Status
      </button>
    </div>

    <span class="text-[10px] font-mono text-[#52525B]">FRIDAY Neural Defense Network &bull; Version 2.0.0</span>
  </div>
</div>
'''

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

body_marker = '<body class="bg-black text-[#F5F5F5] antialiased flex w-full overflow-hidden selection:bg-[#FF3038]/30 selection:text-white" style="height: var(--app-height, 100dvh); max-height: var(--app-height, 100dvh);">'

if body_marker in html:
    new_html = html.replace(body_marker, body_marker + '\n' + maintenance_html)
    with open('index.html', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_html)
    print("SUCCESS: Maintenance overlay injected into index.html")
else:
    print("FAILED: Body marker not matched")

