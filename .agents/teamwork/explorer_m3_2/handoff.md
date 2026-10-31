# Handoff Report — Requirement 3: Chat Concurrency Guard, Live Timer & Stream Abortion

**Agent**: Explorer M3 Concurrency & Timer (`explorer_m3_2`)  
**Target Milestone**: M3 (Chat UX Tactical Radar Progress State & Concurrency Guard)  
**Parent Conversation ID**: `577be955-4ab1-40ee-81ad-fce0ceb6ffa6`  
**Primary Files Investigated**:
- `index.html` (lines 1480–2890, specifically `sendMessage`, `usePrompt`, `startNewChat`, `renderTypingIndicator`, `stopStreaming`, `regenerateLastResponse`, `executeUserMessageEdit`, `streamAssistantResponse`)
- `backend/services/ollama.py` (concurrency capacity governor & user serialization)
- `backend/test_e2e_requirements.py` (R3 tests, cancellation lock preservation)
- `orchestrator/PROJECT.md` (F10, F11, F12, F13 architecture)
- `spec_miner_m3_3/handoff.md` (6-stage telemetry state machine and test patterns)

---

## 1. Observation

Direct examination of `index.html`, `backend/services/ollama.py`, and `backend/test_e2e_requirements.py` revealed:

### Observation 1.1: State Mutation Delay and Race Condition in `sendMessage()`
In `index.html` (lines 1849–1907):
```javascript
1849:  async function sendMessage() {
1850:    const text = chatInput.value.trim();
1851:    if (!text || isStreaming || isSubmitting) return;
1852:
1853:    isSubmitting = true;
1854:    sendBtn.disabled = true;
1855:    sendBtn.classList.add('opacity-40', 'cursor-not-allowed', 'pointer-events-none');
...
1887:    renderUserMessage(text);
1888:    chatInput.value = '';
1889:    chatInput.style.height = 'auto';
1890:    updateSendButtonState();
...
1903:    const typingEl = renderTypingIndicator();
1904:    scrollToBottom(true);
1905:    setInputEnabled(false);
1906:    isStreaming = true;
```
- Line 1851 checks `isStreaming`, but `isStreaming` is not set to `true` until line 1906.
- Lines 1857–1904 perform multiple asynchronous operations (`getAuthHeaders().then(fetch(...))` line 1869), DOM mutations (`renderUserMessage(text)` line 1887), and event dispatches (`updateSendButtonState()` line 1890).
- `chatInput.disabled` is not set until line 1905 (`setInputEnabled(false)`). During the window between line 1853 and 1905, `chatInput` remains active and interactive.
- `isSubmitting = true;` (line 1853) is initialized outside of the `try ... finally` block (line 1908). If any runtime exception occurs between line 1853 and 1908 (e.g. storage error, UUID generation failure, or DOM rendering fault), `isSubmitting` remains permanently `true`, causing an unrecoverable UI deadlock.

### Observation 1.2: Complete Lack of Concurrency Guards in `startNewChat()` and `usePrompt()`
In `index.html` (lines 1785–1814):
```javascript
1785:  function startNewChat() {
1786:    conversationHistory = [];
1787:    currentConversationId = null;
1788:    conversationView.innerHTML = '';
1789:    welcomeView.classList.remove('hidden');
1790:    conversationView.classList.add('hidden');
...
1802:  document.addEventListener('keydown', (e) => {
1803:    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
1804:      e.preventDefault();
1805:      startNewChat();
1806:    }
1807:  });
1808:
1809:  // ─── Prompt Pill ─────────────────────────────────────────────────────────
1810:  function usePrompt(text) {
1811:    chatInput.value = text;
1812:    autoResizeInput();
1813:    sendMessage();
1814:  }
```
- `startNewChat()` (line 1785) contains **no check** for `isStreaming` or `isSubmitting`. If clicked while a response is streaming:
  - `conversationHistory` is cleared to `[]`.
  - `conversationView.innerHTML` is erased.
  - The background stream reader (`activeReader.read()`) continues executing in memory.
  - When tokens arrive from Ollama, they either append to orphaned detached DOM nodes or throw errors, and then push `{ role: 'assistant', content: fullText }` onto the newly initialized empty history, polluting the next session.
- The `Ctrl+N` / `⌘N` shortcut (lines 1802–1807) calls `startNewChat()` without any streaming check.
- `usePrompt(text)` (line 1810) executes without checking `isStreaming`. It unconditionally overwrites `chatInput.value` with `text`. While `sendMessage()` rejects the request at line 1851, the user's prior input is wiped.
- None of the prompt pills (`.prompt-card`) or New Chat buttons (`button[onclick*="startNewChat"]`) are visually locked or disabled during streaming.

### Observation 1.3: Incomplete Concurrency Protection on `.regen-resp-btn`
In `index.html` (lines 2803–2824):
```javascript
2803:  async function regenerateLastResponse(bubble) {
2804:    if (isStreaming) {
2805:      showToast('Please wait for current response to complete', 'info');
2806:      return;
2807:    }
2808:    if (!conversationHistory.length || !conversationHistory.some(m => m.role === 'user')) {
2809:      showToast('No prompt found to regenerate', 'info');
2810:      return;
2811:    }
2812:
2813:    // Pop the assistant turn from conversation history if it's the last one
2814:    if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'assistant') {
2815:      conversationHistory.pop();
2816:    }
2817:
2818:    bubble.remove();
2819:
2820:    const typingEl = renderTypingIndicator();
2821:    scrollToBottom();
2822:    setInputEnabled(false);
2823:    isStreaming = true;
```
- `isStreaming = true;` is only set at line 2823, **after** `bubble.remove()`, history manipulation, and indicator creation.
- `isSubmitting` is neither checked nor set.
- All other `.regen-resp-btn` elements across prior turns remain clickable in the DOM.
- In line 2834 (`catch (err)`):
  ```javascript
  2834:    if (typingEl.isConnected) typingEl.remove();
  ```
  It removes `typingEl` but **fails to call `clearInterval` on `typingEl.dataset.radarInterval`**, leaking an active 1000ms timer closure in memory.

