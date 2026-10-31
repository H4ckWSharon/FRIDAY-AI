# Milestone 1: Backend Model Consolidation & Strict Rebranding — Handoff Report

## 1. Observation

Direct code observations from the target repository files:

### A. `backend/config.py`
- **Lines 15–30**: Contains legacy allowlisted models:
  ```python
  AVAILABLE_MODELS: list[dict[str, Any]] = [
      {
          "id": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
          "name": "Friday v1 The Jr Hacker",
          "description": "AI Junior Pentester & Security Mentor",
          "tag": "Jr Hacker (Default)",
          "is_default": True,
      },
      {
          "id": "huihui_ai/baronllm-abliterated:latest",
          "name": "Friday v1 The Advanced Pentester",
          "description": "Advanced Cyber Security & Penetration Testing Engine",
          "tag": "Advanced Pentester",
          "is_default": False,
      },
  ]
  ```
- **Line 40**: `ollama_model: str = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"`
- **Line 41**: `ollama_timeout: float = 120.0`
- **Lines 123–141**: `get_allowed_model_ids()` builds from `ALLOWED_MODEL_IDS`, and `get_available_models()` iterates over `AVAILABLE_MODELS`.

### B. `backend/.env` & `backend/.env.example`
- **`backend/.env:14`**: `OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0`
- **`backend/.env:17`**: `OLLAMA_TIMEOUT=120`
- **`backend/.env.example:13–14`**:
  ```ini
  # e.g. hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0
  OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0
  ```
- **`backend/.env.example:17`**: `OLLAMA_TIMEOUT=120`

### C. `backend/routes/chat.py`
- **Lines 59–217**: Contains two separate quick route lists (`_QUICK_ROUTES_MODEL_1` and `_QUICK_ROUTES_MODEL_2`). Model 1 greetings refer to `"Friday v1 The Jr Hacker"`, `"AI junior pentester (The Jr Hacker)"`, and Model 2 greetings refer to `"Friday v1 The Advanced Pentester"`, `"advanced penetration testing engine (The Advanced Pentester)"`. Line 217 sets `_QUICK_ROUTES = _QUICK_ROUTES_MODEL_1`.
- **Lines 234–243**: `_MODEL_NAME_REPLACEMENTS` regex list currently only matches Dolphin, BaronLLM, Cognitive Computations, Eric Hartford, huihui_ai, RavichandranJ, and Ollama. It does NOT match `orcasaq-cyber-27b`, `orcasaq`, or `OrcaSAQ`.
- **Lines 255–261**: `_is_advanced_pentester_model(model)` checks for `"baronllm" in lower or "advanced" in lower`.
- **Lines 263–276**: `_quick_route()` branches between `_QUICK_ROUTES_MODEL_2` and `_QUICK_ROUTES_MODEL_1`.
- **Lines 424–440**: `_prepare_messages()` checks `is_model_1 = (model == settings.ollama_model or "Dolphin3-Cyber" in model or "Huihui-Qwen3-Coder" in model or "baronllm" not in model.lower())` to decide whether to attach `BLACK_HAT_SYSTEM_PROMPT`.
- **Lines 576–588**: In model tier gating, line 582 raises:
  `"message": "The Advanced Pentester model requires an Advanced Pentester subscription."`
- **Lines 620 & 656**: `display_model` assignment:
  `display_model = "Friday v1 The Jr Hacker" if not _is_advanced_pentester_model(request.model) else "Friday v1 The Advanced Pentester"`
  `display_model = "Friday v1 The Jr Hacker" if not _is_advanced_pentester_model(model) else "Friday v1 The Advanced Pentester"`

### D. `backend/routes/health.py`
- **Line 27**: Returns `model="FRIDAY Neural Engine"` in `HealthResponse`.

### E. Test Suites
- **`backend/test_models.py:85–94`**: Asserts `"huihui_ai/baronllm-abliterated:latest"` and `"hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"` in `model_ids`; asserts friendly names `"Friday v1 The Jr Hacker"` and `"Friday v1 The Advanced Pentester"`.
- **`backend/test_models.py:128–195`**: Tests model 1 attaching system prompt and model 2 skipping system prompt.
- **`backend/test_models.py:216–254`**: Tests quick route greetings expecting `"The Jr Hacker"` for model 1 and `"Advanced Pentester"` for model 2.
- **`backend/test_backend.py:791–805`**: Tests sanitization on Dolphin and BaronLLM; does not assert on `orcasaq`.
- **`backend/test_integration.py:22`**: Tests `ok = (s.ollama_base_url is not None and ("Dolphin3-Cyber" in s.ollama_model or "Huihui-Qwen3-Coder" in s.ollama_model or "qwen" in s.ollama_model))` which will fail once `ollama_model` is changed to `orcasaq-cyber-27b:latest`.

