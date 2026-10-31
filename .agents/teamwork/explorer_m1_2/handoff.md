# Handoff Report: Milestone 1 — Frontend UI Badges & Branding Consolidation

## 1. Observation

Direct investigation of `index.html` and `admin.html` reveals several hardcoded legacy model names, dual-model dropdown logic, and direct brand leaks (`Dolphin`, `BaronLLM`, `Jr Hacker`, `Advanced Pentester`, `Model 1`, `Model 2`, `FRIDAY v1`).

### A. Findings in `index.html`

1. **Header Default Model Label** (`index.html:430`):
   ```html
   430: <span class="font-mono text-[11px] sm:text-xs truncate font-medium" id="selected-model-label">Friday v1 The Jr Hacker</span>
   ```
   Directly renders `Friday v1 The Jr Hacker` on initial page load before JS updates.

2. **Brand Header in Sidebar** (`index.html:339–342`):
   ```html
   339: <span class="font-heading font-bold text-sm tracking-wide text-[#F5F5F5] flex items-center gap-1.5 truncate">
   340:               FRIDAY v1
   341:               <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-pulse shrink-0"></span>
   342: </span>
   ```
   Renders `FRIDAY v1` as the brand name.

3. **Dropdown Popover Sub-Badge** (`index.html:437–438`):
   ```html
   437: <span class="text-[10px] font-mono uppercase tracking-wider text-[#71717A]">Neural Engine Selection</span>
   438: <span class="text-[9px] font-mono text-[#FF3038] bg-[#FF3038]/10 px-1.5 py-0.5 rounded border border-[#FF3038]/20">FRIDAY Neural Core</span>
   ```
   Has multi-model selection text rather than consolidated active engine status.

4. **In-Browser Models Registry** (`index.html:1378–1393`):
   ```javascript
   1378:   const DEFAULT_MODELS_REGISTRY = [
   1379:     {
   1380:       id: "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
   1381:       name: "Friday v1 The Jr Hacker",
   1382:       description: "AI Junior Pentester & Security Mentor",
   1383:       tag: "Jr Hacker (Default)",
   1384:       is_default: true,
   1385:     },
   1386:     {
   1387:       id: "huihui_ai/baronllm-abliterated:latest",
   1388:       name: "Friday v1 The Advanced Pentester",
   1389:       description: "Advanced Cyber Security & Penetration Testing Engine",
   1390:       tag: "Advanced Pentester",
   1391:       is_default: false,
   1392:     },
   1393:   ];
   ```
   Explicitly registers both legacy models with HuggingFace and huihui_ai vendor paths and old tags.

5. **LocalStorage Fallback & Cache Pollution** (`index.html:1396–1401`):
   ```javascript
   1396:   let savedSelectedModel = localStorage.getItem('friday_selected_model');
   1397:   if (savedSelectedModel && (savedSelectedModel.includes('Huihui-Qwen3-Coder') || savedSelectedModel.includes('mradermacher'))) {
   1398:     savedSelectedModel = DEFAULT_MODELS_REGISTRY[0].id;
   1399:     localStorage.setItem('friday_selected_model', savedSelectedModel);
   1400:   }
   1401:   let currentSelectedModel = savedSelectedModel || DEFAULT_MODELS_REGISTRY[0].id;
   ```
   Returning users with `localStorage['friday_selected_model']` containing Dolphin or BaronLLM will bypass the default and send legacy IDs to the backend unless invalidated.

6. **Model Selection & Obsolete Model 2 Access Gate** (`index.html:1472–1479`):
   ```javascript
   1472:     const isModel2 = modelId.includes('baronllm');
   1473:     const tier = subscriptionStatus?.model_tier || 'free';
   1474:     if (isModel2 && tier === 'model1') {
   1475:       closeModelDropdown();
   1476:       showPricingModal();
   1477:       showToast('The Advanced Pentester requires an Advanced Pentester subscription.', 'warning');
   1478:       return;
   1479:     }
   ```
   References `baronllm` and `The Advanced Pentester`.

7. **Typing Indicator and Assistant Chat Bubbles** (`index.html:2148` & `index.html:2322, 2331`):
   ```html
   2148: <span class="font-heading font-semibold text-xs text-[#F5F5F5]">FRIDAY v1</span>
   ...
   2322: <span class="font-heading font-semibold text-xs text-[#F5F5F5]">FRIDAY v1</span>
   ...
   2331: <span class="text-[10px] font-mono text-[#52525B] hidden xs:inline">FRIDAY AI</span>
   ```
   Directly renders `FRIDAY v1` above incoming assistant replies and stream chunks.