### Observation 1.4: Incomplete Stream Abortion and Missing `AbortController`
In `index.html` (lines 1825–1830 and 2377–2412):
```javascript
1825:  function stopStreaming() {
1826:    if (activeReader) {
1827:      activeReader.cancel().catch(() => {});
1828:      activeReader = null;
1829:    }
1830:  }
...
2377:    const response = await fetch(`${BACKEND_URL}/api/chat`, {
2378:      method: 'POST',
2379:      headers: authHeaders,
2380:      body: JSON.stringify(payload),
2381:    });
...
2411:    activeReader = response.body.getReader();
```
- There is **no `AbortController`** instantiated or passed to `fetch(..., { signal })`.
- `activeReader` is only assigned at line 2411. If the user clicks `#stop-btn` during the initial connection / model queue phase (which can take 1–3s before headers return), `activeReader` is `null`. `stopStreaming()` does nothing, and the inference proceeds anyway.
- When `activeReader.cancel()` executes, `activeReader` is set to `null` in `stopStreaming()` (line 1828). Then in `streamAssistantResponse` (line 2418), the next loop iteration throws `TypeError: Cannot read properties of null (reading 'read')`. Because this is not an `AbortError`, `sendMessage()` catches it and calls `renderErrorMessage()`, presenting an error banner to the user despite them intentionally clicking "Stop".
- On the backend, `backend/services/ollama.py:47–52` serializes inference per user:
  ```python
  active_for_user = _user_active_inferences.get(uid, 0)
  if active_for_user >= settings.max_user_concurrent_inferences:
      raise HTTPException(status_code=429, detail="You have another active generation in progress. Please wait for it to complete.")
  ```
  Without `AbortController.abort()`, the underlying TCP stream is not terminated immediately, keeping the backend's `_user_active_inferences` semaphore locked for up to 300 seconds.

### Observation 1.5: Timer Format and Telemetry Status Deviation
In `index.html` (lines 2263 and 2295–2323):
```javascript
2263:  <span class="text-[10px] font-mono text-[#71717A] ml-auto tactical-timer-badge" id="tactical-radar-timer">00:00</span>
...
2295:  const statusSequence = [
2296:    { at: 0, text: 'Initializing Neural Matrix & Security Weights...' },
2297:    { at: 8, text: 'Synthesizing Threat Vector Matrix & CVE Telemetry...' },
2298:    { at: 20, text: 'Engaging 27B Deep Reasoning Engine...' },
2299:    { at: 40, text: 'Deconstructing Target Attack Surface & Protocols...' },
2300:    { at: 70, text: 'Formulating Offensive Exploit Chains & Mitigations...' },
2301:    { at: 110, text: 'Neural Attention Optimization & Token Assembly...' },
2302:    { at: 150, text: 'Finalizing Structured Cyber Intelligence Payload...' },
2303:  ];
...
2313:  if (timerEl) timerEl.textContent = `${mins}:${secs}`;
```
- Line 2263 and 2313 format the timer as plain `MM:SS`, omitting the authoritative estimated duration marker required by `PROJECT.md` and user specification: `[EST. ~02:45] ELAPSED: MM:SS`.
- Lines 2295–2303 implement a 7-stage sequence with generic copy rather than the authoritative 6-stage telemetry specification outlined in `PROJECT.md` line 19 and `spec_miner_m3_3/handoff.md`.

### Observation 1.6: False Upgrade Modal on 429 Concurrency Backpressure
In `index.html` (lines 2394–2401):
```javascript
2394:  if (response.status === 429) {
2395:    if (!auth.currentUser && !currentFirebaseUser) {
2396:      showAuthModal('Daily free guest limit reached (5 chats/day). Create a free account or upgrade to continue!');
2397:    } else {
2398:      showPricingModal();
2399:    }
2400:    throw new Error(typeof det === 'string' ? det : (det.message || 'Daily limit reached (5 chats/day). Upgrade to continue.'));
2401:  }
```
- If the backend rejects a concurrent request via `acquire_inference_capacity` (HTTP 429: "You have another active generation in progress"), the frontend assumes it was a daily quota depletion and triggers `showPricingModal()`. This presents a false payment barrier to paying users who clicked rapidly.

---

## 2. Logic Chain

1. **Race Condition Elimination Requires Line 1 Synchronous Locking**:
   - JavaScript execution is single-threaded, but browser event queues dispatch asynchronous tasks and microtasks.
   - If user interaction dispatches two events (e.g. Enter keypress followed immediately by Send button click or mechanical key bounce), both events will execute their event handlers.
   - If line 1 of the handler does not immediately inspect and synchronously engage a mutual-exclusion flag (`isStreaming || isSubmitting`), both invocations can pass the entry guard before the first has completed DOM preparation.
   - Therefore, `isStreaming = true;`, `isSubmitting = true;`, and `setInputEnabled(false);` must occur **synchronously on Line 1 of `sendMessage()`** before any DOM manipulation, asynchronous token fetch, or cache sync.

2. **Broadcasting Lock to All Secondary Entry Points**:
   - Chat submission is not triggered exclusively by `#send-btn` or `#chat-input`.
   - Secondary triggers include:
     1. Prompt cards on the welcome screen (`usePrompt()`).
     2. "New Chat" buttons in sidebar, header, and `Ctrl+N` keyboard shortcut (`startNewChat()`).
     3. Regenerate buttons on previous assistant messages (`regenerateLastResponse()`).
     4. User message editing ("Save & Submit" in `executeUserMessageEdit()`).
     5. Feedback suggestion chips (`.feedback-chip`).
   - If any of these entry points lack procedural early returns and DOM-level disabling, concurrent inference requests or state corruption will occur during inference.
   - Therefore, a centralized state synchronization function must toggle `disabled` attributes and pointer-event CSS classes across all such elements whenever streaming state transitions.

3. **Dual-Layer Abortion Guarantees Clean Network & Server Release**:
   - `activeReader.cancel()` operates on the client-side stream reader. It does not cancel an in-flight HTTP request during initial connection or headers negotiation.
   - An `AbortController` signal passed directly to `fetch()` guarantees that if "Stop" is clicked at any point (connection, queuing, or active streaming), the browser immediately terminates the TCP connection.
   - FastAPI server detects socket disconnection through `httpx` or ASGI disconnect, triggering `asyncio.CancelledError` inside `acquire_inference_capacity()`. This instantly releases the backend CPU semaphore and per-user inference lock, allowing subsequent requests without waiting for the 300s timeout.

