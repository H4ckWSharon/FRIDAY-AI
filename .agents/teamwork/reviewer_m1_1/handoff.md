# Reviewer M1-1: Backend Model Consolidation & Rebranding Review Report

## 1. Observation

Direct inspection of code changes, configurations, and test suite execution results:

### A. Code & Configuration Verification
1. **`backend/config.py`**:
   - Lines 15–23: `AVAILABLE_MODELS` contains strictly one entry:
     ```python
     AVAILABLE_MODELS: list[dict[str, Any]] = [
         {
             "id": "orcasaq-cyber-27b:latest",
             "name": "friday Cyber Pro",
             "description": "Advanced Cyber Security & Penetration Testing Engine",
             "tag": "Cyber Pro",
             "is_default": True,
         },
     ]
     ```
   - Line 25: `ALLOWED_MODEL_IDS: set[str] = {m["id"] for m in AVAILABLE_MODELS}`
   - Line 33: `ollama_model: str = "orcasaq-cyber-27b:latest"`
   - Line 34: `ollama_timeout: float = 300.0`
   - Verification output from Python execution:
     `Available models: [{'id': 'orcasaq-cyber-27b:latest', 'name': 'friday Cyber Pro', 'description': 'Advanced Cyber Security & Penetration Testing Engine', 'tag': 'Cyber Pro', 'is_default': True}]`
     `Allowed model IDs: {'orcasaq-cyber-27b:latest'}`
     `Ollama model: orcasaq-cyber-27b:latest`
     `Ollama timeout: 300.0`

2. **`backend/.env` & `backend/.env.example`**:
   - `backend/.env:14`: `OLLAMA_MODEL=orcasaq-cyber-27b:latest`
   - `backend/.env:17`: `OLLAMA_TIMEOUT=300`
   - `backend/.env.example:14`: `OLLAMA_MODEL=orcasaq-cyber-27b:latest`
   - `backend/.env.example:17`: `OLLAMA_TIMEOUT=300`

3. **`backend/routes/health.py`**:
   - Line 27: Exposes `model="friday Cyber Pro"`.
   - Dual signal check: `ollama_ok = await check_ollama_reachable()`, `db_ok = await asyncio.to_thread(check_db_reachable)`.
   - Raw underlying model names and internal URLs are completely withheld from the public health endpoint response.

4. **`backend/routes/chat.py`**:
   - Lines 59–137: `_QUICK_ROUTES` greetings and identity queries answer exclusively as `"friday Cyber Pro"` and `"FRIDAY"`.
   - Lines 155–159: `SYSTEM_TAGS_PATTERN` regex cleanly strips tokenizer control tags (`<|im_start|>`, `<|im_end|>`, `<|system|>`, `<|user|>`, `<|assistant|>`, `<|endoftext|>`, `[INST]`, `[/INST]`, `<<SYS>>`, `<</SYS>>`, `<s>`, `</s>`, `<think>`, `</think>`).
   - Lines 161–228: `_MODEL_NAME_REPLACEMENTS` regex matrix maps all `orcasaq`, `Dolphin`, `BaronLLM` variants, older persona strings ("The Jr Hacker", "The Advanced Pentester"), and vendor names (`Cognitive Computations`, `Eric Hartford`, `huihui_ai`, `RavichandranJ`, `Ollama`) to `"friday Cyber Pro"` / `"FRIDAY"` / `"FRIDAY Neural Engine"`.
   - Lines 381–395: `_prepare_messages` contains `LEGACY_MODEL_MAPPING` mapping `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest` to `orcasaq-cyber-27b:latest`.
   - Lines 389–394: Rejects any unallowlisted model with HTTP 400 (`"Selected model is not allowlisted for FRIDAY."`).
   - Lines 454–488: `_stream_generator` features a 64-character lookahead sliding window buffer with delimiter-safe emission that catches and sanitizes split tokens across SSE chunk boundaries.
   - Lines 625 & 661: `display_model = "friday Cyber Pro"` for all ChatResponses.

### B. Automated Test Suite Execution Results
1. **Backend Unit Suites**:
   - Command: `pytest backend/test_models.py backend/test_backend.py backend/test_auth.py backend/test_production_hardening.py -v`
   - Output: `115 passed, 8 skipped in 58.51s` (0 failures).
2. **Milestone 1 E2E Requirement Tests (R1)**:
   - Command: `pytest backend/test_e2e_requirements.py -k "Requirement1 or _r1_" -v`
   - Output: `12 passed, 53 deselected in 2.16s` (100% pass rate for Milestone 1 scope).

---

## 2. Logic Chain

1. **Model Consolidation & Rebranding**:
   - Per `ORIGINAL_REQUEST.md` (R1) and `PROJECT.md` (F2), older models must be retired and `orcasaq-cyber-27b:latest` retained as the single active engine, branded strictly as "friday Cyber Pro".
   - Observed in Observation 1A that `config.py`, `.env`, and `.env.example` configure only `orcasaq-cyber-27b:latest` with default status and 300.0s timeout.
   - Observed in Observation 1A that `/api/models` lists only this single model.

