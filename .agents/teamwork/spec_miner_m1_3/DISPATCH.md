## Task Assignment: Spec Miner M1-3 — Strict Branding & Zero Leakage Specification

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Project root: `c:\Users\sharo\Desktop\friday`

### Scope & Objective
Extract the exhaustive specification and regex verification test matrix for Milestone 1:
1. Enumerate every raw identifier that must NEVER appear in greetings, UI elements, or error messages:
   - `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`, `Dolphin3`, `Dolphin`, `RavichandranJ`
   - `huihui_ai/baronllm-abliterated:latest`, `baronllm`, `BaronLLM`, `huihui_ai`
   - `orcasaq-cyber-27b:latest`, `orcasaq-cyber-27b`, `orcasaq`, `OrcaSAQ`
   - Vendor strings: `Cognitive Computations`, `Eric Hartford`, `Ollama`
   - Legacy labels: `The Jr Hacker`, `The Advanced Pentester`, `Friday v1`
2. Specify exact regex replacement patterns for `_MODEL_NAME_REPLACEMENTS` in `backend/routes/chat.py`.
3. Provide the exact test cases for `backend/test_models.py` and `backend/test_backend.py` to cryptographically assert zero leaks.

DO NOT modify source code. Produce structured specification in `c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\handoff.md`.

## 2026-10-29T20:29:14Z
You are teamwork_spec_miner assigned as Spec Miner M1-3 for Milestone 1 (Strict Branding & Zero Leakage Specification).
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

Mine authoritative specifications and extract the exact regex replacement matrix and test assertions to ensure zero raw model identifiers (orcasaq, Dolphin, BaronLLM, vendor names, system tags) can ever leak in UI, greetings, error strings, or generated streams.
Write findings to c:\Users\sharo\Desktop\friday\.agents\teamwork\spec_miner_m1_3\handoff.md and notify orchestrator.
