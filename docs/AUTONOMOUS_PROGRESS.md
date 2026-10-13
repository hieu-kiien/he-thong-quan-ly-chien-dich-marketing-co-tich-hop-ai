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


## Phase 8 - Workstream G (AI Foundation: kind=plan) + H (AI Campaign Planner) (done)

Backend - Workstream G (queue foundation):
- `queue.py`: `KIND_PLAN = "plan"` + `JOB_KINDS` (đối xứng với CHECK constraint `chk_ai_job_kind` ở entities)
- `entities.py`: CHECK `chk_ai_job_kind` nhận `'plan'`; cột `is_ai_estimate BOOLEAN NOT NULL DEFAULT false` trên `campaign_budget_allocations` + `campaign_kpi_targets` (dòng do AI sinh gắn nhãn "ước tính", dòng tay giữ false); bảng mới `campaign_plan_applications` (UNIQUE (campaign_id, idempotency_key) = idempotency tầng DB, plan_hash SHA-256, plan_json snapshot audit)
- `database.py`: SQLite `_migrate_ai_job_kind_constraint` (table rebuild, CHỤP SQL 7 index trước rename + tạo lại sau DROP vì bảng mới từ sqlite_master không mang index); ALTER ADD COLUMN is_ai_estimate x2; Postgres: checks tuple += 2 cột + DROP/ADD `chk_ai_job_kind` idempotent qua `pg_get_constraintdef`
- `ai_jobs.py`: `_KIND_REQUEST_MODELS` / `_KIND_QUOTA_PREFIX` (`ai:plan`) / `_KIND_SYNC_ENDPOINT` (`generate_plan`) + description kind/campaign_id + docstring

Backend - Workstream H (planner):
- `schemas.py`: `AIPlanRequest` (campaign_id BẮT BUỘC), `AIPlanResponse` (budget_split min 1, tasks min 1, mọi item mang `is_ai_estimate=True`), `PlanApplyRequest` (idempotency_key bắt buộc), `PlanApplyResponse`; `is_ai_estimate` thêm vào BudgetAllocationResponse/KPITargetResponse
- `prompts/prompts.json`: key `campaign_plan` v3 (system + user template tiếng Việt, chống bịa số)
- `ai_service.py`: `_validate_task_output` + branch PLAN; `_generate_fallback_campaign_plan` (chia đều bằng đồng floor -> tổng LUÔN <= ngân sách thật, KPI chỉ sinh khi context có mục tiêu, task 5 pha theo trục chiến dịch, warnings trung thực); `_fallback_kpi_unit` phân loại unit theo tên metric
- `ai.py`: `POST /ai/plan` (deprecated, đường cũ): quota `ai:plan:user`, tenant check, context thật (budget/dates/channels/KPI hiện có), clamp due_offset trong [0, (end-start).days] + warning, fallback recovery 502 khi fallback tắt
- `campaigns.py`: `POST /campaigns/{id}/plan/apply`: validate TOÀN BỘ trước mọi ghi (channel resolve ACTIVE + không trùng, tổng <= budget, KPI không trùng, task trong khoảng chiến dịch) -> idempotency (200 dedup / 409 khoá sai) -> 1 transaction (application + replace budget + replace KPI chỉ khi list rỗng khác nghĩa "không đổi" + task dedup theo title, due_date = start + offset); IntegrityError -> rollback -> dedup/409

Tests:
- Mới `tests/test_ai_planner.py` (13): maps đồng bộ với JOB_KINDS + DDL, enqueue 202, worker execute_ai_job gọi lại generate_plan, sync plan offline fallback hợp lệ (tong <= 15M, offset <= 29, is_ai_estimate), tenant/role 403, 502 khi fallback tắt, fallback không vượt ngân sách (4 mức budget), apply success (is_ai_estimate + due_date + nhật ký), validate-before-write (5 case 400, không ghi gì), 404/403 auth, dedup 200, 409 khoá trùng kế hoạch khác, OpenAPI deprecated
- Sửa: `test_ai_job_queue.py` (JOB_KINDS + "plan", kind=plan 422 khi thiếu campaign_id), `test_offline_core_works_without_ai.py` (fallback context campaign_plan)

