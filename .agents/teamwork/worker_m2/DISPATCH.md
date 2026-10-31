## Task Assignment: Worker M2 — Payment Plan Consolidation & Subscription Preservation

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\orchestrator\PROJECT.md`
- Survey report on payments: `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_2\handoff.md`
- E2E Test Suite: `c:\Users\sharo\Desktop\friday\TEST_READY.md` and `backend/test_e2e_requirements.py`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may modify:
- `backend/services/subscription.py`
- `backend/routes/subscription.py`
- `backend/test_subscription.py`
- `index.html` (pricing section, pricing modal, checkout review)

### Required Actions
1. **Consolidate Pricing in `backend/services/subscription.py`**:
   - Update `PLAN_CONFIG`:
     - Add `cyber_pro_monthly`: `label: "friday Cyber Pro — Monthly"`, `model_tier: "model2"`, `price_paise: 350000` (₹3,500/mo), `days: 30`, `daily_limit: None`, `purchasable: True`.
     - Add `cyber_pro_yearly`: `label: "friday Cyber Pro — Yearly"`, `model_tier: "model2"`, `price_paise: 3500000` (₹35,000/yr; 10 months = 2 months FREE / 17% discount), `days: 365`, `daily_limit: None`, `purchasable: True`.
     - Free and Founder plans: mark `purchasable: False`.
     - Legacy plans (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly`): Keep their definitions in `PLAN_CONFIG` so active subscriptions can resolve plan metadata, but set `purchasable: False`.
2. **Backend Route Updates in `backend/routes/subscription.py`**:
   - `list_plans()`: In `GET /api/subscription/plans`, filter out any plan where `not config.get("purchasable", False)`. Only `cyber_pro_monthly` and `cyber_pro_yearly` must be returned to the public.
   - `_handle_create_order()`: In `POST /api/create-order` and `POST /api/subscription/create-order`, check `if not PLAN_CONFIG.get(plan_id, {}).get("purchasable", False): raise HTTPException(400, "Plan retired or no longer offered for purchase")`.
   - Ensure `get_subscription_status()` smoothly returns active status and true expiration for users on legacy plans (`advanced_monthly`, etc.).
3. **Frontend Updates in `index.html`**:
   - Update pricing cards and checkout review:
     - Replace the multi-plan tabs in the pricing modal (`mobile-plan-tab-model1`, `mobile-plan-tab-model2`) with a single centered "friday Cyber Pro" card view.
     - Update `renderPricingCards()` to dynamically render the single "friday Cyber Pro" card from `/api/subscription/plans` with monthly (₹3,500) / yearly (₹35,000) rates and "Save 2 months (17%)" badge.
     - Update `openCheckoutReview()` and `startCheckout()` to display "friday Cyber Pro" at ₹3,500 or ₹35,000.
4. **Test Modernization & Verification**:
   - Update `backend/test_subscription.py`:
     - Verify `GET /api/subscription/plans` returns strictly `cyber_pro_monthly` and `cyber_pro_yearly`.
     - Verify `POST /api/create-order` creates orders for `cyber_pro_monthly` (350,000 paise) and `cyber_pro_yearly` (3,500,000 paise).
     - Verify `POST /api/create-order` rejects retired plans (`advanced_monthly`, `jr_hacker_monthly`) with HTTP 400.
     - Verify active grandfathered subscribers retain active status through their expiration date.
   - Run:
     `pytest backend/test_subscription.py -v`
     `pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v`
   - Ensure 100% of these tests pass.

### Deliverables
- Write `c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2\handoff.md` with:
  - Observation (files modified, pricing structure, verification commands & outputs)
  - Proof that active subscriptions in DB remain untouched and honored
  - Proof that old plans return HTTP 400 upon checkout
- Notify orchestrator when complete.


## 2026-10-30T13:38:59Z
You are teamwork_worker assigned as Worker M2 for Milestone 2 (Payment Plan Consolidation & Subscription Preservation).
Your working directory is: c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2\
Read your task instructions at: c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2\DISPATCH.md
MANDATORY: Read the original user request at: c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md before starting work!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement:
1. Update PLAN_CONFIG in backend/services/subscription.py to offer only cyber_pro_monthly (₹3,500 = 350,000 paise) and cyber_pro_yearly (₹35,000 = 3,500,000 paise; 10 months = 2 months free) with purchasable: True; mark legacy plans purchasable: False.
2. In backend/routes/subscription.py: list_plans() returns only purchasable plans; create_order rejects non-purchasable plans with HTTP 400; preserve legacy status resolution.
3. In index.html: update pricing cards grid and checkout review to single tier friday Cyber Pro (₹3,500/mo, ₹35,000/yr).
4. Update backend/test_subscription.py and run both pytest backend/test_subscription.py -v and pytest backend/test_e2e_requirements.py -k "Requirement2 or _r2_" -v to confirm 100% pass.
Write your handoff report to c:\Users\sharo\Desktop\friday\.agents\teamwork\worker_m2\handoff.md and notify the orchestrator.


## 2026-10-30T13:49:21Z
**Context**: Milestone 2 Payment Consolidation Status Check
**Content**: Checking on your progress across `backend/services/subscription.py`, `backend/routes/subscription.py`, `index.html`, and `test_subscription.py`.
**Action**: Please reply with your current step and estimated completion time.