8. **Plan Labels & Dropdown Lock Badges** (`index.html:3083–3088`, `3116–3130`, `3142–3175`):
   ```javascript
   3083:   const PLAN_LABELS = {
   3084:     jr_hacker_monthly:  { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
   3085:     jr_hacker_yearly:   { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
   3086:     advanced_monthly:   { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
   3087:     advanced_yearly:    { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
   3088:   };
   ...
   3116:     badge.classList.add('sub-badge-model1');
   3117:     label.textContent = '⚡ Jr Hacker';
   ...
   3129:     badge.classList.add('sub-badge-model2');
   3130:     label.textContent  = '🔥 Advanced Pentester';
   ...
   3152:     const isModel2 = model.id.includes('baronllm');
   3154:     // Model 2 is only locked if the user is on the Model 1 tier (Jr Hacker).
   3155:     const locked = isModel2 && (tier === 'model1');
   ```

---

### B. Findings in `admin.html`

1. **KPI Metric Card Subtitle** (`admin.html:1039`):
   ```html
   1039: <div class="metric-sub" id="kpi-paid-sub">Model 1 & Model 2 paid</div>
   ```

2. **Grant Plan Modal Dropdown Options** (`admin.html:1139–1146`):
   ```html
   1139: <select id="grant-plan" class="form-select" onchange="handlePlanSelectChange()">
   1140:   <option value="advanced_monthly">🔥 The Advanced Pentester — Monthly (Model 2 Unlimited)</option>
   1141:   <option value="advanced_yearly">🔥 The Advanced Pentester — Yearly (Model 2 Unlimited)</option>
   1142:   <option value="jr_hacker_monthly">⚡ The Jr Hacker — Monthly (Model 1, 50/day)</option>
   1143:   <option value="jr_hacker_yearly">⚡ The Jr Hacker — Yearly (Model 1, 50/day)</option>
   1144:   <option value="founder_unlimited">👑 Founder / Admin (Lifetime VIP — All Models Unlimited)</option>
   1145:   <option value="free">🛡️ Revert to Free Plan (5 chats/day limit)</option>
   1146: </select>
   ```
   Severe leak of internal model numbering ("Model 1", "Model 2") and old plan names.

3. **User Table Model Tier Rendering** (`admin.html:1424–1434`):
   ```javascript
   1424:         // 3. Model Tier
   1425:         let tierLabel = 'Dual Model (5 chats/day)';
   1426:         let tierIcon = '🛡️';
   1427:         if (u.model_tier === 'model2') {
   1428:           tierLabel = 'Model 2 (BaronLLM Abliterated)';
   1429:           tierIcon = '🔥';
   1430:         } else if (u.model_tier === 'model1') {
   1431:           tierLabel = 'Model 1 (Jr Hacker Dolphin)';
   1432:           tierIcon = '⚡';
   1433:         }
   ```
   Directly leaks verbatim model identifiers: `'Model 2 (BaronLLM Abliterated)'` and `'Model 1 (Jr Hacker Dolphin)'`.

4. **Admin Modal Form Defaults** (`admin.html:1564, 1572`):
   ```javascript
   1564: document.getElementById('grant-plan').value = 'advanced_monthly';
   ...
   1572: document.getElementById('grant-plan').value = 'advanced_monthly';
   ```

---

## 2. Logic Chain

