# Orchestrator Soft Handoff (State Dump) — Generation 1

## Milestone State
- **Survey Phase**: Complete (3 Explorers mapped models, payments, UX, security, VPS).
- **TEST_READY.md**: Published at project root. 65 requirement test cases running under `pytest backend/test_e2e_requirements.py`.
- **Milestone 1 (Model Consolidation & Strict Rebranding)**: **DONE**
  - Only `orcasaq-cyber-27b:latest` allowlisted and active, branded "friday Cyber Pro".
  - Timeout elevated to 300.0s in `backend/config.py`, `backend/.env`, `backend/.env.example`.
  - Unified quick routes and 64-char lookahead sliding stream buffer in `backend/routes/chat.py`.
  - Frontend (`index.html`, `admin.html`) completely scrubbed with zero forbidden model/vendor leaks.
  - Gate: 115 unit tests passed, 12 R1 E2E tests passed, Forensic Auditor verdict CLEAN.
- **Milestone 2 (Payment Plan Consolidation & Subscription Preservation)**: **DONE**
  - `PLAN_CONFIG` updated to single tier: `cyber_pro_monthly` (₹3,500 = 350,000 paise) and `cyber_pro_yearly` (₹35,000 = 3,500,000 paise; 2 months free / 17% savings).
  - All legacy plans (`jr_hacker_*`, `advanced_*`, `founder_unlimited`, `free`) marked `purchasable: False`.
  - `GET /api/subscription/plans` returns strictly `['cyber_pro_monthly', 'cyber_pro_yearly']`.
  - `POST /api/create-order` and `POST /api/verify-payment` reject non-purchasable plans with HTTP 400 Bad Request.
  - Active customer subscriptions in database remain valid, active, and honored through their current expiration date with unlimited model access.
  - Frontend pricing cards and checkout review updated to single tier "friday Cyber Pro".
  - Gate: Iteration 2 passed with 49/49 adversarial tests, 16/16 unit tests, 14/14 R2 tests, 18/18 subscriber lifecycle tests, Forensic Auditor verdict CLEAN.
- **Milestone 3 (Chat UX Tactical Radar Progress State & Concurrency Guard)**: **IN_PROGRESS / READY TO DISPATCH**
  - Scope: F10, F11, F12, F13. Implement high-fidelity 360° sweeping radar animation with crimson HUD pulse (`#FF3038`), 6-stage rotating tactical telemetry updates ("ANALYZING TARGET ARCHITECTURE...", "SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD...", etc.), live elapsed/estimated timer (`01:24 / ~02:45`), and synchronous UI locking on `sendMessage`, `usePrompt`, and `startNewChat`.
- **Milestone 4 (Security Vulnerabilities, Webhook & Bug Remediation)**: **PLANNED**
  - Scope: F14 (CORS null removal), F15 (admin.html XSS patch), F16 (Razorpay webhook DB activation), F18 (backend regression tests).
- **Milestone 5 (Live VPS Deployment, Model Removal & Verification)**: **PLANNED**
  - Scope: SSH to 213.133.97.141 (`ssh_exec.py`). Run `ollama rm` on the 8B models, deploy backend code to `/opt/friday/backend`, update VPS `.env`, restart `friday.service`, verify remote health and public tunnel.
- **Milestone 6 (Final E2E Pass, Adversarial Hardening & Maintenance Notice Removal)**: **PLANNED**
  - Scope: 100% E2E test pass across all Tiers 1-4, adversarial coverage hardening (Tier 5), and clean removal of `#friday-maintenance-banner` per user directive F21.

## Active Subagents
- None. All subagents from Generation 1 have delivered their handoffs and completed.

## Pending Decisions & Blocked Items
- None. Milestone 1 and Milestone 2 are cleanly passed.
- Milestone 3 is ready for implementation by the successor orchestrator.

## Remaining Work for Successor
1. **Milestone 3 Execution**:
   - Dispatch `teamwork_worker` to implement tactical scanning radar/pulse animation, dynamic multi-stage ticker, elapsed timer, and immediate synchronous concurrency locking in `index.html`.
   - Dispatch Reviewers, Challengers, and Forensic Auditor for M3 gate.
2. **Milestone 4 Execution**:
   - Dispatch `teamwork_worker` to patch CORS (remove `"null"`), patch `admin.html:1392` XSS, and implement webhook DB activation in `backend/routes/subscription.py`.
   - Gating verification for M4.
3. **Milestone 5 Execution**:
   - Dispatch worker to execute `ollama rm` on `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest` on VPS `213.133.97.141`.
   - Deploy backend code and config to `/opt/friday/backend`.
   - Restart `friday.service` and verify live endpoints.
4. **Milestone 6 Execution**:
   - Run 100% of E2E test suite in `backend/test_e2e_requirements.py`.
   - Run Tier 5 adversarial testing.
   - Cleanly remove `#friday-maintenance-banner` in `index.html` and deploy live to `/opt/friday/index.html`.
   - Synthesize final human report to user.

## Key Artifacts
- Project index: `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Gate verdicts: `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\GATE_STATUS.md`
- Original user request: `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md`
- Dispatch instructions: `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\DISPATCH.md`
- E2E test certification: `c:\Users\sharo\Desktop\friday\TEST_READY.md`
- Parent conversation ID: `3e969642-703e-4493-ac3d-b712bc8c0d61`
