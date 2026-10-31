# Project: FRIDAY Model Consolidation, Rebranding, Pricing & Hardening

## Architecture
- **AI Engine & Inference**:
  - Live VPS Ollama host (`http://127.0.0.1:11434`) serving exclusively `orcasaq-cyber-27b:latest` (27.3B Q4, 15 GB).
  - Legacy models `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest` deleted via `ollama rm`.
  - Backend integration: FastAPI async `httpx.AsyncClient` streaming via Server-Sent Events (`POST /api/chat`, `GET /api/models`).
  - Timeout increased to 300.0s to support 2.5–3 min CPU inferences.
  - Concurrency governor: `asyncio.Semaphore(4)`, bounded queue (40), per-user serialization.
- **Strict Brand Identity**:
  - Display name: "friday Cyber Pro" across frontend, backend, error messages, and greetings.
  - Regex response sanitization layer catches all raw model identifiers (`orcasaq`, `Dolphin`, `BaronLLM`, `Cognitive Computations`, `Ollama`).
- **Billing & Subscriptions**:
  - Razorpay Standard Web Checkout (`checkout.js` + Python `razorpay`).
  - Public purchase catalog: Single tier at ₹3,500/mo (`cyber_pro_monthly`, 350,000 paise) and ₹35,000/yr (`cyber_pro_yearly`, 3,500,000 paise; 10 months = 2 months free / 17% savings).
  - Grandfathering: Legacy plans (`advanced_monthly`, `advanced_yearly`, `jr_hacker_monthly`, `jr_hacker_yearly`) marked `purchasable: False`. Existing active subscriptions retain access through their expiration date (e.g. Nov 2026).
- **Tactical Chat UX**:
  - High-fidelity SVG/CSS 360° sweeping radar animation with crimson neon pulse (`#FF3038`).
  - 6-stage rotating tactical telemetry updates ("ANALYZING TARGET ARCHITECTURE...", "SYNTHESIZING ADVERSARIAL EXPLOIT PAYLOAD...", etc.).
  - Elapsed and estimated duration timer (`[EST. ~02:45] ELAPSED: MM:SS`).
  - Immediate synchronous UI locking on `sendMessage`, `usePrompt`, and `startNewChat` to eliminate race conditions and duplicate inference requests.
- **Security & Hardening**:
  - CORS: remove `"null"` origin.
  - Admin portal: escape `u.id` in `admin.html:1392` against XSS.
  - Webhook: implement subscription activation on `order.paid` / `payment.captured`.
  - VPS service hardening and verification.

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone:
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Ollama Model Cleanup on VPS | Remove Dolphin3-Cyber-8B and baronllm-abliterated from Ollama | M5 | Survey 1, Survey 3, R1 |
| F2 | Single Model Selection & Warmup | Retain and pin only orcasaq-cyber-27b:latest with keep_alive: -1 | M1, M5 | Survey 1, R1 |
| F3 | Strict "friday Cyber Pro" Branding | Eliminate all references to Dolphin, BaronLLM, Jr Hacker, Advanced Pentester | M1 | Survey 1, R1 |
| F4 | Response Output Sanitization | Expand regex replacements to catch orcasaq and replace with friday Cyber Pro | M1 | Survey 1, R1 |
| F5 | Inference Timeout Elevation | Increase ollama_timeout to 300.0s in config.py and .env files | M1, M5 | Survey 1, Survey 3 |
| F6 | Single Pricing Tier (₹3,500/mo) | Offer new single tier at ₹3,500/mo in backend and frontend | M2 | Survey 2, R2 |
| F7 | Yearly Discount Calculation | Calculate yearly tier at ₹35,000/yr (10 months = 2 months free / 17% discount) | M2 | Survey 2, R2 |
| F8 | Grandfathering Active Subscriptions | Preserve active customer subscriptions in DB without interruption through expiration | M2 | Survey 2, R2 |
| F9 | Retiring Legacy Purchase Plans | Mark older plans purchasable: False; reject new orders for legacy tiers | M2 | Survey 2, R2 |
| F10 | Tactical Radar Sweep HUD Animation | Add 360° sweeping radar beam, concentric grids, and crimson pulse in chat | M3 | Survey 3, R3 |
| F11 | Dynamic Multi-Stage Status Updates | Display rotating tactical stage indicators during long inference | M3 | Survey 3, R3 |
| F12 | Live Elapsed / Estimated Timer | Display active timer (e.g. 01:15 / ~02:45) in typing state | M3 | Survey 3, R3 |
| F13 | Concurrency & Retry Spam Guard | Synchronously lock input, usePrompt, startNewChat, and regen buttons during streaming | M3 | Survey 3, R3 |
| F14 | CORS Hardening | Remove "null" origin from cors_origins in config.py | M4 | Survey 3, R4 |
| F15 | Admin Console XSS Patch | Properly sanitize and escape u.id in admin.html | M4 | Survey 3, R4 |
| F16 | Razorpay Webhook DB Activation | Implement database subscription activation on webhook events | M4 | Survey 3, R4 |
| F17 | Admin Portal Branding & Tier Support | Update admin.html to display friday Cyber Pro and grant cyber_pro plans | M2, M4 | Survey 1, Survey 2 |
| F18 | Automated Test Suite Modernization | Update pytest suite (models, subscription, backend) for single-tier & branding | M1, M2, M4 | Survey 1, Survey 2 |
| F19 | Live VPS Service Deployment | Deploy updated code to /opt/friday/backend on 213.133.97.141 and restart friday.service | M5 | Survey 1, Survey 3, R4 |
| F20 | Live VPS Verification & Validation | Verify remote health, active model, and public tunnel endpoints | M5 | Survey 1, Survey 3, R4 |
| F21 | Maintenance Notice Banner Lifecycle | Maintain maintenance banner during upgrades; cleanly remove in M6 after 100% verification | M6 | User Directive 2026-10-29 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Model Consolidation & Strict Rebranding | F2, F3, F4, F5, F18 (models test) | none | DONE |
| M2 | Payment Plan Consolidation & Subscription Preservation | F6, F7, F8, F9, F17, F18 (subs test) | none | DONE |
| M3 | Chat UX Tactical Radar Progress State & Concurrency Guard | F10, F11, F12, F13 | none | IN_PROGRESS |
| M4 | Security Vulnerabilities, Webhook & Bug Remediation | F14, F15, F16, F18 (backend regression) | M1, M2 | PLANNED |
| M5 | Live VPS Model Cleanup, Deployment & Verification | F1, F19, F20 | M1, M2, M3, M4 | PLANNED |
| M6 | Final E2E Test Suite Pass (Tiers 1-4), Adversarial Hardening (Tier 5) & Maintenance Removal | All features (F1-F21), E2E pass, remove #friday-maintenance-banner | M5 | PLANNED |

