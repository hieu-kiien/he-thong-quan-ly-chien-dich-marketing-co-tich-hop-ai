# MarketFlow AI — Opaque-Box E2E Test Suite Infrastructure (TEST_INFRA.md)

## 1. Executive Summary & Testing Philosophy

This document defines the complete infrastructure, test hierarchy, execution mechanics, and pass/fail semantics for the **MarketFlow AI Official Release E2E Testing Track**.

### Opaque-Box Testing Principle
In accordance with Enterprise Software Quality Standards and ISO/IEC/IEEE 29119, the E2E Test Suite operates under an **Opaque-Box (Black-Box)** paradigm:
- Tests are derived strictly from authoritative specifications (`ORIGINAL_REQUEST.md` R1–R6, `PROJECT.md`, and Acceptance Criteria).
- Test cases do **not** depend on internal implementation details, private methods, or hardcoded mocks.
- All interactions occur through observable public boundaries: HTTP REST API endpoints, JWT Bearer authentication headers, standardized JSON payloads, HTTP status codes, and database state invariants.

### Dual-Track Architecture
The E2E Testing Track runs in parallel with the Milestone Implementation Track (M1–M6):
```
┌────────────────────────────────────────────────────────┐
│               MarketFlow AI Project Root               │
├───────────────────────────┬────────────────────────────┤
│   Implementation Track    │      E2E Testing Track     │
│   (M1 -> M2 -> ... -> M6) │   (Tiers 1-4 Test Suite)   │
├───────────────────────────┼────────────────────────────┤
│ - Model & Schema changes  │ - Authoritative Oracles    │
│ - API Routers & Business  │ - Tier 1: Feature Coverage │
│ - UI & Frontend Pages     │ - Tier 2: Boundary/Corners │
│ - Milestone-by-milestone  │ - Tier 3: Cross-Features   │
│                           │ - Tier 4: Real Scenarios   │
└───────────────────────────┴────────────────────────────┘
```

---

## 2. The 4-Tier Test Architecture

The E2E Test Suite is structured into **4 distinct verification tiers**, providing deep, multi-dimensional quality assurance across all functional domains (R1–R6):

```
       ▲
      / \     Tier 4: Real-World Scenarios (Full Agency Lifecycles)
     /   \    ────────────────────────────────────────────────────
    /     \   Tier 3: Cross-Feature Combinations (Integration Matrix)
   /       \  ────────────────────────────────────────────────────
  /         \ Tier 2: Boundary & Corner Cases (Stress, Edge, Zero-Division)
 /           \────────────────────────────────────────────────────
/             \ Tier 1: Feature Coverage (Core Functional Happy Paths R1-R6)
───────────────
```

### Tier 1: Core Feature Coverage (>=5 test cases per feature R1–R6)
Validates standard functional requirements, expected inputs, and successful operational state transitions:

1. **R1: Multi-Workspace & Brand Kit, Auth & RBAC**
   - `test_t1_r1_01_user_registration`: Register new user with designated role (MARKETER, CLIENT_APPROVER, AGENCY_MANAGER).
   - `test_t1_r1_02_user_login_and_token`: Authenticate and receive valid JWT bearer token with user profile.
   - `test_t1_r1_03_create_workspace`: Agency manager provisions a new isolated workspace.
   - `test_t1_r1_04_brand_kit_crud`: Configure and update Brand Kit (USP, Tone of Voice, Banned Keywords).
   - `test_t1_r1_05_workspace_isolation`: Confirm campaigns and assets in Workspace A are inaccessible to Workspace B.

