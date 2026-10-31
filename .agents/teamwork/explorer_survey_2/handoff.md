# Handoff Report: Payment Plans, Pricing Structure & Active Subscriptions Survey

**Agent**: Survey Explorer 2 (`teamwork_explorer`)  
**Mission**: Investigate payment processor integration, current pricing tiers, discount calculation logic, database subscription schema, grandfathering active subscribers, single-tier consolidation to ₹3,500/month, and test suites.  
**Target Requirement**: R2 (Payment Plan Consolidation and Existing Subscriber Preservation)  
**Date**: 2026-10-29T20:20:00Z  

---

## 1. Observation

### 1.1 Payment Processor Integration
- **Processor**: **Razorpay Standard Web Checkout**. No Stripe, PayPal, or mock processors are used in production.
- **Backend SDK**: `razorpay>=2.0.0` declared in `backend/requirements.txt:10` and imported in `backend/services/subscription.py:28`.
- **Frontend SDK**: `<script src="https://checkout.razorpay.com/v1/checkout.js"></script>` loaded at `index.html:14`.
- **Environment & Credentials**:
  - `backend/config.py:80-83`:
    ```python
    # Razorpay Payment Gateway
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    ```
  - `backend/.env:40-43`:
    ```env
    RAZORPAY_KEY_ID=rzp_live_TnRXC2ZhmFMSI9
    RAZORPAY_KEY_SECRET=4nIx56u7zKxy499GwkN7Ol6y
    RAZORPAY_WEBHOOK_SECRET=friday_sec_9f82d1a4
    ```

### 1.2 Current Payment Plans and Tiers Definition
- **Backend Service (`backend/services/subscription.py:83-172`)**:
  - `founder_unlimited`: 0 paise, model_tier: `"model2"`, days: `None`, daily_limit: `None`
  - `free`: 0 paise, model_tier: `"free"`, days: `None`, daily_limit: `5`
  - `jr_hacker_monthly`: 249,900 paise (₹2,499), model_tier: `"model1"`, days: `30`, daily_limit: `50`
  - `jr_hacker_yearly`: 2,499,000 paise (₹24,990), model_tier: `"model1"`, days: `365`, daily_limit: `50`
  - `advanced_monthly`: 499,900 paise (₹4,999), model_tier: `"model2"`, days: `30`, daily_limit: `None`
  - `advanced_yearly`: 4,999,000 paise (₹49,990), model_tier: `"model2"`, days: `365`, daily_limit: `None`
- **Backend Endpoints (`backend/routes/subscription.py`)**:
  - `POST /api/create-order` & `POST /api/subscription/create-order` (lines 59-121): Validates `plan_id in PLAN_CONFIG`, derives exact server-side price in paise, calls Razorpay `client.order.create(...)`.
  - `POST /api/verify-payment` & `POST /api/subscription/verify` (lines 125-222): Verifies HMAC-SHA256 signature (`order_id + "|" + payment_id` with `razorpay_key_secret`), anti-replay check, verifies order amount via Razorpay API `fetch_razorpay_order`, activates subscription.
  - `GET /api/subscription/plans` (lines 281-300): Iterates over `PLAN_CONFIG` (excluding `"free"`) and returns plan details (`plan_id`, `label`, `model_tier`, `price_paise`, `price_inr`, `days`, `daily_limit`, `is_yearly`, `features`).
  - `GET /api/subscription/status` (lines 274-279): Returns user's active tier, remaining daily chats, and expiry.
  - `POST /api/subscription/webhook` & `POST /api/webhook` (lines 304-324): Asynchronous webhook listener.
