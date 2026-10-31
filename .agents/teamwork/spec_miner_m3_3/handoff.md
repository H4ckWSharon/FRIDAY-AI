# Handoff Report — Requirement 3: Chat UX Long-Wait Progress State & Concurrency Guard

**Agent**: Spec Miner M3 Telemetry & Tests (`spec_miner_m3_3`)  
**Target Milestone**: M3 (Chat UX Tactical Radar Progress State & Concurrency Guard)  
**Authoritative Sources**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `backend/test_e2e_requirements.py`, `frontend/index.html`

---

## 1. Observation

Direct examination of the authoritative specification and codebase revealed:

1. **`ORIGINAL_REQUEST.md` (§ R3, lines 17–19, lines 35–38)**:
   - Requires an animated tactical radar/pulse indicator with dynamic multi-stage status updates during long generation cycles (~2.5–3 minutes).
   - Requires waiting state to prevent users from triggering concurrent duplicate requests or queue spikes via retry buttons.

2. **`PROJECT.md` (§ Architecture & Feature Inventory, lines 17–21, lines 41–44)**:
   - **F10 Tactical Radar Sweep HUD Animation**: High-fidelity SVG/CSS 360° sweeping radar beam, concentric grids, and crimson neon pulse (`#FF3038`).
   - **F11 Dynamic Multi-Stage Status Updates**: 6-stage rotating tactical telemetry updates.
   - **F12 Live Elapsed / Estimated Timer**: Active timer formatted as `[EST. ~02:45] ELAPSED: MM:SS` (or `MM:SS / ~02:45`).
   - **F13 Concurrency & Retry Spam Guard**: Immediate synchronous UI locking on `sendMessage`, `usePrompt`, `startNewChat`, and `regen` buttons.

3. **Current State of `frontend/index.html`**:
   - Lines 208–273: CSS definitions for `.tactical-radar-hud`, `.tactical-radar-ring-1`, `.tactical-radar-ring-2`, `.tactical-radar-crosshair-v`, `.tactical-radar-crosshair-h`, `.tactical-radar-sweep`, and `.tactical-radar-core`.
   - Lines 2295–2303: Current JavaScript has a non-standard 7-stage array with generic text (e.g. `'Initializing Neural Matrix & Security Weights...'`, `'Synthesizing Threat Vector Matrix & CVE Telemetry...'`).
   - Line 2263 & 2313: Timer updates as plain `${mins}:${secs}`, omitting the required `[EST. ~02:45]` estimated duration badge.
   - Lines 1833–1846 (`setInputEnabled`): Only toggles `chatInput.disabled` and switches `#send-btn` / `#stop-btn`. It does **not** disable prompt cards (`.prompt-card`), New Chat buttons (`button[onclick*="startNewChat"]`), or retry buttons (`.regen-resp-btn`).
   - Lines 1785–1800 (`startNewChat`): Contains **no check** for `isStreaming || isSubmitting`. Clicking "New Chat" mid-inference leaves the reader dangling and corrupts state.
   - Line 1810 (`usePrompt`): Does not guard against execution during `isStreaming || isSubmitting`.
   - Line 2834 (`regenerateLastResponse`): `catch` block removes `typingEl` without clearing `div.dataset.radarInterval`, leaving an orphaned interval timer.

4. **Current State of `backend/test_e2e_requirements.py`**:
   - Lines 398–468 (`TestTier1Requirement3ChatUXWaitingStateAndConcurrency`):
     - `test_tier1_r3_ui_radar_and_telemetry_markup_present`: Only weakly asserts `assert ("radar" in html.lower() or "thinking" in html.lower() or "#ff3038" in html.lower())`.
     - `test_tier1_r3_ui_concurrency_locks_script_present`: Only asserts `"disabled" in html.lower()` and `"sendmessage" in html.lower()`.
     - Completely lacks verification of the 6-stage telemetry texts, interval timings, estimated timer formatting, or synchronous locking across `usePrompt`, `startNewChat`, and `regen` buttons.

---

## 2. Logic Chain

