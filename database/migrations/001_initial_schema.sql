-- QwickService Contact Integrity System - Initial Schema
-- Version: 1.0.0

-- 1. Detection results
CREATE TABLE integrity_detection (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      VARCHAR(255) NOT NULL,
    thread_id       VARCHAR(255) NOT NULL,
    user_id         VARCHAR(255) NOT NULL,
    risk_score      DECIMAL(4,3) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    labels          JSONB NOT NULL DEFAULT '[]',
    evidence_spans  JSONB NOT NULL DEFAULT '[]',
    hashed_tokens   JSONB NOT NULL DEFAULT '[]',
    stage           SMALLINT NOT NULL,
    ruleset_version VARCHAR(50) NOT NULL,
    model_version   VARCHAR(50),
    gps_lat         DECIMAL(10,7),
    gps_lon         DECIMAL(10,7),
    processing_ms   INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_detection_user ON integrity_detection(user_id, created_at DESC);
CREATE INDEX idx_detection_thread ON integrity_detection(thread_id);
CREATE INDEX idx_detection_score ON integrity_detection(risk_score) WHERE risk_score >= 0.40;

-- 2. Moderation cases
CREATE TABLE integrity_case (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_id    UUID NOT NULL REFERENCES integrity_detection(id),
    user_id         VARCHAR(255) NOT NULL,
    thread_id       VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_review','resolved','appealed','overturned')),
    priority        SMALLINT NOT NULL DEFAULT 0,
    assigned_to     VARCHAR(255),
    resolution      VARCHAR(50),
    resolution_note TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_case_status ON integrity_case(status, priority DESC);
CREATE INDEX idx_case_user ON integrity_case(user_id);

-- 3. Strike records
CREATE TABLE integrity_strike (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255) NOT NULL,
    case_id         UUID REFERENCES integrity_case(id),
    detection_id    UUID REFERENCES integrity_detection(id),
    strike_number   SMALLINT NOT NULL,
    action_taken    VARCHAR(50) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    window_start    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_end      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_strike_user_active ON integrity_strike(user_id, is_active) WHERE is_active = TRUE;

-- 4. Moderation actions (immutable audit log)
CREATE TABLE integrity_moderation_action (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID REFERENCES integrity_case(id),
    actor_id        VARCHAR(255) NOT NULL,
    actor_role      VARCHAR(30) NOT NULL,
    action_type     VARCHAR(50) NOT NULL,
    target_user_id  VARCHAR(255) NOT NULL,
    target_scope    VARCHAR(30) NOT NULL,
    reason_code     VARCHAR(50) NOT NULL,
    metadata        JSONB DEFAULT '{}',
    is_permanent    BOOLEAN NOT NULL DEFAULT FALSE,
    requires_human  BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by     VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at: this table is append-only / immutable
);
CREATE INDEX idx_mod_action_case ON integrity_moderation_action(case_id);
CREATE INDEX idx_mod_action_target ON integrity_moderation_action(target_user_id, created_at DESC);

-- 5. Configuration versioning
CREATE TABLE integrity_config_version (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key      VARCHAR(100) NOT NULL,
    config_value    JSONB NOT NULL,
    version         INTEGER NOT NULL,
    changed_by      VARCHAR(255) NOT NULL,
    change_reason   TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    activated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_config_active ON integrity_config_version(config_key) WHERE is_active = TRUE;
CREATE INDEX idx_config_history ON integrity_config_version(config_key, version DESC);

-- Seed initial configuration
INSERT INTO integrity_config_version (config_key, config_value, version, changed_by, change_reason, is_active, activated_at)
VALUES
    ('risk_thresholds', '{
        "allow_max": 0.39,
        "nudge_min": 0.40,
        "nudge_max": 0.64,
        "soft_block_min": 0.65,
        "soft_block_max": 0.84,
        "hard_block_min": 0.85
    }'::jsonb, 1, 'system', 'Initial risk threshold configuration', TRUE, NOW()),
    ('strike_policy', '{
        "window_days": 30,
        "escalation": [
            {"strike": 1, "action": "warning", "duration_hours": 0},
            {"strike": 2, "action": "cooldown", "duration_hours": 24},
            {"strike": 3, "action": "restriction", "duration_hours": 72},
            {"strike": 4, "action": "suspension_candidate", "duration_hours": null}
        ]
    }'::jsonb, 1, 'system', 'Initial strike escalation policy', TRUE, NOW()),
    ('detection_rules', '{
        "ruleset_version": "1.0.0",
        "stage1_weight": 0.50,
        "stage2_weight": 0.30,
        "stage3_weight": 0.20,
        "sync_threshold": 0.65
    }'::jsonb, 1, 'system', 'Initial detection rule weights', TRUE, NOW());