- **Frontend UI (`index.html`)**:
  - Lines 600-611: Monthly / Yearly toggle (`#billing-toggle`), with label "Save 17%".
  - Lines 613-621: Mobile plan tabs:
    ```html
    <button id="mobile-plan-tab-model1">Starter Pro (₹2,499)</button>
    <button id="mobile-plan-tab-model2">★ Advanced (₹4,999)</button>
    ```
  - Line 624: Grid `#pricing-cards-grid` dynamically populated by `renderPricingCards()`.
  - Lines 680-785: Checkout modal view showing selected plan card, payment method selector (UPI, Cards, NetBanking), and Razorpay PCI-DSS security badges.
  - Lines 3083-3088:
    ```javascript
    const PLAN_LABELS = {
      jr_hacker_monthly:  { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
      jr_hacker_yearly:   { name: 'Jr Hacker',          tier: 1, badge: 'model1' },
      advanced_monthly:   { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
      advanced_yearly:    { name: 'Advanced Pentester', tier: 2, badge: 'model2' },
    };
    ```
  - Lines 3226-3324: `renderPricingCards()` fetches `${BACKEND_URL_SUB}/api/subscription/plans`, filters `is_yearly === billingYearly`, and generates cards for `pricing-card-adv` and `pricing-card-jr`.
  - Lines 3328-3367: `setMobilePlanTab(tier)` controls tab switching between `model1` and `model2`.
  - Lines 3369-3426: `openCheckoutReview(planId)` formats price in INR and updates checkout button `Pay ₹${priceINR} with Razorpay`.
  - Lines 3455-3544: `startCheckout(planId)` calls `/api/create-order`, opens `new Razorpay(options)`, and handles payment return with `handlePaymentSuccess` -> `/api/verify-payment`.
- **Admin UI & Endpoints (`admin.html` and `backend/routes/admin.py`)**:
  - `admin.html:1139-1146`: Plan grant modal dropdown (`advanced_monthly`, `advanced_yearly`, `jr_hacker_monthly`, `jr_hacker_yearly`, `founder_unlimited`, `free`).
  - `admin.html:1408-1413`: User table plan badge rendering (`.plan-founder`, `.plan-adv`, `.plan-jr`, `.plan-free`).
  - `backend/routes/admin.py:275-337`: `POST /api/admin/grant-subscription` and `POST /api/admin/revoke-subscription`.

### 1.3 Discount Logic in Codebase
- Direct verbatim comments in `backend/services/subscription.py`:
  - Line 127: `"price_paise": 2499000,  # ₹24,990 in paise (10 months = 2 months FREE)`
  - Line 136: `"Save 2 months (₹24,990/yr)"`
  - Line 158: `"price_paise": 4999000,  # ₹49,990 in paise (10 months = 2 months FREE)`
  - Line 169: `"Save 2 months (₹49,990/yr)"`
- Arithmetic:
  - Monthly ₹2,499 * 10 = ₹24,990 (equivalent to paying for 10 months and getting 2 months free out of 12).
  - Monthly ₹4,999 * 10 = ₹49,990 (equivalent to paying for 10 months and getting 2 months free out of 12).
  - Discount percentage: 2 / 12 = 16.666...% ≈ 16.7% (rendered as `Save 17%` at `index.html:608`).
  - Effective monthly calculation rendered at `index.html:3276`: `Math.round((plan.price_paise / 100) / 12)`.

### 1.4 Subscription Database Schema & Query Verification
- **Dual Persistence Architecture**: PostgreSQL (Supabase) via connection pooler (`backend/.env:35`) and SQLite (`backend/friday.db`).
- **Table Definition (`backend/services/db.py:229-245` & `334-350`)**:
  ```sql
  CREATE TABLE IF NOT EXISTS subscriptions (
      id                  TEXT PRIMARY KEY,
      user_id             TEXT NOT NULL,
      plan_id             TEXT NOT NULL,
      status              TEXT NOT NULL DEFAULT 'active',
      model_tier          TEXT NOT NULL DEFAULT 'free',
      razorpay_order_id   TEXT,
      razorpay_payment_id TEXT,
      razorpay_sub_id     TEXT,
      starts_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      expires_at          TIMESTAMPTZ,
      created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
  CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
  ```