1. **Inference Latency Context**: Ollama inference on the 27.3B Q4 parameter model (`orcasaq-cyber-27b:latest`) on CPU takes ~150s to 180s (~2.5 to 3 minutes). Without engaging tactical feedback, users perceive the system as frozen and trigger page refreshes or duplicate clicks.
2. **Telemetry State Machine Alignment**:
   - To reflect realistic CPU inference progression, the state machine must transition through 6 distinct tactical stages corresponding to inference phases (attack surface analysis -> vector evaluation -> payload synthesis -> evasion heuristics -> neural matrix compilation -> intelligence stream delivery).
   - Each stage transition must occur at exact timestamps: `0s`, `20s`, `50s`, `90s`, `130s`, `170s+`.
3. **Deterministic DOM Verification**:
   - Automated tests need reliable DOM identifiers rather than loose substring checks.
   - Adding explicit IDs, CSS classes, and `data-testid` / `data-stage` attributes allows both static regex assertions and dynamic DOM/browser assertions to verify every visual element deterministically.
4. **Client-Side Concurrency Elimination**:
   - While the backend already enforces `acquire_inference_capacity(user_id)` (returning 429), client-side double-clicks waste network roundtrips and show error toasts.
   - Locking must be synchronous and comprehensive across all 4 entry points: `sendMessage()`, `usePrompt()`, `startNewChat()`, and `regenerateLastResponse()`.

---

## 3. Specifications Discovered

### A. The 6-Stage Telemetry Status State Machine

```
   [User Submits Query]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: [0s - 20s)                                         │
│ Text: "ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE..."   │
└──────────────────────────┬──────────────────────────────────┘
                           │ (t = 20s)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: [20s - 50s)                                        │
│ Text: "EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS..."
└──────────────────────────┬──────────────────────────────────┘
                           │ (t = 50s)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: [50s - 90s)                                        │
│ Text: "SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD..."         │
└──────────────────────────┬──────────────────────────────────┘
                           │ (t = 90s)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: [90s - 130s)                                       │
│ Text: "CORRELATING OFFENSIVE HEURISTICS & DEFENSE EVASION..."
└──────────────────────────┬──────────────────────────────────┘
                           │ (t = 130s)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: [130s - 170s)                                      │
│ Text: "COMPILING NEURAL RESPONSE MATRIX..."                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ (t = 170s+)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 6: [170s+)                                            │
│ Text: "FINALIZING TACTICAL INTELLIGENCE STREAM..."          │
└──────────────────────────┬──────────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
[First SSE Chunk Arrives]      [Error or Abort / Stop]
- clearInterval(radarInterval) - clearInterval(radarInterval)
- Replace HUD with Assistant   - Remove typing indicator
  Bubble                       - Restore UI controls
- Stream text tokens           - Display error toast
```

#### Exact State Progression Table
| Stage # | Time Window | Threshold (`at`) | Exact Telemetry Text | Semantic Phase |
|---------|-------------|------------------|----------------------|----------------|
| **Stage 1** | `0s ≤ t < 20s` | `0` | `ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE...` | Ingests prompt, tokenizes input, checks system weights |
| **Stage 2** | `20s ≤ t < 50s` | `20` | `EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS...` | Evaluates CVE heuristics, protocol vectors, prompt intent |
| **Stage 3** | `50s ≤ t < 90s` | `50` | `SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD...` | Deep 27B CPU transformer layers computing payload |
| **Stage 4** | `90s ≤ t < 130s` | `90` | `CORRELATING OFFENSIVE HEURISTICS & DEFENSE EVASION...` | Offense/defense correlation and stealth synthesis |
| **Stage 5** | `130s ≤ t < 170s` | `130` | `COMPILING NEURAL RESPONSE MATRIX...` | Attention head aggregation and output formatting |
| **Stage 6** | `t ≥ 170s` | `170` | `FINALIZING TACTICAL INTELLIGENCE STREAM...` | Final token assembly and SSE streaming preparation |

#### Lifecycle Hooks
1. **Instantiation (`renderTypingIndicator`)**:
   - Immediately sets `#tactical-status-label` to Stage 1 text.
   - Sets `data-telemetry-stage="1"`.
   - Sets `#tactical-radar-timer` to initial format `[EST. ~02:45] ELAPSED: 00:00`.
   - Starts 1000ms `setInterval`.
2. **Tick Evaluation (Every 1000ms)**:
   - Increments elapsed counter `startSeconds++`.
   - Updates `#tactical-radar-timer` with `[EST. ~02:45] ELAPSED: MM:SS`.
   - Iterates sequence in descending order: `for (let i = statusSequence.length - 1; i >= 0; i--)`.
   - When `startSeconds >= statusSequence[i].at`, updates `#tactical-status-label.textContent` and `data-stage="<stage>"`.