2. **Leakage Prevention & Cross-Chunk Resilience**:
   - In streaming responses, tokenizers may split words across SSE packets (e.g., `Orca` in packet 1, `SAQ` in packet 2). Naive per-packet regex fails on split boundaries.
   - The 64-character lookahead sliding buffer in `chat.py:454–488` retains incomplete tokens until safe delimiters or stream completion, verified by `test_streaming_zero_cross_chunk_leakage`.
   - All 39+ vendor and model variants are replaced with sanitized brand terms; system and reasoning tags (`<think>`, `<|im_start|>`) are stripped.

3. **Backward Compatibility & Strict Gating**:
   - Legacy model IDs from previous bookmarks or sessions are silently remapped to `orcasaq-cyber-27b:latest` without disrupting users (`LEGACY_MODEL_MAPPING`).
   - Arbitrary model injections are strictly rejected with HTTP 400.

4. **Integrity Verification**:
   - Actively audited for hardcoded test fixtures, facades, shortcuts, or fake verification outputs.
   - All tests were executed directly in real environments against dynamic SQLite test databases, verified with genuine HTTP assertions. Zero integrity violations detected.

---

## 3. Caveats

1. **Live VPS Ollama Model Cleanup (`ollama rm`)**:
   - Execution of `ollama rm` on the live VPS host (213.133.97.141) is scheduled for Milestone 5 per `PROJECT.md`. Local backend configurations, routing, and fallbacks are 100% ready for that step.
2. **Subscription Catalog Modernization (Milestone 2)**:
   - `PLAN_CONFIG` and payment endpoints in `services/subscription.py` currently retain legacy plan identifiers until Milestone 2 implements the consolidated ₹3,500/mo tier and retired plan gating.

---

## 4. Conclusion

**Verdict: APPROVE**

The backend implementation for Milestone 1 satisfies all requirements in `ORIGINAL_REQUEST.md` (R1) and `PROJECT.md` (F2):
- Model allowlist consolidated to `orcasaq-cyber-27b:latest` branded as "friday Cyber Pro".
- Ollama timeout verified at 300.0s.
- Legacy models remapped cleanly to `orcasaq-cyber-27b:latest`.
- Zero raw model, vendor, or tokenizer tag leakage across non-streaming and streaming responses (including cross-chunk boundaries).
- All unit and E2E Milestone 1 test suites pass at 100% (115 unit tests passed, 12 R1 E2E tests passed, 0 failures).

---

## 5. Verification Method

To independently reproduce and verify this review:

1. **Verify Config and Model Allowlist**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'backend'); from config import get_settings, get_available_models, get_allowed_model_ids; print(get_settings().ollama_model); print(get_settings().ollama_timeout); print(get_available_models())"
   ```
   *Expected Output*:
   - `orcasaq-cyber-27b:latest`
   - `300.0`
   - `[{'id': 'orcasaq-cyber-27b:latest', 'name': 'friday Cyber Pro', 'description': 'Advanced Cyber Security & Penetration Testing Engine', 'tag': 'Cyber Pro', 'is_default': True}]`

2. **Execute Unit Test Suites**:
   ```powershell
   pytest backend/test_models.py backend/test_backend.py backend/test_auth.py backend/test_production_hardening.py -v
   ```
   *Expected Output*: `115 passed, 8 skipped` in ~58 seconds.

3. **Execute Milestone 1 E2E Requirements Tests**:
   ```powershell
   pytest backend/test_e2e_requirements.py -k "Requirement1 or _r1_" -v
   ```
   *Expected Output*: `12 passed, 53 deselected` in ~2 seconds.

4. **Verify Legacy Model Remapping & Model Rejection**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'backend'); from routes.chat import _prepare_messages; from schemas import ChatRequest, ChatMessage; req1 = ChatRequest(messages=[ChatMessage(role='user', content='test')], model='huihui_ai/baronllm-abliterated:latest'); print('Remapped:', _prepare_messages(req1)[1])"
   ```
   *Expected Output*: `Remapped: orcasaq-cyber-27b:latest`.

---

## 6. Adversarial Challenge & Stress-Test Summary

- **Challenge 1: Cross-chunk split token leakage**:
  - *Scenario*: Model emits `"Orca"` in chunk 1 and `"SAQ-cyber-27b"` in chunk 2.
  - *Result*: PASS. The 64-character lookahead buffer halts premature emission until delimiter boundaries or stream completion.
- **Challenge 2: Arbitrary model ID injection**:
  - *Scenario*: Malicious operator supplies `model="malicious-model:latest"`.
  - *Result*: PASS. Rejected with HTTP 400 `"Selected model is not allowlisted for FRIDAY."`.
- **Challenge 3: Lowercase and whitespace variations in legacy models**:
  - *Scenario*: Client requests `model="  hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0  "`.
  - *Result*: PASS. Stripped and mapped to `orcasaq-cyber-27b:latest`.
- **Challenge 4: Tokenizer and system tag stripping**:
  - *Scenario*: Response contains `<|im_start|>system` and `<think>internal reasoning</think>`.
  - *Result*: PASS. All tags stripped cleanly by `SYSTEM_TAGS_PATTERN`.
