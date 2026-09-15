CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'auditor')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    rule_gid INTEGER NOT NULL,
    rule_signature_id INTEGER NOT NULL,
    rule_revision INTEGER NOT NULL,
    rule_signature TEXT NOT NULL,
    rule_category TEXT,
    rule_severity INTEGER,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alert_categorizations (
    alert_id BIGINT PRIMARY KEY REFERENCES alerts(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES categories(id),
    user_id BIGINT NOT NULL REFERENCES users(id),
    categorized_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alert_focus (
    alert_id BIGINT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    focused_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (alert_id, user_id)
);

CREATE TABLE autocategories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category_id BIGINT NOT NULL REFERENCES categories(id),
    field_path TEXT NOT NULL,
    match_value TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id BIGINT,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX alerts_uncategorized_idx ON alerts (event_timestamp DESC, id DESC);
CREATE INDEX alerts_rule_idx ON alerts (rule_gid, rule_signature_id, rule_revision);
CREATE INDEX alerts_source_idx ON alerts (source_id, event_timestamp DESC);
CREATE INDEX audit_entity_idx ON audit_log (entity_type, entity_id, created_at DESC);
