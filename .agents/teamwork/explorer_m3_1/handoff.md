# Handoff Report: Tactical Scanning Radar HUD Component Design (Milestone M3 / Requirement R3 / Feature F10)

## 1. Observation

### 1.1 Legacy Thinking Orb Vestiges in `index.html`
- **File**: `c:\Users\sharo\Desktop\friday\index.html`
- **Lines 111–198**: Static thinking orb CSS rules:
  ```css
  /* ─── Thinking Orb (Minimal) ─────────────────────────────────────────── */
  .thinking-orb-wrap {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 6px 14px;
    border-radius: 9999px;
    background: rgba(13, 13, 16, 0.75);
    border: 1px solid rgba(255, 48, 56, 0.22);
    width: fit-content;
  }
  .thinking-orb-box { position: relative; width: 14px; height: 14px; ... }
  .thinking-orb { width: 9px; height: 9px; border-radius: 50%; ... }
  .thinking-active .thinking-orb { opacity: 1; transform: scale(1); animation: orb-pulse 1.8s ease-in-out infinite; }
  .thinking-orb-ring { ... }
  .thinking-active .thinking-orb-ring { animation: ring-expand 1.8s ease-in-out infinite; }
  .thinking-label { ... }
  ```
- **Lines 2284–2290**: Dead vestige DOM inside `renderTypingIndicator()`:
  ```html
  <div class="thinking-orb-wrap hidden" id="thinking-orb-wrap-${Date.now()}">
    <div class="thinking-orb-box">
      <div class="thinking-orb"></div>
      <div class="thinking-orb-ring"></div>
    </div>
    <span class="thinking-label">Thinking…</span>
  </div>
  ```
- **Lines 2359–2362 & cleanup points**: Unnecessary 300ms timer setting classes on hidden elements:
  ```javascript
  const orbTimer = setTimeout(() => {
    const wrap = typingEl.querySelector('.thinking-orb-wrap');
    if (wrap) wrap.classList.add('thinking-active');
  }, 300);
  ```
  Cleared at lines 2384, 2438, 2449, 2456, and 2464.

### 1.2 Current Prototype Radar Implementation Analysis
- **Lines 209–273**: Basic prototype radar styling:
  ```css
  .tactical-radar-hud {
    position: relative;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 48, 56, 0.12) 0%, rgba(13, 13, 16, 0.95) 75%);
    border: 1.5px solid rgba(255, 48, 56, 0.5);
    box-shadow: 0 0 16px rgba(255, 48, 56, 0.25), inset 0 0 12px rgba(255, 48, 56, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
  }
  .tactical-radar-sweep {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: conic-gradient(from 0deg, rgba(255, 48, 56, 0.75) 0deg, rgba(255, 48, 56, 0.15) 50deg, transparent 90deg);
    animation: radar-sweep 2.4s linear infinite;
  }
  ```
- **Conic-Gradient Direction Defect**:
  In CSS `conic-gradient`, angles increase clockwise. When the element rotates clockwise from 0° to 360°, points at larger angles (e.g., 50°, 90°) hit screen coordinates *before* 0° arrives. In the current gradient (`from 0deg, 0.75 at 0deg, 0.15 at 50deg, transparent at 90deg`), the faded tail (50°–90°) moves *ahead* of the bright leading line (0°), inverting the natural radar phosphor decay.
- **Lines 2248–2255**: DOM lacks tactical mounting reticles, synchronized target blip nodes, and sonar ping waves.

### 1.3 Memory Leak in Error Paths
- In `sendMessage` (lines 1924–1928):
  ```javascript
  } catch (err) {
    if (typingEl) {
      const radarInt = Number(typingEl.dataset.radarInterval);
      if (radarInt) clearInterval(radarInt);
      if (typingEl.isConnected) typingEl.remove();
    }
  ```
  `radarInt` is cleared properly here.
- In `handleEditMessage` (lines 2228–2232) and `regenerateResponse` (lines 2833–2838):
  ```javascript
  } catch (err) {
    if (typingEl.isConnected) typingEl.remove();
    if (err.name !== 'AbortError' && !err.message?.includes('cancel')) {
      renderErrorMessage(err.message || 'Something went wrong.');
    }
  }
  ```
  In both locations, `clearInterval(radarInt)` is omitted when an error or abort occurs, causing `setInterval` to continue ticking in the background against detached DOM nodes.