2. **R2: Deep 3-Channel AI Creative Engine**
   - `test_t1_r2_01_omnichannel_generation_all_channels`: Single brief generates Facebook, TikTok, and Email assets simultaneously.
   - `test_t1_r2_02_facebook_payload_contract`: Validates title, spaced body, action CTA, and structured hashtags.
   - `test_t1_r2_03_tiktok_payload_contract`: Validates 3-second hook, structured scenes (scene #, visual, voiceover, sound), and trending audio.
   - `test_t1_r2_04_email_payload_contract`: Validates A/B subject line variants, preheader, personalized greeting, nurture body, CTA button, and P.S. note.
   - `test_t1_r2_05_brand_kit_inheritance`: Verifies AI prompt inherits and respects Brand Kit tone and product positioning.

3. **R3: Enterprise Brand Safety & Compliance Guardrail**
   - `test_t1_r3_01_compliance_check_passed`: Clean marketing copy receives `PASSED` status and high safety score.
   - `test_t1_r3_02_compliance_brand_blacklist_detection`: Content containing Brand Kit banned words receives `VIOLATION` or `WARNING`.
   - `test_t1_r3_03_compliance_ad_policy_detection`: Content with false guarantees ("cam kết 100%") or forbidden claims is flagged.
   - `test_t1_r3_04_strict_submit_gate_blocks_high_severity`: Content with HIGH severity violations is blocked from submission (HTTP 422).
   - `test_t1_r3_05_strict_human_in_the_loop_approval`: Marketers cannot approve (HTTP 403); only Managers / Client Approvers can approve (`APPROVED`).

4. **R4: High-Fidelity Social Preview Engine & Action Tools**
   - `test_t1_r4_01_attach_product_image_url`: Marketing content accepts and persists `image_url` for creative banner preview.
   - `test_t1_r4_02_facebook_preview_metadata`: Content model exposes full Facebook card structure (page info, sponsored tag, engagement counters).
   - `test_t1_r4_03_tiktok_mockup_representation`: Video script payload structures align with 9:16 vertical phone layout requirements.
   - `test_t1_r4_04_email_inbox_preview_structure`: Email sequence payload exposes inbox row preview (sender, subject line, preheader) and body.
   - `test_t1_r4_05_one_click_copy_and_export_contract`: Content formatting preserves line breaks and Unicode emojis; campaign plan export structure is intact.

5. **R5: Attribution Analytics & Actionable AI Doctor**
   - `test_t1_r5_01_kpi_summary_economic_metrics`: Accurately computes Views, Clicks, Conversions, Cost, Revenue.
   - `test_t1_r5_02_kpi_derived_rates`: Accurately calculates CTR (%), CPC (VNĐ), CVR (%), ROAS (`revenue / cost`), and ROI (%).
   - `test_t1_r5_03_channel_attribution_breakdown`: Attribution analytics reports per-channel metrics for Facebook, TikTok, and Email.
   - `test_t1_r5_04_ai_doctor_health_diagnosis`: AI Doctor provides grounded health status (`HEALTHY`, `NEEDS_ATTENTION`, `CRITICAL`).
   - `test_t1_r5_05_ai_doctor_actionable_recommendations`: AI Doctor outputs specific, data-backed optimization actions (`SCALE`, `REDUCE`, `OPTIMIZE`).

6. **R6: Enterprise Settings & Bring Your Own Key (BYOK)**
   - `test_t1_r6_01_test_ai_connection_gemini`: Verification endpoint successfully validates Gemini API key connection and measures latency.
   - `test_t1_r6_02_store_custom_byok_key`: Custom API key is submitted, encrypted, and saved without leaking plain text.
   - `test_t1_r6_03_retrieve_masked_byok_settings`: GET endpoint returns masked key (`AIzaSy...4xQ9`), ensuring zero plaintext exposure.
   - `test_t1_r6_04_update_byok_model_selection`: User can configure preferred model (e.g., `gemini-2.5-flash`, `gemini-2.5-pro`).
   - `test_t1_r6_05_delete_deactivate_byok_key`: User can remove custom key, falling back seamlessly to workspace/system level.

---

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature R1–R6)
Tests extreme input conditions, edge values, fault recovery, and defensive sanitization:

1. **R1 Boundary**:
   - `test_t2_r1_01_empty_workspace_name_rejected`: Rejects empty strings, single spaces, or missing required fields with HTTP 422.
   - `test_t2_r1_02_special_characters_brand_kit`: Tests Vietnamese diacritics, HTML injection (`<script>alert(1)</script>`), and emoji strings.
   - `test_t2_r1_03_expired_or_malformed_jwt`: Ensures 401 Unauthorized for expired tokens, random garbage tokens, or missing Bearer prefix.
   - `test_t2_r1_04_invalid_email_format_registration`: Rejects invalid email patterns (`user@`, `user@.com`, `user_without_at`) with HTTP 422.
   - `test_t2_r1_05_nonexistent_workspace_access`: Requests targeting invalid or negative workspace IDs return HTTP 404 cleanly.

2. **R2 Boundary**:
   - `test_t2_r2_01_empty_brief_validation`: Empty brief triggers HTTP 422 validation without crashing the server.
   - `test_t2_r2_02_oversized_brief_stress`: Handles long briefs (>5,000 characters) gracefully without memory exhaustion or timeouts.
   - `test_t2_r2_03_single_channel_subset`: Requesting only `["facebook"]` returns Facebook payload while omitting unrequested channels cleanly.
   - `test_t2_r2_04_unsupported_channel_handling`: Gracefully rejects or ignores unsupported channels (e.g., `["myspace"]`).
   - `test_t2_r2_05_ai_provider_fallback_resilience`: When AI service encounters an upstream network outage, smart fallback delivers valid deterministic structure with `is_fallback: true`.