1. **Consolidation Premise**: The user requirement (R1) specifies that only `orcasaq-cyber-27b:latest` is retained on Ollama, branded strictly as "friday Cyber Pro", with zero exposure of underlying vendor/model identifiers.
2. **Frontend Model Registry**: In `index.html:1378–1393`, replacing `DEFAULT_MODELS_REGISTRY` with a single item pointing to `orcasaq-cyber-27b:latest` (branded "friday Cyber Pro", tag "Cyber Pro") ensures that offline/initial state presents the single consolidated model.
3. **Cache Invalidation**: Because `localStorage.getItem('friday_selected_model')` retains user choices across sessions, existing users would continue requesting `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` or `huihui_ai/baronllm-abliterated:latest`. Upgrading the validation condition at lines 1396–1401 ensures any cached value not present in the new registry is immediately overwritten with `orcasaq-cyber-27b:latest`.
4. **Dropdown Simplification**: With a single model, dropdown locking logic (`updateModelDropdownLocks` at line 3142 and `isModel2` check in `selectModel` at line 1472) is obsolete. Retaining the single active engine view with a "Cyber Pro" badge and checkmark provides a clean, polished UI without misleading "upgrade to unlock Model 2" prompts.
5. **Chat Interface Consistency**: Replacing `FRIDAY v1` in the brand header (line 340), `#selected-model-label` (line 430), typing indicator (line 2148), and assistant bubble header (line 2322) ensures absolute brand uniformity across every chat turn.
6. **Admin Interface Sanitization**:
   - In `admin.html:1425–1434`, updating `tierLabel` to render `friday Cyber Pro` for all tiers (with sub-labels `Unlimited`, `50 chats/day` for grandfathered users, or `Free, 5/day`) completely eliminates the leaks of `BaronLLM` and `Dolphin` while preserving telemetry accuracy.
   - In `admin.html:1139–1146`, updating the `<select id="grant-plan">` options to `cyber_pro_monthly`, `cyber_pro_yearly`, and `founder_unlimited` aligns administrative plan overrides with the new product catalog.

---

## 3. Implementation Plan (Exact Line-by-Line Changes)

### Target File 1: `index.html`

#### Edit 1: Brand Header (`index.html:339–342`)
- **Before**:
  ```html
  <span class="font-heading font-bold text-sm tracking-wide text-[#F5F5F5] flex items-center gap-1.5 truncate">
                FRIDAY v1
                <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-pulse shrink-0"></span>
  </span>
  ```
- **After**:
  ```html
  <span class="font-heading font-bold text-sm tracking-wide text-[#F5F5F5] flex items-center gap-1.5 truncate">
                friday Cyber Pro
                <span class="w-1.5 h-1.5 rounded-full bg-[#FF3038] animate-pulse shrink-0"></span>
  </span>
  ```

#### Edit 2: Top Bar Dropdown Trigger & Popover (`index.html:430, 437–438`)
- **Before**:
  ```html
  <span class="font-mono text-[11px] sm:text-xs truncate font-medium" id="selected-model-label">Friday v1 The Jr Hacker</span>
  ...
  <span class="text-[10px] font-mono uppercase tracking-wider text-[#71717A]">Neural Engine Selection</span>
  <span class="text-[9px] font-mono text-[#FF3038] bg-[#FF3038]/10 px-1.5 py-0.5 rounded border border-[#FF3038]/20">FRIDAY Neural Core</span>
  ```
- **After**:
  ```html
  <span class="font-mono text-[11px] sm:text-xs truncate font-medium" id="selected-model-label">friday Cyber Pro</span>
  ...
  <span class="text-[10px] font-mono uppercase tracking-wider text-[#71717A]">Active Neural Engine</span>
  <span class="text-[9px] font-mono text-[#FF3038] bg-[#FF3038]/10 px-1.5 py-0.5 rounded border border-[#FF3038]/20">friday Cyber Pro</span>
  ```

#### Edit 3: Model Registry & LocalStorage Invalidation (`index.html:1378–1401`)
- **Before**:
  ```javascript
  const DEFAULT_MODELS_REGISTRY = [
    {
      id: "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
      name: "Friday v1 The Jr Hacker",
      description: "AI Junior Pentester & Security Mentor",
      tag: "Jr Hacker (Default)",
      is_default: true,
    },
    {
      id: "huihui_ai/baronllm-abliterated:latest",
      name: "Friday v1 The Advanced Pentester",
      description: "Advanced Cyber Security & Penetration Testing Engine",
      tag: "Advanced Pentester",
      is_default: false,
    },
  ];

  let availableModels = [...DEFAULT_MODELS_REGISTRY];
  let savedSelectedModel = localStorage.getItem('friday_selected_model');
  if (savedSelectedModel && (savedSelectedModel.includes('Huihui-Qwen3-Coder') || savedSelectedModel.includes('mradermacher'))) {
    savedSelectedModel = DEFAULT_MODELS_REGISTRY[0].id;
    localStorage.setItem('friday_selected_model', savedSelectedModel);
  }
  let currentSelectedModel = savedSelectedModel || DEFAULT_MODELS_REGISTRY[0].id;
  ```
