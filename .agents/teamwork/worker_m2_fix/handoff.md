# Handoff Report: Milestone 2 Remediation — Retired Plan Verification Fix

**Agent**: Worker M2 Fix (`teamwork_worker`)  
**Status**: **COMPLETE**  
**Timestamp**: 2026-10-30T14:27:00Z  

---

## 1. Observation

### 1.1 Initial Problem Verification
Challenger M2-1 identified a defense-in-depth vulnerability in `POST /api/verify-payment`:
- Running `pytest backend/test_adversarial_m2.py -k "test_adv_verify_payment_must_reject_retired_plans" -v` reproduced 4 failures:
  ```
  FAILED backend/test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[jr_hacker_monthly-249900]
  FAILED backend/test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[jr_hacker_yearly-2499000]
  FAILED backend/test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[advanced_monthly-499900]
  FAILED backend/test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[advanced_yearly-4999000]
  ```
  Verbatim error:
  ```
  AssertionError: Security Flaw: /api/verify-payment accepted retired plan 'jr_hacker_monthly' and returned status 200 instead of 400!
  assert 200 == 400
  ```

### 1.2 Root Cause
In `backend/routes/subscription.py` (`_handle_verify_payment`) and `backend/services/subscription.py` (`verify_and_activate`), order verification verified HMAC signatures, anti-replay, and price thresholds, but did not check `not plan.get("purchasable", False)`. An attacker could create an un-tagged custom order matching legacy pricing (e.g. ₹2,499) and successfully activate retired tiers (`jr_hacker_*`, `advanced_*`).

---

## 2. Logic Chain

1. **Purchasability Enforcement on Route Verification (`backend/routes/subscription.py`)**:
   - In `_handle_verify_payment`, when `plan_id` is provided in the request body, validate that the plan exists and is explicitly marked purchasable:
     ```python
     if plan_id:
         if plan_id not in PLAN_CONFIG or not PLAN_CONFIG[plan_id].get("purchasable", False):
             raise HTTPException(
                 status_code=400,
                 detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
             )
         plan = PLAN_CONFIG[plan_id]
     ```
   - Scoped `user_id` and `create_subscription` inside `if plan_id:`, maintaining correct execution independent of whether `fetch_razorpay_order` returned a mock or None.

2. **Purchasability Enforcement on Service Verification (`backend/services/subscription.py`)**:
   - In `verify_and_activate`, added the explicit purchasable check right after verifying HMAC signature and plan existence:
     ```python
     plan = PLAN_CONFIG.get(plan_id)
     if not plan:
         raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id}")

     if not plan.get("purchasable", False):
         raise HTTPException(
             status_code=400,
             detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
         )
     ```

3. **Adapting Legacy Test Setup (`backend/test_subscription.py`)**:
   - In `test_free_user_can_use_both_models_within_limit`, the test previously attempted to turn a test user into a Model 1 subscriber by invoking `POST /api/verify-payment` with `jr_hacker_monthly`.
   - Because `jr_hacker_monthly` is a retired plan and no longer purchasable/activatable via checkout, this test was updated to seed the legacy subscriber directly in the database (`temp_db.create_subscription`), matching how grandfathered subscriber preservation is verified in `test_grandfathered_active_subscriber_preservation`.

---

## 3. Caveats

- **Grandfathered Subscribers Intact**: Pre-existing legacy subscriptions in SQLite continue to function and maintain active status with unhindered model access until their stored `expires_at` date. Only new order creation and new payment activations of retired plans are blocked.
- **Frontend Alignment**: The frontend UI already only offers `cyber_pro_monthly` and `cyber_pro_yearly`; this fix protects the exposed REST API against direct HTTP tampering.

---

## 4. Conclusion

The retired plan payment verification loophole is completely remediated across both route and service layers:
- Attempting to activate any non-purchasable or retired plan (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly`, `free`, `founder_unlimited`) via `/api/verify-payment` or `verify_and_activate()` returns HTTP 400 Bad Request.
- All 49 adversarial tests in `backend/test_adversarial_m2.py` pass with 100% success rate.
- All 16 subscription unit tests, all 18 subscriber integrity tests, and all 14 Requirement 2 E2E tests pass with zero regressions.

---

## 5. Verification Method

To independently verify this remediation:

```powershell
# 1. Verify Challenger M2-1 adversarial suite (all 49 tests must pass)
pytest backend/test_adversarial_m2.py -v

# 2. Verify subscription unit suite (all 16 tests must pass)
pytest backend/test_subscription.py -v

# 3. Verify Requirement 2 E2E specification suite (all 14 tests must pass)
pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v

# 4. Verify grandfathered subscriber lifecycle suite (all 18 tests must pass)
pytest backend/test_m2_2_challenger_subscribers.py -v
```

All 4 commands execute with code 0 and 0 failures.