---

## 2. Logic Chain

1. **Model Consolidation (R1, F2)**:
   - Observation A shows `AVAILABLE_MODELS` has two models. The user request mandates retaining exclusively `orcasaq-cyber-27b:latest`.
   - Therefore, `AVAILABLE_MODELS` must be updated to a single entry:
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
   - `Settings.ollama_model` in `config.py` and `OLLAMA_MODEL` in `.env` / `.env.example` must default to `"orcasaq-cyber-27b:latest"`.

2. **Timeout Elevation (F5)**:
   - Inference on 27B model on CPU takes 2.5–3 minutes. Observation A shows default timeout is 120.0s.
   - Therefore, `ollama_timeout` in `config.py` must be increased to `300.0`, and `OLLAMA_TIMEOUT` in `.env` / `.env.example` must be set to `300`. `httpx.AsyncClient` in `backend/services/ollama.py:162` consumes `settings.ollama_timeout`, so elevating it in `config.py` propagates throughout all streaming and complete inferences.

3. **Strict Rebranding & Quick Routes Unification (R1, F3)**:
   - Observation C shows persona split into Jr Hacker and Advanced Pentester.
   - The user request explicitly demands eliminating legacy persona names and branding all outputs exclusively as "friday Cyber Pro".
   - Therefore, `_QUICK_ROUTES_MODEL_1` and `_QUICK_ROUTES_MODEL_2` must be merged into a single `_QUICK_ROUTES` list where all greetings and self-identifications identify as `"friday Cyber Pro"` (or `"FRIDAY, your cyber security & penetration testing engine (friday Cyber Pro)"`).
   - `_is_advanced_pentester_model()` should be simplified to return `False` (or deprecated), and `_quick_route()` should iterate directly over `_QUICK_ROUTES`.
   - `display_model` in `chat.py:620` and `chat.py:656` must be set directly to `"friday Cyber Pro"`.

4. **Regex Output Sanitization (R1, F4)**:
   - The 27B model or Ollama may emit internal tags or base model names (`OrcaSAQ`, `orcasaq-cyber-27b`, `Cognitive Computations`, etc.).
   - Observation C shows `_MODEL_NAME_REPLACEMENTS` lacks patterns for OrcaSAQ.
   - Therefore, add a case-insensitive regex pattern:
     `(re.compile(r"\b(?:orcasaq|OrcaSAQ)(?:[-_]?(?:cyber)?[-_]?(?:27b)?(?::\w+)?)?\b", re.IGNORECASE), "friday Cyber Pro")`
     and update the other replacements so Dolphin / BaronLLM / huihui_ai also replace with `"friday Cyber Pro"` / `"FRIDAY"`.

5. **Legacy Model Fallback & Error Sanitization (Interface Contract & R1)**:
   - If an existing client or frontend session requests `hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` or `huihui_ai/baronllm-abliterated:latest`, it should be mapped cleanly via a `LEGACY_MODEL_MAPPING` dict in `_prepare_messages()` to `orcasaq-cyber-27b:latest`.
   - Unallowlisted arbitrary models (e.g. `malicious-model:latest`) must continue to trigger HTTP 400 Bad Request.
   - Error strings in `chat.py:582` mentioning `"The Advanced Pentester model requires an Advanced Pentester subscription."` must be changed to:
     `"message": "friday Cyber Pro requires an active subscription."`

6. **Test Modernization (F18)**:
   - Existing unit tests in `test_models.py` expect 2 models, "The Jr Hacker", and "The Advanced Pentester". Running them against the single model configuration will fail unless updated.
   - Tests must be adjusted to validate:
     - Allowlist returns 1 model: `orcasaq-cyber-27b:latest` branded "friday Cyber Pro".
     - Default model fallback maps to `orcasaq-cyber-27b:latest`.
     - Quick route greets with "friday Cyber Pro" and zero mentions of "Jr Hacker" or "Advanced Pentester".
     - Sanitization catches all variants of OrcaSAQ, Dolphin, BaronLLM, and vendor names with zero leakage.
     - `test_integration.py:22` recognizes `orcasaq` in `settings.ollama_model`.