3. **Transition to Streaming (`chunk` SSE event received)**:
   - Invokes `clearInterval(radarInterval)`.
   - Clears `orbTimer`.
   - Seamlessly replaces `typingEl` with `assistantEl` in the DOM.
4. **Cancellation / Error (`stopBtn` clicked, network failure, 4xx/5xx)**:
   - Invokes `clearInterval(radarInterval)`.
   - Removes `typingEl` from DOM if connected.
   - Unlocks all UI controls via `setInputEnabled(true)`.

---

### B. Deterministic DOM Identifiers & Attributes

| Element Description | Selector / ID | Data Attributes | CSS Classes | Test Assertion Purpose |
|---------------------|---------------|-----------------|-------------|------------------------|
| Radar HUD Outer Sphere | `.tactical-radar-hud` | `data-testid="radar-hud"` | `tactical-radar-hud shrink-0` | Verifies presence of HUD container |
| Radar Inner Concentric Ring 1 | `.tactical-radar-ring-1` | `data-testid="radar-ring-1"` | `tactical-radar-ring-1` | Verifies inner dashed targeting ring |
| Radar Outer Concentric Ring 2 | `.tactical-radar-ring-2` | `data-testid="radar-ring-2"` | `tactical-radar-ring-2` | Verifies outer solid range circle |
| Vertical Crosshair | `.tactical-radar-crosshair-v` | `data-testid="radar-crosshair-v"` | `tactical-radar-crosshair-v` | Verifies vertical targeting alignment |
| Horizontal Crosshair | `.tactical-radar-crosshair-h` | `data-testid="radar-crosshair-h"` | `tactical-radar-crosshair-h` | Verifies horizontal targeting alignment |
| 360° Rotating Radar Beam | `.tactical-radar-sweep` | `data-testid="radar-sweep"` | `tactical-radar-sweep` | Verifies conical gradient & `radar-sweep` 360° keyframes |
| Pulsing Neon Radar Core | `.tactical-radar-core` | `data-testid="radar-core"` | `tactical-radar-core` | Verifies crimson pulse `#FF3038` and scale animation |
| Telemetry Header Badge | `.tactical-telemetry-badge` | `data-testid="telemetry-badge"` | `tactical-telemetry-badge` | Verifies tactical badge styling |
| Telemetry Status Label | `#tactical-status-label` | `data-testid="tactical-status-label"`, `data-stage="1".."6"` | `font-mono text-xs text-[#F5F5F5] font-medium tracking-wide truncate` | Verifies exact stage text rotation |
| Live & Estimated Timer | `#tactical-radar-timer` | `data-testid="radar-timer"` | `tactical-timer-badge` | Verifies `[EST. ~02:45] ELAPSED: MM:SS` format |
| Progress Bar Container | `.tactical-progress-container` | `data-testid="tactical-progress"` | `tactical-progress-container` | Verifies tactical container |
| Indeterminate Shimmer Fill | `.tactical-progress-bar-fill` | `data-testid="progress-fill"` | `tactical-progress-bar-fill` | Verifies gradient sweep animation |
| Send Message Button | `#send-btn` | `data-concurrency-locked="true|false"` | - | Verifies button disabled during streaming |
| Chat Input Textarea | `#chat-input` | `data-concurrency-locked="true|false"` | - | Verifies input disabled during streaming |
| Suggested Prompt Cards | `.prompt-card` | `data-testid="prompt-card"` | `prompt-card` | Verifies prompt pills locked during streaming |
| New Chat Triggers | `#new-chat-btn`, `#header-new-chat-btn`, `button[onclick*="startNewChat"]` | `data-testid="new-chat-btn"` | - | Verifies new chat action guarded |
| Response Regenerate Buttons | `.regen-resp-btn` | `data-testid="regen-resp-btn"` | `regen-resp-btn` | Verifies retry button locked during streaming |

---

### C. Concurrency Guard Architecture

To eliminate race conditions, the UI must implement a two-tier locking mechanism:

1. **Procedural Early Returns**:
   - `sendMessage()`:
     ```javascript
     if (!text || isStreaming || isSubmitting) return;
     isSubmitting = true;
     ```
   - `usePrompt(text)`:
     ```javascript
     if (isStreaming || isSubmitting) return;
     chatInput.value = text;
     autoResizeInput();
     sendMessage();
     ```
   - `startNewChat()`:
     ```javascript
     if (isStreaming || isSubmitting) return;
     ```
   - `regenerateLastResponse(bubble)`:
     ```javascript
     if (isStreaming || isSubmitting) {
       showToast('Please wait for current response to complete', 'info');
       return;
     }
     ```
   - `document.addEventListener('keydown', (e) => ...)`:
     ```javascript
     if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
       e.preventDefault();
       if (isStreaming || isSubmitting) return;
       startNewChat();
     }
     ```

2. **DOM-Level State Locking via `setInputEnabled(enabled)`**:
   ```javascript
   function setInputEnabled(enabled) {
     chatInput.disabled = !enabled;
     
     // Toggle send / stop buttons
     if (enabled) {
       sendBtn.classList.remove('hidden');
       stopBtn.classList.add('hidden');
       stopBtn.classList.remove('flex');
       updateSendButtonState();
     } else {
       sendBtn.classList.add('hidden');
       stopBtn.classList.remove('hidden');
       stopBtn.classList.add('flex');
     }
     
     // Lock / unlock prompt cards
     document.querySelectorAll('.prompt-card').forEach(card => {
       card.disabled = !enabled;
       card.classList.toggle('pointer-events-none', !enabled);
       card.classList.toggle('opacity-50', !enabled);
     });
     
     // Lock / unlock New Chat buttons
     document.querySelectorAll('button[onclick*="startNewChat"]').forEach(btn => {
       btn.disabled = !enabled;
       btn.classList.toggle('pointer-events-none', !enabled);
       btn.classList.toggle('opacity-50', !enabled);
     });
     
     // Lock / unlock Regenerate buttons
     document.querySelectorAll('.regen-resp-btn').forEach(btn => {
       btn.disabled = !enabled;
       btn.classList.toggle('pointer-events-none', !enabled);
       btn.classList.toggle('opacity-40', !enabled);
     });
     
     document.body.dataset.concurrencyLocked = (!enabled).toString();
   }
   ```

3. **Guaranteed Unlock in `finally`**:
   Both `sendMessage()` and `regenerateLastResponse()` must restore `isSubmitting = false`, `isStreaming = false`, and call `setInputEnabled(true)` in their `finally` blocks, ensuring no deadlock occurs regardless of whether the call succeeded, failed with HTTP error, or was aborted by the user.

---

### D. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Chat UX | 360° Tactical Radar Sweep | Conic gradient radar beam rotating 360° in 2.4s with concentric rings & crosshairs | CSS keyframes `radar-sweep`, `from { transform: rotate(0deg); } to { transform: rotate(360deg); }` | Sweeping neon beam (#FF3038) over crosshairs | Degrades gracefully to static HUD if CSS animations disabled | `PROJECT.md` line 18, `index.html` lines 209–273 |
| 2 | Chat UX | Neon Core Pulse Animation | Glowing red central orb pulsating scale and box-shadow every 1.4s | CSS keyframes `tactical-pulse` | `#FF3038` neon heartbeat glow | N/A | `index.html` lines 260–273 |
| 3 | Chat UX | 6-Stage Telemetry State Machine | Dynamic status label rotating through 6 tactical inference phases based on elapsed time | Elapsed seconds `0`, `20`, `50`, `90`, `130`, `170+` | Uppercase tactical strings in `#tactical-status-label` | Fallback to Stage 6 on extended wait (>170s) | Dispatch Scope, `PROJECT.md` line 19 |
| 4 | Chat UX | Elapsed & Estimated Duration Timer | Real-time ticker counting elapsed generation time alongside estimated baseline (~02:45) | 1s `setInterval` tick | Text matching `[EST. ~02:45] ELAPSED: MM:SS` in `#tactical-radar-timer` | Timer stops on first SSE chunk or error | `PROJECT.md` line 20, Dispatch Scope |
| 5 | Concurrency | Synchronous Send Button Lock | Immediate disabling and hiding of `#send-btn` when query is dispatched | Click or `Enter` on `#chat-input` | `#send-btn` hidden, `#stop-btn` displayed, `isSubmitting=true` | Re-enabled in `finally` block | `index.html` lines 1853–1856, `PROJECT.md` line 21 |
| 6 | Concurrency | Synchronous Prompt Pill Lock | Disabling clickability on `.prompt-card` during inference | Click on prompt pill | Prompt cards given `disabled` and `pointer-events-none` | Re-enabled in `finally` block | Dispatch Scope, `index.html` line 1810 |
| 7 | Concurrency | Synchronous New Chat Lock | Blocking new chat resets while generation is active | Click on New Chat or `Ctrl+N` / `⌘N` | Action ignored, state preserved | Re-enabled when response completes | Dispatch Scope, `index.html` lines 1785, 1802 |
| 8 | Concurrency | Synchronous Regenerate Button Lock | Blocking duplicate retries on `.regen-resp-btn` while streaming | Click on `.regen-resp-btn` | Button disabled, `showToast` notice if clicked | Re-enabled in `finally` block | Dispatch Scope, `index.html` lines 2803–2807 |
| 9 | Lifecycle | First Chunk HUD Swap | Seamlessly swapping radar HUD typing indicator with assistant markdown bubble upon first token | SSE event: `chunk` | `typingEl.replaceWith(assistantEl)` and `clearInterval` | Swapped on `done` if stream was empty | `index.html` lines 2435–2442 |
| 10 | Lifecycle | Interval Timer Cleanup | Guaranteed cancellation of `setInterval` on abort, error, or completion | `clearInterval(radarInterval)` | Stops timer thread, prevents memory leaks | Guarded check `if (radarInt) clearInterval(radarInt)` | `index.html` lines 1925–1927, 2439 |