4. **Guaranteed Timer Teardown Prevents Memory Leaks**:
   - Storing the timer `intervalId` solely in the DOM element's `dataset` is fragile: if the element is disconnected or removed before the interval is cleared, the interval closure continues executing indefinitely.
   - Storing a module-level reference (`activeRadarTimerInterval`) alongside element datasets allows a centralized teardown routine to clean up the timer under all terminal conditions (chunk arrival, stream end, error, user stop, or page navigation).

5. **Precise Telemetry & Timer Formatting Aligns with Authoritative Specs**:
   - Standardizing the timer format to `[EST. ~02:45] ELAPSED: MM:SS` provides immediate predictability for CPU inference times (~150s–180s).
   - Aligning the 6-stage telemetry messages with the phases of CPU inference keeps users informed and prevents premature page refreshes.

---

## 3. Caveats

- **CSS Visual Styling**: The visual design and CSS keyframes for the Radar HUD (`.tactical-radar-hud`, `@keyframes radar-sweep`) were analyzed in `index.html` lines 208–273 and are fully compatible. Detailed CSS styling was scoped to Explorer M3-1 (`explorer_m3_1`).
- **Backend Concurrency Model**: Backend inference concurrency is fixed at 1 active request per user by `backend/services/ollama.py`. Frontend concurrency locking directly supports this backend invariant; no backend changes are needed for M3.
- **Assumed Browser Support**: `AbortController` and `ReadableStream.getReader()` are supported across all modern browsers (Chrome 66+, Firefox 57+, Safari 11.1+, Edge 79+). No polyfills are required.

---

## 4. Conclusion & Code Patch Specification

### Summary of Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Chat Concurrency Lifecycle Architecture              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                  [User Input: Send / Prompt / Retry]
                                  │
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │ LINE 1 SYNCHRONOUS LOCKING:                             │
      │ if (isStreaming || isSubmitting) return;                │
      │ isStreaming = true; isSubmitting = true;                │
      │ setInputEnabled(false);                                 │
      │ - Disables #chat-input, hides #send-btn, shows #stop-btn│
      │ - Disables .prompt-card, New Chat btns, .regen-resp-btn │
      └───────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │ RENDER & INITIALIZE:                                    │
      │ - renderUserMessage(text)                               │
      │ - renderTypingIndicator():                              │
      │   * timer starts: "[EST. ~02:45] ELAPSED: 00:00"        │
      │   * activeRadarTimerInterval = setInterval(..., 1000)   │
      │   * activeAbortController = new AbortController()       │
      └───────────────────────────┬─────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
      [First SSE Chunk Arrived]       [User Clicks "Stop" Button]
      - clearActiveRadarTimer()       - activeAbortController.abort()
      - swap typingEl with bubble     - activeReader.cancel()
      - stream chunks into bubble     - clearActiveRadarTimer()
                    │                 - remove typingEl immediately
                    │                 - showToast("Generation stopped")
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │ FINALLY (Guaranteed Atomic Cleanup):                    │
      │ isStreaming = false; isSubmitting = false;              │
      │ activeReader = null; activeAbortController = null;      │
      │ clearActiveRadarTimer();                                │
      │ setInputEnabled(true);                                  │
      │ - Enables #chat-input, shows #send-btn, hides #stop-btn │
      │ - Restores .prompt-card, New Chat btns, .regen-resp-btn │
      └─────────────────────────────────────────────────────────┘
```

---

### Exact JavaScript Execution Flow & Code Patches

Below are the exact recommended code modifications for `index.html`.

#### Patch 1: Global State Declarations (near Line 1480)
**Location**: `index.html:1480`
```javascript
<<<< BEFORE
  let isStreaming = false;
  let activeReader = null;             // ReadableStreamDefaultReader - for cancel
====
  let isStreaming = false;
  let isSubmitting = false;
  let activeReader = null;             // ReadableStreamDefaultReader - for stream cancel
  let activeAbortController = null;    // AbortController - for immediate network abortion
  let activeTypingEl = null;           // Reference to current active typing indicator row
  let activeRadarTimerInterval = null; // Reference to 1000ms timer interval ID
>>>>
```

#### Patch 2: Centralized Timer Cleanup Helper
**Location**: Insert near line 1820
```javascript
  // ─── Centralized Radar Timer Teardown Helper ─────────────────────────────
  function clearActiveRadarTimer() {
    if (activeRadarTimerInterval) {
      clearInterval(activeRadarTimerInterval);
      activeRadarTimerInterval = null;
    }
    if (activeTypingEl) {
      const id = Number(activeTypingEl.dataset?.radarInterval);
      if (id) clearInterval(id);
    }
  }

  function isCancellationError(err) {
    if (!err) return false;
    return (
      err.name === 'AbortError' ||
      err.message?.toLowerCase().includes('abort') ||
      err.message?.toLowerCase().includes('cancel') ||
      err.message?.includes('The user aborted a request')
    );
  }
```

#### Patch 3: Comprehensive `setInputEnabled(enabled)`
**Location**: `index.html:1833–1846`
```javascript
<<<< BEFORE
  function setInputEnabled(enabled) {
    chatInput.disabled = !enabled;
    // Toggle send / stop button visibility
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
  }
====
  function setInputEnabled(enabled) {
    chatInput.disabled = !enabled;
    
    // 1. Toggle Send and Stop buttons
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

    // 2. Lock / unlock prompt cards on welcome screen
    document.querySelectorAll('.prompt-card').forEach(card => {
      card.disabled = !enabled;
      card.classList.toggle('pointer-events-none', !enabled);
      card.classList.toggle('cursor-not-allowed', !enabled);
      card.classList.toggle('opacity-50', !enabled);
    });

    // 3. Lock / unlock New Chat triggers in sidebar and header
    document.querySelectorAll('button[onclick*="startNewChat"], #new-chat-btn, #header-new-chat-btn').forEach(btn => {
      btn.disabled = !enabled;
      btn.classList.toggle('pointer-events-none', !enabled);
      btn.classList.toggle('cursor-not-allowed', !enabled);
      btn.classList.toggle('opacity-50', !enabled);
    });

    // 4. Lock / unlock Regenerate / Retry buttons across all turns
    document.querySelectorAll('.regen-resp-btn').forEach(btn => {
      btn.disabled = !enabled;
      btn.classList.toggle('pointer-events-none', !enabled);
      btn.classList.toggle('cursor-not-allowed', !enabled);
      btn.classList.toggle('opacity-40', !enabled);
    });

    // 5. Lock / unlock User Edit buttons
    document.querySelectorAll('.user-edit-btn').forEach(btn => {
      btn.disabled = !enabled;
      btn.classList.toggle('pointer-events-none', !enabled);
      btn.classList.toggle('cursor-not-allowed', !enabled);
      btn.classList.toggle('opacity-40', !enabled);
    });

    // 6. Set deterministic body attribute for automated testing
    document.body.dataset.concurrencyLocked = (!enabled).toString();
  }
