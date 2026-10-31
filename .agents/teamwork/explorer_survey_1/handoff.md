# Survey Explorer 1 Handoff Report: Ollama Models, Backend AI Integration & Branding Architecture

## 1. Observation

### 1.1 Backend Framework and AI Orchestration Architecture
- **Framework & Runtime**: Python 3.13.13 with FastAPI (`fastapi==0.115.0`) and Uvicorn (`uvicorn==0.31.0`).
- **Core Orchestration Modules**:
  1. `backend/main.py` (189 lines):
     - App lifecycle (`lifespan`, lines 33-55): Initializes DB schema via `services.db.init_db()` and triggers background model warm-up via `services.ollama.warmup_model(settings.ollama_model)`.
     - Security & Telemetry Middleware (lines 97-168): 10 MB payload limiter, IP sliding-window rate limiter (180 req/60s), request ID tracking (`X-Request-ID`), response time tracking (`X-Response-Time`), and OWASP security headers.
     - Router mounts (lines 182-187): `health`, `auth`, `chat`, `conversations`, `subscription`, `admin`.
  2. `backend/config.py` (142 lines):
     - Model allowlist registry (`AVAILABLE_MODELS`, lines 15-30).
     - Pydantic `Settings` (lines 35-89): `ollama_base_url` (default `"http://localhost:11434"`), `ollama_model` (default `"hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`), `ollama_timeout` (default `120.0`), `max_concurrent_inferences` (`4`), `max_inference_queue` (`40`), `max_user_concurrent_inferences` (`1`).
  3. `backend/services/ollama.py` (300 lines):
     - Concurrency Governor (`acquire_inference_capacity`, lines 36-120): Uses an `asyncio.Semaphore(max_concurrent_inferences)` with per-user concurrency tracking (`_user_active_inferences`) and bounded queue (`max_inference_queue=40`).
     - Connection Pooling (`get_http_client`, lines 149-163): Reuses an `httpx.AsyncClient` with keep-alive (`keepalive_expiry=300.0`, `max_connections=20`).
     - Ollama API Invocations:
       - `warmup_model()` (line 218): `POST {ollama_base_url}/api/chat` with 1-token prompt to pre-load weights into RAM/VRAM.
       - `check_ollama_reachable()` (line 203): `GET {ollama_base_url}/api/tags`.
       - `chat_stream()` (line 240): `POST {ollama_base_url}/api/chat` with `stream=True`, parsing JSON lines and yielding string tokens.
       - `chat_complete()` (line 288): Collects `chat_stream()` chunks for non-streaming mode.
  4. `backend/routes/chat.py` (677 lines):
     - System Prompt (`BLACK_HAT_SYSTEM_PROMPT`, lines 42-52): High-density adversarial mentor persona.
     - Quick Response Router (`_quick_route`, lines 59-218): Regex-based instant conversational routing bypasses Ollama.
     - Response Sanitization (`_sanitize_response`, lines 220-253): Regex replacement for model/vendor names and safety disclaimers.
     - Model Selection & Validation (`_prepare_messages`, lines 389-442): Enforces model allowlist against `get_allowed_model_ids()`.
     - Stream Generator (`_stream_generator`, lines 449-530): Wraps tokens into Server-Sent Events (`event: chunk\ndata: {"text": "..."}\n\n`).
  5. `backend/services/execution_intelligence.py` (230 lines):
     - Classifies lifecycle intents (`Architecture`, `CodeGen`, `RunEnv`, `Debug`, `Hardening`, `Beginner`) and injects dynamic `[ACTIVE STAGE DIRECTIVE: ...]` into user prompts.
  6. `backend/services/subscription.py` (477 lines):
     - Daily usage limits and model tier enforcement (`FREE_DAILY_LIMIT = 5`, `MODEL1_DAILY_LIMIT = 50`).

---

### 1.2 References to Ollama Models Across the Entire Codebase
Verbatim inventory of model references across all configuration files, backend routes, services, frontend templates, benchmark scripts, and tests:

1. **`hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`**:
   - `backend/config.py:17`: `"id": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`
   - `backend/config.py:40`: `ollama_model: str = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`
   - `backend/.env:14`: `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`
   - `backend/.env.example:14`: `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`
   - `backend/routes/chat.py:235`: `(re.compile(r"\b(?:hf\.co/)?(?:RavichandranJ/)?Dolphin(?:3)?(?:-Cyber)?(?:-8B)?(?:-GGUF)?(?::Q\d+_\w+)?\b", re.IGNORECASE), "FRIDAY")`
   - `backend/routes/chat.py:426`: `is_model_1 = (model == settings.ollama_model or "Dolphin3-Cyber" in model ...)`
   - `backend/services/subscription.py:78`: `MODEL_1_ID = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`
   - `backend/test_models.py:86, 89, 131, 245`: Referenced throughout model testing fixtures
   - `backend/test_backend.py:794, 798`: `test_sanitize_original_model_names` asserts "Dolphin3-Cyber" stripped
   - `backend/test_integration.py:22`: `("Dolphin3-Cyber" in s.ollama_model ...)`
   - `index.html:1380`: `id: "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`
   - `deploy_benchmark.py:21`: `("Dolphin3-Cyber-8B", "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0")`
   - VPS `/opt/friday/backend/.env:3`: `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`

2. **`huihui_ai/baronllm-abliterated:latest`**:
   - `backend/config.py:24`: `"id": "huihui_ai/baronllm-abliterated:latest"`
   - `backend/routes/chat.py:236`: `(re.compile(r"\b(?:huihui_ai/)?baronllm(?:-abliterated)?(?::latest)?\b", re.IGNORECASE), "FRIDAY")`
   - `backend/routes/chat.py:260`: `return "baronllm" in lower or "advanced" in lower`
   - `backend/routes/chat.py:426`: `"baronllm" not in model.lower()`
   - `backend/services/subscription.py:79`: `MODEL_2_ID = "huihui_ai/baronllm-abliterated:latest"`
   - `backend/test_models.py:85, 92, 164, 227`: Referenced in Model 2 test cases
   - `backend/test_backend.py:795, 801`: `test_sanitize_original_model_names` asserts "BaronLLM" stripped
   - `index.html:1387`: `id: "huihui_ai/baronllm-abliterated:latest"`
   - `index.html:1472`: `const isModel2 = modelId.includes('baronllm');`
   - `index.html:3152`: `const isModel2 = model.id.includes('baronllm');`
   - `admin.html:1428`: `tierLabel = 'Model 2 (BaronLLM Abliterated)';`
   - `deploy_benchmark.py:22`: `("BaronLLM-Abliterated", "huihui_ai/baronllm-abliterated:latest")`
   - `test_ollama_direct.py:21`: Model prompt call to `huihui_ai/baronllm-abliterated:latest`
   - `DEPLOYMENT_GUIDE.md:10`: `Ollama["Ollama Neural Engine\n(Huihui-Qwen3 & BaronLLM)"]`

3. **`orcasaq-cyber-27b:latest`**:
   - `deploy_benchmark.py:20`: `("OrcaSAQ-Cyber-27B", "orcasaq-cyber-27b:latest")`
   - `test_ollama_direct.py:35`: Model prompt call to `orcasaq-cyber-27b:latest`
   - `test_single_eval.py:24, 60`: Model evaluation runner for `orcasaq-cyber-27b:latest`
   - `upload_test_single.py:12`: Model test script for `orcasaq-cyber-27b:latest`

---

### 1.3 Model Invocation Mechanism
- Invocations are **direct asynchronous HTTP REST calls** using `httpx.AsyncClient` inside `backend/services/ollama.py`. No LangChain, LlamaIndex, or Ollama Python SDK is used.
- Payload structure generated in `_build_payload()` (`backend/services/ollama.py:182-199`):
  ```python
  {
      "model": model,
      "messages": messages,
      "stream": stream,
      "keep_alive": -1,  # Keeps model pinned permanently in memory/VRAM
      "options": {
          "temperature": 0.6,
          "top_p": 0.9,
          "top_k": 40,
          "num_predict": 2048,
          "num_ctx": 4096,     # Optimized KV cache size (prevents CPU RAM thrashing)
          "num_thread": 6,     # Tuned to host Intel i7-8700 6 physical cores
      },
  }
  ```
- Endpoint targeted: `POST {ollama_base_url}/api/chat`.
- Streaming responses are read line-by-line using `response.aiter_lines()`, decoded from JSON, sanitized against leaked vendor tags, and emitted as SSE frames (`backend/routes/chat.py:476-483`).

---

### 1.4 Branding & Leakage Audit: Where Model Selection, Greetings, Prompts, Errors, and Badges Live

