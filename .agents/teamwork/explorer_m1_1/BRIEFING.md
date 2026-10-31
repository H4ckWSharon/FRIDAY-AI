# BRIEFING — 2026-10-29T20:36:00Z

## Mission
Investigate backend files and formulate the exact line-by-line implementation strategy for Milestone 1 Backend changes: consolidating Ollama model to `orcasaq-cyber-27b:latest` branded "friday Cyber Pro", timeout 300s, unified quick routes, regex sanitization, and test adjustments.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_1\
- Original parent: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Milestone: M1 (Model Consolidation & Strict Rebranding)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT modify source code
- Produce structured recommendations in handoff.md

## Current Parent
- Conversation ID: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Updated: 2026-10-29T20:30:00Z

## Investigation State
- **Explored paths**: `backend/config.py`, `backend/.env`, `backend/.env.example`, `backend/routes/chat.py`, `backend/routes/health.py`, `backend/services/ollama.py`, `backend/services/subscription.py`, `backend/test_models.py`, `backend/test_backend.py`, `backend/test_integration.py`, `backend/test_production_hardening.py`
- **Key findings**:
  1. `backend/config.py`: `AVAILABLE_MODELS` has 2 legacy models; needs consolidation to 1 entry (`orcasaq-cyber-27b:latest` as "friday Cyber Pro"); `ollama_model` needs update to `orcasaq-cyber-27b:latest`; `ollama_timeout` needs increase from `120.0` to `300.0`.
  2. `backend/.env` & `.env.example`: `OLLAMA_MODEL` and `OLLAMA_TIMEOUT` must be updated to `orcasaq-cyber-27b:latest` and `300`.
  3. `backend/routes/chat.py`: Split `_QUICK_ROUTES_MODEL_1` and `_QUICK_ROUTES_MODEL_2` must merge into single `_QUICK_ROUTES` branded "friday Cyber Pro"; `_MODEL_NAME_REPLACEMENTS` must regex scrub `orcasaq`, `orcasaq-cyber-27b`, `OrcaSAQ`, `Dolphin`, `BaronLLM`, `Cognitive Computations`, `Eric Hartford`, `huihui_ai`, `RavichandranJ`; legacy model mapping `LEGACY_MODEL_MAPPING` provides seamless fallback; `display_model` assignments on lines 620 & 656 must be `"friday Cyber Pro"`; 403 error string on line 582 must eliminate "The Advanced Pentester";
  4. `backend/routes/health.py`: Line 27 reports `model="friday Cyber Pro"`.
  5. `backend/test_models.py` & `backend/test_backend.py`: Mapped exact test assertions for single model allowlist, quick route brand text, zero leakage, and `test_integration.py` config check.
- **Unexplored areas**: None for M1 Backend scope.

## Key Decisions Made
- Outlined precise before/after line numbers and replacement blocks for all target backend files.
- Provided backward compatibility legacy model mapping in `chat.py` so old cached requests map to `orcasaq-cyber-27b:latest` rather than crashing, while arbitrary models still return 400.

## Artifact Index
- DISPATCH.md — Task Assignment
- BRIEFING.md — Situational awareness
- progress.md — Liveness heartbeat
- handoff.md — Final investigation report