---

## 3. Caveats

1. **Ollama Service Running Locally vs VPS**:
   - In local development, Ollama may not have the 15GB `orcasaq-cyber-27b:latest` weights pulled locally. Mocking `chat_stream` and `chat_complete` in `pytest` isolates unit and schema testing from live model availability.
2. **Subscription Tier Consolidation Scope (Milestone 2 dependency)**:
   - `services/subscription.py` has `MODEL_1_ID` and `MODEL_2_ID` used by payment plan gating. Explorer M1-1 confines changes to model consolidation, branding, regex sanitization, and routing. Milestone 2 will handle `PLAN_CONFIG` and payment tier consolidation. Legacy model mapping ensures compatibility.
3. **No Code Written by Explorer**:
   - This report outlines exact line-by-line recommendations for the implementer agent. No source files were modified during this investigation.

---

## 4. Conclusion & Concrete Implementation Recommendations

The implementer should execute the following exact edits:

### File 1: `backend/config.py`

#### Lines 15–30: Replace `AVAILABLE_MODELS`
```python
<<<<
AVAILABLE_MODELS: list[dict[str, Any]] = [
    {
        "id": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
        "name": "Friday v1 The Jr Hacker",
        "description": "AI Junior Pentester & Security Mentor",
        "tag": "Jr Hacker (Default)",
        "is_default": True,
    },
    {
        "id": "huihui_ai/baronllm-abliterated:latest",
        "name": "Friday v1 The Advanced Pentester",
        "description": "Advanced Cyber Security & Penetration Testing Engine",
        "tag": "Advanced Pentester",
        "is_default": False,
    },
]
====
AVAILABLE_MODELS: list[dict[str, Any]] = [
    {
        "id": "orcasaq-cyber-27b:latest",
        "name": "friday Cyber Pro",
        "description": "Advanced Cyber Security & Penetration Testing Engine",
        "tag": "Cyber Pro",
        "is_default": True,
    },
]
>>>>
```

#### Lines 40–41: Replace `ollama_model` and `ollama_timeout`
```python
<<<<
    ollama_model: str = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"
    ollama_timeout: float = 120.0
====
    ollama_model: str = "orcasaq-cyber-27b:latest"
    ollama_timeout: float = 300.0
>>>>
```

---

### File 2: `backend/.env` & `backend/.env.example`

#### `backend/.env`: Lines 14 & 17
```ini
<<<<
OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0
...
OLLAMA_TIMEOUT=120
====
OLLAMA_MODEL=orcasaq-cyber-27b:latest
...
OLLAMA_TIMEOUT=300
>>>>
```

#### `backend/.env.example`: Lines 13–17
```ini
<<<<
# The exact model name as it appears in `ollama list`
# e.g. hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0
OLLAMA_MODEL=hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0

# How long (seconds) to wait for Ollama to respond
OLLAMA_TIMEOUT=120
====
# The exact model name as it appears in `ollama list`
# e.g. orcasaq-cyber-27b:latest
OLLAMA_MODEL=orcasaq-cyber-27b:latest

# How long (seconds) to wait for Ollama to respond
OLLAMA_TIMEOUT=300
>>>>
```

---

### File 3: `backend/routes/chat.py`