- **Active Subscription Query (`backend/services/db.py:769-779`)**:
  ```python
  def get_active_subscription(user_id: str) -> Optional[dict]:
      with get_db() as conn:
          row = conn.execute(
              """SELECT * FROM subscriptions
                 WHERE user_id = ? AND status = 'active'
                 AND (expires_at IS NULL OR expires_at > ?)
                 ORDER BY created_at DESC LIMIT 1""",
              (user_id, _now()),
          ).fetchone()
      return dict(row) if row else None
  ```
- **Anti-Replay Mechanism (`backend/services/db.py:833-869`)**:
  `is_order_or_payment_redeemed(...)` checks if `razorpay_order_id` or `razorpay_payment_id` has already been recorded in `subscriptions`.

### 1.5 Live Database Status (Supabase PostgreSQL Query Output)
Executed live database query:
`python -c "from backend.config import get_settings; import psycopg2; s = get_settings(); conn = psycopg2.connect(s.database_url); cur = conn.cursor(); ..."`
- Total registered users: **231**
- Total subscription records: **4**
  1. `sub_f616fedf96864d53`: User `ih5zm1zzusd3gwZLF69fYKWA14d2` (`sharonanil555@gmail.com`), `founder_unlimited`, `active`, `model_tier: "model2"`, `expires_at: NULL` (Permanent VIP Founder).
  2. `sub_e71fb5599d4a4c7c`: User `FxxeUBnWlBM7emQYUEZDq6saxzn2`, `advanced_monthly`, `cancelled`.
  3. `sub_c229120329b74fbf`: User `FxxeUBnWlBM7emQYUEZDq6saxzn2`, `advanced_monthly`, `active`, `model_tier: "model2"`, `expires_at: 2026-11-11 20:18:01 UTC`.
  4. `sub_bcc96daa71a04cb3`: User `Bqn7wmPCJpNQYZUz9qhcJjvCSq52`, `advanced_monthly`, `active`, `model_tier: "model2"`, `expires_at: 2026-11-19 18:13:17 UTC`.

### 1.6 Existing Automated Test Suite
- Test file: `backend/test_subscription.py` (554 lines).
- Executed `pytest backend/test_subscription.py`:
  Result: **14 passed in 11.07s** (100% pass rate).
- Tests cover:
  - `test_get_plans_returns_configured_pricing`
  - `test_free_user_status_and_daily_limit`
  - `test_free_user_can_chat_model_1_and_increments_usage`
  - `test_free_user_can_use_both_models_within_limit`
  - `test_free_user_hitting_limit_returns_429`
  - `test_razorpay_order_creation`
  - `test_create_order_rejects_sub_100_paise`
  - `test_create_order_invalid_auth_returns_401`
  - `test_create_order_razorpay_api_error_returns_500`
  - `test_verify_payment_signature_mismatch_returns_400`
  - `test_verify_payment_missing_fields_returns_400`
  - `test_verify_payment_and_activate_plan`
  - `test_verify_payment_rejects_price_tampering_and_plan_spoofing`
  - `test_admin_endpoints`

---

## 2. Logic Chain

### 2.1 Pricing Calculation for the Consolidated Single Tier
1. **Observation 1.3** establishes that the codebase calculates yearly pricing using the explicit rule: `10 months = 2 months FREE` (`Yearly = Monthly * 10`).
2. The user requirement mandates updating to a single tier at **₹3,500 monthly**.
3. Applying the established formula:
   $$\text{Yearly Price} = ₹3,500 \times 10 = ₹35,000$$
4. In Razorpay paise (where ₹1 = 100 paise):
   - Monthly: $3,500 \times 100 = 350,000\text{ paise}$ (`price_paise: 350000`)
   - Yearly: $35,000 \times 100 = 3,500,000\text{ paise}$ (`price_paise: 3500000`)