Verification:
- Full pytest: 1671 passed, 4 failed = 4 pre-existing fail ngay tại HEAD df3790e (đối chứng qua worktree sạch): 2 e2e tier3 compliance 403, challenger banned-keywords 403, design_docs pagination doc claim
- `analyze --index-only` (re-index) + `detect-changes --scope all`: 13 files, 80 symbols, 18 processes, risk critical (expected: fallback dùng chung mọi endpoint AI + migration mỗi startup; mitigated additive-only + 1671 tests)


## Phase 9 - Workstream I: FE Planner UI (done)

Frontend:
- `types/index.ts`: `AIPlanResponse` / `AIPlanBudgetItem` / `AIPlanKPIItem` / `AIPlanTaskItem` / `PlanApplyRequest` / `PlanApplyResponse` (khop contract backend `schemas.py`); them `is_ai_estimate?: boolean` vao `BudgetAllocation` + `KPITarget`
- `services/api.ts`: `isAiPath` + `/ai/plan` (timeout dai 600s nhu cac endpoint AI dong bo); `aiApi.generatePlan(campaignId)` POST `/ai/plan` + offline-demo mock (is_fallback=true, model_used=OFFLINE_DEMO_MODEL_LABEL, model_provider=OFFLINE_DEMO_PROVIDER - khong goi AI); `campaignApi.applyPlan(campaignId, payload)` POST `/campaigns/{id}/plan/apply` + offline-demo mock (tasks_created, khong gia lap channel_id that)
- `components/campaign-hub/PlannerTab.tsx` (moi): sinh ke hoach -> hien summary (fallback banner amber khi is_fallback), bang phan bo ngan sach (tong vs budget, badge "Uoc tinh AI", canh bao vuot ngan sach va tu disable apply), bang KPI (format theo unit vnd/percent/ratio), bang task (due_date = start_date + due_offset_days, priority badge, loai task tieng Viet); nut "Ap dung" generate idempotency_key = crypto.randomUUID() moi ke hoach moi, giu key qua retry mang, doi key khi 409; xu ly 200 dedup/400/403/409/502; gate FE owner/manager (backend chan lai day du) + chi CLIENT_APPROVER khong phai owner bi disable
- `campaign-hub/index.ts`: export PlannerTab
- `WorkflowCanvas.tsx`: tab moi 'planner' (nut Wand2 "Ke Hoach AI (Planner)" truoc tab lifecycle); onApplied nạp lai task + budget allocations + KPI summary + KPI progress + goi onRefreshData

Verification:
- FE: `npm run typecheck` + `npm run lint --max-warnings=0` + `npm run build` pass
- Backend full pytest: 1671 passed, 4 failed = 4 pre-existing (khong doi so voi Phase 8 - FE changes khong anh huong backend)


## Phase 10 - Workstream J: Integration - async plan job path (done)

Bo sung tich hop duong async cho ke hoach (dong bo hoa voi cac loai job khac):
- `aiJobPoller.ts`: `AIJobKind` += `'plan'` - truoc do FE khong the enqueue kind=plan du backend ho tro day du (Workstream G)
- `services/api.ts` `buildOfflineDemoSnapshot`: `case 'plan'` goi `aiApi.generatePlan` (offline demo tra ve snapshot succeeded voi noi dung mau, nhan OFFLINE_DEMO_* ong hoat nhu 4 kind khac)
- `PlannerTab.tsx`: chuyen sinh ke hoach sang duong `POST /ai/jobs kind=plan` -> poll qua `useAIJob` + `AIJobProgress` (progress + cancel + retry classification); ly do: endpoint dong bo /ai/plan bi Cloudflare Worker cat ~100s (524) voi model cham - chinh la ly do hang doi ton tai; toast ghi nhan nguon goc qua `describeAIResultOrigin` (fallback = canh bao khong goi duoc AI); loi hien qua AIJobError classification (timeout/rate_limit/quota/...)
- idempotency: poller tu sinh `idempotency_key` cho moi job; plan apply van dung crypto.randomUUID() rieng

Verification: FE tsc + eslint --max-warnings=0 + build pass; backend khong doi (1671 passed + 4 pre-existing tai Phase 9); kind=plan enqueue/worker da duoc bao boi `tests/test_ai_planner.py`


## Phase 11 - Bugfix: useAIJob + React.StrictMode (dev) + browser-skill verification