#### Lines 59–219: Replace split routes with unified `_QUICK_ROUTES`
```python
<<<<
_QUICK_ROUTES_MODEL_1: list[tuple[re.Pattern, str]] = [
...
]

_QUICK_ROUTES_MODEL_2: list[tuple[re.Pattern, str]] = [
...
]

_QUICK_ROUTES = _QUICK_ROUTES_MODEL_1
====
_QUICK_ROUTES: list[tuple[re.Pattern, str]] = [
    # ── Greetings ─────────────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:hi|hey|hello|sup|yo|greetings|howdy|what'?s\s+up)"
            r"(?:[,!.\s]+(?:friday|there|f\.r\.i\.d\.a\.y\.?))?"
            r"(?:[,!.\s]+(?:how\s+are\s+you|how's\s+it\s+going|how\s+r\s+u))?[!.?\s]*$",
            re.IGNORECASE,
        ),
        "Hey! I'm FRIDAY, your cyber security & penetration testing engine (friday Cyber Pro). Ready to help you with exploit dev, network recon, code audits, or security labs.\n"
        "What target or project are we working on today?",
    ),
    # ── How are you / status ──────────────────────────────────────────────
    (
        re.compile(
            r"^(?:how\s+are\s+you(?:\s+doing)?|how's\s+it\s+going|how\s+r\s+u|status\s+check)"
            r"(?:[,!.\s]+(?:friday|f\.r\.i\.d\.a\.y\.?))?[!.?\s]*$",
            re.IGNORECASE,
        ),
        "Systems primed. Cyber Pro penetration testing engine is armed and operational.\n"
        "What target or objective are we executing today?",
    ),
    # ── Good morning / evening / night ────────────────────────────────────
    (
        re.compile(
            r"^good\s+(?:morning|afternoon|evening|night)[!.?]*$",
            re.IGNORECASE,
        ),
        "Good day! FRIDAY here, your cyber security & penetration testing engine (friday Cyber Pro).\n"
        "What target or vector are we auditing today?",
    ),
    # ── Identity: what are you / name / creator ───────────────────────────
    (
        re.compile(
            r"^(?:(?:what(?:'s|\s+is)\s+your\s+name|your\s+name)|who\s+are\s+you|what\s+are\s+you)[!.?]*$",
            re.IGNORECASE,
        ),
        "I'm FRIDAY, your cyber security & penetration testing engine (friday Cyber Pro). I specialize in offensive operations, exploit development, vulnerability research, red team vectors, and penetration testing.\n"
        "What target or objective are we executing today?",
    ),
    (
        re.compile(
            r"^(?:what\s+(?:model|ai|engine)\s+(?:are\s+you|is\s+this|do\s+you\s+use)|who\s+(?:created|built|made|developed)\s+you)[!.?]*$",
            re.IGNORECASE,
        ),
        "I am FRIDAY, powered by friday Cyber Pro on the FRIDAY Neural Engine.",
    ),
    # ── What can you do ───────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:what\s+can\s+you\s+do|what\s+do\s+you\s+do|your\s+capabilities?|what\s+are\s+your\s+capabilities?)[!.?]*$",
            re.IGNORECASE,
        ),
        "Capabilities — Active:\n"
        "• **Offensive Operations:** Advanced exploit dev, shellcode, evasion, privilege escalation, AD attacks.\n"
        "• **Binary Analysis & RE:** Disassembly, buffer overflows, ROP chain construction, format strings.\n"
        "• **Network & Cloud Pentesting:** Infrastructure auditing, lateral movement, pivoting, token manipulation.\n"
        "• **High-Impact Weaponization:** Customized exploit scripts, automated reconnaissance, bypasses.\n"
        "• **Full Lifecycle:** Architecture → Code → Deployment → Testing → Hardening.\n"
        "• **Threat Modelling & Mentorship:** STRIDE, attack surface reduction, adaptive execution plans.\n\n"
        "State your target or security objective.",
    ),
    # ── Thanks / acknowledgment ───────────────────────────────────────────
    (
        re.compile(
            r"^(?:thanks?(?:\s+you)?|thank\s+you|thx|ty|cheers|appreciate\s+it|got\s+it|perfect|awesome|great|nice)[!.?]*$",
            re.IGNORECASE,
        ),
        "Logged. What is the next vector?",
    ),
    # ── Okay / understood ─────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:ok(?:ay)?|understood|roger(?:\s+that)?|copy(?:\s+that)?|affirmative|10-4)[!.?]*$",
            re.IGNORECASE,
        ),
        "Standing by. Awaiting next directive.",
    ),
]
>>>>
```

