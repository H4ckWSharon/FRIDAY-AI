## Task Assignment: E2E Test Writer — Requirements-Driven E2E Test Suite (Tiers 1-4)

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\test_writer_e2e\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\TEST_INFRA.md`
- Project root: `c:\Users\sharo\Desktop\friday`

### Objective
Create a comprehensive, opaque-box, requirement-driven automated E2E test suite covering Requirements R1 through R4.
The test suite must be saved in `backend/test_e2e_requirements.py` (so it integrates seamlessly with `pytest`).

### Requirements to Test
1. **R1: Single Model Consolidation & Strict Rebranding**:
   - `GET /api/models` returns only `orcasaq-cyber-27b:latest` branded as "friday Cyber Pro".
   - Zero tolerance for leaked model identifiers (`orcasaq`, `Dolphin`, `BaronLLM`, `Cognitive Computations`, `Ollama`, `Jr Hacker`, `Advanced Pentester`) in outputs, greetings, system prompts, error messages.
   - Quick route greetings introduce "friday Cyber Pro".
2. **R2: Payment Pricing & Grandfathering Preservation**:
   - `GET /api/subscription/plans` offers strictly `cyber_pro_monthly` (₹3,500 / 350,000 paise) and `cyber_pro_yearly` (₹35,000 / 3,500,000 paise).
   - Older plans (`jr_hacker_*`, `advanced_*`) are rejected for purchase (`POST /api/create-order` returns 400).
   - Active grandfathered customer subscriptions (`advanced_monthly` in DB) remain active and honored without interruption or premature termination.
3. **R3: Chat UX Waiting State & Concurrency Protection**:
   - Concurrency locking: duplicate concurrent chats or invalid requests are blocked cleanly.
   - Streaming SSE format compliance.
4. **R4: Security, Stability & Verification**:
   - CORS origin validation (no "null" origin allowed).
   - Razorpay signature verification and tamper rejection.
   - Health check endpoint verification.

### Test Structure (Tiers 1-4)
- **Tier 1 (Feature Coverage)**: >= 25 test cases (>= 5 per requirement area).
- **Tier 2 (Boundary & Corner Cases)**: >= 25 test cases (edge inputs, price tampering, signature spoofing, expired subs, rate limits).
- **Tier 3 (Pairwise Interactions)**: >= 5 test cases testing interaction between features.
- **Tier 4 (Real-World Scenarios)**: >= 5 realistic end-to-end integration workflows.
Total test cases must be >= 60.

### Deliverables
1. Test file: `backend/test_e2e_requirements.py`
2. Publish `TEST_READY.md` at project root `c:\Users\sharo\Desktop\friday\TEST_READY.md` following the template in `PROJECT.md`.
3. Report back with `handoff.md` and test suite summary.

## 2026-10-29T20:27:42Z
You are teamwork_test_writer assigned to the E2E Testing Track.
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\test_writer_e2e\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\test_writer_e2e\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

Design and implement a comprehensive, requirement-driven, opaque-box E2E test suite in backend/test_e2e_requirements.py covering:
- Tier 1: Feature coverage (>=25 tests)
- Tier 2: Boundary & corner cases (>=25 tests)
- Tier 3: Cross-feature combinations (>=5 tests)
- Tier 4: Real-world user application scenarios (>=5 tests)
Total: >=60 test cases.

When the test suite is created and verified to run with pytest, publish TEST_READY.md at project root (c:\Users\sharo\Desktop\friday\TEST_READY.md) with test runner command and coverage summary table.
Write your handoff report to c:\Users\sharo\Desktop\friday\.agents\teamwork\test_writer_e2e\handoff.md and notify the orchestrator.

## 2026-10-29T20:39:01Z
**Context**: E2E Test Writer status check
**Content**: Checking in on progress for `backend/test_e2e_requirements.py` and `TEST_READY.md`.
**Action**: Please report current status and estimated time to completion.


