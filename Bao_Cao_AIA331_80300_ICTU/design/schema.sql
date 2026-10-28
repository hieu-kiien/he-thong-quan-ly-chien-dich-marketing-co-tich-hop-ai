-- MarketFlow AI — Lược đồ Cơ sở dữ liệu Quan hệ 14 Bảng (PostgreSQL 16 / SQLite WAL)
-- Đồng bộ 100% với SQLAlchemy 2.0 ORM trong backend/app/models/

PRAGMA foreign_keys = ON;

-- 1. Bảng users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('MANAGER', 'MARKETER')),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng channels
CREATE TABLE channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(30) NOT NULL UNIQUE CHECK (code IN ('FACEBOOK', 'INSTAGRAM', 'TIKTOK', 'EMAIL', 'GOOGLE_ADS', 'ZALO_OA', 'WEBSITE')),
    name VARCHAR(100) NOT NULL,
    format_rules JSON NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng brand_profile
CREATE TABLE brand_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name VARCHAR(200) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    tone_of_voice TEXT NOT NULL DEFAULT '',
    target_audience TEXT NOT NULL DEFAULT '',
    guidelines TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng banned_keywords
CREATE TABLE banned_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword VARCHAR(100) NOT NULL UNIQUE,
    note VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Bảng campaigns
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    goal VARCHAR(30) NOT NULL,
    objective TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    product TEXT NOT NULL,
    key_message TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (budget >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED',
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT date_range CHECK (end_date >= start_date)
);

-- 6. Bảng campaign_channels
CREATE TABLE campaign_channels (
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL REFERENCES channels(id),
    planned_budget NUMERIC(14, 2) CHECK (planned_budget IS NULL OR planned_budget >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (campaign_id, channel_id)
);

-- 7. Bảng ai_threads
CREATE TABLE ai_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL DEFAULT 'Phiên mới',
    opencode_session_id VARCHAR(100),
    pinned BOOLEAN NOT NULL DEFAULT 0,
    last_message_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Bảng ai_messages
CREATE TABLE ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES ai_threads(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('USER', 'ASSISTANT', 'TOOL')),
    content TEXT NOT NULL DEFAULT '',
    parts_json JSON NOT NULL DEFAULT '[]',
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETE',
    error_code VARCHAR(50),
    model VARCHAR(100),
    latency_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. Bảng ai_actions
CREATE TABLE ai_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES ai_threads(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES ai_messages(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool VARCHAR(64) NOT NULL,
    args_json JSON NOT NULL DEFAULT '{}',
    summary VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED', 'EXECUTED', 'REJECTED', 'FAILED')),
    result_json JSON,
    error TEXT,
    executed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Bảng contents
CREATE TABLE contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    channel_id INTEGER NOT NULL REFERENCES channels(id),
    content_type VARCHAR(30) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    cta VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED')),
    origin VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    ai_message_id INTEGER REFERENCES ai_messages(id) ON DELETE SET NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    published_url VARCHAR(500),
    published_at TIMESTAMP,
    published_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. Bảng content_reviews
CREATE TABLE content_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    decision VARCHAR(20) NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 12. Bảng schedules
CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP NOT NULL,
    assignee_id INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED',
    note TEXT,
    done_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 13. Bảng metrics
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    channel_id INTEGER NOT NULL REFERENCES channels(id),
    metric_date DATE NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    source VARCHAR(20) NOT NULL,
    entered_by INTEGER REFERENCES users(id),
    import_batch VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metrics_campaign_channel_date UNIQUE (campaign_id, channel_id, metric_date),
    CONSTRAINT counts_non_negative CHECK (views >= 0 AND clicks >= 0 AND conversions >= 0),
    CONSTRAINT cost_non_negative CHECK (cost >= 0),
    CONSTRAINT clicks_le_views CHECK (views = 0 OR clicks <= views),
    CONSTRAINT conversions_le_clicks CHECK (clicks = 0 OR conversions <= clicks)
);

-- 14. Bảng notifications
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(40) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    link VARCHAR(255),
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
