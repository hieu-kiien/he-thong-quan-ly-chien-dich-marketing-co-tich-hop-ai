PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('MANAGER','MARKETER')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    usp TEXT NOT NULL,
    audience TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','INACTIVE')),
    FOREIGN KEY (category_id) REFERENCES product_categories(id)
        ON DELETE RESTRICT
);

CREATE TABLE marketing_channels (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    format_rules TEXT NOT NULL
);

CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    budget REAL NOT NULL CHECK (budget >= 0),
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','ACTIVE','PAUSED','DONE')),
    CHECK (end_date >= start_date),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE marketing_contents (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','AI_DRAFT','PENDING',
                          'APPROVED','REJECTED','PUBLISHED')),
    ai_provider TEXT,
    prompt_version TEXT,
    source_ids TEXT,
    rejection_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (channel_id) REFERENCES marketing_channels(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE marketing_schedules (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL,
    scheduled_at TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    status TEXT NOT NULL DEFAULT 'PLANNED'
        CHECK (status IN ('PLANNED','CANCELLED','EXECUTED')),
    FOREIGN KEY (content_id) REFERENCES marketing_contents(id)
);

CREATE TABLE campaign_metrics (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    metric_date TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0 CHECK (views >= 0),
    clicks INTEGER NOT NULL DEFAULT 0 CHECK (clicks >= 0),
    conversions INTEGER NOT NULL DEFAULT 0 CHECK (conversions >= 0),
    cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
    revenue REAL NOT NULL DEFAULT 0 CHECK (revenue >= 0),
    UNIQUE (campaign_id, channel_id, metric_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (channel_id) REFERENCES marketing_channels(id)
);

CREATE TABLE ai_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    campaign_id INTEGER,
    function_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    result_status TEXT NOT NULL,
    error_code TEXT,
    source_ids TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);