1. **Greetings & Quick Routes**:
   - `backend/routes/chat.py:59-137` (`_QUICK_ROUTES_MODEL_1`):
     - Line 68: `"Hey! I'm FRIDAY, your AI junior pentester (The Jr Hacker)..."` -> **LEAK**: reveals "Jr Hacker" / "junior pentester".
     - Line 87: `"Good day! FRIDAY here, your AI junior pentester (The Jr Hacker)..."` -> **LEAK**.
     - Line 96: `"I'm FRIDAY, your AI junior pentester (The Jr Hacker)..."` -> **LEAK**.
   - `backend/routes/chat.py:139-215` (`_QUICK_ROUTES_MODEL_2`):
     - Line 148: `"Hey! I'm FRIDAY, your advanced penetration testing engine (The Advanced Pentester)..."` -> **LEAK**.
     - Line 167: `"Good day! FRIDAY here, your advanced penetration testing engine (The Advanced Pentester)..."` -> **LEAK**.
     - Line 176: `"I'm FRIDAY, your advanced penetration testing engine (The Advanced Pentester)..."` -> **LEAK**.

2. **System Prompts**:
   - `backend/routes/chat.py:42-52` (`BLACK_HAT_SYSTEM_PROMPT`):
     - Declares: `"You are FRIDAY: Senior Red Team Architect, OFFENSIVE SECURITY Authority, and Elite Technical Mentor."`
     - Controlled by `enable_blackhat_prompt` setting (`backend/config.py:65`).
     - Lines 426-440 currently selectively bypass the system prompt for Model 2 (`"baronllm" not in model.lower()`). With a single model (`orcasaq-cyber-27b:latest`), this split must be eliminated so that all generations uniformly apply the prompt when enabled.

3. **Response Sanitization (Output Leakage Protection)**:
   - `backend/routes/chat.py:234-243` (`_MODEL_NAME_REPLACEMENTS`):
     - Catches Dolphin3, BaronLLM, Cognitive Computations, Eric Hartford, huihui_ai, RavichandranJ, and Ollama.
     - **CRITICAL LEAK RISK**: It does **NOT** catch `orcasaq-cyber-27b`, `orcasaq`, or `OrcaSAQ`!
     - Furthermore, all current replacements substitute `"FRIDAY"`, whereas the required branding is `"friday Cyber Pro"`.

4. **API Endpoint & Output Model Names**:
   - `backend/routes/chat.py:533-543` (`GET /api/models`):
     - Returns `AVAILABLE_MODELS` from `config.py` and active default. Currently returns two items with names "Friday v1 The Jr Hacker" and "Friday v1 The Advanced Pentester".
   - `backend/routes/chat.py:620, 656`:
     - Explicitly sets `display_model = "Friday v1 The Jr Hacker"` or `"Friday v1 The Advanced Pentester"`.
   - `backend/routes/health.py:27`:
     - Returns `model="FRIDAY Neural Engine"`.

5. **Error Messages**:
   - `backend/routes/chat.py:405`: `"Selected model is not allowlisted for FRIDAY."`
   - `backend/routes/chat.py:582`: `"The Advanced Pentester model requires an Advanced Pentester subscription."` -> **LEAK**.
   - `backend/services/ollama.py:64`: `"FRIDAY neural engine is currently operating at peak capacity. Please retry shortly."`
   - `index.html:1477`: `'The Advanced Pentester requires an Advanced Pentester subscription.'` -> **LEAK**.

6. **Frontend UI Elements & Badges (`index.html`)**:
   - Line 430: `<span ... id="selected-model-label">Friday v1 The Jr Hacker</span>` -> **LEAK**.
   - Lines 427-444: `#model-selector-wrapper` and `#model-dropdown-menu`.
   - Lines 1378-1393: `DEFAULT_MODELS_REGISTRY` hardcodes both Dolphin3 and BaronLLM with older names.
   - Lines 1428, 1431: Model option buttons render old names.
   - Lines 2148, 2322: `<span class="font-heading font-semibold text-xs text-[#F5F5F5]">FRIDAY v1</span>` -> **LEAK**.
   - Line 2331: `<span class="text-[10px] font-mono text-[#52525B] hidden xs:inline">FRIDAY AI</span>`.
   - Line 3152: `updateModelDropdownLocks` checks `baronllm` and adds upgrade locks.

7. **Admin Portal UI (`admin.html`)**:
   - Lines 1428, 1431:
     - `tierLabel = 'Model 2 (BaronLLM Abliterated)';` -> **LEAK**.
     - `tierLabel = 'Model 1 (Jr Hacker Dolphin)';` -> **LEAK**.

