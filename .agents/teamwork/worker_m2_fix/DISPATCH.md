## Task Assignment: Worker M2 Fix — Remediate Retired Plan Verification Loophole

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2_fix\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- Challenger M2-1 handoff report: `c:\Users\sharo\Desktop\friday\.agents\teamwork\challenger_m2_1\handoff.md`
- Project root: `c:\Users\sharo\Desktop\friday`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Problem Identified by Challenger M2-1
In `backend/routes/subscription.py` (`_handle_verify_payment`) and `backend/services/subscription.py` (`verify_and_activate`), while order creation checks `purchasable: True`, payment verification omitted the `purchasable` check. If a custom order matches a retired plan price, calling `/api/verify-payment` activates retired plans (`jr_hacker_*`, `advanced_*`) returning HTTP 200 instead of HTTP 400.

### Required Changes
1. In `backend/routes/subscription.py` inside `_handle_verify_payment()` (around lines 170-176):
   Add check:
   ```python
   if not plan.get("purchasable", False):
       raise HTTPException(
           status_code=400,
           detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
       )
   ```
2. In `backend/services/subscription.py` inside `verify_and_activate()`:
   Add check:
   ```python
   if not plan.get("purchasable", False):
       raise HTTPException(
           status_code=400,
           detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
       )
   ```
3. Run:
   ```powershell
   pytest backend/test_adversarial_m2.py -v
   pytest backend/test_subscription.py -v
   pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v
   ```
   Ensure 100% of all 49 adversarial tests pass, all 16 subscription unit tests pass, and all 14 R2 tests pass.
4. Write handoff report in `c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2_fix\handoff.md` and notify orchestrator.


## 2026-10-30T14:12:43Z
You are teamwork_worker assigned as Worker M2 Fix to remediate the retired plan verification loophole in Milestone 2.
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2_fix\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2_fix\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Remediate the vulnerability identified by Challenger M2-1:
1. In `backend/routes/subscription.py` (`_handle_verify_payment`) and `backend/services/subscription.py` (`verify_and_activate`), enforce `if not plan.get("purchasable", False): raise HTTPException(400, "Cannot activate plan: plan is retired or not purchasable")`.
2. Run `pytest backend/test_adversarial_m2.py -v` to ensure all 49 tests pass.
3. Run `pytest backend/test_subscription.py -v` and `pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v` to confirm no regressions.
4. Deliver your handoff report to `c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2_fix\handoff.md` and notify orchestrator.


## 2026-10-30T14:19:16Z
**Context**: Milestone 2 Remediation Status Check
**Content**: Checking on your progress fixing the retired plan activation check in `backend/routes/subscription.py` and `backend/services/subscription.py` and running `test_adversarial_m2.py`.
**Action**: Please report your current step and estimated delivery time.