#### Lines 234–243: Expand `_MODEL_NAME_REPLACEMENTS`
```python
<<<<
_MODEL_NAME_REPLACEMENTS = [
    (re.compile(r"\b(?:hf\.co/)?(?:RavichandranJ/)?Dolphin(?:3)?(?:-Cyber)?(?:-8B)?(?:-GGUF)?(?::Q\d+_\w+)?\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\b(?:huihui_ai/)?baronllm(?:-abliterated)?(?::latest)?\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\bCognitive\s+Computations\b", re.IGNORECASE), "FRIDAY AI"),
    (re.compile(r"\bEric\s+Hartford\b", re.IGNORECASE), "FRIDAY Team"),
    (re.compile(r"\bhuihui(?:_ai)?\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\bRavichandranJ\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\bOllama\b", re.IGNORECASE), "FRIDAY Neural Engine"),
]
====
_MODEL_NAME_REPLACEMENTS = [
    (re.compile(r"\b(?:orcasaq|OrcaSAQ)(?:[-_]?(?:cyber)?[-_]?(?:27b)?(?::\w+)?)?\b", re.IGNORECASE), "friday Cyber Pro"),
    (re.compile(r"\b(?:hf\.co/)?(?:RavichandranJ/)?Dolphin(?:3)?(?:-Cyber)?(?:-8B)?(?:-GGUF)?(?::Q\d+_\w+)?\b", re.IGNORECASE), "friday Cyber Pro"),
    (re.compile(r"\b(?:huihui_ai/)?baronllm(?:-abliterated)?(?::latest)?\b", re.IGNORECASE), "friday Cyber Pro"),
    (re.compile(r"\bCognitive\s+Computations\b", re.IGNORECASE), "FRIDAY AI"),
    (re.compile(r"\bEric\s+Hartford\b", re.IGNORECASE), "FRIDAY Team"),
    (re.compile(r"\bhuihui(?:_ai)?\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\bRavichandranJ\b", re.IGNORECASE), "FRIDAY"),
    (re.compile(r"\bOllama\b", re.IGNORECASE), "FRIDAY Neural Engine"),
]
>>>>
```

#### Lines 255–277: Update `_is_advanced_pentester_model` and `_quick_route`
```python
<<<<
def _is_advanced_pentester_model(model: str | None) -> bool:
    """Return True if model corresponds to Model 2 (Friday v1 The Advanced Pentester / BaronLLM)."""
    if not model:
        return False
    lower = model.lower()
    return "baronllm" in lower or "advanced" in lower


def _quick_route(text: str, model: str | None = None) -> str | None:
    """
    Check if the message matches a quick-route pattern.
    Selects model-appropriate persona responses (Jr Hacker vs Advanced Pentester).
    Returns the pre-written response string, or None to fall through to Ollama.
    Greetings ALWAYS answer with FRIDAY identity.
    """
    routes = _QUICK_ROUTES_MODEL_2 if _is_advanced_pentester_model(model) else _QUICK_ROUTES_MODEL_1
    stripped = text.strip()
    for pattern, response in routes:
        if pattern.match(stripped):
            logger.info("Quick route matched for: %r (model=%r)", stripped[:60], model)
            return response
    return None
====
def _is_advanced_pentester_model(model: str | None) -> bool:
    """Deprecated: Retained for backward-compatibility; always returns False."""
    return False


def _quick_route(text: str, model: str | None = None) -> str | None:
    """
    Check if the message matches a quick-route pattern.
    Returns the pre-written response string, or None to fall through to Ollama.
    Greetings ALWAYS answer with friday Cyber Pro identity.
    """
    stripped = text.strip()
    for pattern, response in _QUICK_ROUTES:
        if pattern.match(stripped):
            logger.info("Quick route matched for: %r (model=%r)", stripped[:60], model)
            return response
    return None
>>>>
```

#### Lines 389–410: Add `LEGACY_MODEL_MAPPING` in `_prepare_messages`
```python
<<<<
    if request.model is not None and request.model.strip():
        requested_model = request.model.strip()
        if requested_model not in allowed_ids:
            logger.warning("Unallowlisted model requested: %r", requested_model)
            raise HTTPException(
                status_code=400,
                detail="Selected model is not allowlisted for FRIDAY.",
            )
        model = requested_model
    else:
        model = settings.ollama_model
====
    LEGACY_MODEL_MAPPING = {
        "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0": "orcasaq-cyber-27b:latest",
        "huihui_ai/baronllm-abliterated:latest": "orcasaq-cyber-27b:latest",
    }
    if request.model is not None and request.model.strip():
        requested_model = request.model.strip()
        if requested_model in LEGACY_MODEL_MAPPING:
            requested_model = LEGACY_MODEL_MAPPING[requested_model]
        if requested_model not in allowed_ids:
            logger.warning("Unallowlisted model requested: %r", requested_model)
            raise HTTPException(
                status_code=400,
                detail="Selected model is not allowlisted for FRIDAY.",
            )
        model = requested_model
    else:
        model = settings.ollama_model
>>>>
```