- **After**:
  ```javascript
  const DEFAULT_MODELS_REGISTRY = [
    {
      id: "orcasaq-cyber-27b:latest",
      name: "friday Cyber Pro",
      description: "Elite Cyber Security & Offensive Operations Engine",
      tag: "Cyber Pro",
      is_default: true,
    },
  ];

  let availableModels = [...DEFAULT_MODELS_REGISTRY];
  let savedSelectedModel = localStorage.getItem('friday_selected_model');
  if (!savedSelectedModel || !DEFAULT_MODELS_REGISTRY.some(m => m.id === savedSelectedModel)) {
    savedSelectedModel = DEFAULT_MODELS_REGISTRY[0].id;
    localStorage.setItem('friday_selected_model', savedSelectedModel);
  }
  let currentSelectedModel = savedSelectedModel;
  ```

#### Edit 4: `selectModel()` & Dropdown Lock Purge (`index.html:1468–1480`)
- **Before**:
  ```javascript
  function selectModel(modelId, notify = true) {
    const found = availableModels.find(m => m.id === modelId);
    if (!found) return;

    const isModel2 = modelId.includes('baronllm');
    const tier = subscriptionStatus?.model_tier || 'free';
    if (isModel2 && tier === 'model1') {
      closeModelDropdown();
      showPricingModal();
      showToast('The Advanced Pentester requires an Advanced Pentester subscription.', 'warning');
      return;
    }
  ```
- **After**:
  ```javascript
  function selectModel(modelId, notify = true) {
    const found = availableModels.find(m => m.id === modelId);
    if (!found) return;
  ```

#### Edit 5: Typing Indicator Bubble (`index.html:2147–2151`)
- **Before**:
  ```html
  <div class="flex items-center gap-1.5 sm:gap-2 mb-1.5 flex-wrap">
    <span class="font-heading font-semibold text-xs text-[#F5F5F5]">FRIDAY v1</span>
    <span class="text-[9px] font-mono bg-[#FF3038]/20 text-[#FF3038] px-1.5 py-0.5 rounded font-bold">AI</span>
    <span class="text-[10px] font-mono text-[#71717A]">Processing…</span>
  </div>
  ```
- **After**:
  ```html
  <div class="flex items-center gap-1.5 sm:gap-2 mb-1.5 flex-wrap">
    <span class="font-heading font-semibold text-xs text-[#F5F5F5]">friday Cyber Pro</span>
    <span class="text-[9px] font-mono bg-[#FF3038]/20 text-[#FF3038] px-1.5 py-0.5 rounded font-bold">AI</span>
    <span class="text-[10px] font-mono text-[#71717A]">Processing…</span>
  </div>
  ```

#### Edit 6: Assistant Message Bubble (`index.html:2321–2332`)
- **Before**:
  ```html
  <div class="flex items-center gap-1.5 sm:gap-2 mb-1.5 flex-wrap">
    <span class="font-heading font-semibold text-xs text-[#F5F5F5]">FRIDAY v1</span>
    <span class="text-[9px] font-mono bg-[#FF3038]/20 text-[#FF3038] px-1.5 py-0.5 rounded font-bold">AI</span>
    <span class="text-[10px] font-mono text-[#71717A]">${time}</span>
  </div>
  ...
  <span class="text-[10px] font-mono text-[#52525B] hidden xs:inline">FRIDAY AI</span>
  ```
- **After**:
  ```html
  <div class="flex items-center gap-1.5 sm:gap-2 mb-1.5 flex-wrap">
    <span class="font-heading font-semibold text-xs text-[#F5F5F5]">friday Cyber Pro</span>
    <span class="text-[9px] font-mono bg-[#FF3038]/20 text-[#FF3038] px-1.5 py-0.5 rounded font-bold">AI</span>
    <span class="text-[10px] font-mono text-[#71717A]">${time}</span>
  </div>
  ...
  <span class="text-[10px] font-mono text-[#52525B] hidden xs:inline">friday Cyber Pro</span>
  ```

#### Edit 7: Plan Labels & Sub Badges (`index.html:3083–3088`, `3116–3130`)
- **Before**:
  ```javascript
  const PLAN_LABELS = {
    jr_hacker_monthly:  { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
    jr_hacker_yearly:   { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
    advanced_monthly:   { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
    advanced_yearly:    { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
  };
  ```
