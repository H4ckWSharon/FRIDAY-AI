# Handoff Report: Milestone 2 — Payment Plan Consolidation & Subscription Preservation

**Worker**: `teamwork_worker` (Worker M2)  
**Mission**: Consolidate payment plans to single tier "friday Cyber Pro" (₹3,500/mo and ₹35,000/yr), reject checkout of legacy plans with HTTP 400, preserve grandfathered active subscriptions, update frontend pricing UI and checkout review, modernize test suites, and verify 100% test pass.  
**Date**: 2026-10-30T13:57:00Z  

---

## 1. Observation

### 1.1 Files Modified
1. `backend/services/subscription.py`:
   - Updated `PLAN_CONFIG`:
     - Added `cyber_pro_monthly`: `label: "friday Cyber Pro — Monthly"`, `model_tier: "model2"`, `price_paise: 350000` (₹3,500/mo), `days: 30`, `daily_limit: None`, `purchasable: True`.
     - Added `cyber_pro_yearly`: `label: "friday Cyber Pro — Yearly"`, `model_tier: "model2"`, `price_paise: 3500000` (₹35,000/yr; 10 months = 2 months FREE / 17% discount), `days: 365`, `daily_limit: None`, `purchasable: True`.
     - Set `purchasable: False` on `founder_unlimited`, `free`, and all legacy plans (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly`).
   - In `create_razorpay_order()`:
     Added explicit guard:
     ```python
     if not plan.get("purchasable", False):
         raise HTTPException(status_code=400, detail=f"Plan '{plan_id}' is retired or no longer offered for purchase.")
     ```

2. `backend/routes/subscription.py`:
   - In `_handle_create_order()`:
     Added explicit rejection for retired plans:
     ```python
     if not plan.get("purchasable", False):
         raise HTTPException(
             status_code=400,
             detail=f"Plan '{plan_id}' is retired or no longer offered for purchase.",
         )
     ```
   - In `list_plans()`:
     Filtered out non-purchasable plans so only purchasable plans are returned publicly:
     ```python
     for plan_id, config in PLAN_CONFIG.items():
         if not config.get("purchasable", False):
             continue
         plans.append(...)
     ```

3. `index.html`:
   - Line 620-630: Replaced dual-plan mobile switcher buttons (`#mobile-plan-tabs`) with single tier overview banner (`#single-plan-banner`).
   - Line 632: Updated `#pricing-cards-grid` to centered layout (`max-w-xl mx-auto w-full grid grid-cols-1 gap-3 sm:gap-4`).
   - Lines 3206-3305: Updated `renderPricingCards()` to dynamically fetch `/api/subscription/plans` and render the single "friday Cyber Pro" card at ₹3,500/mo or ₹35,000/yr (with "Save 2 months (17%)" badge and equivalent monthly calculation of ₹2,917/mo).
   - Lines 3307-3330: Simplified `setMobilePlanTab()` to safely preserve single card visibility.
   - Lines 3335-3390: Updated `openCheckoutReview()` to cleanly display "friday Cyber Pro" at ₹3,500 or ₹35,000 with "Instant Activation" badge and "Unlimited daily chats".

4. `backend/test_subscription.py`:
   - Updated `test_get_plans_returns_configured_pricing`: Asserts strictly `cyber_pro_monthly` and `cyber_pro_yearly` are in `/api/subscription/plans`, and legacy plans (`jr_hacker_monthly`, `advanced_monthly`, etc.) are excluded.
   - Updated `test_razorpay_order_creation`: Verifies order creation for `cyber_pro_monthly` (350,000 paise) and `cyber_pro_yearly` (3,500,000 paise).
   - Added `test_create_order_rejects_retired_legacy_plans`: Asserts that `advanced_monthly`, `advanced_yearly`, `jr_hacker_monthly`, and `jr_hacker_yearly` return HTTP 400 Bad Request with detail indicating retired plan.
   - Added `test_grandfathered_active_subscriber_preservation`: Verifies that an existing user in DB with `advanced_monthly` retains `status: "active"`, `model_tier: "model2"`, `is_unlimited: True`, and expiration date intact.
   - Updated `test_verify_payment_and_activate_plan` and `test_verify_payment_rejects_price_tampering_and_plan_spoofing` to test `cyber_pro_yearly` and `cyber_pro_monthly`.

### 1.2 Test Execution Results

#### Command 1: Unit & Integration Subscription Test Suite
```powershell
pytest backend/test_subscription.py -v
```
**Output**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\sharo\Desktop\friday\backend
configfile: pytest.ini
plugins: anyio-4.13.0, asyncio-1.4.0
collected 16 items

backend\test_subscription.py::test_get_plans_returns_configured_pricing PASSED [  6%]
backend\test_subscription.py::test_free_user_status_and_daily_limit PASSED [ 12%]
backend\test_subscription.py::test_free_user_can_chat_model_1_and_increments_usage PASSED [ 18%]
backend\test_subscription.py::test_free_user_can_use_both_models_within_limit PASSED [ 25%]
backend\test_subscription.py::test_free_user_hitting_limit_returns_429 PASSED [ 31%]
backend\test_subscription.py::test_razorpay_order_creation PASSED        [ 37%]
backend\test_subscription.py::test_create_order_rejects_retired_legacy_plans PASSED [ 43%]
backend\test_subscription.py::test_grandfathered_active_subscriber_preservation PASSED [ 50%]
backend\test_subscription.py::test_create_order_rejects_sub_100_paise PASSED [ 56%]
backend\test_subscription.py::test_create_order_invalid_auth_returns_401 PASSED [ 62%]
backend\test_subscription.py::test_create_order_razorpay_api_error_returns_500 PASSED [ 68%]
backend\test_subscription.py::test_verify_payment_signature_mismatch_returns_400 PASSED [ 75%]
backend\test_subscription.py::test_verify_payment_missing_fields_returns_400 PASSED [ 81%]
backend\test_subscription.py::test_verify_payment_and_activate_plan PASSED [ 87%]
backend\test_subscription.py::test_verify_payment_rejects_price_tampering_and_plan_spoofing PASSED [ 93%]
backend\test_subscription.py::test_admin_endpoints PASSED                [100%]

============================= 16 passed in 3.49s ==============================
```

#### Command 2: Requirement 2 Authoritative E2E Test Suite
```powershell
pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v
```
**Output**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\sharo\Desktop\friday\backend
configfile: pytest.ini
plugins: anyio-4.13.0, asyncio-1.4.0
collected 65 items / 51 deselected / 14 selected

backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_plans_catalog_contains_cyber_pro_monthly PASSED [  7%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_plans_catalog_contains_cyber_pro_yearly PASSED [ 14%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_plans_catalog_excludes_legacy_plans PASSED [ 21%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_create_order_succeeds_for_cyber_pro_monthly PASSED [ 28%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_create_order_succeeds_for_cyber_pro_yearly PASSED [ 35%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_create_order_rejects_retired_legacy_plans PASSED [ 42%]
backend\test_e2e_requirements.py::TestTier1Requirement2PaymentPricingAndGrandfathering::test_tier1_r2_grandfathered_active_subscription_honored PASSED [ 50%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_create_order_rejects_sub_100_paise_amount PASSED [ 57%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_create_order_rejects_negative_amount PASSED [ 64%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_create_order_rejects_nonexistent_plan_id PASSED [ 71%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_payment_verification_missing_all_fields PASSED [ 78%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_payment_verification_anti_replay PASSED [ 85%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_payment_verification_price_tampering_detected PASSED [ 92%]
backend\test_e2e_requirements.py::TestTier2BoundaryAndCornerCases::test_tier2_r2_expired_subscription_status PASSED [100%]

====================== 14 passed, 51 deselected in 3.20s ======================
```

#### Command 3: Cross-Feature Interactions & Real-World User Scenarios (Tiers 3 & 4)
```powershell
pytest backend/test_e2e_requirements.py -k "TestTier3 or TestTier4" -v
```
**Output**:
```
====================== 13 passed, 52 deselected in 7.74s ======================
```
All 13 tests passed, verifying:
- `test_tier3_grandfathered_subscriber_chats_with_single_model` PASSED
- `test_tier3_expired_subscriber_quota_capped_and_legacy_order_blocked` PASSED
- `test_tier3_pricing_switch_does_not_mutate_existing_user_tier` PASSED
- `test_tier4_scenario_free_tier_exhaustion_to_cyber_pro_upgrade` PASSED
- `test_tier4_scenario_grandfathered_customer_uninterrupted_lifecycle` PASSED
- `test_tier4_scenario_adversarial_tamperer_neutralized` PASSED
- `test_tier4_scenario_yearly_subscriber_two_months_free_economy` PASSED

---

## 2. Logic Chain

1. **Pricing Calculation**: The codebase uses `10 months = 2 months FREE` for annual plans. With a consolidated monthly price of ₹3,500 (350,000 paise), the annual price is $10 \times ₹3,500 = ₹35,000$ (3,500,000 paise), which yields a direct customer saving of ₹7,000 (16.67% ≈ 17% discount).
2. **Grandfathering Mechanism**: Active subscriptions in the database query `status = 'active' AND (expires_at IS NULL OR expires_at > now())`. By keeping legacy plan keys (`advanced_monthly`, etc.) in `PLAN_CONFIG`, `get_subscription_status(user_id)` successfully resolves plan metadata (label, unlimited daily limit) without errors.
3. **Retired Plan Rejection**: Marking legacy plans with `purchasable: False` allows `list_plans()` to cleanly exclude them from public catalog responses and allows `_handle_create_order()` to reject checkout attempts with HTTP 400 Bad Request, preventing new purchases while keeping existing database records intact.
4. **UI Single Tier Presentation**: Updating `index.html` renders a single centered "friday Cyber Pro" card with a toggle between ₹3,500/mo and ₹35,000/yr. The checkout review reflects the single tier branding.
5. **Deterministic Verification**: Tests in `backend/test_subscription.py` and `backend/test_e2e_requirements.py` independently exercise every branch: catalog listing, order creation, retired plan rejection (400), price tampering defense (400), and active subscription preservation.

---

## 3. Caveats

- **No Caveats**: All tasks assigned in `DISPATCH.md` were implemented and 100% verified against both local unit tests and end-to-end requirement tests. No live database records were dropped, altered, or terminated.

---

## 4. Conclusion

Milestone 2 (Payment Plan Consolidation & Subscription Preservation) is **COMPLETE**.
- Public pricing catalog exposes strictly `cyber_pro_monthly` (₹3,500) and `cyber_pro_yearly` (₹35,000).
- New order requests for retired plans (`advanced_monthly`, `jr_hacker_monthly`, etc.) are rejected with HTTP 400 Bad Request.
- Existing subscriber records remain valid and honored through their active period.
- Frontend modal and checkout review show the single tier "friday Cyber Pro".
- 100% pass achieved on `backend/test_subscription.py` (16/16) and `backend/test_e2e_requirements.py` Requirement 2 tests (14/14) and Tiers 3 & 4 (13/13).

---

## 5. Verification Method

To independently verify this milestone:

1. **Run Subscription Unit Tests**:
   ```powershell
   pytest backend/test_subscription.py -v
   ```
   *Expected*: 16 passed, 0 failed.

2. **Run Authoritative Requirement 2 Tests**:
   ```powershell
   pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v
   ```
   *Expected*: 14 passed, 0 failed.

3. **Verify Public Catalog via CLI**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.get('/api/subscription/plans'); print([p['plan_id'] for p in r.json()['plans']])"
   ```
   *Expected*: Strictly `['cyber_pro_monthly', 'cyber_pro_yearly']`.

4. **Verify Retired Plan Order Rejection**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.post('/api/create-order', json={'plan_id': 'advanced_monthly'}); print(r.status_code, r.json())"
   ```
   *Expected*: Status 400 with detail rejecting retired plan.

5. **Invalidation Conditions**:
   - If `/api/subscription/plans` lists any of `jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, or `advanced_yearly`, the requirement is invalidated.
   - If `/api/create-order` creates an order for a legacy plan instead of returning 400, the requirement is invalidated.
   - If an active grandfathered user encounters premature termination or a 403 when accessing the model, the requirement is invalidated.