5. Direct customer savings:
   - Full 12-month value: $12 \times ₹3,500 = ₹42,000$.
   - Annual plan price: $₹35,000$.
   - Annual savings: $₹42,000 - ₹35,000 = ₹7,000$ (exactly 2 free months, or $\frac{7,000}{42,000} = 16.67\% \approx 17\%$).
   - Effective monthly rate under yearly billing: $\frac{₹35,000}{12} = ₹2,916.67 \approx ₹2,917/\text{mo}$.

### 2.2 Preservation of Existing Active Subscribers (Grandfathering)
1. **Observation 1.5** demonstrates that real customer subscriptions exist in Supabase (`FxxeUBnWlBM7emQYUEZDq6saxzn2` expiring 2026-11-11 and `Bqn7wmPCJpNQYZUz9qhcJjvCSq52` expiring 2026-11-19). Both have `plan_id: "advanced_monthly"`, `status: "active"`, and `model_tier: "model2"`.
2. **Observation 1.4** shows that access validation is driven by:
   ```sql
   WHERE user_id = ? AND status = 'active' AND (expires_at IS NULL OR expires_at > ?)
   ```
3. Therefore, as long as:
   - The database records are not altered, cancelled, or overwritten.
   - `PLAN_CONFIG` continues to recognize `advanced_monthly` (for metadata lookups in `get_subscription_status`).
   - The AI chat gate in `chat.py` treats `model_tier: "model2"` (or active paid subscriptions) as authorized for the single consolidated model `orcasaq-cyber-27b:latest` ("friday Cyber Pro").
4. Under these conditions, existing subscribers will retain uninterrupted, unlimited access until their respective expiration dates in mid-November 2026. On their expiration timestamp, `expires_at > now()` will naturally evaluate to `False`, smoothly transitioning them to the free tier (5 chats/day) without errors.

