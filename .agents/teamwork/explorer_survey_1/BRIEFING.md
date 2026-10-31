# BRIEFING — 2026-10-29T20:20:00Z

## Mission
Investigate Ollama models, AI chat backend, and prompt/branding architecture for FRIDAY consolidation and rebranding to "friday Cyber Pro".

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: Survey Explorer 1 (Ollama Models, AI Chat Backend & Prompt/Branding Architecture)
- Working directory: c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\
- Original parent: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Milestone: Survey & Investigation (Phase 1)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT modify or write source code
- Files for content delivery, Messages for coordination
- Maintain progress.md with timestamp heartbeats
- Produce structured 5-component handoff report in handoff.md

## Current Parent
- Conversation ID: 577be955-4ab1-40ee-81ad-fce0ceb6ffa6
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `backend/main.py`, `backend/config.py`, `backend/schemas.py`
  - `backend/routes/chat.py`, `backend/routes/health.py`, `backend/routes/subscription.py`, `backend/routes/admin.py`
  - `backend/services/ollama.py`, `backend/services/subscription.py`, `backend/services/db.py`, `backend/services/execution_intelligence.py`
  - `index.html`, `admin.html`, `deploy_vps.sh`, `DEPLOYMENT_GUIDE.md`
  - VPS `213.133.97.141` live inspection via SSH (`ollama list`, `ollama ps`, `friday.service`, `cloudflared`)
  - Test suites: `backend/test_models.py`, `backend/test_backend.py`, `backend/test_subscription.py`, `backend/test_production_hardening.py`, `backend/test_auth.py`
- **Key findings**:
  - `orcasaq-cyber-27b:latest` (15 GB) is ALREADY downloaded on the VPS!
  - `Dolphin3-Cyber-8B-GGUF:Q8_0` (8.5 GB) and `baronllm-abliterated:latest` (4.9 GB) are currently present on the VPS and Dolphin is resident in memory. Removing them will free 13.4 GB.
  - Backend uses FastAPI + custom async httpx client in `services/ollama.py` with keep-alive, streaming SSE, and an inference semaphore governor.
  - Multiple locations across backend and frontend leak old model names, greetings ("The Jr Hacker", "The Advanced Pentester"), error messages, and assistant tags ("FRIDAY v1").
  - Test suite has 124 passing unit tests; `test_models.py` explicitly tests the two-model setup and will need consolidation updates.
- **Unexplored areas**: None for Phase 1 Survey Explorer 1 scope.

## Key Decisions Made
- Completed systematic investigation of all 7 target questions from DISPATCH.md.
- Synthesized exact file paths, line numbers, and before/after transition requirements into handoff.md.

## Artifact Index
- DISPATCH.md — Task dispatch and instructions
- BRIEFING.md — Persistent working memory
- progress.md — Liveness heartbeat and progress tracking
- handoff.md — Structured investigation report