>>>>
```

#### Patch 4: Clean Stream Abortion via `stopStreaming()`
**Location**: `index.html:1825–1830`
```javascript
<<<< BEFORE
  function stopStreaming() {
    if (activeReader) {
      activeReader.cancel().catch(() => {});
      activeReader = null;
    }
  }
====
  function stopStreaming() {
    // 1. Instantly abort in-flight HTTP request via AbortController
    if (activeAbortController) {
      try {
        activeAbortController.abort();
      } catch (e) {
        console.warn('activeAbortController abort warning:', e);
      }
      activeAbortController = null;
    }

    // 2. Cancel stream reader
    if (activeReader) {
      try {
        activeReader.cancel().catch(() => {});
      } catch (e) {
        console.warn('activeReader cancel warning:', e);
      }
      activeReader = null;
    }

    // 3. Clean up active timer interval
    clearActiveRadarTimer();

    // 4. Instantly remove typing indicator for immediate visual feedback
    if (activeTypingEl) {
      if (activeTypingEl.isConnected) {
        activeTypingEl.remove();
      }
      activeTypingEl = null;
    }

    // 5. Inform user
    showToast('Generation stopped', 'info');
  }
>>>>
```

#### Patch 5: `startNewChat()` and Keyboard Guard
**Location**: `index.html:1785–1807`
```javascript
<<<< BEFORE
  function startNewChat() {
    conversationHistory = [];
    currentConversationId = null;
    conversationView.innerHTML = '';
    welcomeView.classList.remove('hidden');
    conversationView.classList.add('hidden');
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
    closeSidebar();
    updateSidebarActive(null);
    updateWelcomeGreeting();
    userScrolledUp = false;
    updateScrollBottomBtn(false);
  }

  // ─── Keyboard Shortcut: Ctrl+N / ⌘N ─────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
      e.preventDefault();
      startNewChat();
    }
  });
====
  function startNewChat() {
    if (isStreaming || isSubmitting) {
      showToast('Please wait for current response to complete before starting a new chat', 'info');
      return;
    }
    clearActiveRadarTimer();
    conversationHistory = [];
    currentConversationId = null;
    conversationView.innerHTML = '';
    welcomeView.classList.remove('hidden');
    conversationView.classList.add('hidden');
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
    closeSidebar();
    updateSidebarActive(null);
    updateWelcomeGreeting();
    userScrolledUp = false;
    updateScrollBottomBtn(false);
  }

  // ─── Keyboard Shortcut: Ctrl+N / ⌘N ─────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
      e.preventDefault();
      if (isStreaming || isSubmitting) {
        showToast('Please wait for current response to complete before starting a new chat', 'info');
        return;
      }
      startNewChat();
    }
  });
>>>>
```

#### Patch 6: `usePrompt()` Guard
**Location**: `index.html:1810–1814`
```javascript
<<<< BEFORE
  function usePrompt(text) {
    chatInput.value = text;
    autoResizeInput();
    sendMessage();
  }
====
  function usePrompt(text) {
    if (isStreaming || isSubmitting) {
      showToast('Please wait for current response to complete', 'info');
      return;
    }
    chatInput.value = text;
    autoResizeInput();
    sendMessage();
  }
>>>>
```

#### Patch 7: Synchronous Line 1 Locking in `sendMessage()`
**Location**: `index.html:1849–1942`
```javascript
<<<< BEFORE
  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isStreaming || isSubmitting) return;

    isSubmitting = true;
    sendBtn.disabled = true;
    sendBtn.classList.add('opacity-40', 'cursor-not-allowed', 'pointer-events-none');

    const user = auth.currentUser || currentFirebaseUser;
    const isGuest = !user;
    const guestId = isGuest ? getGuestId() : null;

    if (isGuest && !localStorage.getItem('friday_guest_notified')) {
      showToast('⚡ Guest session active (5 free chats/day). Sign up anytime to save history!', 'info');
      localStorage.setItem('friday_guest_notified', 'true');
    }

    // Create or reuse conversation ID — registers backend record in background
    if (!currentConversationId) {
      currentConversationId = generateUUID();
      getAuthHeaders().then(headers => {
        fetch(`${BACKEND_URL}/api/conversations`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ id: currentConversationId, title: 'New Conversation' }),
        }).catch(() => {});
      });
    }

    showConversation();
    conversationHistory.push({ role: 'user', content: text });
    if (currentConversationId) {
      convMessagesCache.set(currentConversationId, {
        id: currentConversationId,
        messages: [...conversationHistory],
        selectedModel: currentSelectedModel,
      });
    }
    renderUserMessage(text);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    updateSendButtonState();

    // Instantly refresh remaining chats count in UI upon sending each chat
    if (subscriptionStatus && !subscriptionStatus.is_unlimited) {
      subscriptionStatus.daily_used = (subscriptionStatus.daily_used || 0) + 1;
      if (subscriptionStatus.chats_remaining !== null && subscriptionStatus.chats_remaining !== undefined) {
        subscriptionStatus.chats_remaining = Math.max(0, subscriptionStatus.chats_remaining - 1);
      }
      updateSubBadge(subscriptionStatus);
    }

    userScrolledUp = false;
    updateScrollBottomBtn(false);
    const typingEl = renderTypingIndicator();
    scrollToBottom(true);
    setInputEnabled(false);
    isStreaming = true;

    try {
      const assistantEl = await streamAssistantResponse(typingEl);
      const fullText = assistantEl.dataset.rawText || '';
      if (fullText) {
        conversationHistory.push({ role: 'assistant', content: fullText });
      }
      if (currentConversationId) {
        convMessagesCache.set(currentConversationId, {
          id: currentConversationId,
          messages: [...conversationHistory],
          selectedModel: currentSelectedModel,
        });
      }
      // Refresh sidebar so title updates after first turn
      loadSidebarHistory();
    } catch (err) {
      if (typingEl) {
        const radarInt = Number(typingEl.dataset.radarInterval);
        if (radarInt) clearInterval(radarInt);
        if (typingEl.isConnected) typingEl.remove();
      }
      if (err.name !== 'AbortError' && !err.message?.includes('cancel')) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      isSubmitting = false;
      isStreaming = false;
      activeReader = null;
      setInputEnabled(true);
      updateSendButtonState();
      chatInput.focus({ preventScroll: true });
      scrollToBottom(false);
      fetchSubscriptionStatus(); // Instant server sync after each chat completes or errors
    }
  }