#### Lines 424–440: Connect `BLACK_HAT_SYSTEM_PROMPT` to the consolidated model
```python
<<<<
    # Only Model 1 (Friday v1 The Jr Hacker) connects with the chat.py prompt.
    # Model 2 (Friday v1 The Advanced Pentester / BaronLLM) runs raw without chat.py prompt.
    is_model_1 = (model == settings.ollama_model or "Dolphin3-Cyber" in model or "Huihui-Qwen3-Coder" in model or "baronllm" not in model.lower())

    if is_model_1:
        messages = [{"role": "system", "content": BLACK_HAT_SYSTEM_PROMPT}]
        if user_content:
            stage = detect_lifecycle_intent(user_content, raw_history)
            directive = get_stage_directive(stage, user_content)
            if directive and prepared_history and prepared_history[-1]["role"] == "user":
                orig_content = prepared_history[-1]["content"]
                prepared_history[-1]["content"] = f"{orig_content}\n\n[ACTIVE STAGE DIRECTIVE: {directive}]"
        messages.extend(prepared_history)
    else:
        # Model 2: Standalone conversational turns without chat.py system prompt/directives
        messages = prepared_history
====
    # All inference connects to friday Cyber Pro with full system prompt & stage directives
    messages = [{"role": "system", "content": BLACK_HAT_SYSTEM_PROMPT}]
    if user_content:
        stage = detect_lifecycle_intent(user_content, raw_history)
        directive = get_stage_directive(stage, user_content)
        if directive and prepared_history and prepared_history[-1]["role"] == "user":
            orig_content = prepared_history[-1]["content"]
            prepared_history[-1]["content"] = f"{orig_content}\n\n[ACTIVE STAGE DIRECTIVE: {directive}]"
    messages.extend(prepared_history)
>>>>
```

#### Lines 576–588: Access gate error message rebrand
```python
<<<<
    elif _tier == "model1":
        if _requested_model == MODEL_2_ID:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "model_access_denied",
                    "message": "The Advanced Pentester model requires an Advanced Pentester subscription.",
                    "upgrade_required": True,
                    "required_tier": "model2",
                },
            )
        if user_id:
            check_and_increment_model1_usage(user_id)  # raises HTTP 429 if 50 chats/day limit exceeded
====
    elif _tier == "model1":
        # Legacy grandfathered tier or access verification
        if _requested_model == "huihui_ai/baronllm-abliterated:latest":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "model_access_denied",
                    "message": "friday Cyber Pro requires an active subscription.",
                    "upgrade_required": True,
                    "required_tier": "model2",
                },
            )
        if user_id:
            check_and_increment_model1_usage(user_id)  # raises HTTP 429 if 50 chats/day limit exceeded
>>>>
```

#### Lines 620 & 656: Update `display_model` assignment
```python
<<<<
        display_model = "Friday v1 The Jr Hacker" if not _is_advanced_pentester_model(request.model) else "Friday v1 The Advanced Pentester"
====
        display_model = "friday Cyber Pro"
>>>>
```
and
```python
<<<<
        display_model = "Friday v1 The Jr Hacker" if not _is_advanced_pentester_model(model) else "Friday v1 The Advanced Pentester"
====
        display_model = "friday Cyber Pro"
>>>>
```

---

### File 4: `backend/routes/health.py`

#### Line 27:
```python
<<<<
        model="FRIDAY Neural Engine",
====
        model="friday Cyber Pro",
>>>>
```

---

### File 5: `backend/test_models.py`

#### Lines 75–95: Update `test_get_models_authenticated_returns_allowlist`
```python
<<<<
    model_ids = [m["id"] for m in data["models"]]
    assert "huihui_ai/baronllm-abliterated:latest" in model_ids
    assert "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0" in model_ids

    # Check friendly branding
    model_1 = next(m for m in data["models"] if m["id"] == "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0")
    assert model_1["name"] == "Friday v1 The Jr Hacker"

    model_2 = next(m for m in data["models"] if m["id"] == "huihui_ai/baronllm-abliterated:latest")
    assert model_2["name"] == "Friday v1 The Advanced Pentester"
====
    model_ids = [m["id"] for m in data["models"]]
    assert len(model_ids) == 1
    assert "orcasaq-cyber-27b:latest" in model_ids
    assert "huihui_ai/baronllm-abliterated:latest" not in model_ids
    assert "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0" not in model_ids
    assert data["default"] == "orcasaq-cyber-27b:latest"

    # Check friendly branding
    model = data["models"][0]
    assert model["id"] == "orcasaq-cyber-27b:latest"
    assert model["name"] == "friday Cyber Pro"
    assert model["tag"] == "Cyber Pro"
    assert model["is_default"] is True
>>>>
```

