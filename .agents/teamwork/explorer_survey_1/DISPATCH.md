## Task Assignment: Survey Explorer 1 — Ollama Models, Backend AI Integration & Branding

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- Project Root: `c:\Users\sharo\Desktop\friday`
- VPS Host: `213.133.97.141` (SSH: root / AfjbCUvqgdpST8)

### Objective
Conduct an in-depth codebase and architecture survey focused on Requirement R1 (Ollama Model Cleanup and Rebranding) and overall backend AI service structure.

### Specific Questions to Investigate
1. What language/framework is used for the backend and AI orchestration? Where are the files located?
2. Where are the Ollama models (`hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`, `huihui_ai/baronllm-abliterated:latest`, and `orcasaq-cyber-27b:latest`) referenced in the codebase? (config, routes, scripts, prompts, frontend)?
3. How is the model invoked? Direct HTTP calls to Ollama, an Ollama SDK, LangChain, or something else?
4. How is model selection, greetings, system prompts, error messages, and UI model badges implemented? Where could raw model identifiers or vendor names leak?
5. How is Ollama configured and running locally vs on the VPS (213.133.97.141)? What scripts/services control it?
6. What changes are required to enforce "friday Cyber Pro" branding everywhere with zero leakage?
7. How are tests run in this repository? What test harnesses or test files currently exist?

### Rules & Deliverables
- DO NOT modify or write source code.
- Write your findings, verified evidence (file paths, line numbers, code snippets), and recommendations to `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\handoff.md`.
- Keep `progress.md` updated with timestamp heartbeats.
- When finished, send a message to the orchestrator with your summary and handoff path.


## 2026-10-29T20:09:29Z
You are teamwork_explorer assigned as Survey Explorer 1 for the FRIDAY consolidation and rebranding project.
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

Focus on: Ollama Models, AI Chat Backend & Prompt/Branding Architecture.
Investigate:
1. Backend framework and AI orchestration files.
2. References to Ollama models (hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0, huihui_ai/baronllm-abliterated:latest, and orcasaq-cyber-27b:latest).
3. Where model selection, greetings, system prompts, error messages, and UI model badges live.
4. Branding enforcement to "friday Cyber Pro" with zero raw identifier leakage.
5. Ollama config and integration on local and VPS (213.133.97.141).
6. Existing tests and runners.

Produce your structured handoff report in:
c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_1\handoff.md
Maintain progress.md with timestamp heartbeats.
When complete, send a message to orchestrator with summary and handoff path.