---

### 1.5 Ollama Deployment & Configuration: Local vs. Live VPS (213.133.97.141)

1. **Live VPS (`213.133.97.141`) Status (Verified via SSH command execution)**:
   - Command: `ollama list`
     ```
     NAME                                               ID              SIZE      MODIFIED     
     orcasaq-cyber-27b:latest                           62d42125e7d4    15 GB     11 hours ago    
     hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0    433166fd820b    8.5 GB    11 days ago     
     huihui_ai/baronllm-abliterated:latest              976c91bbc8eb    4.9 GB    2 weeks ago     
     ```
     *Verification*: `orcasaq-cyber-27b:latest` (15 GB) is **already downloaded** and present on the VPS!
     *Removals required*: `ollama rm hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` (8.5 GB) and `ollama rm huihui_ai/baronllm-abliterated:latest` (4.9 GB) will free 13.4 GB disk space.
   - Command: `ollama ps`
     ```
     NAME                                               ID              SIZE     PROCESSOR    CONTEXT    UNTIL   
     hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0    433166fd820b    10 GB    100% CPU     4096       Forever    
     ```
     *Verification*: The Dolphin model is currently resident in CPU memory with keep-alive forever.
   - Command: `systemctl status friday.service`
     - Service file: `/etc/systemd/system/friday.service`
     - User: `friday`, Group: `friday`
     - Working directory: `/opt/friday/backend`
     - Command: `/opt/friday/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8008 --workers 1 --proxy-headers`
     - Active: `active (running) since Thu 2026-10-29 09:14:22 CET; 12h ago`
   - Command: `ps aux | grep cloudflared`
     - Process: `/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:8008`
   - Remote Config: `/opt/friday/backend/.env`:
     - `OLLAMA_BASE_URL=http://127.0.0.1:11434`
     - `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`
     - `OLLAMA_TIMEOUT=120`
     - `BACKEND_PORT=8008`
     - `DATABASE_URL=postgresql://...aws-0-ap-southeast-2.pooler.supabase.com...`

2. **Local Development Environment (`c:\Users\sharo\Desktop\friday`)**:
   - `backend/.env`:
     - `OLLAMA_BASE_URL=http://127.0.0.1:11435` (local tunnel/port)
     - `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`
     - `OLLAMA_TIMEOUT=120`
     - `BACKEND_PORT=8000`

---

### 1.6 Existing Tests and Runners
- **Test Framework**: `pytest 9.1.1` on Python 3.13.13 with `pytest-asyncio 1.4.0` and `pytest.ini` (`asyncio_mode = auto`).
- **Test Execution Command**:
  ```bash
  cd backend; .venv\Scripts\python -m pytest -m "not integration"
  ```
- **Test Suite Results**:
  - Total collected: 138 tests
  - Deselected: 14 integration tests (requiring live Ollama connection)
  - Selected & Ran: 124 tests
  - Result: **124 passed, 0 failed, 1 warning in 16.44s**.
- **Test File Inventory**:
  - `backend/test_models.py` (8 tests): Tests model allowlist, default fallback, system prompt attachment, and Model 1 vs Model 2 routing.
  - `backend/test_backend.py` (77 tests): Config, history trimming, schemas, database CRUD, health, sanitization (`test_sanitize_original_model_names`), quick router, and lifecycle intelligence.
  - `backend/test_auth.py` (9 tests): Firebase token verification, IDOR isolation, protected endpoints.
  - `backend/test_production_hardening.py` (10 tests): Concurrency governor, backpressure, queue cancellation, payload size limiter, sliding-window rate limiting.
  - `backend/test_subscription.py` (14 tests): Plan catalog, free tier quotas, Razorpay order creation, HMAC-SHA256 signature verification, anti-replay, and price tampering prevention.
  - `backend/test_integration.py` (6 tests): End-to-end live Ollama chat and health checks.

---

## 2. Logic Chain

1. **Premise 1 (Model Inventory & Consolidation Target)**:
   - Per Original Request R1 and Dispatch question 2, Ollama models `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest` must be eliminated, and only `orcasaq-cyber-27b:latest` retained and branded as "friday Cyber Pro".
   - Direct VPS inspection (Observation 1.5) proves `orcasaq-cyber-27b:latest` (15 GB) is already pulled on the VPS host.
   - Therefore, no lengthy 15 GB model download is necessary; consolidation requires removing the two older models via Ollama CLI, updating configuration files (`backend/config.py`, `backend/.env`, VPS `/opt/friday/backend/.env`), and re-pointing `Settings.ollama_model` to `orcasaq-cyber-27b:latest`.