====
  async function sendMessage() {
    // ── LINE 1: SYNCHRONOUS PROCEDURAL & RE-ENTRANCY LOCK ──────────────────
    if (isStreaming || isSubmitting) return;

    const text = chatInput.value.trim();
    if (!text) return;

    // Immediately acquire locking state BEFORE any async ticks or DOM dispatches
    isSubmitting = true;
    isStreaming = true;
    setInputEnabled(false); // Instantly disables chatInput, switches sendBtn to stopBtn, locks prompt cards, new chat, and retry btns

    let typingEl = null;

    try {
      const user = auth.currentUser || currentFirebaseUser;
      const isGuest = !user;
      const guestId = isGuest ? getGuestId() : null;

      if (isGuest && !localStorage.getItem('friday_guest_notified')) {
        showToast('⚡ Guest session active (5 free chats/day). Sign up anytime to save history!', 'info');
        localStorage.setItem('friday_guest_notified', 'true');
      }

      // Create or reuse conversation ID
      if (!currentConversationId) {
        currentConversationId = generateUUID();
        getAuthHeaders().then(headers => {
          fetch(`${BACKEND_URL}/api/conversations`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ id: currentConversationId, title: 'New Conversation' }),
          }).catch(() => {});
        });
      }

      showConversation();
      conversationHistory.push({ role: 'user', content: text });
      if (currentConversationId) {
        convMessagesCache.set(currentConversationId, {
          id: currentConversationId,
          messages: [...conversationHistory],
          selectedModel: currentSelectedModel,
        });
      }
      renderUserMessage(text);
      chatInput.value = '';
      chatInput.style.height = 'auto';

      // Update quota count
      if (subscriptionStatus && !subscriptionStatus.is_unlimited) {
        subscriptionStatus.daily_used = (subscriptionStatus.daily_used || 0) + 1;
        if (subscriptionStatus.chats_remaining !== null && subscriptionStatus.chats_remaining !== undefined) {
          subscriptionStatus.chats_remaining = Math.max(0, subscriptionStatus.chats_remaining - 1);
        }
        updateSubBadge(subscriptionStatus);
      }

      userScrolledUp = false;
      updateScrollBottomBtn(false);
      typingEl = renderTypingIndicator();
      scrollToBottom(true);

      const assistantEl = await streamAssistantResponse(typingEl);
      const fullText = assistantEl.dataset.rawText || '';
      if (fullText) {
        conversationHistory.push({ role: 'assistant', content: fullText });
      }
      if (currentConversationId) {
        convMessagesCache.set(currentConversationId, {
          id: currentConversationId,
          messages: [...conversationHistory],
          selectedModel: currentSelectedModel,
        });
      }
      loadSidebarHistory();
    } catch (err) {
      clearActiveRadarTimer();
      if (typingEl && typingEl.isConnected) {
        typingEl.remove();
      }
      if (!isCancellationError(err)) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      // ── GUARANTEED RECOVERY: Release all locks atomically ─────────────────
      isSubmitting = false;
      isStreaming = false;
      activeReader = null;
      activeAbortController = null;
      activeTypingEl = null;
      clearActiveRadarTimer();
      setInputEnabled(true);
      updateSendButtonState();
      chatInput.focus({ preventScroll: true });
      scrollToBottom(false);
      fetchSubscriptionStatus();
    }
  }
