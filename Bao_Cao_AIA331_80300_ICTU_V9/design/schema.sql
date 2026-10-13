-- AIA331 / 80300
-- Design baseline for the marketing campaign management system.
-- This file is a proposed SQLite schema, not evidence of a running application.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('MANAGER', 'MARKETER')),
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'DISABLED')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_categories (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id              INTEGER PRIMARY KEY,
    category_id     INTEGER NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    usp             TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INACTIVE')),
    FOREIGN KEY (category_id) REFERENCES product_categories(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE marketing_channels (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    format_rules    TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE campaigns (
    id              INTEGER PRIMARY KEY,
    product_id      INTEGER NOT NULL,
    owner_id        INTEGER NOT NULL,
    name            TEXT NOT NULL,
    objective       TEXT NOT NULL,
    audience        TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    budget          NUMERIC NOT NULL DEFAULT 0 CHECK (budget >= 0),
    status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (status IN
                        ('DRAFT', 'PLANNED', 'ACTIVE', 'PAUSED',
                         'COMPLETED', 'ARCHIVED')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    FOREIGN KEY (product_id) REFERENCES products(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (owner_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE campaign_members (
    campaign_id     INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    member_role     TEXT NOT NULL DEFAULT 'CONTRIBUTOR'
                    CHECK (member_role IN ('OWNER', 'CONTRIBUTOR')),
    assigned_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (campaign_id, user_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE marketing_contents (
    id              INTEGER PRIMARY KEY,
    campaign_id     INTEGER NOT NULL,
    channel_id      INTEGER NOT NULL,
    created_by      INTEGER NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    cta             TEXT,
    status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (status IN
                        ('DRAFT', 'AI_DRAFT', 'IN_REVIEW', 'APPROVED',
                         'REJECTED', 'PUBLISHED')),
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    warnings_json   TEXT NOT NULL DEFAULT '[]',
    version_no      INTEGER NOT NULL DEFAULT 1 CHECK (version_no > 0),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES marketing_channels(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE content_reviews (
    id              INTEGER PRIMARY KEY,
    content_id      INTEGER NOT NULL,
    reviewer_id     INTEGER NOT NULL,
    decision        TEXT NOT NULL CHECK
                    (decision IN ('APPROVED', 'REJECTED', 'REQUEST_CHANGES')),
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES marketing_contents(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE marketing_schedules (
    id              INTEGER PRIMARY KEY,
    content_id      INTEGER NOT NULL,
    scheduled_at    TEXT NOT NULL,
    timezone        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PLANNED'
                    CHECK (status IN ('PLANNED', 'CANCELLED', 'EXECUTED')),
    created_by      INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES marketing_contents(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE campaign_metrics (
    id              INTEGER PRIMARY KEY,
    campaign_id     INTEGER NOT NULL,
    channel_id      INTEGER NOT NULL,
    metric_date     TEXT NOT NULL,
    views           INTEGER NOT NULL DEFAULT 0 CHECK (views >= 0),
    clicks          INTEGER NOT NULL DEFAULT 0 CHECK (clicks >= 0),
    conversions     INTEGER NOT NULL DEFAULT 0 CHECK (conversions >= 0),
    cost            NUMERIC NOT NULL DEFAULT 0 CHECK (cost >= 0),
    revenue         NUMERIC NOT NULL DEFAULT 0 CHECK (revenue >= 0),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (campaign_id, channel_id, metric_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES marketing_channels(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (clicks <= views)
);

CREATE TABLE ai_logs (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    campaign_id     INTEGER,
    task_type       TEXT NOT NULL CHECK
                    (task_type IN ('IDEA', 'DRAFT', 'SUMMARY')),
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    input_hash      TEXT NOT NULL,
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    output_json     TEXT,
    result_status   TEXT NOT NULL CHECK
                    (result_status IN
                        ('SUCCESS', 'SCHEMA_ERROR', 'TIMEOUT',
                         'RATE_LIMIT', 'PROVIDER_ERROR', 'BLOCKED')),
    error_code      TEXT,
    latency_ms      INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX idx_campaigns_owner_status
    ON campaigns(owner_id, status);
CREATE INDEX idx_campaigns_dates
    ON campaigns(start_date, end_date);
CREATE INDEX idx_contents_campaign_status
    ON marketing_contents(campaign_id, status);
CREATE INDEX idx_reviews_content_created
    ON content_reviews(content_id, created_at);
CREATE INDEX idx_schedules_time_status
    ON marketing_schedules(scheduled_at, status);
CREATE INDEX idx_metrics_campaign_date
    ON campaign_metrics(campaign_id, metric_date);
CREATE INDEX idx_ai_logs_campaign_created
    ON ai_logs(campaign_id, created_at);
