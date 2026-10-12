# Autonomous Progress — MarketFlow AI MVP

Branch: `feat/mvp-phase1-security-data-integrity` (HEAD `4d7eb8c` → Phase 2 commit)

## Phase 0 — Gate (done earlier)
- Baseline: pytest 1628 passed; FE typecheck/lint/build pass
- Local SQLite + offsite pg_dump backup verified
- Local secrets inventory: SECRET_KEY default public; JWT/BYOK missing → fallback to SECRET_KEY

## Phase 1 — Security / Data Integrity (done)
Commit `4d7eb8c`:

| # | Fix | Files |
| --- | --- | --- |
| 1.1 | Local secrets: add `JWT_SECRET_KEY` + `BYOK_ENCRYPTION_KEY` to `backend/.env` (keep SECRET_KEY for MultiFernet legacy); BYOK ciphertext still decrypts; new JWTs decode | `backend/.env` (not committed) |
| 1.2 | IDOR `POST /contents/compliance-check`: reject cross-tenant `workspace_id` via `assert_workspace_access` | `backend/app/api/v1/contents.py` |
| 1.3 | `GET /settings/ai-models` no longer accepts `?api_key=`; header `X-Test-Api-Key` only | `backend/app/api/v1/settings.py` |
| 1.4 | Null-ws fail-closed: MANAGER/AGENCY_MANAGER cannot bypass `campaign.workspace_id IS NULL` (owner/member only) | `backend/app/api/v1/metrics.py`, `ai.py` |
| 1.5 | Remove fake KPI fallbacks / mock doctor: PerformanceTab, WorkflowCanvas, ChannelROIComparison, AIDoctorWidget, AIStudio export ids | FE components above |

Tests added in `test_multi_tenant_hardening.py`:
- `test_compliance_check_cross_tenant_workspace_id_forbidden`
- `test_ai_models_rejects_api_key_in_query_string`
- `test_metrics_null_workspace_manager_bypass_removed`

Verification:
- Targeted pytest: multi_tenant + adversarial + tier1 → 107 passed
- Full FE typecheck + lint `--max-warnings=0` + build → pass

## Phase 2 — Campaign State Machine + Soft Delete + Wizard (done)
New `backend/app/services/campaign_lifecycle.py`:
- `CREATE_ALLOWED_STATUSES = {DRAFT, PLANNED, ACTIVE}`; `ALLOWED_TRANSITIONS` matrix (ARCHIVED restore → DRAFT/PLANNED); `assert_create_status` / `assert_transition` (422 + valid-next message); `compute_progress_pct` → `None` when 0 tasks (no fake number)
- `HIDDEN_FROM_DEFAULT_LIST = {ARCHIVED}`

Backend (`campaigns.py`, `schemas.py`):
- `CampaignCreate.status` validated on create (was hardcoded DRAFT); `CampaignResponse.progress_pct` added
- PUT validates transition BEFORE applying status change; status/budget change requires owner/manager
- DELETE → soft-delete `status=ARCHIVED` (keeps metrics/tasks/history); list hides ARCHIVED unless `?status=ARCHIVED`
- `progress_pct` serialized via bulk task counts (no N+1) in list + detail

Frontend:
- `Campaigns.tsx` wizard now sends `status: launchStatus` on create (bug: created DRAFT always, then only updated when DRAFT — inverted logic)
- `api.ts` campaignApi.create accepts optional `status` (offline demo defaults DRAFT); `types` Campaign adds `progress_pct`

Tests:
- New `test_campaign_lifecycle.py` (7): create ACTIVE preserved, invalid status 422, valid/invalid transitions, ACTIVE↔PAUSED toggle, soft-delete archive+hidden list, progress_pct from tasks, unit helpers
- Updated `test_extended_coverage.py` cascade test → soft-delete semantics (ARCHIVED + history kept + trash filter)
- Updated `test_tier5_security_and_concurrency.py::test_27` → soft-delete semantics (keeps children, ARCHIVED)

Verification:
- pytest campaign_lifecycle + extended_coverage + multi_tenant_hardening → 97 passed
- pytest deep_scenarios + offline + tier5 + wave1 + adversarial_v3 → 223 passed (1 old hard-delete test updated)
- pytest extended + ieee829 + challenger_w1 + adversarial_v3 + deep_scenarios + wave1 → 272 passed
- FE tsc --noEmit + eslint --max-warnings=0 + vite build → pass
- `detect_changes --scope all`: 26 symbols, risk critical (expected — campaign CRUD core; covered by tests above)

## Phase 3 — Workstream B: Budget (done)
Backend:
- `PUT /campaigns/{id}/budget-allocations`: reject duplicate channel (400, thay vì IntegrityError 500) + reject total planned > campaign.budget (400, thông báo tiếng Việt)
- New `GET /campaigns/{id}/budget-summary` → `BudgetSummaryResponse`: total_budget / total_allocated / total_spent (SUM `CampaignMetric.cost`) / unallocated / remaining / allocated_pct / spent_pct / per-channel planned+spent; zero-budget safe (0% thay vì chia 0); tenant-scoped qua `check_campaign_access`

Frontend:
- `BudgetSummary` type + `budgetApi.getBudgetSummary`
- Campaigns drawer "Phân bổ Ngân sách theo Kênh": hiển thị tổng quan (ngân sách/phân bổ/đã chi/còn lại + thanh spent_pct màu theo ngưỡng 80/100%) và "Đã chi" từng kênh

Tests `test_budget_workstream.py` (7): over-budget 400, duplicate channel 400, within-budget 200, spent tracking delta, zero-budget no-division, cross-tenant 403/404, unauth 401

Verification:
- pytest budget + tasks + lifecycle + quota → 48 passed
- FE tsc + eslint + build → pass
- `detect_changes --scope all`: 34 symbols, risk medium

## Next — Phase 4+ (not started)
- Workstream C: KPI targets CRUD + real metrics (validate metric_name allowlist, unit)
- Workstream D: Tasks/Notifications
- Workstream E: Auth (logout revocation, change password)