>>>>
```

#### Patch 8: Live Timer & Telemetry State Machine in `renderTypingIndicator()`
**Location**: `index.html:2244–2327`
```javascript
<<<< BEFORE
  function renderTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'flex gap-3 sm:gap-4 items-start typing-indicator-row w-full min-w-0';
    div.innerHTML = `
      <div class="tactical-radar-hud shrink-0" title="FRIDAY Neural Radar">
        <div class="tactical-radar-ring-1"></div>
        <div class="tactical-radar-ring-2"></div>
        <div class="tactical-radar-crosshair-v"></div>
        <div class="tactical-radar-crosshair-h"></div>
        <div class="tactical-radar-sweep"></div>
        <div class="tactical-radar-core"></div>
      </div>
      <div class="flex-1 flex flex-col max-w-2xl min-w-0 gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-heading font-semibold text-xs text-[#F5F5F5]">friday Cyber Pro</span>
          <span class="tactical-telemetry-badge">
            <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-ping"></span>
            NEURAL RADAR
          </span>
          <span class="text-[10px] font-mono text-[#71717A] ml-auto tactical-timer-badge" id="tactical-radar-timer">00:00</span>
        </div>
        <div class="tactical-progress-container flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="material-symbols-outlined text-[15px] text-[#FF3038] animate-spin shrink-0">autorenew</span>
              <span class="font-mono text-xs text-[#F5F5F5] font-medium tracking-wide truncate" id="tactical-status-label">Initializing Neural Matrix & Security Weights...</span>
            </div>
            <span class="text-[9px] font-mono text-[#71717A] shrink-0 font-bold uppercase tracking-wider hidden sm:inline">CPU 27B</span>
          </div>
          <div class="tactical-progress-bar-bg">
            <div class="tactical-progress-bar-fill"></div>
          </div>
          <div class="flex items-center justify-between text-[10px] font-mono text-[#71717A]">
            <span class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Deep CPU inference in progress (~2-3 mins). Model is computing full tactical response.
            </span>
            <span class="text-[9px] text-[#FF3038] font-bold shrink-0 uppercase tracking-wider">DO NOT REFRESH</span>
          </div>
        </div>
        <div class="thinking-orb-wrap hidden" id="thinking-orb-wrap-${Date.now()}">
          <div class="thinking-orb-box">
            <div class="thinking-orb"></div>
            <div class="thinking-orb-ring"></div>
          </div>
          <span class="thinking-label">Thinking…</span>
        </div>
      </div>
    `;
    conversationView.appendChild(div);

    const statusSequence = [
      { at: 0, text: 'Initializing Neural Matrix & Security Weights...' },
      { at: 8, text: 'Synthesizing Threat Vector Matrix & CVE Telemetry...' },
      { at: 20, text: 'Engaging 27B Deep Reasoning Engine...' },
      { at: 40, text: 'Deconstructing Target Attack Surface & Protocols...' },
      { at: 70, text: 'Formulating Offensive Exploit Chains & Mitigations...' },
      { at: 110, text: 'Neural Attention Optimization & Token Assembly...' },
      { at: 150, text: 'Finalizing Structured Cyber Intelligence Payload...' },
    ];

    let startSeconds = 0;
    const timerEl = div.querySelector('#tactical-radar-timer');
    const labelEl = div.querySelector('#tactical-status-label');

    const intervalId = setInterval(() => {
      startSeconds++;
      const mins = String(Math.floor(startSeconds / 60)).padStart(2, '0');
      const secs = String(startSeconds % 60).padStart(2, '0');
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;

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
====
  function renderTypingIndicator() {
    clearActiveRadarTimer();

    const div = document.createElement('div');
    div.className = 'flex gap-3 sm:gap-4 items-start typing-indicator-row w-full min-w-0';
    div.dataset.testid = 'typing-indicator-row';
    div.innerHTML = `
      <div class="tactical-radar-hud shrink-0" data-testid="radar-hud" title="FRIDAY Neural Radar">
        <div class="tactical-radar-ring-1" data-testid="radar-ring-1"></div>
        <div class="tactical-radar-ring-2" data-testid="radar-ring-2"></div>
        <div class="tactical-radar-crosshair-v" data-testid="radar-crosshair-v"></div>
        <div class="tactical-radar-crosshair-h" data-testid="radar-crosshair-h"></div>
        <div class="tactical-radar-sweep" data-testid="radar-sweep"></div>
        <div class="tactical-radar-core" data-testid="radar-core"></div>
      </div>
      <div class="flex-1 flex flex-col max-w-2xl min-w-0 gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-heading font-semibold text-xs text-[#F5F5F5]">friday Cyber Pro</span>
          <span class="tactical-telemetry-badge" data-testid="telemetry-badge">
            <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-ping"></span>
            NEURAL RADAR
          </span>
          <span class="text-[10px] font-mono text-[#71717A] ml-auto tactical-timer-badge" id="tactical-radar-timer" data-testid="radar-timer">[EST. ~02:45] ELAPSED: 00:00</span>
        </div>
        <div class="tactical-progress-container flex flex-col gap-2" data-testid="tactical-progress">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="material-symbols-outlined text-[15px] text-[#FF3038] animate-spin shrink-0">autorenew</span>
              <span class="font-mono text-xs text-[#F5F5F5] font-medium tracking-wide truncate" id="tactical-status-label" data-testid="tactical-status-label" data-stage="1">ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE...</span>
            </div>
            <span class="text-[9px] font-mono text-[#71717A] shrink-0 font-bold uppercase tracking-wider hidden sm:inline">CPU 27B</span>
          </div>
          <div class="tactical-progress-bar-bg">
            <div class="tactical-progress-bar-fill" data-testid="progress-fill"></div>
          </div>
          <div class="flex items-center justify-between text-[10px] font-mono text-[#71717A]">
            <span class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Deep CPU inference in progress (~2.5-3 mins). Model is computing full tactical response.
            </span>
            <span class="text-[9px] text-[#FF3038] font-bold shrink-0 uppercase tracking-wider">DO NOT REFRESH</span>
          </div>
        </div>
        <div class="thinking-orb-wrap hidden" id="thinking-orb-wrap-${Date.now()}">
          <div class="thinking-orb-box">
            <div class="thinking-orb"></div>
            <div class="thinking-orb-ring"></div>
          </div>
          <span class="thinking-label">Thinking…</span>
        </div>
      </div>
    `;
    conversationView.appendChild(div);

    // Authoritative 6-stage telemetry state machine
    const statusSequence = [
      { at: 0,   stage: '1', text: 'ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE...' },
      { at: 20,  stage: '2', text: 'EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS...' },
      { at: 50,  stage: '3', text: 'SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD...' },
      { at: 90,  stage: '4', text: 'CORRELATING OFFENSIVE HEURISTICS & DEFENSE EVASION...' },
      { at: 130, stage: '5', text: 'COMPILING NEURAL RESPONSE MATRIX...' },
      { at: 170, stage: '6', text: 'FINALIZING TACTICAL INTELLIGENCE STREAM...' },
    ];

    let startSeconds = 0;
    const timerEl = div.querySelector('#tactical-radar-timer');
    const labelEl = div.querySelector('#tactical-status-label');
    const fillEl  = div.querySelector('.tactical-progress-bar-fill');

    const intervalId = setInterval(() => {
      startSeconds++;
      const mins = String(Math.floor(startSeconds / 60)).padStart(2, '0');
      const secs = String(startSeconds % 60).padStart(2, '0');
      if (timerEl) {
        timerEl.textContent = `[EST. ~02:45] ELAPSED: ${mins}:${secs}`;
      }

      // Smooth progress bar scale towards ~165s
      if (fillEl) {
        const pct = Math.min(96, Math.round((startSeconds / 165) * 100));
        fillEl.style.width = `${pct}%`;
      }

      for (let i = statusSequence.length - 1; i >= 0; i--) {
        if (startSeconds >= statusSequence[i].at) {
          if (labelEl && labelEl.textContent !== statusSequence[i].text) {
            labelEl.textContent = statusSequence[i].text;
            labelEl.dataset.stage = statusSequence[i].stage;
          }
          break;
        }
      }
    }, 1000);

    activeRadarTimerInterval = intervalId;
    div.dataset.radarInterval = String(intervalId);
    activeTypingEl = div;
    return div;
  }
>>>>
```

#### Patch 9: `AbortController` Integration & 429 Discrimination in `streamAssistantResponse()`
**Location**: `index.html:2364–2468`
```javascript
<<<< BEFORE
    const authHeaders = await getAuthHeaders();
    const payload = {
      messages: conversationHistory,
      conversation_id: currentConversationId,
      stream: true,
    };
    const activeGuestId = (!auth.currentUser && !currentFirebaseUser) ? getGuestId() : null;
    if (activeGuestId) {
      payload.guest_id = activeGuestId;
    }
    if (currentSelectedModel) {
      payload.model = currentSelectedModel;
    }
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      clearTimeout(orbTimer);
      if (response.status === 401) {
        showAuthModal('Sign up or sign in to continue chatting with FRIDAY.');
        throw new Error('Authentication required or session expired. Please sign in or create an account.');
      }
      // Subscription limit / access gate errors
      if (response.status === 403 || response.status === 429) {
        let errDetail = {};
        try { errDetail = await response.json(); } catch {}
        const det = errDetail.detail || errDetail;
        if (response.status === 429) {
          if (!auth.currentUser && !currentFirebaseUser) {
            showAuthModal('Daily free guest limit reached (5 chats/day). Create a free account or upgrade to continue!');
          } else {
            showPricingModal();
          }
          throw new Error(typeof det === 'string' ? det : (det.message || 'Daily limit reached (5 chats/day). Upgrade to continue.'));
        }
        if (det.upgrade_required) {
          showPricingModal();
          throw new Error(det.message || 'Upgrade required to use this model.');
        }
        throw new Error(det.message || `Access denied (HTTP ${response.status})`);
      }
      throw new Error(`FRIDAY service encountered an issue (HTTP ${response.status})`);
    }
====
    activeAbortController = new AbortController();

    const authHeaders = await getAuthHeaders();
    const payload = {
      messages: conversationHistory,
      conversation_id: currentConversationId,
      stream: true,
    };
    const activeGuestId = (!auth.currentUser && !currentFirebaseUser) ? getGuestId() : null;
    if (activeGuestId) {
      payload.guest_id = activeGuestId;
    }
    if (currentSelectedModel) {
      payload.model = currentSelectedModel;
    }

    let response;
    try {
      response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(payload),
        signal: activeAbortController.signal,
      });
    } catch (fetchErr) {
      clearTimeout(orbTimer);
      clearActiveRadarTimer();
      throw fetchErr;
    }

    if (!response.ok) {
      clearTimeout(orbTimer);
      clearActiveRadarTimer();
      if (response.status === 401) {
        showAuthModal('Sign up or sign in to continue chatting with FRIDAY.');
        throw new Error('Authentication required or session expired. Please sign in or create an account.');
      }
      // Subscription limit / access gate errors
      if (response.status === 403 || response.status === 429) {
        let errDetail = {};
        try { errDetail = await response.json(); } catch {}
        const det = errDetail.detail || errDetail;
        const msgStr = typeof det === 'string' ? det : (det.message || '');
        
        // Discriminate concurrent inference rejection (429) vs daily quota depletion (429)
        if (response.status === 429) {
          if (msgStr.toLowerCase().includes('active generation') || msgStr.toLowerCase().includes('active request')) {
            showToast('⚡ Generation already in progress. Please wait for it to complete.', 'info');
            throw new Error(msgStr || 'Active generation in progress.');
          }
          if (!auth.currentUser && !currentFirebaseUser) {
            showAuthModal('Daily free guest limit reached (5 chats/day). Create a free account or upgrade to continue!');
          } else {
            showPricingModal();
          }
          throw new Error(msgStr || 'Daily limit reached (5 chats/day). Upgrade to continue.');
        }
        if (det.upgrade_required) {
          showPricingModal();
          throw new Error(det.message || 'Upgrade required to use this model.');
        }
        throw new Error(det.message || `Access denied (HTTP ${response.status})`);
      }
      throw new Error(`FRIDAY service encountered an issue (HTTP ${response.status})`);
    }
