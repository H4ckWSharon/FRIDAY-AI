# Adversarial Challenge Report: Milestone 2 — Pricing & Order Tampering Challenger

**Agent**: Challenger M2-1 (`teamwork_challenger`)  
**Verdict**: **`REQUEST_CHANGES`**  
**Timestamp**: 2026-10-30T14:10:00Z  

---

## 1. Observation

### 1.1 Test Suite & Tool Commands Executed
Created and executed an empirical stress harness at `backend/test_adversarial_m2.py` (49 tests):
```powershell
pytest backend/test_adversarial_m2.py -v
```

#### Results Summary:
- **45 PASSED**, **4 FAILED**.
- Successful Defenses Verified:
  1. **Retired Plan Order Creation Rejection (HTTP 400)**:
     - `test_adv_create_order_rejects_retired_plans_at_primary_endpoint`: Rejected `advanced_monthly`, `advanced_yearly`, `jr_hacker_monthly`, `jr_hacker_yearly`, `founder_unlimited`, and `free` with HTTP 400.
     - `test_adv_create_order_rejects_retired_plans_at_subscription_endpoint`: Rejected all 6 plans with HTTP 400.
     - `test_adv_direct_service_rejects_retired_plans`: `create_razorpay_order()` raises HTTP 400 for all retired plans.
  2. **Price Tampering Defenses on Order Creation**:
     - `test_adv_create_order_overrides_client_supplied_tampered_price`: Sending `{"plan_id": "cyber_pro_monthly", "amount": 100}` safely forces server-side `amount = 350000` (₹3,500).
     - `test_adv_create_order_yearly_overrides_tampered_zero_price`: Sending `{"plan_id": "cyber_pro_yearly", "amount": -1000}` safely forces server-side `amount = 3500000` (₹35,000).
  3. **Price Tampering Defenses on Payment Verification**:
     - `test_adv_verify_payment_rejects_sub_plan_price`: Paying 100 paise (₹1) for `cyber_pro_monthly` rejected with HTTP 400: `"Payment validation failed. Paid amount does not match required plan price."`
     - `test_adv_verify_payment_rejects_one_paise_underpayment`: Paying 349,999 paise rejected with HTTP 400.
     - `test_adv_verify_payment_rejects_plan_tier_escalation`: Paying 350,000 paise and attempting to claim `cyber_pro_yearly` rejected with HTTP 400.
     - `test_adv_verify_payment_rejects_plan_spoofing_even_if_amount_matches`: Tampered order notes detected and rejected with HTTP 400: `"Plan mismatch"`.
  4. **Fuzzing, Malicious Payloads & Boundary Inputs**:
     - `test_adv_create_order_rejects_fuzzed_plan_ids`: Rejected directory traversal (`"../"`, `"../../etc/passwd"`), SQL injection (`"' OR 1=1 --"`, `"'; DROP TABLE subscriptions; --"`), XSS (`"<script>alert('xss')</script>"`), case confusion (`"CYBER_PRO_MONTHLY"`), trailing/leading spaces, null bytes (`"cyber_pro_monthly\x00"`), and 4096-character buffer strings with HTTP 400.
     - `test_adv_create_order_rejects_invalid_raw_amounts`: Rejected amounts `-10000`, `-1`, `0`, `1`, `99` with HTTP 400.
     - `test_adv_create_order_empty_payload_rejected`: Rejected `{}` with HTTP 400.
  5. **Anti-Replay & Signature Security**:
     - `test_adv_anti_replay_prevents_duplicate_activation`: Replaying a redeemed order returns HTTP 409 Conflict.
     - `test_adv_tampered_signature_rejected`: Single-bit flipped signature returns HTTP 400.
  6. **Grandfathered Customer Access Preservation**:
     - `test_adv_grandfathered_active_subscriber_unaffected_by_new_pricing`: User with pre-existing `advanced_monthly` retains `model2` unlimited access and expiration date.
     - `test_adv_expired_legacy_subscriber_cannot_renew_retired_plan`: Expired legacy user blocked from re-purchasing retired plans with HTTP 400.

### 1.2 Observed Failure: Retired Plan Activation Loophole in `/api/verify-payment`
When running `test_adv_verify_payment_must_reject_retired_plans`:
```powershell
pytest backend/test_adversarial_m2.py -k "test_adv_verify_payment_must_reject_retired_plans" -v
```
**Output**:
```
FAILED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[jr_hacker_monthly-249900]
FAILED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[jr_hacker_yearly-2499000]
FAILED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[advanced_monthly-499900]
FAILED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[advanced_yearly-4999000]
PASSED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[founder_unlimited-0]
PASSED backend\test_adversarial_m2.py::test_adv_verify_payment_must_reject_retired_plans[free-0]
```
Verbatim failure:
```
AssertionError: Security Flaw: /api/verify-payment accepted retired plan 'jr_hacker_monthly' and returned status 200 instead of 400!
assert 200 == 400
 +  where 200 = <Response [200 OK]>.status_code
```