---

### E. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Telemetry State Machine | Ultra-fast response (< 1s, e.g. quick greeting "hi") | Only Stage 1 is displayed for < 1s; first chunk immediately cancels interval and replaces HUD before Stage 2 triggers |
| 2 | Telemetry State Machine | Extended slow inference (t = 240s, up to 300s timeout) | State machine reaches Stage 6 at 170s and remains in Stage 6 until chunk arrives or 300s timeout occurs |
| 3 | Concurrency Guard | Rapid multi-click spam on Send button (5 clicks in 100ms) | First click sets `isSubmitting = true`; subsequent 4 clicks return immediately at line 1851 without creating network requests |
| 4 | Concurrency Guard | User clicks prompt pill while streaming active query | `usePrompt()` evaluates `if (isStreaming || isSubmitting) return;` and ignores input without clearing textarea |
| 5 | Concurrency Guard | User presses `Ctrl+N` / `Cmd+N` mid-stream | Key handler blocks execution; ongoing SSE stream is not interrupted or orphaned |
| 6 | Concurrency Guard | User clicks Retry / Regenerate on previous message while another response is generating | `regenerateLastResponse()` detects `isStreaming === true` and displays notice toast: "Please wait for current response to complete" |
| 7 | Lifecycle / Abort | User clicks `#stop-btn` during Stage 3 (t = 65s) | `activeReader.cancel()` triggers, interval is cleared, HUD is removed, and controls are synchronously unlocked |
| 8 | Error Handling | Backend returns HTTP 429 (Daily limit reached) | Error caught in `streamAssistantResponse()`, `typingEl` interval cleared and removed, pricing modal opened, controls unlocked |
| 9 | Network Drop | Server disconnects / TCP reset mid-generation | SSE reader throws error; `finally` block executes `setInputEnabled(true)` preventing UI deadlock |
| 10 | Regenerate Cleanup | Error thrown during regeneration request | `catch` in `regenerateLastResponse` clears `radarInterval` and removes `typingEl` cleanly |

---

## 4. Concrete Python Automated Test Assertions

Below are the complete, runnable Python pytest test methods specified to replace and expand the superficial tests currently in `backend/test_e2e_requirements.py`:

```python
import os
import re
import pytest

INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")


def read_index_html() -> str:
    assert os.path.exists(INDEX_HTML_PATH), f"index.html must exist at {INDEX_HTML_PATH}"
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


class TestRequirement3ChatUXRadarAndTelemetrySpecifications:
    """Rigorous verification of R3 Tactical Radar HUD, Telemetry, and Concurrency Guards."""

    def test_r3_radar_hud_and_360_animation_specification(self):
        """
        Verify index.html contains the full tactical radar HUD hierarchy:
        - Outer HUD container (.tactical-radar-hud)
        - Concentric rings (.tactical-radar-ring-1, .tactical-radar-ring-2)
        - Crosshairs (.tactical-radar-crosshair-v, .tactical-radar-crosshair-h)
        - Sweeping conical beam (.tactical-radar-sweep)
        - Pulsing neon core (.tactical-radar-core)
        - 360-degree rotation keyframes (@keyframes radar-sweep)
        - Crimson neon branding color (#FF3038)
        """
        html = read_index_html()

        # 1. Structure & Classes
        assert ".tactical-radar-hud" in html, "Missing .tactical-radar-hud CSS class"
        assert ".tactical-radar-ring-1" in html, "Missing .tactical-radar-ring-1 CSS class"
        assert ".tactical-radar-ring-2" in html, "Missing .tactical-radar-ring-2 CSS class"
        assert ".tactical-radar-crosshair-v" in html, "Missing .tactical-radar-crosshair-v CSS class"
        assert ".tactical-radar-crosshair-h" in html, "Missing .tactical-radar-crosshair-h CSS class"
        assert ".tactical-radar-sweep" in html, "Missing .tactical-radar-sweep CSS class"
        assert ".tactical-radar-core" in html, "Missing .tactical-radar-core CSS class"

        # 2. Keyframes & 360-degree sweep
        sweep_match = re.search(r"@keyframes\s+radar-sweep\s*\{([^}]+)\}", html, re.DOTALL)
        assert sweep_match is not None, "Missing @keyframes radar-sweep"
        keyframes_content = sweep_match.group(1)
        assert "rotate(0deg)" in keyframes_content, "radar-sweep must start at 0deg"
        assert "rotate(360deg)" in keyframes_content, "radar-sweep must rotate full 360deg"

        # 3. Pulse animation & Brand Color
        assert "@keyframes tactical-pulse" in html, "Missing @keyframes tactical-pulse"
        assert re.search(r"#ff3038", html, re.IGNORECASE), "Missing crimson neon color #FF3038"

    def test_r3_telemetry_6_stage_state_machine_specification(self):
        """
        Verify index.html specifies the exact 6-stage telemetry state machine
        with required verbatim texts and timing boundaries:
          Stage 1 (0s):   ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE...
          Stage 2 (20s):  EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS...
          Stage 3 (50s):  SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD...
          Stage 4 (90s):  CORRELATING OFFENSIVE HEURISTICS & DEFENSE EVASION...
          Stage 5 (130s): COMPILING NEURAL RESPONSE MATRIX...
          Stage 6 (170s): FINALIZING TACTICAL INTELLIGENCE STREAM...
        """
        html = read_index_html()

        expected_stages = [
            (0, "ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE..."),
            (20, "EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS..."),
            (50, "SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD..."),
            (90, "CORRELATING OFFENSIVE HEURISTICS & DEFENSE EVASION..."),
            (130, "COMPILING NEURAL RESPONSE MATRIX..."),
            (170, "FINALIZING TACTICAL INTELLIGENCE STREAM..."),
        ]

        # Verify all 6 exact messages appear in the codebase
        for threshold, text in expected_stages:
            assert text in html, f"Missing telemetry stage text for {threshold}s: '{text}'"

        # Verify status label element exists
        assert 'id="tactical-status-label"' in html, "Missing #tactical-status-label element in index.html"

        # Verify threshold numbers are present in statusSequence rotation logic
        for threshold, _ in expected_stages:
            assert re.search(rf"(?:at|seconds|time)\s*:\s*{threshold}\b", html), \
                f"Missing rotation threshold definition at {threshold}s in index.html"

    def test_r3_elapsed_and_estimated_timer_specification(self):
        """
        Verify index.html contains the timer HUD with:
        - #tactical-radar-timer element
        - Estimated baseline context ([EST. ~02:45])
        - Dynamic elapsed formatting (ELAPSED: MM:SS or mins:secs)
        - Clean interval cancellation (clearInterval)
        """
        html = read_index_html()

        assert 'id="tactical-radar-timer"' in html, "Missing #tactical-radar-timer DOM element"
        assert "[EST. ~02:45]" in html or "~02:45" in html, "Missing estimated duration marker (~02:45)"
        assert "ELAPSED:" in html or "elapsed" in html.lower(), "Missing ELAPSED label in timer display"
        assert "clearInterval" in html, "Missing clearInterval for radar timer interval"

    def test_r3_synchronous_concurrency_locks_specification(self):
        """
        Verify synchronous locking across all entry points to eliminate race conditions:
        1. sendMessage checks !text || isStreaming || isSubmitting
        2. usePrompt checks isStreaming || isSubmitting
        3. startNewChat checks isStreaming || isSubmitting
        4. regenerateLastResponse checks isStreaming || isSubmitting
        5. Ctrl+N keydown shortcut checks isStreaming || isSubmitting
        6. setInputEnabled disables input, sendBtn, prompt cards, and New Chat triggers
        """
        html = read_index_html()

        # 1. Guard in sendMessage
        assert re.search(r"function\s+sendMessage\s*\(\)\s*\{[^}]*isStreaming", html), \
            "sendMessage() must guard against isStreaming"

        # 2. Guard in usePrompt
        assert re.search(r"function\s+usePrompt\s*\([^)]*\)\s*\{[^}]*isStreaming", html), \
            "usePrompt() must guard against isStreaming"

        # 3. Guard in startNewChat
        assert re.search(r"function\s+startNewChat\s*\(\)\s*\{[^}]*isStreaming", html), \
            "startNewChat() must guard against isStreaming"

        # 4. Guard in regenerateLastResponse
        assert re.search(r"async\s+function\s+regenerateLastResponse\s*\([^)]*\)\s*\{[^}]*isStreaming", html), \
            "regenerateLastResponse() must guard against isStreaming"

        # 5. setInputEnabled comprehensive locking
        assert "setInputEnabled" in html, "Missing setInputEnabled function"
        assert "prompt-card" in html and "disabled" in html, "prompt cards must be locked during streaming"
```