>>>>
```

And in chunk handling (lines 2435–2468):
```javascript
<<<< BEFORE
          if (eventType === 'chunk') {
            // First chunk: cancel orb timer & radar interval, swap indicator for bubble
            if (!firstChunkReceived) {
              firstChunkReceived = true;
              clearTimeout(orbTimer);
              const radarInt = Number(typingEl.dataset.radarInterval);
              if (radarInt) clearInterval(radarInt);
              typingEl.replaceWith(assistantEl);
            }
====
          if (eventType === 'chunk') {
            // First chunk: cancel orb timer & radar interval, swap indicator for bubble
            if (!firstChunkReceived) {
              firstChunkReceived = true;
              clearTimeout(orbTimer);
              clearActiveRadarTimer();
              typingEl.replaceWith(assistantEl);
              activeTypingEl = null;
            }
>>>>
```

#### Patch 10: `regenerateLastResponse()` Immediate Locking & Cleanup
**Location**: `index.html:2803–2845`
```javascript
<<<< BEFORE
  async function regenerateLastResponse(bubble) {
    if (isStreaming) {
      showToast('Please wait for current response to complete', 'info');
      return;
    }
    if (!conversationHistory.length || !conversationHistory.some(m => m.role === 'user')) {
      showToast('No prompt found to regenerate', 'info');
      return;
    }

    // Pop the assistant turn from conversation history if it's the last one
    if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'assistant') {
      conversationHistory.pop();
    }

    bubble.remove();

    const typingEl = renderTypingIndicator();
    scrollToBottom();
    setInputEnabled(false);
    isStreaming = true;

    try {
      const assistantEl = await streamAssistantResponse(typingEl);
      const fullText = assistantEl.dataset.rawText || '';
      if (fullText) {
        conversationHistory.push({ role: 'assistant', content: fullText });
      }
      loadSidebarHistory();
      showToast('Response regenerated!', 'success');
    } catch (err) {
      if (typingEl.isConnected) typingEl.remove();
      if (err.name !== 'AbortError' && !err.message?.includes('cancel')) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      isStreaming = false;
      activeReader = null;
      setInputEnabled(true);
      chatInput.focus();
      scrollToBottom();
    }
  }
====
  async function regenerateLastResponse(bubble) {
    // ── LINE 1: SYNCHRONOUS PROCEDURAL & RE-ENTRANCY LOCK ──────────────────
    if (isStreaming || isSubmitting) {
      showToast('Please wait for current response to complete', 'info');
      return;
    }
    if (!conversationHistory.length || !conversationHistory.some(m => m.role === 'user')) {
      showToast('No prompt found to regenerate', 'info');
      return;
    }

    // Immediately acquire locking state BEFORE any async ticks or DOM mutations
    isSubmitting = true;
    isStreaming = true;
    setInputEnabled(false);

    let typingEl = null;

    try {
      if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'assistant') {
        conversationHistory.pop();
      }

      bubble.remove();

      userScrolledUp = false;
      updateScrollBottomBtn(false);
      typingEl = renderTypingIndicator();
      scrollToBottom();

      const assistantEl = await streamAssistantResponse(typingEl);
      const fullText = assistantEl.dataset.rawText || '';
      if (fullText) {
        conversationHistory.push({ role: 'assistant', content: fullText });
      }
      loadSidebarHistory();
      showToast('Response regenerated!', 'success');
    } catch (err) {
      clearActiveRadarTimer();
      if (typingEl && typingEl.isConnected) {
        typingEl.remove();
      }
      if (!isCancellationError(err)) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      isSubmitting = false;
      isStreaming = false;
      activeReader = null;
      activeAbortController = null;
      activeTypingEl = null;
      clearActiveRadarTimer();
      setInputEnabled(true);
      updateSendButtonState();
      chatInput.focus({ preventScroll: true });
      scrollToBottom();
      fetchSubscriptionStatus();
    }
  }