## Interface Contracts
### Frontend ↔ Backend Chat Interface
- Endpoint: `POST /api/chat` (streaming SSE)
- Headers: `Authorization: Bearer <token>`, `Content-Type: application/json`
- Request Payload: `{"model": "orcasaq-cyber-27b:latest", "messages": [{"role": "user", "content": "..."}], "stream": true}`
- Model default fallback: If `model` omitted or legacy id passed, server maps cleanly to `orcasaq-cyber-27b:latest`.
- Response SSE Events: `event: chunk\ndata: {"text": "..."}\n\n`
- Models Catalog: `GET /api/models` returns `{"models": [{"id": "orcasaq-cyber-27b:latest", "name": "friday Cyber Pro", "tag": "Cyber Pro", "is_default": true}], "default_model": "orcasaq-cyber-27b:latest"}`

### Frontend ↔ Backend Subscription Interface
- Catalog: `GET /api/subscription/plans` returns only `cyber_pro_monthly` and `cyber_pro_yearly`.
- Order Creation: `POST /api/create-order` accepts only `cyber_pro_monthly` or `cyber_pro_yearly`. Legacy plans return 400.
- User Status: `GET /api/subscription/status` recognizes legacy plans (`advanced_monthly`, `jr_hacker_monthly`, `founder_unlimited`) and returns active status with true expiration.

## Code Layout
- `backend/config.py`: `AVAILABLE_MODELS`, `ollama_model`, `ollama_timeout`, `cors_origins`.
- `backend/routes/chat.py`: Quick route greetings, system prompt, `_MODEL_NAME_REPLACEMENTS`, `/api/models`, `/api/chat`.
- `backend/services/subscription.py`: `PLAN_CONFIG` (`cyber_pro_monthly`, `cyber_pro_yearly`), legacy non-purchasable plans.
- `backend/routes/subscription.py`: `list_plans()`, `create_order()`, `verify_payment()`, webhook.
- `backend/routes/admin.py`: Subscription granting/revocation.
- `index.html`: Tactical radar animation CSS/HTML, multi-stage ticker JS, concurrency locks, pricing cards, model badge.
- `admin.html`: Plan granting options, user table badge rendering, XSS fix.
- `backend/test_models.py`, `backend/test_subscription.py`, `backend/test_backend.py`: Pytest suites.
- Remote VPS `/opt/friday/backend/.env`: `OLLAMA_MODEL=orcasaq-cyber-27b:latest`, `OLLAMA_TIMEOUT=300`.