3. **R3 Boundary**:
   - `test_t2_r3_01_blacklist_case_and_accent_insensitivity`: Matches banned words regardless of casing or diacritics (e.g. `CAM KẾT 100%`, `cam kết 100%`).
   - `test_t2_r3_02_overlapping_banned_keywords`: Evaluates content triggering multiple banned keywords simultaneously without duplicating errors.
   - `test_t2_r3_03_empty_content_compliance_scan`: Scanning empty title and body returns clean `PASSED` without false positives.
   - `test_t2_r3_04_illegal_state_jump_rejected`: Direct jump from `DRAFT` to `PUBLISHED` or `APPROVED` via PUT returns HTTP 400.
   - `test_t2_r3_05_edit_approved_content_reverts_state`: Modifying title or body of an already `APPROVED` content automatically resets state to `DRAFT` or `AI_DRAFT`.

4. **R4 Boundary**:
   - `test_t2_r4_01_malformed_image_url_handling`: Handles non-URL strings or invalid schemes gracefully without database corruption.
   - `test_t2_r4_02_copy_format_preserves_multiline_and_emoji`: Formatted copy strings retain multiple consecutive `\n` newlines and Unicode symbols (🔥, 🚀, 💡).
   - `test_t2_r4_03_content_without_image_defaults_cleanly`: Content with `image_url: null` renders preview metadata cleanly without null pointer exceptions.
   - `test_t2_r4_04_boundary_length_title_and_body`: Tests titles at max length (255 chars) and long body copy (>10,000 chars).
   - `test_t2_r4_05_export_empty_campaign`: Exporting a campaign with 0 marketing contents returns an empty template rather than HTTP 500.

5. **R5 Boundary**:
   - `test_t2_r5_01_zero_cost_division_safety`: When `cost = 0`, ROAS and CPC safely default to 0.0 without triggering `ZeroDivisionError`.
   - `test_t2_r5_02_zero_clicks_and_views_safety`: When `clicks = 0` and `views = 0`, CTR and CVR safely compute as 0.0%.
   - `test_t2_r5_03_negative_cost_revenue_validation`: API rejects negative cost or negative revenue inputs with HTTP 422.
   - `test_t2_r5_04_ai_doctor_sparse_metrics_context`: AI Doctor on brand new campaigns with 0 views/cost outputs informative diagnosis without crashing.
   - `test_t2_r5_05_large_scale_financial_values`: Calculates ROAS and ROI correctly with values up to 50 billion VNĐ without floating-point overflow.

6. **R6 Boundary**:
   - `test_t2_r6_01_empty_byok_key_rejected`: Rejects empty strings or whitespace-only keys with HTTP 422.
   - `test_t2_r6_02_prohibited_ai_providers_rejected`: Rejects models containing prohibited strings ("claude", "gpt", "sonnet") per project rules.
   - `test_t2_r6_03_test_connection_invalid_key_fails_cleanly`: Testing an invalid dummy key returns `{success: false}` cleanly without unhandled stack traces.
   - `test_t2_r6_04_byok_encryption_at_rest`: Directly inspects database storage to confirm keys are stored encrypted, never in plaintext.
   - `test_t2_r6_05_masked_key_format_integrity`: Confirms masked key displays prefix and suffix with asterisk masking (`AIzaSy...4xQ9`).

---

### Tier 3: Cross-Feature Combinations (Integration Matrix)
Validates interactions across multiple subsystems:

- `test_t3_cross_01_workspace_brandkit_omnichannel_compliance`:
  Provisions Workspace A with specific banned keywords -> Generates Omnichannel 3-channel content -> Passes content through Compliance Scanner -> Verifies compliance scanner enforces Workspace A's specific Brand Kit rules.
- `test_t3_cross_02_multi_tenant_blacklist_isolation`:
  Workspace A bans "trắng da cấp tốc", Workspace B does not. The identical marketing copy is marked as `VIOLATION` in Workspace A, but `PASSED` in Workspace B.
- `test_t3_cross_03_rbac_workflow_review_queue_gate`:
  Marketer creates content with ad policy violation -> Blocked from submit -> Marketer cleans content -> Submits to `IN_REVIEW` -> Marketer attempts approve (HTTP 403 Forbidden) -> Client Approver logs in and approves -> Content reaches `APPROVED`.
