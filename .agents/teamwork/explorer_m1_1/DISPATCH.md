## Task Assignment: Explorer M1-1 — Backend Model Consolidation & Rebranding

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_1\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Project root: `c:\Users\sharo\Desktop\friday`

### Scope & Objective
Formulate the exact line-by-line implementation strategy for Milestone 1 Backend changes:
1. `backend/config.py`: Update `AVAILABLE_MODELS` to single entry for `orcasaq-cyber-27b:latest` ("friday Cyber Pro"), `ollama_model: str = "orcasaq-cyber-27b:latest"`, `ollama_timeout: float = 300.0`.
2. `backend/.env` & `backend/.env.example`: Set `OLLAMA_MODEL=orcasaq-cyber-27b:latest` and `OLLAMA_TIMEOUT=300`.
3. `backend/routes/chat.py`:
   - Replace `_QUICK_ROUTES_MODEL_1` and `_QUICK_ROUTES_MODEL_2` with a single unified `_QUICK_ROUTES` speaking as "friday Cyber Pro".
   - Expand `_MODEL_NAME_REPLACEMENTS` regex list to scrub `orcasaq-cyber-27b`, `orcasaq`, `OrcaSAQ`, `Dolphin`, `BaronLLM`, `Cognitive Computations`, `Eric Hartford`, `huihui_ai`, `RavichandranJ`, replacing with `"friday Cyber Pro"`.
   - Update `GET /api/models` and `display_model` assignments.
   - Update error strings to eliminate "The Advanced Pentester requires..." and replace with "friday Cyber Pro".
4. `backend/test_models.py` and `backend/test_backend.py`: Map exact test adjustments needed so tests validate the single model and zero leakage.

DO NOT modify source code. Produce structured recommendations in `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_m1_1\handoff.md`.