---

## 5. Caveats

1. **Client Clock Drift**:
   - `setInterval(..., 1000)` in browser tabs can drift if the tab is backgrounded. While acceptable for a cosmetic waiting indicator, if exact wall-clock alignment is desired, comparing `Date.now() - startTime` inside the tick handler provides drift-proof elapsed seconds.
2. **Mobile Viewport Constraints**:
   - On very narrow screens (< 360px), displaying `[EST. ~02:45] ELAPSED: MM:SS` alongside the badge requires either wrapping or `truncate` handling. The CSS flex row handles wrapping gracefully with `flex-wrap`.
3. **No Direct Changes Applied**:
   - In accordance with the Spec Miner role, no files outside `.agents/teamwork/spec_miner_m3_3/` were modified. The implementation must be executed by the assigned Developer agent in Milestone 3.

---

## 6. Conclusion

Requirement 3 requires three primary deliverables:
1. **Frontend State Machine Overhaul**: Update `statusSequence` in `index.html` from the outdated 7 generic stages to the authoritative 6-stage telemetry sequence (`0s`, `20s`, `50s`, `90s`, `130s`, `170s+`) with exact uppercase labels, and format `#tactical-radar-timer` as `[EST. ~02:45] ELAPSED: MM:SS`.
2. **Comprehensive Concurrency Lockout**: Extend `setInputEnabled(false)` and function heads (`usePrompt`, `startNewChat`, `regenerateLastResponse`, and `Ctrl+N`) to synchronously block all user interaction paths during inference.
3. **Automated Test Hardening**: Replace the 2 superficial test methods in `backend/test_e2e_requirements.py` (`test_tier1_r3_ui_radar_and_telemetry_markup_present` and `test_tier1_r3_ui_concurrency_locks_script_present`) with the 4 rigorous test methods specified above.

---

## 7. Verification Method

Once Milestone 3 implementation is applied, run the following verification commands:

1. **Verify Existing Suite Baseline**:
   ```powershell
   pytest backend\test_e2e_requirements.py -k "r3 or R3" -v
   ```
2. **Run Modernized Requirement 3 Specification Tests**:
   ```powershell
   pytest backend\test_e2e_requirements.py -k "TestTier1Requirement3ChatUXWaitingStateAndConcurrency" -v
   ```
3. **Inspect Frontend HTML Elements Directly**:
   ```powershell
   Select-String -Path "index.html" -Pattern "ANALYZING TARGET ARCHITECTURE|SYNTHESIZING ADVERSARIAL|EST\. ~02:45"
   ```