- `test_t3_cross_04_approved_content_social_preview_and_calendar`:
  Content in `DRAFT` is rejected from Marketing Calendar scheduling. Once approved by Client Approver, it can be scheduled with attached banner image and preview metadata.
- `test_t3_cross_05_byok_key_resolution_in_ai_generation`:
  User configures custom Gemini key -> AI Service key resolver selects user-specific key ahead of workspace and system defaults.

---

### Tier 4: Real-World Scenarios (Comprehensive End-to-End Lifecycles)
Simulates end-to-end enterprise user journeys:

- `test_t4_scenario_01_complete_agency_onboarding_to_kpi_doctor`:
  Full enterprise lifecycle:
  1. Register Agency Manager and Client Approver accounts.
  2. Agency Manager provisions Workspace "VinFast Agency Global".
  3. Configures Brand Kit (USP: "Công nghệ xanh tương lai", Tone: "Chuyên nghiệp", Blacklist: ["cam kết 100%", "phá giá"]).
  4. Creates Campaign "Ra mắt xe điện VF3".
  5. Triggers Omnichannel 1-Click Generation for Facebook, TikTok, Email.
  6. Runs Compliance Pre-Check; verifies adherence to Brand Kit.
  7. Attaches banner `image_url` and submits content for review (`IN_REVIEW`).
  8. Client Approver inspects Review Queue and executes approval (`APPROVED`).
  9. Content is scheduled on the Marketing Calendar.
  10. Marketing metrics are recorded (Views: 100k, Clicks: 4k, Cost: 10M, Revenue: 35M).
  11. Requests KPI summary (ROAS: 3.5x, ROI: 250%) and triggers AI Doctor strategic recommendations.

- `test_t4_scenario_02_adversarial_compliance_interception_and_remediation`:
  Adversarial content flow:
  1. Marketer drafts aggressive advertising copy with prohibited medical/financial claims ("cam kết 100% hoàn vốn").
  2. Compliance Scanner flags HIGH severity violation.
  3. Submit gate strictly blocks submission with HTTP 422.
  4. Marketer remediates the copy, removing the prohibited guarantee.
  5. Compliance Scanner re-scans and grants `PASSED`.
  6. Content is submitted to `IN_REVIEW` and approved by Client Approver.

- `test_t4_scenario_03_zero_cost_viral_campaign_analytics`:
  Viral organic growth lifecycle:
  1. Campaign generated for TikTok organic viral video.
  2. Content approved and scheduled.
  3. Viral organic metrics ingested (Cost: 0 VNĐ, Views: 500,000, Clicks: 25,000, Revenue: 50,000,000 VNĐ).
  4. KPI engine calculates zero-cost metrics without division by zero.
  5. AI Doctor diagnoses organic viral growth, classifying the campaign health as `HEALTHY` and recommending scaling paid promotion.

---

## 3. Test Runner & Framework Architecture

### Directory Structure
```
backend/
├── tests/
│   ├── conftest.py             # Shared DB, in-memory engine, client fixtures
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── conftest_e2e.py     # E2E-specific fixtures, multi-role auth tokens
│   │   ├── test_tier1_feature_coverage.py
│   │   ├── test_tier2_boundary_corner.py
│   │   ├── test_tier3_cross_feature.py
│   │   ├── test_tier4_real_scenarios.py
│   │   └── run_e2e.py          # Standalone runner with visual report & JSON output
```

### Execution Commands
- **Run Full E2E Suite**:
  ```bash
  pytest backend/tests/e2e/ -v --tb=short
  ```
- **Run Specific Tier**:
  ```bash
  pytest backend/tests/e2e/test_tier1_feature_coverage.py -v
  pytest backend/tests/e2e/test_tier2_boundary_corner.py -v
  pytest backend/tests/e2e/test_tier3_cross_feature.py -v
  pytest backend/tests/e2e/test_tier4_real_scenarios.py -v
  ```
- **Run Standalone E2E Runner**:
  ```bash
  python -m backend.tests.e2e.run_e2e
  ```

---

## 4. Pass / Fail Semantics & Progressive Testability

| Status | Code | Meaning | Action |
|--------|------|---------|--------|
| **PASS** | `green` | Endpoint satisfies all schema, business rules, status codes, and database invariants. | Requirement met. |
| **FAIL** | `red` | Endpoint returned unexpected status code, data corruption, or schema violation. | Escalate bug report to Implementation Track. |
| **XFAIL / PENDING** | `yellow` | Test is authored against a planned milestone (e.g. M2–M6) not yet merged into the active branch. | Marks progressive testability until milestone completion. |

---
*Document published for MarketFlow AI Official Release E2E Testing Track.*
