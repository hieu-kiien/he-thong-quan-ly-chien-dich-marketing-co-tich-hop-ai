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

## Phase 4 — Workstream C: KPI (done)
Backend:
- `PUT /kpi-targets`: reject duplicate metric_name (case-insensitive) → 400 thay vì IntegrityError 500
- New `GET /campaigns/{id}/kpi-progress` → `KpiProgressResponse`: map metric_name → actual từ SUM CampaignMetric (CTR/CVR/CPC/CPA/ROAS/ROI/revenue/cost/conversions/clicks/views); metric lạ → `measurable=false, actual=None` (không bịa); `overall_achieved_pct` = avg các metric đo được; zero-metrics an toàn

Frontend:
- `KpiProgress` type + `kpiApi.getKpiProgress`
- WorkflowCanvas nạp kpiProgress song song KPI summary; OverviewTab hiển thị danh sách target vs actual (màu theo ngưỡng 50/100%, "Chưa đo được" khi không map)

Tests `test_kpi_workstream.py` (7): duplicate 400, unique 200, achieved_pct tính đúng (baseline-aware), no-metrics zero-division, cross-tenant, unauth, ROAS/revenue mapping

Verification:
- pytest kpi + tasks + lifecycle + budget → 32 passed
- FE tsc + eslint --max-warnings=0 + build → pass
- `detect_changes --scope all`: 25 symbols, risk medium

## Next — Phase 5+ (not started)
- Workstream D: Tasks/Notifications
- Workstream E: Auth (logout revocation, change password)


## Phase 5 � Workstream D: Tasks/Notifications (done)
Backend:
- `POST /campaigns/{id}/tasks`: g?i notification cho assignee (target_tab=`tasks`, lo?i `task`) khi giao vi?c cho ngu?i kh�c; b? qua khi t? giao cho m�nh
- `PATCH /tasks/{id}`: g?i notification cho assignee m?i khi d?i ngu?i (reassign)
- Notification failure kh�ng l�m h?ng vi?c t?o/c?p nh?t task (log warning + rollback)

Tests `test_notifications.py` (12): create-notify assignee, self-assign no-notify, reassign-notify

Verification:
- pytest tasks + notifications + lifecycle + budget + kpi ? 30+ passed
- `detect_changes --scope all`: risk medium

## Next � Phase 6+
- Workstream E: Auth (logout revocation, change password)

## Phase 6 � Workstream E: Auth (done)
Backend:
- `users.token_version` (c?t m?i, migration SQLite + Postgres): logout / d?i m?t kh?u tang phi�n b?n ? m?i token cu b? 401 fail-closed qua `assert_token_version_current` (g?i ? `get_current_user` + `RoleChecker`)
- `POST /auth/logout` (204): thu h?i to�n b? phi�n c?a user
- `POST /auth/change-password` (200): x�c minh m?t kh?u hi?n t?i (400 n?u sai / tr�ng m?i), ghi hash m?i, thu h?i phi�n cu, c?p token m?i cho phi�n dang d?i
- Login nh�ng claim `ver` = token_version

Fix P0 k�m theo (pre-existing, fail ngay tr�n HEAD):
- `GET /campaigns` �p `_apply_tenant_scope` � tru?c d�y thi?u filter workspace ? danh s�ch tr? c? chi?n d?ch `workspace_id=NULL` c?a tenant kh�c (test P0-4 fail 34/34 sau fix)

Frontend:
- `authApi.logout()` g?i `POST /auth/logout` best-effort (kh�ng await) tru?c khi d?n localStorage
- `authApi.changePassword` + form "�?i m?t kh?u" trong Settings tab H? so

Tests: `test_auth_workstream.py` (7) + to�n b? security suites ? 130 passed
Verification: FE tsc + eslint --max-warnings=0 + build pass; detect_changes risk critical (auth core � expected)

## Next � Phase 7+: Workstream F (DB/Performance), G (AI Foundation), H (AI Planner), I (FE/UX), J (Integration)

## Phase 7 - Workstream F: DB/Performance (done)
- Index hot cho manh "Viec cua toi": idx_tasks_assignee_due (assignee_id, due_date), idx_tasks_workspace_status (workspace_id, status) - entities.py + migration SQLite/Postgres (CREATE INDEX IF NOT EXISTS, idempotent)
- GET /tasks/my-tasks/summary: gop 5 COUNT thanh 1 query SUM(CASE...) - giam 4 round-trip moi lan mo man hinh
- Verification: 193 passed (tasks + pagination + budget + kpi + lifecycle + tier5 + p0 + auth_workstream); FE khong doi
