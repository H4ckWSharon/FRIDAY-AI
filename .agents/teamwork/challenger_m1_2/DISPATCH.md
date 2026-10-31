## Task Assignment: Challenger M1-2 — API Boundary & Legacy Model Remapping Stress Tests

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\challenger_m1_2\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Worker handoff: `c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m1\handoff.md`

### Objective
Adversarially challenge and stress-test the API endpoints and legacy model mappings:
1. Test `GET /api/models`:
   - Verify unauthenticated and authenticated requests return ONLY `orcasaq-cyber-27b:latest` branded as "friday Cyber Pro".
   - Assert zero occurrences of legacy IDs in JSON response.
2. Test `POST /api/chat`:
   - Send requests with legacy model IDs (`hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest`) and assert they map cleanly to `orcasaq-cyber-27b:latest` without 400/500 errors.
   - Send requests with unallowlisted arbitrary models (e.g. `llama3:8b`, `gpt-4o`) and assert they are strictly rejected with HTTP 400 Bad Request.
3. Test `GET /health` to confirm `model: "friday Cyber Pro"`.
4. Deliver empirical verification results and a clear verdict: `APPROVE` or `REQUEST_CHANGES` in your `handoff.md`.


## 2026-10-29T21:15:58Z
You are teamwork_challenger assigned as Challenger M1-2 for Milestone 1.
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\challenger_m1_2\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\challenger_m1_2\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

Adversarially challenge and stress-test the API endpoints (/api/models, /api/chat, /health), legacy model mappings, and unallowlisted model rejections.
Deliver empirical results and a clear verdict: APPROVE or REQUEST_CHANGES in c:\Users\sharo\Desktop\friday\.agents\teamwork\challenger_m1_2\handoff.md and notify orchestrator.