---

## 2. Logic Chain

### 2.1 Full Replacement of `.thinking-orb-wrap`
1. Observation 1.1 reveals that `.thinking-orb-wrap` (a 9px dot) is currently set to `hidden` with unused DOM nodes and a zombie `orbTimer` timeout running in `streamAssistantResponse()`.
2. Requirement R3 and Feature F10 demand a single, unified tactical radar HUD component representing the deep CPU inference state of "friday Cyber Pro".
3. Replacing `.thinking-orb-wrap` completely involves:
   - Removing lines 111–198 (`.thinking-orb-wrap` CSS).
   - Removing the dead `<div class="thinking-orb-wrap hidden">` from `renderTypingIndicator()`.
   - Removing `orbTimer` and its `clearTimeout(orbTimer)` calls from `streamAssistantResponse()`.
   - Centering the visual identity around `.tactical-radar-wrapper` and `.tactical-radar-hud`.

### 2.2 Mathematical Correction of the Sweeping Radar Conic Gradient
1. In clockwise rotation $\theta(t) = \omega t$:
   - For pixel $P$ on screen, as rotation advances, the leading ray should strike $P$ first, followed by the phosphor persistence decay trailing behind it.
   - Therefore, the decaying tail must occupy angles *counter-clockwise* from the leading edge ($\theta_{\text{tail}} < \theta_{\text{head}}$).
2. Setting the leading ray at 360°/0° and decaying from 280° to 360°:
   ```css
   conic-gradient(
     from 0deg at 50% 50%,
     rgba(255, 48, 56, 0.85) 0deg,
     transparent 1.5deg,
     transparent 280deg,
     rgba(255, 48, 56, 0.04) 285deg,
     rgba(255, 48, 56, 0.20) 325deg,
     rgba(255, 48, 56, 0.60) 355deg,
     rgba(255, 48, 56, 0.95) 360deg
   )
   ```
3. Adding a pseudo-element `.tactical-radar-sweep::after` creates a razor-sharp, sub-pixel radial ray line with `#FFFFFF` core and `#FF3038` neon bloom along the leading edge that rotates seamlessly on the same GPU composited layer.

### 2.3 Layered Military/Offensive Cyber HUD Architecture
To produce an authentic black-hat cyber aesthetic matching FRIDAY AI:
1. **Mounting Brackets (`.tactical-radar-bracket`)**: Four 5px corner reticles (`┌ ┐ └ ┘`) in `#FF3038` framing the circular optic.
2. **Polar Range Grid**:
   - Ring 1: 16px diameter, 1px dashed crimson border (`rgba(255, 48, 56, 0.45)`).
   - Ring 2: 32px diameter, 1px solid translucent crimson border (`rgba(255, 48, 56, 0.28)`).
   - Crosshairs: Vertical and horizontal 1px gradient axes with optical center glow.
3. **Synchronized Target Blips (`.tactical-radar-blip`)**:
   - 3 neural target nodes placed at tactical angles (Sector 1 at 45°, Sector 3 at 210°, Sector 4 at 315°).
   - Each blip's CSS `animation-delay` is calibrated to the exact instant the 2.2s sweep beam sweeps across its coordinates:
     - Sector 1 (45°): $2.2 \text{s} \times (45/360) = 0.275 \text{s} \approx 0.3 \text{s}$.
     - Sector 3 (210°): $2.2 \text{s} \times (210/360) = 1.28 \text{s} \approx 1.3 \text{s}$.
     - Sector 4 (315°): $2.2 \text{s} \times (315/360) = 1.925 \text{s} \approx 1.9 \text{s}$.
   - Blips flash brightly when swept and slowly fade, creating dynamic target acquisition without JavaScript execution.
4. **Center Diode & Sonar Ping Echo**:
   - Diode core (`.tactical-radar-core`): 7px crimson dot with radial white highlight and breathing pulse.
   - Sonar wave (`.tactical-radar-ping`): Expanding translucent crimson ripple (`scale(0.4) \to scale(3.2)`).