- **After**:
  ```javascript
  const PLAN_LABELS = {
    cyber_pro_monthly:  { name: 'friday Cyber Pro',   tier: 1, badge: 'cyber_pro' },
    cyber_pro_yearly:   { name: 'friday Cyber Pro',   tier: 1, badge: 'cyber_pro' },
    jr_hacker_monthly:  { name: 'friday Cyber Pro',   tier: 1, badge: 'model1' },
    jr_hacker_yearly:   { name: 'friday Cyber Pro',   tier: 1, badge: 'model1' },
    advanced_monthly:   { name: 'friday Cyber Pro',   tier: 2, badge: 'model2' },
    advanced_yearly:    { name: 'friday Cyber Pro',   tier: 2, badge: 'model2' },
  };
  ```
- **And in `updateSubBadge(status)`**:
  - `label.textContent = '⚡ Jr Hacker';` -> `label.textContent = '⚡ friday Cyber Pro';`
  - `label.textContent = '🔥 Advanced Pentester';` -> `label.textContent = '🔥 friday Cyber Pro';`
- **And in `updateModelDropdownLocks(status)` (`index.html:3142–3175`)**:
  - Convert to no-op or remove `baronllm` gating so that the single model is never rendered with a lock icon.

---

### Target File 2: `admin.html`

#### Edit 1: KPI Subtitle (`admin.html:1039`)
- **Before**:
  ```html
  <div class="metric-sub" id="kpi-paid-sub">Model 1 & Model 2 paid</div>
  ```
- **After**:
  ```html
  <div class="metric-sub" id="kpi-paid-sub">Active Cyber Pro plans</div>
  ```

#### Edit 2: Grant Plan Modal Dropdown (`admin.html:1139–1146`)
- **Before**:
  ```html
  <select id="grant-plan" class="form-select" onchange="handlePlanSelectChange()">
    <option value="advanced_monthly">🔥 The Advanced Pentester — Monthly (Model 2 Unlimited)</option>
    <option value="advanced_yearly">🔥 The Advanced Pentester — Yearly (Model 2 Unlimited)</option>
    <option value="jr_hacker_monthly">⚡ The Jr Hacker — Monthly (Model 1, 50/day)</option>
    <option value="jr_hacker_yearly">⚡ The Jr Hacker — Yearly (Model 1, 50/day)</option>
    <option value="founder_unlimited">👑 Founder / Admin (Lifetime VIP — All Models Unlimited)</option>
    <option value="free">🛡️ Revert to Free Plan (5 chats/day limit)</option>
  </select>
  ```
- **After**:
  ```html
  <select id="grant-plan" class="form-select" onchange="handlePlanSelectChange()">
    <option value="cyber_pro_monthly">🔥 friday Cyber Pro — Monthly (Unlimited)</option>
    <option value="cyber_pro_yearly">🔥 friday Cyber Pro — Yearly (Unlimited)</option>
    <option value="founder_unlimited">👑 Founder / Admin (Lifetime VIP — Unlimited)</option>
    <option value="free">🛡️ Revert to Free Plan (5 chats/day limit)</option>
  </select>
  ```

#### Edit 3: User Table Plan & Model Tier Rendering (`admin.html:1408–1434`)
- **Before**:
  ```javascript
        } else if (u.model_tier === 'model2' || (u.plan_id && u.plan_id.includes('advanced'))) {
          planBadgeClass = 'plan-adv';
          planEmoji = '🔥';
        } else if (u.model_tier === 'model1' || (u.plan_id && u.plan_id.includes('jr_hacker'))) {
          planBadgeClass = 'plan-jr';
          planEmoji = '⚡';
        }

        const planCell = `
          <td>
            <span class="plan-badge ${planBadgeClass}">
              ${planEmoji} ${escapeHtml(u.plan_label || 'Free Plan')}
            </span>
          </td>
        `;

        // 3. Model Tier
        let tierLabel = 'Dual Model (5 chats/day)';
        let tierIcon = '🛡️';
        if (u.model_tier === 'model2') {
          tierLabel = 'Model 2 (BaronLLM Abliterated)';
          tierIcon = '🔥';
        } else if (u.model_tier === 'model1') {
          tierLabel = 'Model 1 (Jr Hacker Dolphin)';
          tierIcon = '⚡';
        }
  ```
