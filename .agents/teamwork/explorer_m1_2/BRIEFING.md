# BRIEFING — 2026-10-29T20:38:00Z

## Mission
Investigate frontend and admin files (index.html, admin.html) and formulate an exact line-by-line implementation strategy for consolidating model labels, registry, dropdowns, and badges to "friday Cyber Pro" with zero leaks.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\
- Original parent: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Milestone: Milestone 1 (Frontend UI Badges & Branding Consolidation)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strict branding adherence: brand model exclusively as "friday Cyber Pro" (or "Cyber Pro" badge where concise)
- Zero leaks: never reveal underlying model names, vendors, or raw system names (`orcasaq-cyber-27b`, `Dolphin3-Cyber-8B-GGUF`, `baronllm-abliterated`, RavichandranJ, huihui_ai, etc.)
- Only write metadata to `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\`

## Current Parent
- Conversation ID: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Updated: 2026-10-29T20:38:00Z

## Investigation State
- **Explored paths**: `index.html`, `admin.html`, `backend/routes/chat.py`, `backend/routes/admin.py`, `backend/config.py`, `backend/test_models.py`
- **Key findings**:
  - `index.html`: Line 340 (FRIDAY v1 in Brand Header), Line 430 (`#selected-model-label`), Lines 1378-1393 (`DEFAULT_MODELS_REGISTRY`), Lines 1396-1401 (localStorage fallback), Lines 1468-1479 (`selectModel` `isModel2` gate), Lines 2148 & 2322 (`FRIDAY v1` in typing/assistant bubble), Line 2331 (`FRIDAY AI` bubble footer), Lines 3083-3088 (`PLAN_LABELS`), Lines 3117 & 3130 (`updateSubBadge`), Lines 3142-3175 (`updateModelDropdownLocks`).
  - `admin.html`: Line 1039 (KPI subtitle `Model 1 & Model 2 paid`), Lines 1139-1144 (`#grant-plan` options with Model 1 and Model 2 text), Lines 1424-1434 (`Model 1 (Jr Hacker Dolphin)` and `Model 2 (BaronLLM Abliterated)` verbatim leak in user table), Lines 1564 & 1572 (`grant-plan` default select value).
- **Unexplored areas**: None. All frontend UI elements and JS logic mapped.

## Key Decisions Made
- Outlined complete line-by-line change specification for `index.html` and `admin.html`.
- Formulated localStorage migration logic so returning users do not retain stale legacy model IDs in `friday_selected_model`.
- Ensured grandfathered tier mappings remain functional for active subscribers while hiding all internal model names.

## Artifact Index
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\DISPATCH.md` — Task assignment & instructions
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\progress.md` — Liveness & status heartbeat
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_2\handoff.md` — Final investigation report