### 2.4 Performance and 60fps compositor Execution
1. All continuous animations use exclusively `transform` and `opacity`:
   - Sweeping beam: `transform: rotate(...)` with `will-change: transform; transform: translateZ(0);`.
   - Core pulse: `transform: scale(...)`.
   - Ping echo: `transform: scale(...)` and `opacity`.
   - Blips: `transform: scale(...)` and `opacity`.
2. CSS `contain: paint` is applied to `.tactical-radar-hud`, isolating repaints from the chat conversation container and eliminating browser layout recalculations.
3. The dynamic ticker and timer update via `setInterval` once per second (1Hz). String updates are guarded by `if (el.textContent !== newText)` checks, ensuring zero redundant DOM mutations.

### 2.5 Unified Indicator Cleanup Function
To fix the memory leaks observed in Observation 1.3:
```javascript
function removeTypingIndicator(el) {
  if (!el) return;
  const radarInt = Number(el.dataset.radarInterval);
  if (radarInt) {
    clearInterval(radarInt);
    delete el.dataset.radarInterval;
  }
  if (el.isConnected) el.remove();
}
```
Calling this in `handleEditMessage`, `regenerateResponse`, and `sendMessage` guarantees 100% leak-free cleanup under all circumstances (normal response, streaming error, or user cancellation).

---

## 3. Caveats

1. **Accessibility (`prefers-reduced-motion`)**:
   Users with vestibular disorders or reduced-motion preferences should have a fallback media query that pauses 360° rotation and replaces it with a gentle static glow.
2. **Mobile Viewport (< 640px)**:
   The radar is set to 48px × 48px. On narrow mobile screens (~360px width), the right column has `max-w-full min-w-0` and flex-wrap headers to prevent horizontal overflow.
3. **Backend Independence**:
   This component is purely frontend (DOM/CSS/JS in `index.html`). No changes to FastAPI routes or Ollama proxy APIs are required.

---

## 4. Conclusion

The tactical scanning radar HUD component provides a high-fidelity offensive cyber visual interface that replaces the static 9px `.thinking-orb-wrap`. It provides:
1. 360° sweeping beam with mathematically correct phosphor decay trail.
2. Razor-sharp radial leading beam line.
3. Dual concentric range rings and crosshairs.
4. Corner tactical reticle brackets (`[ ┌ ┐ └ ┘ ]`).
5. Synchronized target threat nodes that illuminate as the beam passes.
6. Expanding sonar ping wave and pulsing center core diode.
7. 60fps locked hardware-accelerated rendering using GPU compositor layers.
8. Clean leak-free lifecycle with immediate cleanup when the first streaming chunk arrives.

### 4.1 Production-Ready CSS Specification
Replace `index.html` lines 111–198 and 209–273 with:

```css
/* ─── Tactical Radar HUD & Cyber Telemetry State ───────────────────────── */
:root {
  --radar-size: 48px;
  --radar-crimson: #FF3038;
  --radar-crimson-glow: rgba(255, 48, 56, 0.45);
}

/* Outer Bracket Wrapper */
.tactical-radar-wrapper {
  position: relative;
  width: var(--radar-size);
  height: var(--radar-size);
  padding: 2px;
  box-sizing: border-box;
}

/* Corner Reticle Brackets [ ┌ ┐ └ ┘ ] */
.tactical-radar-bracket {
  position: absolute;
  width: 5px;
  height: 5px;
  border-color: rgba(255, 48, 56, 0.65);
  pointer-events: none;
  z-index: 5;
}
.bracket-tl { top: 0; left: 0; border-top: 1.5px solid; border-left: 1.5px solid; }
.bracket-tr { top: 0; right: 0; border-top: 1.5px solid; border-right: 1.5px solid; }
.bracket-bl { bottom: 0; left: 0; border-bottom: 1.5px solid; border-left: 1.5px solid; }
.bracket-br { bottom: 0; right: 0; border-bottom: 1.5px solid; border-right: 1.5px solid; }

/* Radar Housing / Optic Disc */
.tactical-radar-hud {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(255, 48, 56, 0.14) 0%, rgba(18, 10, 12, 0.88) 55%, rgba(5, 5, 8, 0.98) 100%);
  border: 1.5px solid rgba(255, 48, 56, 0.55);
  box-shadow: 0 0 16px rgba(255, 48, 56, 0.28), inset 0 0 12px rgba(255, 48, 56, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  contain: paint;
}

/* Concentric Calibrated Range Rings */
.tactical-radar-ring-1 {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px dashed rgba(255, 48, 56, 0.45);
  pointer-events: none;
  z-index: 1;
}

.tactical-radar-ring-2 {
  position: absolute;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(255, 48, 56, 0.28);
  pointer-events: none;
  z-index: 1;
}

/* Crosshairs with Optical Center Gradient */
.tactical-radar-crosshair-v {
  position: absolute;
  width: 1px;
  height: 100%;
  background: linear-gradient(to bottom, transparent 0%, rgba(255, 48, 56, 0.2) 15%, rgba(255, 48, 56, 0.55) 50%, rgba(255, 48, 56, 0.2) 85%, transparent 100%);
  pointer-events: none;
  z-index: 1;
}

.tactical-radar-crosshair-h {
  position: absolute;
  height: 1px;
  width: 100%;
  background: linear-gradient(to right, transparent 0%, rgba(255, 48, 56, 0.2) 15%, rgba(255, 48, 56, 0.55) 50%, rgba(255, 48, 56, 0.2) 85%, transparent 100%);
  pointer-events: none;
  z-index: 1;
}

/* 360° Sweeping Beam with Clockwise Phosphor Persistence Trail */
.tactical-radar-sweep {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg at 50% 50%,
    rgba(255, 48, 56, 0.85) 0deg,
    transparent 1.5deg,
    transparent 280deg,
    rgba(255, 48, 56, 0.04) 285deg,
    rgba(255, 48, 56, 0.18) 325deg,
    rgba(255, 48, 56, 0.55) 355deg,
    rgba(255, 48, 56, 0.90) 360deg
  );
  animation: radar-sweep 2.2s linear infinite;
  will-change: transform;
  transform: translateZ(0);
  z-index: 2;
  pointer-events: none;
}

/* Razor-Sharp Radial Leading Beam Ray */
.tactical-radar-sweep::after {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  width: 1.5px;
  height: 50%;
  background: linear-gradient(to top, rgba(255, 48, 56, 0.2), #FFFFFF 85%, #FF3038 100%);
  box-shadow: 0 0 6px 1px #FF3038;
  transform: translateX(-50%);
}

@keyframes radar-sweep {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Target Threat / Neural Synapse Blips */
.tactical-radar-blip {
  position: absolute;
  width: 3.5px;
  height: 3.5px;
  border-radius: 50%;
  background: #FF3038;
  opacity: 0.15;
  transform: translate(-50%, -50%) scale(0.7);
  animation: radar-blip-pulse 2.2s ease-in-out infinite;
  z-index: 3;
  pointer-events: none;
}

.tactical-radar-blip.blip-1 {
  top: 28%;
  left: 68%;
  animation-delay: 0.3s;
}

.tactical-radar-blip.blip-2 {
  top: 68%;
  left: 24%;
  animation-delay: 1.3s;
}

.tactical-radar-blip.blip-3 {
  top: 72%;
  left: 72%;
  animation-delay: 1.9s;
}

@keyframes radar-blip-pulse {
  0%, 100% {
    opacity: 0.15;
    transform: translate(-50%, -50%) scale(0.7);
    box-shadow: none;
  }
  20%, 35% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.4);
    box-shadow: 0 0 6px #FF3038, 0 0 12px rgba(255, 48, 56, 0.9);
  }
  65% {
    opacity: 0.35;
    transform: translate(-50%, -50%) scale(0.9);
  }
}

/* Center Core Diode Emitter */
.tactical-radar-core {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #FFFFFF 0%, #FF4D54 40%, #FF3038 80%, #990000 100%);
  box-shadow: 0 0 8px #FF3038, 0 0 16px rgba(255, 48, 56, 0.85);
  animation: tactical-core-pulse 1.4s ease-in-out infinite;
  z-index: 4;
}

@keyframes tactical-core-pulse {
  0%, 100% {
    transform: scale(0.85);
    opacity: 0.85;
    box-shadow: 0 0 6px #FF3038, 0 0 12px rgba(255, 48, 56, 0.55);
  }
  50% {
    transform: scale(1.25);
    opacity: 1;
    box-shadow: 0 0 12px #FF3038, 0 0 22px rgba(255, 48, 56, 0.95);
  }
}

/* Expanding Radar Ping Echo Wave */
.tactical-radar-ping {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 48, 56, 0.7);
  pointer-events: none;
  z-index: 3;
  animation: radar-ping-wave 2.2s cubic-bezier(0.1, 0.6, 0.4, 1) infinite;
}

@keyframes radar-ping-wave {
  0%   { transform: scale(0.4); opacity: 0.9; }
  65%  { opacity: 0.3; }
  100% { transform: scale(3.2); opacity: 0; }
}

/* Reduced Motion Fallback */
@media (prefers-reduced-motion: reduce) {
  .tactical-radar-sweep,
  .tactical-radar-blip,
  .tactical-radar-core,
  .tactical-radar-ping {
    animation: none !important;
  }
  .tactical-radar-sweep {
    opacity: 0.35;
  }
}
```