2. **Premise 2 (Zero Raw Identifier Leakage Enforcement)**:
   - Observations 1.4.1 through 1.4.7 identify 7 distinct layers where raw model identifiers or older brand names ("Jr Hacker", "Advanced Pentester", "BaronLLM", "Dolphin", "FRIDAY v1") are exposed:
     a) Quick route greetings (`backend/routes/chat.py:68, 87, 96, 148, 167, 176`)
     b) Model allowlist & registry (`backend/config.py:15-30`, `AVAILABLE_MODELS`)
     c) API response model labels (`backend/routes/chat.py:620, 656`)
     d) Output response sanitization regex table (`backend/routes/chat.py:234-243`)
     e) Frontend UI elements & badges (`index.html:430, 1378-1393, 2148, 2322`)
     f) Error strings and gating messages (`backend/routes/chat.py:582`, `index.html:1477`)
     g) Admin portal table formatting (`admin.html:1428, 1431`)
   - To achieve zero leakage:
     - `_MODEL_NAME_REPLACEMENTS` in `backend/routes/chat.py` must be expanded to include all variants of `orcasaq`, `orcasaq-cyber-27b`, `OrcaSAQ`, `Dolphin`, and `BaronLLM`, translating them to `"friday Cyber Pro"`.
     - Quick route greetings must be unified into a single set introducing "friday Cyber Pro".
     - UI badges and labels must render `"friday Cyber Pro"` exclusively.
     - The frontend model dropdown must be simplified to present a single active "friday Cyber Pro" engine badge.

3. **Premise 3 (Inference Latency & Timeout Configuration)**:
   - `orcasaq-cyber-27b:latest` is a 27-billion parameter model running purely on CPU inference (Intel i7-8700 6 cores / 12 threads) on the VPS.
   - Observation from `test_single_eval.py` and Original Request R3 indicates inference latency is ~2.5–3 minutes (150–180 seconds).
   - Currently, `ollama_timeout` is set to 120.0 seconds in `backend/config.py:41` and `backend/.env:17`.
   - If a generation takes 150 seconds, `httpx.TimeoutException` will trigger at 120s, prematurely killing the stream and yielding an error to the user.
   - Therefore, `ollama_timeout` in `Settings` and `.env` files must be increased to at least 300.0 seconds (5 minutes).

4. **Premise 4 (Test Suite Impact & Co-adaptation)**:
   - `backend/test_models.py` currently tests the presence of both Dolphin3 and BaronLLM in `AVAILABLE_MODELS` (lines 85-86) and asserts distinct system prompt handling between Model 1 and Model 2 (lines 128-196).
   - Once `config.py` is consolidated to a single allowlisted model (`orcasaq-cyber-27b:latest` branded as "friday Cyber Pro"), `test_models.py` will fail unless updated to reflect the new single-model specification.
   - `backend/test_backend.py:791-805` (`test_sanitize_original_model_names`) must also be updated to assert that `orcasaq` and `orcasaq-cyber-27b` are sanitized and replaced with "friday Cyber Pro".

---

## 3. Caveats

1. **CPU Memory Footprint on VPS**:
   - `orcasaq-cyber-27b:latest` takes ~15 GB of system memory when active. The host machine must have sufficient free RAM (~20-24 GB) to avoid OOM killing `ollama` or `friday.service`. Running `ollama rm` on the two older models before warming up `orcasaq` will free disk and ensure clean unloads.
2. **Cloudflare Tunnel Persistence**:
   - The public URL in `index.html:965` (`PRODUCTION_DEFAULT_BACKEND`) points to `https://powerpoint-deal-loved-filling.trycloudflare.com`. Cloudflare Quick Tunnels can change if the process restarts. During live VPS deployment, the cloudflared process should be checked to verify the active hostname.
3. **Black Hat System Prompt Strategy for 27B Model**:
   - In `backend/config.py:65`, `enable_blackhat_prompt` is currently `False` by default for maximum generation speed and lower Time-to-First-Token (TTFT) on CPU. When enabled, it injects `BLACK_HAT_SYSTEM_PROMPT` (Observation 1.4.2). The prompt architecture works identically with single-model consolidation.