### 1.3 Exact Code Inspection
In `backend/routes/subscription.py` (lines 170–176):
```python
    sub_record = None
    plan_id = body.plan_id
    if plan_id and plan_id in PLAN_CONFIG:
        plan = PLAN_CONFIG[plan_id]
        if plan_id in ("free", "founder_unlimited"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot activate tier '{plan_id}' via standard payment verification.",
            )
```
And in `backend/services/subscription.py` (lines 464–471):
```python
    plan = PLAN_CONFIG.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id}")

    expires_at = None
    if plan["days"]:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()
```
Notice:
While `_handle_create_order()` in `backend/routes/subscription.py` has:
```python
    if not plan.get("purchasable", False):
        raise HTTPException(
            status_code=400,
            detail=f"Plan '{plan_id}' is retired or no longer offered for purchase.",
        )
```
Neither `_handle_verify_payment()` nor `verify_and_activate()` check `if not plan.get("purchasable", False)`.

---

## 2. Logic Chain

1. **Vulnerability Scenario**:
   - `POST /api/create-order` supports custom amounts without requiring `plan_id` (e.g. `{"amount": 249900}`).
   - An attacker creates a Razorpay order for ₹2,499 (249,900 paise, the retired Jr Hacker rate) without specifying `plan_id`. The order is created on Razorpay with no `plan_id` in `notes`.
   - The attacker completes payment via Razorpay for ₹2,499.
   - The attacker calls `POST /api/verify-payment` providing `plan_id: "jr_hacker_monthly"` along with the valid Razorpay order, payment ID, and HMAC signature.
2. **Execution Flow in Handler**:
   - Signature check passes because Razorpay generated the signature for the ₹2,499 payment.
   - Anti-replay check passes on first submission.
   - `plan_id` is in `PLAN_CONFIG`.
   - `plan_id in ("free", "founder_unlimited")` evaluates to `False`.
   - `fetch_razorpay_order` verifies order amount (249,900 paise) >= plan required price (249,900 paise) -> Passes.
   - `order_plan` in notes is `None` -> Plan spoofing check does not trigger.
   - **Crucial gap**: Because `not plan.get("purchasable", False)` is never evaluated, the server proceeds to call `create_subscription(user_id=user_id, plan_id="jr_hacker_monthly", model_tier="model1", ...)`.
   - The user receives an active 30-day `model1` subscription for ₹2,499.
3. **Requirement Violation**:
   - `ORIGINAL_REQUEST.md` R2 states: *"Remove all older payment plans from being offered for purchase and offer only the new single tier updated to 3,500 monthly... Backend payment routes process new subscriptions and checkouts exclusively under the updated pricing."*
   - Activating a retired tier at legacy pricing violates R2 and the single consolidated tier policy.

---

## 3. Caveats

- **No Caveats**: This vulnerability was empirically demonstrated and reproduced directly against the live FastAPI test client.
- Note: An attacker cannot purchase legacy tiers via the frontend UI because `index.html` only requests `cyber_pro_monthly` and `cyber_pro_yearly`. However, the backend API is publicly exposed and vulnerable to direct HTTP automation.

---

## 4. Conclusion

**Verdict**: **`REQUEST_CHANGES`**

While order creation, pricing overrides, fuzzing defenses, and anti-replay protections are implemented effectively, there is a defense-in-depth vulnerability in the payment verification pipeline:
- `POST /api/verify-payment` allows activating retired plans (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly`) when an un-tagged custom amount order matches the legacy price.
- Worker M2 must patch this gap by enforcing `purchasable: True` during payment verification.

### Actionable Remediation Required:
1. In `backend/routes/subscription.py` inside `_handle_verify_payment()` (replace lines 172–176):
   ```python
   if not plan.get("purchasable", False):
       raise HTTPException(
           status_code=400,
           detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
       )
   ```
2. In `backend/services/subscription.py` inside `verify_and_activate()`:
   ```python
   if not plan.get("purchasable", False):
       raise HTTPException(
           status_code=400,
           detail=f"Cannot activate plan '{plan_id}': plan is retired or not purchasable.",
       )
   ```
3. Once applied, all 49 tests in `backend/test_adversarial_m2.py` will pass 100%.

---

## 5. Verification Method

To independently reproduce this finding:
```powershell
pytest backend/test_adversarial_m2.py -k "test_adv_verify_payment_must_reject_retired_plans" -v
```
- **Observed**: 4 failures (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly` return HTTP 200 instead of 400).
- **Target Invalidation Condition**: Once Worker M2 adds the `purchasable` check to `_handle_verify_payment()`, the command will exit with code 0 (6 passed).
- **Full Suite Run**:
  ```powershell
  pytest backend/test_adversarial_m2.py -v
  ```