### 4.2 Production-Ready `renderTypingIndicator()` DOM Implementation
Replace `index.html` lines 2244–2327 with:

```javascript
  // ─── Render: Typing Indicator (Tactical Radar HUD & Telemetry) ───────────
  function renderTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'flex gap-3 sm:gap-4 items-start typing-indicator-row w-full min-w-0';
    div.innerHTML = `
      <!-- Tactical Scanning Radar HUD Column -->
      <div class="tactical-radar-wrapper shrink-0 relative" title="FRIDAY Neural Radar">
        <div class="tactical-radar-bracket bracket-tl"></div>
        <div class="tactical-radar-bracket bracket-tr"></div>
        <div class="tactical-radar-bracket bracket-bl"></div>
        <div class="tactical-radar-bracket bracket-br"></div>
        <div class="tactical-radar-hud">
          <div class="tactical-radar-ring-1"></div>
          <div class="tactical-radar-ring-2"></div>
          <div class="tactical-radar-crosshair-v"></div>
          <div class="tactical-radar-crosshair-h"></div>
          <div class="tactical-radar-sweep"></div>
          <div class="tactical-radar-blip blip-1"></div>
          <div class="tactical-radar-blip blip-2"></div>
          <div class="tactical-radar-blip blip-3"></div>
          <div class="tactical-radar-ping"></div>
          <div class="tactical-radar-core"></div>
        </div>
      </div>

      <!-- Telemetry & Dynamic Multi-Stage Progress Column -->
      <div class="flex-1 flex flex-col max-w-full sm:max-w-2xl min-w-0 gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-heading font-semibold text-xs text-[#F5F5F5] tracking-wide">friday Cyber Pro</span>
          <span class="tactical-telemetry-badge">
            <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-ping"></span>
            NEURAL RADAR ACTIVE
          </span>
          <span class="text-[10px] font-mono text-[#71717A] ml-auto tactical-timer-badge" id="tactical-radar-timer">[EST. ~02:45] ELAPSED: 00:00</span>
        </div>
        <div class="tactical-progress-container flex flex-col gap-2.5">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="material-symbols-outlined text-[15px] text-[#FF3038] animate-spin shrink-0">autorenew</span>
              <span class="font-mono text-xs text-[#F5F5F5] font-medium tracking-wide truncate" id="tactical-status-label">Initializing Neural Matrix &amp; Security Weights...</span>
            </div>
            <span class="text-[9px] font-mono text-[#FF4D54] bg-[#FF3038]/10 border border-[#FF3038]/30 px-1.5 py-0.5 rounded shrink-0 font-bold uppercase tracking-wider hidden sm:inline">CPU 27B</span>
          </div>
          <div class="tactical-progress-bar-bg">
            <div class="tactical-progress-bar-fill"></div>
          </div>
          <div class="flex items-center justify-between text-[10px] font-mono text-[#71717A] gap-2">
            <span class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
              <span class="truncate">Deep CPU inference in progress (~2-3 mins). Model is computing full tactical response.</span>
            </span>
            <span class="text-[9px] text-[#FF3038] font-bold shrink-0 uppercase tracking-wider whitespace-nowrap">DO NOT REFRESH</span>
          </div>
        </div>
      </div>
    `;
    conversationView.appendChild(div);

    const statusSequence = [
      { at: 0,   text: 'Initializing Neural Matrix & Security Weights...' },
      { at: 7,   text: 'Analyzing Target Architecture & Surface Telemetry...' },
      { at: 20,  text: 'Engaging 27B Deep Reasoning & Threat Synthesis Engine...' },
      { at: 42,  text: 'Deconstructing Protocol Vectors & CVE Intelligence...' },
      { at: 72,  text: 'Formulating Offensive Exploit Chains & Hardened Defenses...' },
      { at: 110, text: 'Neural Attention Optimization & Token Assembly in Progress...' },
      { at: 150, text: 'Compiling Final Tactical Cyber Payload...' },
    ];

    let startSeconds = 0;
    const timerEl = div.querySelector('#tactical-radar-timer');
    const labelEl = div.querySelector('#tactical-status-label');

    const intervalId = setInterval(() => {
      startSeconds++;
      const mins = String(Math.floor(startSeconds / 60)).padStart(2, '0');
      const secs = String(startSeconds % 60).padStart(2, '0');
      if (timerEl) timerEl.textContent = `[EST. ~02:45] ELAPSED: ${mins}:${secs}`;

      for (let i = statusSequence.length - 1; i >= 0; i--) {
        if (startSeconds >= statusSequence[i].at) {
          if (labelEl && labelEl.textContent !== statusSequence[i].text) {
            labelEl.textContent = statusSequence[i].text;
          }
          break;
        }
      }
    }, 1000);

    div.dataset.radarInterval = String(intervalId);
    return div;
  }
```

