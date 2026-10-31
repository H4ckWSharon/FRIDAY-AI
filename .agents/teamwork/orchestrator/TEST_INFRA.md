# E2E Test Infra: FRIDAY AI Consolidation & Hardening

## Test Philosophy
- Opaque-box, requirement-driven derived from `ORIGINAL_REQUEST.md` (R1-R4).
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Application Workload Testing.

## Feature Inventory & Test Matrix
| # | Feature Area | Requirement | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Real-World) |
|---|-------------|-------------|:-----------------:|:-----------------:|:-----------------:|:-------------------:|
| 1 | Single Model & Rebranding | R1 | 5 | 5 | ✓ | ✓ |
| 2 | Pricing Tier & Subscription Preservation | R2 | 5 | 5 | ✓ | ✓ |
| 3 | Chat UX Radar Animation & Concurrency | R3 | 5 | 5 | ✓ | ✓ |
| 4 | Security Vulnerabilities & Bug Fixes | R4 | 5 | 5 | ✓ | ✓ |
| 5 | VPS Host Deployment & Cleanup | R4 | 5 | 5 | ✓ | ✓ |

## Coverage Goals
- **Tier 1 (Feature Coverage)**: >= 25 test cases (5 per feature area).
- **Tier 2 (Boundary & Corner Cases)**: >= 25 test cases (5 per feature area).
- **Tier 3 (Cross-Feature Combinations)**: >= 5 test cases testing interactions (e.g. expired vs active sub querying model; rapid retry while streaming; order creation with retired plan ID).
- **Tier 4 (Real-World Application Scenarios)**: >= 5 end-to-end integration workflows.
- **Total Minimum Test Cases**: >= 60 test cases.

## Test Architecture
- Test Runner: `pytest` on backend test suite and automated integration test runner.
- Invocation: `pytest backend/test_models.py backend/test_subscription.py backend/test_backend.py -v`
- Pass/Fail Semantics: 100% tests pass, zero regressions, zero model leaks.
