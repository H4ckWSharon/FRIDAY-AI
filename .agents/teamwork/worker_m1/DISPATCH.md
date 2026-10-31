## Task Assignment: Worker M1 — Model Consolidation & Strict Rebranding Implementation

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m1\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Backend explorer report: `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_1\handoff.md`
- Frontend explorer report: `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\handoff.md`
- Spec miner report: `c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\handoff.md`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may modify:
- `backend/config.py`
- `backend/.env`
- `backend/.env.example`
- `backend/routes/chat.py`
- `backend/routes/health.py`
- `backend/test_models.py`
- `backend/test_backend.py`
- `backend/test_integration.py`
- `index.html`
- `admin.html`

### Required Actions
1. **Backend Consolidation**:
   - In `backend/config.py`: Update `AVAILABLE_MODELS` to single entry `orcasaq-cyber-27b:latest` ("friday Cyber Pro", tag "Cyber Pro"), set `ollama_model = "orcasaq-cyber-27b:latest"`, and `ollama_timeout = 300.0`.
   - In `backend/.env` and `backend/.env.example`: Set `OLLAMA_MODEL=orcasaq-cyber-27b:latest` and `OLLAMA_TIMEOUT=300`.
   - In `backend/routes/chat.py`:
     - Unify quick routes into single `_QUICK_ROUTES` with "friday Cyber Pro" persona; remove all Jr Hacker / Advanced Pentester text.
     - Add `LEGACY_MODEL_MAPPING` to map legacy IDs to `orcasaq-cyber-27b:latest`.
     - Expand `_MODEL_NAME_REPLACEMENTS` regex table to catch `orcasaq-cyber-27b`, `orcasaq`, `OrcaSAQ`, `Dolphin`, `BaronLLM`, `Cognitive Computations`, `Eric Hartford`, `huihui_ai`, `RavichandranJ`, `Ollama`, replacing with "friday Cyber Pro".
     - Update `display_model` assignments to "friday Cyber Pro".
     - Update error strings to eliminate old model names.
   - In `backend/routes/health.py`: Set `model="friday Cyber Pro"`.
2. **Frontend UI Badges & Brand Consolidation**:
   - In `index.html`:
     - Update brand title / sidebar to "friday Cyber Pro".
     - Update `#selected-model-label` to "friday Cyber Pro".
     - Update `DEFAULT_MODELS_REGISTRY` to only `orcasaq-cyber-27b:latest` ("friday Cyber Pro", tag "Cyber Pro").
     - Invalidate legacy `localStorage['friday_selected_model']`.
     - Update typing indicator bubble and assistant message headers to "friday Cyber Pro".
     - Update `PLAN_LABELS` and sub-badges.
     - Remove lock icons and dual-model gating from model dropdown.
   - In `admin.html`:
     - Update KPI subtitle to "Active Cyber Pro plans".
     - Update `#grant-plan` `<select>` options to `cyber_pro_monthly`, `cyber_pro_yearly`, `founder_unlimited`, `free`.
     - Update user table model tier badges to render "friday Cyber Pro (Unlimited / 50 chats/day / Free)".
3. **Tests & Verification**:
   - Update `backend/test_models.py`, `backend/test_backend.py`, and `backend/test_integration.py` to match the single-model allowlist, zero-leakage sanitization, and quick routes.
   - Run the pytest suite:
     `pytest backend/test_models.py backend/test_backend.py backend/test_auth.py backend/test_production_hardening.py -v`
   - Ensure 100% test passes.

### Deliverables
- Write `c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m1\handoff.md` with:
  - Observation (what files were modified and verified)
  - Verification Commands & Test Results
  - Zero-leakage verification output
- Send completion message to orchestrator.

## 2026-10-29T20:53:22Z
[Message] sender=577be955-4ab1-40ee-81ad-fce0ceb6ffa6
**Context**: Milestone 1 implementation status check
**Content**: Checking on your progress across backend, frontend, and test suite updates.
**Action**: Please reply with your current step and estimated completion time.

## 2026-10-29T21:04:56Z
[Message] sender=577be955-4ab1-40ee-81ad-fce0ceb6ffa6
**Context**: Milestone 1 Implementation Completion Check
**Content**: 10 minutes have elapsed since your last update. Are the test updates and verification finished?
**Action**: Please reply with your status and estimated delivery time for handoff.md.