---

## 4. Conclusion

1. **Architecture Is Clean and Readily Consolidatable**:
   The backend uses FastAPI and direct async HTTP streaming to Ollama without bloated dependencies. Model allowlisting is centralized in `backend/config.py:AVAILABLE_MODELS`.
2. **Target Model Is Already on VPS**:
   `orcasaq-cyber-27b:latest` is already present on the VPS. Consolidating the live Ollama instance requires only deleting the two older models and updating `.env` to point `OLLAMA_MODEL` to `orcasaq-cyber-27b:latest`.
3. **Branding Consolidation Action Plan**:
   - Consolidate `AVAILABLE_MODELS` in `backend/config.py` to:
     ```python
     AVAILABLE_MODELS = [
         {
             "id": "orcasaq-cyber-27b:latest",
             "name": "friday Cyber Pro",
             "description": "Elite Offensive Cyber Security & Penetration Testing Engine",
             "tag": "Cyber Pro",
             "is_default": True,
         }
     ]
     ```
   - Update `ollama_model` in `config.py` and all `.env` files to `orcasaq-cyber-27b:latest`.
   - Increase `ollama_timeout` to `300.0` seconds to accommodate 2.5–3 minute 27B CPU inferences.
   - Unify `_QUICK_ROUTES` in `backend/routes/chat.py` with "friday Cyber Pro" persona and strip all "Jr Hacker" / "Advanced Pentester" text.
   - Expand `_MODEL_NAME_REPLACEMENTS` to replace `orcasaq`, `orcasaq-cyber-27b`, `OrcaSAQ`, `Dolphin`, and `BaronLLM` with `"friday Cyber Pro"`.
   - Update `index.html` model registry, header badges, and assistant tags to "friday Cyber Pro".
   - Update `admin.html` model tier formatting to "friday Cyber Pro".
   - Update `backend/test_models.py` and `backend/test_backend.py` to validate single-model allowlisting and 100% zero-leakage sanitization.

---

## 5. Verification Method

### 5.1 Automated Test Verification
Run the backend test suite from the project root:
```powershell
cd c:\Users\sharo\Desktop\friday\backend
.venv\Scripts\python -m pytest -m "not integration" -v
```
**Expected outcome**: All 124+ unit tests pass without errors or regressions.

### 5.2 Model Leakage and Sanitization Verification
Run Python test directly on the sanitization logic:
```powershell
cd c:\Users\sharo\Desktop\friday\backend
.venv\Scripts\python -c "
from routes.chat import _sanitize_response
text = 'I am OrcaSAQ-Cyber-27B and Dolphin3-Cyber by Cognitive Computations on Ollama'
cleaned = _sanitize_response(text)
assert 'OrcaSAQ' not in cleaned
assert 'Dolphin' not in cleaned
assert 'Cognitive Computations' not in cleaned
assert 'Ollama' not in cleaned
print('Sanitization Verification: PASS! Cleaned text:', cleaned)
"
```

### 5.3 Live VPS Remote Verification
Using `ssh_exec.py`:
1. Check models:
   ```powershell
   python ssh_exec.py "ollama list"
   ```
   **Verification criteria**: Only `orcasaq-cyber-27b:latest` appears. Neither `Dolphin3-Cyber-8B-GGUF:Q8_0` nor `baronllm-abliterated:latest` is present.
2. Check active loaded model:
   ```powershell
   python ssh_exec.py "ollama ps"
   ```
   **Verification criteria**: `orcasaq-cyber-27b:latest` is resident.
3. Check backend service:
   ```powershell
   python ssh_exec.py "systemctl status friday.service --no-pager"
   ```
   **Verification criteria**: `friday.service` is `active (running)`.
4. Check health endpoint:
   ```powershell
   python ssh_exec.py "curl -s http://127.0.0.1:8008/health"
   ```
   **Verification criteria**: Returns `{"status":"ok","ollama_reachable":true,...}`.

### 5.4 Invalidation Conditions
- Any occurrence of `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` or `huihui_ai/baronllm-abliterated:latest` in `GET /api/models` response.
- Any output token containing raw strings `"orcasaq"`, `"OrcaSAQ"`, `"baronllm"`, or `"Dolphin"`.
- Any greeting or UI element displaying "Friday v1", "The Jr Hacker", or "The Advanced Pentester" instead of "friday Cyber Pro".