>>>>
```

#### Patch 11: `executeUserMessageEdit()` Locking & Cleanup
**Location**: `index.html:2099–2241`
```javascript
<<<< BEFORE
  async function executeUserMessageEdit(userRow, newText) {
    if (!newText) {
      showToast('Message cannot be empty', 'info');
      return;
    }
    if (isStreaming) {
      showToast('Please wait for current response to complete before submitting', 'info');
      return;
    }
...
    userScrolledUp = false;
    updateScrollBottomBtn(false);
    const typingEl = renderTypingIndicator();
    scrollToBottom(true);
    setInputEnabled(false);
    isStreaming = true;
...
    } catch (err) {
      if (typingEl.isConnected) typingEl.remove();
      if (err.name !== 'AbortError' && !err.message?.includes('cancel')) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      isStreaming = false;
      activeReader = null;
      setInputEnabled(true);
      chatInput.focus({ preventScroll: true });
      scrollToBottom(false);
      fetchSubscriptionStatus();
    }
  }
====
  async function executeUserMessageEdit(userRow, newText) {
    if (!newText) {
      showToast('Message cannot be empty', 'info');
      return;
    }
    if (isStreaming || isSubmitting) {
      showToast('Please wait for current response to complete before submitting', 'info');
      return;
    }

    isSubmitting = true;
    isStreaming = true;
    setInputEnabled(false);

    let typingEl = null;
    try {
      // (Lines 2110-2205 DOM removal and message replacement remain unchanged)
      ...
      userScrolledUp = false;
      updateScrollBottomBtn(false);
      typingEl = renderTypingIndicator();
      scrollToBottom(true);

      const assistantEl = await streamAssistantResponse(typingEl);
      const fullText = assistantEl.dataset.rawText || '';
      if (fullText) {
        conversationHistory.push({ role: 'assistant', content: fullText });
      }
      if (currentConversationId) {
        convMessagesCache.set(currentConversationId, {
          id: currentConversationId,
          messages: [...conversationHistory],
          selectedModel: currentSelectedModel,
        });
      }
      loadSidebarHistory();
    } catch (err) {
      clearActiveRadarTimer();
      if (typingEl && typingEl.isConnected) {
        typingEl.remove();
      }
      if (!isCancellationError(err)) {
        renderErrorMessage(err.message || 'Something went wrong.');
      }
    } finally {
      isSubmitting = false;
      isStreaming = false;
      activeReader = null;
      activeAbortController = null;
      activeTypingEl = null;
      clearActiveRadarTimer();
      setInputEnabled(true);
      updateSendButtonState();
      chatInput.focus({ preventScroll: true });
      scrollToBottom(false);
      fetchSubscriptionStatus();
    }
  }
>>>>
```

---

## 5. Verification Method

### Automated Test Commands
Run the full suite of requirement and concurrency tests:
```powershell
cd c:\Users\sharo\Desktop\friday\backend
pytest test_e2e_requirements.py -k R3 -v
```

### Static Inspection Verification
1. Inspect `index.html` to confirm synchronous locking at line 1 of `sendMessage()`:
   - Check that `isStreaming = true;`, `isSubmitting = true;`, and `setInputEnabled(false);` occur immediately after the null/empty check.
2. Inspect `usePrompt()` and `startNewChat()` to verify the presence of `if (isStreaming || isSubmitting) return;`.
3. Inspect `setInputEnabled()` to confirm it queries and locks:
   - `#chat-input`
   - `#send-btn` / `#stop-btn`
   - `.prompt-card`
   - `button[onclick*="startNewChat"]`
   - `.regen-resp-btn`
4. Inspect `renderTypingIndicator()` to verify:
   - Timer initial display is `[EST. ~02:45] ELAPSED: 00:00`.
   - Dynamic update interval formats as `[EST. ~02:45] ELAPSED: MM:SS`.
   - Status sequence includes all 6 stages (`ANALYZING TARGET ARCHITECTURE & ATTACK SURFACE...`, etc.).
5. Inspect `stopStreaming()` to verify:
   - Calls `activeAbortController.abort()`.
   - Calls `activeReader.cancel()`.
   - Clears interval via `clearActiveRadarTimer()`.
   - Instantly removes `activeTypingEl`.

### Browser Manual Verification Script
Open DevTools Console on `index.html` and verify:
1. **Rapid Double-Enter**: Type a message, press `Enter` twice in under 50ms. Observe that only one assistant indicator is appended, `#chat-input` is disabled, and no duplicate SSE request appears in the Network tab.
2. **Prompt Pill Click During Stream**: Click a `.prompt-card` while the radar HUD is spinning. Verify that the toast "Please wait for current response to complete" appears and the current stream is unaffected.
3. **New Chat Click During Stream**: Click "New Chat" in the sidebar while the radar HUD is spinning. Verify that the toast appears, history is preserved, and the stream continues.
4. **Stop Button Click**: Click the red "Stop" button. Verify that the network request terminates immediately (Status `(canceled)` in Network tab), the radar indicator disappears instantly without throwing an error box, and the input re-enables.
5. **Timer Progression**: Allow stream to run for 25s. Confirm timer shows `[EST. ~02:45] ELAPSED: 00:25` and the label reads `EVALUATING VULNERABILITY VECTORS & SYSTEM CONSTRAINTS...`.