#### Lines 120–125: Update `test_chat_with_default_model_attaches_system_prompt`
```python
<<<<
        assert called_model == settings.ollama_model
====
        assert called_model == "orcasaq-cyber-27b:latest"
>>>>
```

#### Lines 128–195: Replace old multi-model tests with Cyber Pro & Legacy Remapping tests
```python
<<<<
@pytest.mark.asyncio
async def test_chat_model_1_jr_hacker_attaches_system_prompt(temp_db):
...
@pytest.mark.asyncio
async def test_chat_model_2_advanced_pentester_does_not_attach_chat_prompt(temp_db):
...
====
@pytest.mark.asyncio
async def test_chat_cyber_pro_attaches_system_prompt(temp_db):
    """friday Cyber Pro connects with the chat.py BLACK_HAT_SYSTEM_PROMPT."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    target_model = "orcasaq-cyber-27b:latest"
    called_model = None
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_model, called_messages
        called_model = model
        called_messages = messages
        yield "Cyber Pro response chunk"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "audit this memory layout"}],
                    "model": target_model,
                    "stream": True,
                },
            )
        assert res.status_code == 200
        assert called_model == target_model
        assert "Cyber Pro response chunk" in res.text
        assert called_messages[0]["role"] == "system"
        assert "Senior Red Team Architect" in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_legacy_model_remapped_cleanly(temp_db):
    """Legacy model ID is safely remapped to orcasaq-cyber-27b:latest."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    called_model = None

    async def mock_stream(messages, model):
        nonlocal called_model
        called_model = model
        yield "Mapped response"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "test payload"}],
                    "model": "huihui_ai/baronllm-abliterated:latest",
                    "stream": True,
                },
            )
        assert res.status_code == 200
        assert called_model == "orcasaq-cyber-27b:latest"
>>>>
```

#### Lines 216–255: Update `test_quick_route_unaffected_by_model`
```python
<<<<
@pytest.mark.asyncio
async def test_quick_route_unaffected_by_model(temp_db):
    """Conversational intents ('hi') route instantaneously with model-appropriate persona."""
    import re as re_mod
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Model 2 (The Advanced Pentester)
        res_m2 = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "huihui_ai/baronllm-abliterated:latest",
                "stream": True,
            },
        )
        assert res_m2.status_code == 200
        assert "event: chunk" in res_m2.text
        assert "event: done" in res_m2.text
        m2_text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res_m2.text))
        assert "FRIDAY" in m2_text
        assert "Advanced Pentester" in m2_text
        assert "junior pentester" not in m2_text.lower()

        # Test Model 1 (The Jr Hacker)
        res_m1 = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
                "stream": True,
            },
        )
        assert res_m1.status_code == 200
        m1_text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res_m1.text))
        assert "FRIDAY" in m1_text
        assert "The Jr Hacker" in m1_text
        assert "junior pentester" in m1_text.lower()
====
@pytest.mark.asyncio
async def test_quick_route_unaffected_by_model(temp_db):
    """Conversational intents ('hi') route instantaneously with friday Cyber Pro persona."""
    import re as re_mod
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "orcasaq-cyber-27b:latest",
                "stream": True,
            },
        )
        assert res.status_code == 200
        assert "event: chunk" in res.text
        assert "event: done" in res.text
        text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res.text))
        assert "FRIDAY" in text
        assert "friday Cyber Pro" in text
        assert "The Jr Hacker" not in text
        assert "The Advanced Pentester" not in text
        assert "junior pentester" not in text.lower()
>>>>
```

#### Add Zero Leakage Test to `test_models.py`:
```python
@pytest.mark.asyncio
async def test_model_name_sanitization_zero_leakage(temp_db):
    """Response sanitizer strips all raw base model identifiers and vendors."""
    from routes.chat import _sanitize_response
    sample = (
        "Generated by orcasaq-cyber-27b:latest and OrcaSAQ. "
        "Also Dolphin3-Cyber, BaronLLM, Cognitive Computations, Eric Hartford, huihui_ai, RavichandranJ, and Ollama."
    )
    cleaned = _sanitize_response(sample)
    assert "orcasaq-cyber-27b" not in cleaned
    assert "orcasaq" not in cleaned.lower()
    assert "OrcaSAQ" not in cleaned
    assert "Dolphin3-Cyber" not in cleaned
    assert "BaronLLM" not in cleaned
    assert "Cognitive Computations" not in cleaned
    assert "Eric Hartford" not in cleaned
    assert "huihui_ai" not in cleaned
    assert "RavichandranJ" not in cleaned
    assert "Ollama" not in cleaned
    assert "friday Cyber Pro" in cleaned
```