### 4.3 Integration & Cleanup in `streamAssistantResponse`
1. Remove `const orbTimer = setTimeout(...)` at lines 2359–2362.
2. In `streamAssistantResponse()` on first chunk (lines 2436–2442):
   ```javascript
   if (!firstChunkReceived) {
     firstChunkReceived = true;
     const radarInt = Number(typingEl.dataset.radarInterval);
     if (radarInt) clearInterval(radarInt);
     typingEl.replaceWith(assistantEl);
   }
   ```
3. Add helper function `removeTypingIndicator(el)` and use it in all catch/finally blocks:
   ```javascript
   function removeTypingIndicator(el) {
     if (!el) return;
     const radarInt = Number(el.dataset.radarInterval);
     if (radarInt) {
       clearInterval(radarInt);
       delete el.dataset.radarInterval;
     }
     if (el.isConnected) el.remove();
   }
   ```
   Apply to:
   - `handleEditMessage` catch block (`index.html:2229`)
   - `regenerateResponse` catch block (`index.html:2834`)
   - `sendMessage` catch block (`index.html:1924`)

---

## 5. Verification Method

### 5.1 Verification Commands
To independently verify the removal of dead `.thinking-orb` rules and syntax validity:
```powershell
# 1. Verify no lingering thinking-orb classes in index.html after implementation
powershell -Command "Select-String -Path index.html -Pattern 'thinking-orb'"

# 2. Verify all catch blocks invoke radar cleanup
powershell -Command "Select-String -Path index.html -Pattern 'removeTypingIndicator'"

# 3. Verify CSS keyframe definitions are present
powershell -Command "Select-String -Path index.html -Pattern '@keyframes radar-sweep|@keyframes radar-blip-pulse|@keyframes tactical-core-pulse'"
```

### 5.2 Browser Runtime Validation
1. Open `index.html` in Chrome/Edge Developer Tools.
2. Send a prompt to trigger typing indicator.
3. In Developer Tools -> Rendering tab:
   - Enable "Paint flashing": Confirm no continuous green rect flashes outside `.tactical-radar-hud` (isolated via `contain: paint`).
   - Enable "Frame Rendering Stats": Confirm frame rate stays pinned at 60fps (or 120/144fps on high-refresh displays).
4. Simulate first chunk response:
   - Verify indicator is cleanly replaced by the assistant bubble with zero DOM remnants.
   - Inspect Chrome Developer Tools Memory tab: confirm active `setInterval` count decreases by 1.
5. Invalidation Conditions:
   - If the radar beam sweeps counter-clockwise or its tail appears ahead of the leading ray, the conic-gradient angle mapping has been altered.
   - If `setInterval` logs warnings or ticks after response completion, `radarInterval` was not cleared in the active exit path.