- **After**:
  ```javascript
        } else if (u.model_tier === 'cyber_pro' || (u.plan_id && u.plan_id.includes('cyber_pro')) || u.model_tier === 'model2' || (u.plan_id && u.plan_id.includes('advanced'))) {
          planBadgeClass = 'plan-adv';
          planEmoji = '🔥';
        } else if (u.model_tier === 'model1' || (u.plan_id && u.plan_id.includes('jr_hacker'))) {
          planBadgeClass = 'plan-jr';
          planEmoji = '⚡';
        }

        const planCell = `
          <td>
            <span class="plan-badge ${planBadgeClass}">
              ${planEmoji} ${escapeHtml(u.plan_label || 'Free Plan')}
            </span>
          </td>
        `;

        // 3. Model Tier
        let tierLabel = 'friday Cyber Pro (Free, 5/day)';
        let tierIcon = '🛡️';
        if (u.is_founder || u.model_tier === 'cyber_pro' || u.model_tier === 'model2' || (u.plan_id && (u.plan_id.includes('advanced') || u.plan_id.includes('cyber_pro')))) {
          tierLabel = 'friday Cyber Pro (Unlimited)';
          tierIcon = '🔥';
        } else if (u.model_tier === 'model1' || (u.plan_id && u.plan_id.includes('jr_hacker'))) {
          tierLabel = 'friday Cyber Pro (50 chats/day)';
          tierIcon = '⚡';
        }
  ```

#### Edit 4: Admin Form JS Default Value (`admin.html:1564, 1572`)
- **Before**:
  ```javascript
  document.getElementById('grant-plan').value = 'advanced_monthly';
  ```
- **After**:
  ```javascript
  document.getElementById('grant-plan').value = 'cyber_pro_monthly';
  ```

---

## 4. Caveats

1. **Backend Dependency**: The frontend `loadAvailableModels()` calls `GET /api/models`. When the implementer updates backend `AVAILABLE_MODELS` (handled by Milestone 1 Backend tasks), the endpoint will return `{"models": [{"id": "orcasaq-cyber-27b:latest", "name": "friday Cyber Pro", "tag": "Cyber Pro", "is_default": true}], "default": "orcasaq-cyber-27b:latest"}`. The frontend changes specified above are designed so that the UI is 100% branded and consolidated even if `loadAvailableModels()` fails or runs offline using `DEFAULT_MODELS_REGISTRY`.
2. **Pricing Grid (Milestone 2)**: The pricing modal (`index.html:614–621`, `3239–3259`) contains tabs and pricing cards for ₹2,499 and ₹4,999. Milestone 2 will consolidate these into the single ₹3,500/mo tier. The changes in this report focus strictly on model badges, model dropdowns, greetings, chat bubbles, and brand leak elimination for Milestone 1.

---

## 5. Conclusion

The line-by-line strategy above comprehensively eliminates all brand leaks (`Dolphin`, `BaronLLM`, `Jr Hacker`, `Advanced Pentester`, `Model 1`, `Model 2`, `FRIDAY v1`) across `index.html` and `admin.html`. It consolidates the client-side model registry to `orcasaq-cyber-27b:latest` branded as "friday Cyber Pro", migrates stale user local storage, cleans up the model selection dropdown to display a single active badge ("friday Cyber Pro", "Cyber Pro"), and preserves backward-compatible badge rendering for active grandfathered accounts in the admin console without revealing legacy model names.

---

## 6. Verification Method

To verify after implementation:

1. **Source Inspection & Regex Scan**:
   Run grep across `index.html` and `admin.html` to confirm zero occurrences of forbidden strings:
   ```powershell
   Select-String -Path "index.html", "admin.html" -Pattern "Dolphin", "baronllm", "RavichandranJ", "huihui_ai", "Jr Hacker", "Advanced Pentester", "Model 1", "Model 2", "FRIDAY v1"
   ```
   **Expected**: 0 matches (except possible Razorpay script CDN URL `/v1/checkout.js`).

2. **Automated Models Tests**:
   Run the pytest suite to verify model endpoints and allowlist compliance:
   ```powershell
   pytest backend/test_models.py -v
   ```

3. **Browser Inspection**:
   - Inspect `#selected-model-label` in DOM -> contains exact text `"friday Cyber Pro"`.
   - Clear `localStorage` and reload -> `localStorage['friday_selected_model']` is initialized to `"orcasaq-cyber-27b:latest"`.
   - Inspect typing indicator and assistant chat bubble headers -> render `"friday Cyber Pro"`.
   - Open `/admin` -> user table Model Tier column renders `"friday Cyber Pro (Unlimited)"` or `"friday Cyber Pro (50 chats/day)"` or `"friday Cyber Pro (Free, 5/day)"`.