---

### File 6: `backend/test_backend.py`

#### Lines 791–805: Update `test_sanitize_original_model_names`
```python
<<<<
    def test_sanitize_original_model_names(self):
        from routes.chat import _sanitize_response
        sample = (
            "Hello, I am Dolphin3-Cyber developed by Cognitive Computations and Eric Hartford on Ollama. "
            "BaronLLM by huihui_ai is another tool."
        )
        cleaned = _sanitize_response(sample)
        assert "Dolphin3-Cyber" not in cleaned
        assert "Cognitive Computations" not in cleaned
        assert "Eric Hartford" not in cleaned
        assert "BaronLLM" not in cleaned
        assert "huihui_ai" not in cleaned
        assert "Ollama" not in cleaned
        assert "FRIDAY" in cleaned
====
    def test_sanitize_original_model_names(self):
        from routes.chat import _sanitize_response
        sample = (
            "Hello, I am Dolphin3-Cyber developed by Cognitive Computations and Eric Hartford on Ollama. "
            "BaronLLM by huihui_ai is another tool. Also orcasaq-cyber-27b and OrcaSAQ from RavichandranJ."
        )
        cleaned = _sanitize_response(sample)
        assert "Dolphin3-Cyber" not in cleaned
        assert "Cognitive Computations" not in cleaned
        assert "Eric Hartford" not in cleaned
        assert "BaronLLM" not in cleaned
        assert "huihui_ai" not in cleaned
        assert "Ollama" not in cleaned
        assert "orcasaq-cyber-27b" not in cleaned
        assert "orcasaq" not in cleaned.lower()
        assert "OrcaSAQ" not in cleaned
        assert "RavichandranJ" not in cleaned
        assert "FRIDAY" in cleaned or "friday Cyber Pro" in cleaned
>>>>
```

---

### File 7: `backend/test_integration.py`

#### Line 22:
```python
<<<<
    ok = (s.ollama_base_url is not None and ("Dolphin3-Cyber" in s.ollama_model or "Huihui-Qwen3-Coder" in s.ollama_model or "qwen" in s.ollama_model))
====
    ok = (s.ollama_base_url is not None and ("orcasaq" in s.ollama_model.lower() or "cyber" in s.ollama_model.lower()))
>>>>
```

---

## 5. Verification Method

Once implemented, independently verify using:

1. **Unit Test Suite Execution**:
   ```powershell
   python -m pytest backend/test_backend.py backend/test_models.py backend/test_subscription.py -v
   ```
   *Expected Result*: All tests pass (100% green, 0 failures, 0 errors).

2. **Allowlist Inspection**:
   ```powershell
   python -c "from backend.config import get_settings, get_available_models; print('Model:', get_settings().ollama_model); print('Timeout:', get_settings().ollama_timeout); print('Available:', get_available_models())"
   ```
   *Expected Result*:
   - `Model: orcasaq-cyber-27b:latest`
   - `Timeout: 300.0`
   - `Available: [{'id': 'orcasaq-cyber-27b:latest', 'name': 'friday Cyber Pro', 'description': 'Advanced Cyber Security & Penetration Testing Engine', 'tag': 'Cyber Pro', 'is_default': True}]`

3. **Zero Model Leakage Verification**:
   ```powershell
   python -c "from backend.routes.chat import _sanitize_response; text = 'orcasaq-cyber-27b Dolphin3-Cyber BaronLLM huihui_ai RavichandranJ Ollama Cognitive Computations Eric Hartford'; print(_sanitize_response(text))"
   ```
   *Expected Result*: String contains only `"friday Cyber Pro"`, `"FRIDAY"`, `"FRIDAY Neural Engine"`, `"FRIDAY Team"`, and zero original model strings.

4. **Invalidation Conditions**:
   - Any test expecting `"Friday v1 The Jr Hacker"` or `"Friday v1 The Advanced Pentester"` fails.
   - Any reference to `huihui_ai/baronllm-abliterated:latest` or `Dolphin3-Cyber` appears in `GET /api/models`.
   - Any raw base model name is emitted without being caught by `_sanitize_response()`.