Bug: `useAIJob` tao task 1 lan trong render va `useEffect` cleanup goi `dispose()` -> trong React.StrictMode (dev) mount -> cleanup -> mount, task cu da dispose VING VIEN (flag `disposed` trong closure), lan mount lai van dung task do -> `run()` luon nem "Tac vu da bi huy do roi khoi trang" im lang, khong co request nao. Anh huong MOI consumer (AIDrawer, AIStudio, Campaigns, WorkflowCanvas copilot, PlannerTab) - chi hien ro o dev, production build khong double-effect.

Fix `frontend/src/hooks/useAIJob.ts` (giu nguyen API contract):
- helper `buildTask(transport, deadlineMs, onUpdate)` cap module
- render body van lazy-init (giu truocg behavior cho layout effect caller)
- `useEffect` hien tai Tao TASK MOI moi setup (deps `[transport, deadlineMs]` - ca 2 on dinh vi consumer nao cung goi `useAIJob()` khong args), cleanup dispose task cua chinh no

Verification:
- FE: tsc + eslint --max-warnings=0 pass
- impact(`useAIJob` upstream): risk CRITICAL, 5 direct callers, 7 processes - da canh bao truoc khi sua; contract giu nguyen (khong doi return shape)
- detect-changes --scope all: 3 files (chi commit useAIJob + progress doc; 2 file PROMPT_VARIANT van dirty tuyet doi khong dot cham), risk critical = expected cho hub hook
- Browser-skill live test (backend uvicorn :8001 + vite :5174, seed marketer): login -> WorkflowCanvas -> tab Kế Hoạch AI -> Sinh ke hoach (POST /ai/jobs 202 -> poll -> fallback plan: banner amber + 5k x 3.000.000 = 15.000.000 + 5 task due 1/9..27/9) -> Ap dung (POST /campaigns/1/plan/apply 200, badge Tasks 0->5) -> GET budget-allocations: 5 row is_ai_estimate=true, GET tasks: 5 item due_date dung khoang chien dich
- Consumer thu 2: Copilot "Tim y tuong" cung hoat dong (POST /ai/jobs 202 + poll) truoc do cung bi loi nay

## Phase 12 - Cleanup: gỡ co che banner "danh thuc may chu (Render)" legacy

Ly do: du an da chay toan bo tren VPS (vn-hn.cloudcode.io.vn, /opt/marketflow), khong con Render - nhung banner van hien "Render Cloud dang khoi dong container tu che do ngu dong" moi khi request cham hon 3.5s -> hieu nham (VPS luon on, cham = network/DB/dev compile).

- Xoa `components/ServerAwakeningIndicator.tsx` + import/usage trong App.tsx
- `services/api.ts`: xoa toan bo khoi awakening (ServerAwakeningStatus, subscribeServerAwakening, broadcastAwakening, activeRequestsCount, awakeningTimer, cleanupAwakeningTracking); GIU NGUYEN `backendReachable`/`isBackendConnected` (risk HIGH khi impact, khong cham toi) va cau hinh `VITE_AI_API_URL`
- Don comment Render nhu deployment hien tai (api.ts AI_BASE_URL + timeout); comment lich su do thuc 237s tren Render free giu nguyen (qua khua, giai thich vi sao co hang doi AI)

Verification: tsc + eslint --max-warnings=0 + build pass; impact: ServerAwakeningIndicator/subscribeServerAwakening risk LOW (App chi dung de render banner); detect-changes risk high = App la hub, diff chi 2 dong

## Phase 13 - Dọn rac repo (user request)

Xoa (untracked/ignored, tai tao duoc): test-recordings/ (67.5MB playwright), test-results/, archive/, .agents/ (log teamwork cu), .coverage, coverage.xml, backend/uvicorn.log, frontend/vite.log, test_marketing.db-shm/-wal, marketing_campaigns.db root (stray 27/09), 4 anh screenshot root (ai_studio_*.png, dashboard_view.png)
Xoa (tracked, sua link kem): TEST_INFRA.md + TEST_READY.md (docs tu goi la bao cao test cu) + cap nhat docs/README.md, docs/TESTING.md, docs/ROADMAP.md
Giu: ORIGINAL_REQUEST.md, BIEN_BAN_NGHIEM_THU.md (nguon/cau chung tests), CLAUDE.md (= AGENTS.md, config Claude Code), Bao_Cao V9 + PDF da nop, 2 anh chup yeu cau mon hoc
Verify: test_design_docs_integrity + test_ai_ethics + test_prompt_variant_harness: 52 passed, 1 failed = pre-existing pagination doc claim
