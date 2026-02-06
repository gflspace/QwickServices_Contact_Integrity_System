-- Test seed data for CIS development
-- Uses deterministic UUIDs for predictable testing

-- Test detections
INSERT INTO integrity_detection (id, message_id, thread_id, user_id, risk_score, labels, evidence_spans, hashed_tokens, stage, ruleset_version, processing_ms)
VALUES
    ('a0000000-0000-0000-0000-000000000001', 'msg-001', 'thread-100', 'user-alice', 0.92,
     '["phone_number", "obfuscation"]',
     '[{"offset": 10, "length": 14, "type": "phone", "text": "***redacted***"}]',
     '["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]',
     1, '1.0.0', 45),

    ('a0000000-0000-0000-0000-000000000002', 'msg-002', 'thread-100', 'user-alice', 0.55,
     '["intent_phrase"]',
     '[{"offset": 0, "length": 30, "type": "intent", "text": "***redacted***"}]',
     '[]',
     2, '1.0.0', 320),

    ('a0000000-0000-0000-0000-000000000003', 'msg-003', 'thread-200', 'user-bob', 0.78,
     '["email", "social_handle"]',
     '[{"offset": 5, "length": 20, "type": "email", "text": "***redacted***"}]',
     '["d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"]',
     1, '1.0.0', 38),

    ('a0000000-0000-0000-0000-000000000004', 'msg-004', 'thread-300', 'user-carol', 0.25,
     '[]', '[]', '[]',
     1, '1.0.0', 12);

-- Test cases
INSERT INTO integrity_case (id, detection_id, user_id, thread_id, status, priority)
VALUES
    ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'user-alice', 'thread-100', 'open', 5),
    ('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000003', 'user-bob', 'thread-200', 'in_review', 3);

-- Test strikes
INSERT INTO integrity_strike (id, user_id, case_id, detection_id, strike_number, action_taken, is_active, window_start, window_end)
VALUES
    ('c0000000-0000-0000-0000-000000000001', 'user-alice', 'b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     1, 'warning', TRUE, NOW(), NOW() + INTERVAL '30 days');

-- Test moderation actions
INSERT INTO integrity_moderation_action (id, case_id, actor_id, actor_role, action_type, target_user_id, target_scope, reason_code, metadata)
VALUES
    ('d0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'system', 'system', 'block', 'user-alice', 'message', 'phone_detected',
     '{"risk_score": 0.92, "auto_action": true}'),
    ('d0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'mod-dan', 'moderator', 'quarantine', 'user-bob', 'thread', 'email_detected',
     '{"risk_score": 0.78, "manual_review": true}');