### 2.3 Segregation Between Purchase Offerings and Grandfathered Registry
1. **Observation 1.2** shows that `GET /api/subscription/plans` iterates over `PLAN_CONFIG` and returns all non-free plans. If older plans are left in `PLAN_CONFIG` as currently structured, they will be served to the frontend and available for checkout.
2. Conversely, if older plans are deleted from `PLAN_CONFIG`, `get_subscription_status(user_id)` line 244 (`plan = PLAN_CONFIG.get(sub["plan_id"], {})`) will fail to find plan metadata, breaking the UI badge and status responses for existing customers.
3. Logical resolution:
   - Introduce an explicit flag `purchasable: bool` (or `is_offered: bool`) in `PLAN_CONFIG`.
   - New single tier (`cyber_pro_monthly` and `cyber_pro_yearly`) is marked `purchasable: True`.
   - Older plans (`jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, `advanced_yearly`) are marked `purchasable: False`.
   - `list_plans()` in `backend/routes/subscription.py` filters `if not config.get("purchasable", False): continue`.
   - `_handle_create_order` checks `if not PLAN_CONFIG.get(plan_id, {}).get("purchasable", False): raise HTTPException(400, "Plan retired")`.
   - This cleanly removes old tiers from purchase offerings while preserving full metadata for existing subscribers.

---

## 3. Caveats

1. **Model Access Gate Coupling**: Under Requirement R1, the two older models (`Dolphin3-Cyber-8B-GGUF` and `baronllm-abliterated`) are removed from Ollama. In `backend/routes/chat.py`, existing access gating checks `if _tier == "model1": if _requested_model == MODEL_2_ID: raise 403`. Because Dolphin is removed, any user on `model1` (if any existed) must be allowed to chat with the single available model ("friday Cyber Pro") without hitting a 403 or missing model error. In our live database audit, all active customers are on `model2` (`advanced_monthly`), so no active customer has `model1`.
2. **Payment Webhook Handling**: `POST /api/subscription/webhook` verifies signatures but currently only logs incoming events (`lines 322-323`). Order activation occurs synchronously via client POST to `/api/verify-payment`. The single-tier migration does not disrupt webhooks.
3. **Database Migration Requirement**: No database schema migration or table alteration is necessary. The existing schema (`subscriptions`) fully supports any `plan_id` and `model_tier`.

---

## 4. Conclusion

### 4.1 Recommended New Plan Structure
Add to `PLAN_CONFIG` in `backend/services/subscription.py`:

```python
PLAN_CONFIG: dict[str, dict] = {
    # ─── Active Purchase Offering: Single Consolidated Tier ───
    "cyber_pro_monthly": {
        "label": "friday Cyber Pro — Monthly",
        "model_tier": "model2",
        "price_paise": 350000,      # ₹3,500/mo in paise
        "days": 30,
        "daily_limit": None,        # Unlimited chats
        "purchasable": True,
        "features": [
            "Unlimited chats — zero daily throttling",
            "friday Cyber Pro (27B neural offensive intelligence)",
            "Deep pentesting, exploit dev & red-team execution",
            "Uncensored security intelligence",
            "Priority neural engine inference",
            "Instant activation via UPI, Cards & NetBanking",
        ],
    },
    "cyber_pro_yearly": {
        "label": "friday Cyber Pro — Yearly",
        "model_tier": "model2",
        "price_paise": 3500000,     # ₹35,000/yr in paise (10 months = 2 months FREE)
        "days": 365,
        "daily_limit": None,        # Unlimited chats
        "purchasable": True,
        "features": [
            "Unlimited chats — zero daily throttling",
            "friday Cyber Pro (27B neural offensive intelligence)",
            "Deep pentesting, exploit dev & red-team execution",
            "Uncensored security intelligence",
            "Priority neural engine inference",
            "Save 2 months (₹7,000 discount / ₹35,000/yr)",
            "Instant activation via UPI, Cards & NetBanking",
        ],
    },

    # ─── Free & Founder Tiers ─────────────────────────────────
    "founder_unlimited": {
        "label": "Founder / Admin (Lifetime VIP)",
        "model_tier": "model2",
        "price_paise": 0,
        "days": None,
        "daily_limit": None,
        "purchasable": False,
        "features": [
            "Permanent Founder & Admin Access",
            "friday Cyber Pro unlocked",
            "Unlimited chats — zero throttling",
            "Full developer & testing privileges",
        ],
    },
    "free": {
        "label": "Free",
        "model_tier": "free",
        "price_paise": 0,
        "days": None,
        "daily_limit": FREE_DAILY_LIMIT,
        "purchasable": False,
        "features": [
            "5 chats per day",
            "friday Cyber Pro preview",
            "Standard response speed",
        ],
    },

    # ─── Grandfathered Legacy Tiers (Non-Purchasable) ─────────
    "jr_hacker_monthly": {
        "label": "Jr Hacker — Monthly (Legacy)",
        "model_tier": "model1",
        "price_paise": 249900,
        "days": 30,
        "daily_limit": 50,
        "purchasable": False,
        "features": ["Legacy 50 chats/day plan"],
    },
    "jr_hacker_yearly": {
        "label": "Jr Hacker — Yearly (Legacy)",
        "model_tier": "model1",
        "price_paise": 2499000,
        "days": 365,
        "daily_limit": 50,
        "purchasable": False,
        "features": ["Legacy 50 chats/day plan"],
    },
    "advanced_monthly": {
        "label": "Advanced Pentester — Monthly (Legacy)",
        "model_tier": "model2",
        "price_paise": 499900,
        "days": 30,
        "daily_limit": None,
        "purchasable": False,
        "features": ["Legacy unlimited plan"],
    },
    "advanced_yearly": {
        "label": "Advanced Pentester — Yearly (Legacy)",
        "model_tier": "model2",
        "price_paise": 4999000,
        "days": 365,
        "daily_limit": None,
        "purchasable": False,
        "features": ["Legacy unlimited plan"],
    },
}
```

### 4.2 Exact Action Items for Implementation Phase

| Component | File Path | Lines | Action Required |
|---|---|---|---|
| **Backend Plans** | `backend/services/subscription.py` | 83-172 | Define `cyber_pro_monthly` (₹3,500) and `cyber_pro_yearly` (₹35,000) with `purchasable: True`; set older plans to `purchasable: False`. |
| **Backend Routes** | `backend/routes/subscription.py` | 73-84, 281-300 | In `list_plans()`, filter out `not config.get("purchasable")`. In `_handle_create_order()`, reject order creation for non-purchasable plans. |
| **Backend Chat Gate**| `backend/routes/chat.py` | 562-594 | Ensure all paid tiers (`model2`, `model1`, `cyber_pro_*`, `advanced_*`) can query the single `orcasaq-cyber-27b:latest` model without 403 blocks. |
| **Admin Route** | `backend/routes/admin.py` | 275-337 | Support granting `cyber_pro_monthly` and `cyber_pro_yearly` from admin console. |
| **Frontend Modal** | `index.html` | 613-625 | Replace the 2-plan mobile switcher (`mobile-plan-tabs`) with single-tier card view; update pricing grid container to center the single card. |
| **Frontend JS** | `index.html` | 3083-3088, 3101-3140 | Add `cyber_pro_monthly` and `cyber_pro_yearly` to `PLAN_LABELS` and `updateSubBadge()`. |
| **Frontend Cards** | `index.html` | 3226-3324 | Update `renderPricingCards()` to render the single "friday Cyber Pro" card dynamically from `/api/subscription/plans`. |
| **Frontend Checkout**| `index.html` | 3369-3426 | Update `openCheckoutReview()` to display "friday Cyber Pro" summary cleanly. |
| **Admin Console** | `admin.html` | 1139-1147, 1408-1413| Update `<select id="grant-plan">` with `cyber_pro_monthly` and `cyber_pro_yearly`, and update badge styling for `cyber_pro`. |
| **Automated Tests** | `backend/test_subscription.py` | 65-87, 220-230, 340-350 | Update pricing assertions to ₹3,500/mo and ₹35,000/yr; add tests for retired plan rejection and active grandfathered subscriber preservation. |

---

## 5. Verification Method

### 5.1 Independent Commands to Execute

1. **Verify Backend Tests**:
   ```powershell
   pytest backend/test_subscription.py -v
   ```
   *Expected*: All test cases pass without failure.

2. **Verify Public API Offering (Only New Single Tier Returned)**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.get('/api/subscription/plans'); print(r.status_code, [p['plan_id'] for p in r.json()['plans']])"
   ```
   *Expected*: Status 200, returning strictly `['cyber_pro_monthly', 'cyber_pro_yearly']`.

3. **Verify Older Plan Purchase Rejection (HTTP 400)**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r = c.post('/api/create-order', json={'plan_id': 'advanced_monthly'}); print(r.status_code, r.json())"
   ```
   *Expected*: Status 400 with detail rejecting retired/non-purchasable plan.

4. **Verify Existing Customer Active Preservation**:
   ```powershell
   python -c "from backend.config import get_settings; import psycopg2; s = get_settings(); conn = psycopg2.connect(s.database_url); cur = conn.cursor(); cur.execute(\"SELECT user_id, plan_id, status, expires_at FROM subscriptions WHERE status = 'active'\"); print(cur.fetchall())"
   ```
   *Expected*: Subscriptions for `FxxeUBnWlBM7emQYUEZDq6saxzn2` and `Bqn7wmPCJpNQYZUz9qhcJjvCSq52` remain `status: 'active'` with their respective November 2026 expiration dates.

5. **Verify Invalidation Conditions**:
   - If `GET /api/subscription/plans` returns any of `jr_hacker_monthly`, `jr_hacker_yearly`, `advanced_monthly`, or `advanced_yearly`, the requirement is invalidated.
   - If existing users `FxxeUBnWlBM7emQYUEZDq6saxzn2` or `Bqn7wmPCJpNQYZUz9qhcJjvCSq52` encounter a 403 Forbidden or 429 Limit reached when chatting, grandfathering is invalidated.
   - If the yearly price is not exactly ₹35,000 (3,500,000 paise), the calculation is invalidated.
