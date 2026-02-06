# Policy & Enforcement Engine

Production-grade policy enforcement service for the Contact Integrity System. Implements threshold-based risk classification and rolling-window strike management with configurable escalation policies.

## Architecture

### Core Components

1. **Threshold Engine** (`engine/thresholds.py`)
   - Maps risk scores (0.0-1.0) to risk bands (LOW, MEDIUM, HIGH, CRITICAL)
   - Configurable thresholds for runtime tuning and A/B testing
   - Validates threshold configurations to prevent gaps/overlaps

2. **Strike Manager** (`engine/strikes.py`)
   - Tracks policy violations with 30-day rolling window
   - Escalation policy: WARNING → COOLDOWN (24h) → RESTRICTION (72h) → SUSPENSION_CANDIDATE
   - Automatic expiry of strikes outside rolling window

3. **Action Engine** (`engine/actions.py`)
   - Combines risk classification with strike history
   - Generates user-facing enforcement messages
   - Creates audit trail for moderation actions

### Risk Band Classification

| Risk Score | Risk Band | Base Action | Description |
|------------|-----------|-------------|-------------|
| 0.00 - 0.39 | LOW | ALLOW | Message delivered normally |
| 0.40 - 0.64 | MEDIUM | NUDGE | Warning shown, message delivered |
| 0.65 - 0.84 | HIGH | SOFT_BLOCK | Message blocked, strike added |
| 0.85 - 1.00 | CRITICAL | HARD_BLOCK | Message blocked, strike added |

### Strike Escalation Policy

| Strike # | Action | Duration | Scope |
|----------|--------|----------|-------|
| 1 | WARNING | - | Message |
| 2 | COOLDOWN | 24 hours | Account |
| 3 | RESTRICTION | 72 hours | Account |
| 4+ | SUSPENSION_CANDIDATE | Until review | Account |

## API Endpoints

### POST /api/v1/enforce
Evaluate a detection result and determine enforcement action.

**Request:**
```json
{
  "detection_id": "det_abc123",
  "user_id": "user_456",
  "thread_id": "thread_789",  // optional
  "risk_score": 0.75,
  "labels": ["harassment", "inappropriate"]
}
```

**Response:**
```json
{
  "action": "warning",
  "risk_band": "high",
  "strike_count": 1,
  "strike_id": "strike_uuid",
  "case_id": "case_abc123",
  "enforcement_details": {
    "duration_hours": null,
    "message": "Your message was flagged for harassment...",
    "scope": "message"
  }
}
```

### GET /api/v1/strikes/{user_id}
Get strike history for a user.

**Query Parameters:**
- `active_only` (boolean, default: true) - Return only active strikes

**Response:**
```json
{
  "user_id": "user_456",
  "strikes": [
    {
      "id": "strike_uuid",
      "user_id": "user_456",
      "strike_number": 1,
      "action_taken": "warning",
      "is_active": true,
      "window_start": "2025-01-15T10:00:00Z",
      "window_end": "2025-02-14T10:00:00Z",
      "case_id": "case_abc123",
      "detection_id": "det_abc123"
    }
  ],
  "total_active": 1
}
```

### GET /api/v1/thresholds
Get current threshold configuration.

**Response:**
```json
{
  "allow_max": 0.39,
  "nudge_min": 0.40,
  "nudge_max": 0.64,
  "soft_block_min": 0.65,
  "soft_block_max": 0.84,
  "hard_block_min": 0.85
}
```

### PUT /api/v1/thresholds
Update threshold configuration (admin only).

**Request:**
```json
{
  "thresholds": {
    "allow_max": 0.35,
    "nudge_min": 0.36,
    "nudge_max": 0.60,
    "soft_block_min": 0.61,
    "soft_block_max": 0.80,
    "hard_block_min": 0.81
  },
  "changed_by": "admin@example.com",
  "reason": "A/B test: stricter nudge threshold"
}
```

### DELETE /api/v1/strikes/{strike_id}
Deactivate a specific strike (admin action, typically after appeal).

**Response:**
```json
{
  "status": "success",
  "message": "Strike abc123 deactivated"
}
```

### GET /api/v1/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "policy-enforcement",
  "version": "1.0.0"
}
```

## Running the Service

### Local Development

```bash
# Install dependencies
cd services/policy
pip install -e .

# Run the service
python -m services.policy.src.main

# Or using uvicorn directly
uvicorn services.policy.src.main:app --reload --port 8002
```

### Docker

```bash
# Build image
docker build -t cis-policy:latest .

# Run container
docker run -p 8002:8002 \
  -e POSTGRES_HOST=postgres \
  -e REDIS_HOST=redis \
  cis-policy:latest
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | cis | Database name |
| `POSTGRES_USER` | cis_user | Database user |
| `POSTGRES_PASSWORD` | changeme_in_production | Database password |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `POLICY_PORT` | 8002 | Service port |
| `POLICY_LOG_LEVEL` | info | Log level |
| `POLICY_STRIKE_WINDOW_DAYS` | 30 | Strike rolling window |

## Testing

### Run Full Test Suite

```bash
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Threshold classification tests
pytest tests/test_thresholds.py -v

# Strike management tests
pytest tests/test_strikes.py -v

# API integration tests
pytest tests/test_api.py -v
```

### Quick Validation

```bash
python run_tests.py
```

### Test Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

## Design Decisions

### In-Memory Strike Storage

Current implementation uses in-memory storage for simplicity. In production, this should be replaced with persistent storage (PostgreSQL + Redis):

```python
# Production implementation would use:
# - PostgreSQL for durable strike history
# - Redis for fast active strike lookups
# - Background job to expire old strikes
```

### Strike Escalation Philosophy

The escalation policy is designed to be:
1. **Educational first**: First strike is a warning, not punishment
2. **Progressive**: Each violation increases consequences
3. **Time-bounded**: Strikes expire to allow rehabilitation
4. **Human-reviewed**: Severe cases (4+ strikes) require human review

### Threshold Configurability

Thresholds are configurable to support:
- **A/B testing**: Test different enforcement strictness levels
- **Adaptation**: Adjust to changing abuse patterns
- **Experimentation**: Find optimal balance of precision/recall

### Action Message Design

Enforcement messages follow these principles:
- **Clear**: Explain what happened and why
- **Actionable**: Tell user what to do next
- **Non-hostile**: Educational tone, not punitive
- **Specific**: Include relevant violation details

## Production Considerations

### Monitoring

Monitor these metrics:
- Enforcement action distribution (allow/nudge/block/etc.)
- Strike escalation rates
- Average strikes per user
- Threshold boundary crossings
- API latency (p50, p95, p99)

### Scaling

For high throughput:
1. Add Redis for distributed strike storage
2. Implement caching for threshold config
3. Use connection pooling for database
4. Consider read replicas for strike queries

### Audit Trail

All enforcement actions should be logged with:
- Detection ID
- User ID
- Risk score and labels
- Action taken
- Strike count
- Case ID (for follow-up)
- Timestamp

### Error Handling

The service implements defensive error handling:
- Invalid risk scores → 422 validation error
- Invalid thresholds → 400 bad request with rollback
- Unknown errors → 500 with sanitized error message
- All errors logged for investigation

### Security

- **Input validation**: All inputs validated via Pydantic models
- **No PII in logs**: User IDs are opaque identifiers
- **Admin actions**: Threshold updates require authentication (implement in production)
- **Rate limiting**: Add rate limits to prevent abuse (not implemented yet)

## Future Enhancements

1. **Persistent Storage**: Migrate to PostgreSQL + Redis
2. **Appeal Workflow**: Allow users to appeal strikes
3. **Context-Aware Escalation**: Consider user history, account age
4. **ML-Based Threshold Tuning**: Automatically optimize thresholds
5. **Batch Processing**: Support bulk enforcement decisions
6. **Webhook Notifications**: Notify other services of enforcement actions
7. **Analytics Dashboard**: Real-time enforcement metrics
8. **Policy Templates**: Pre-configured threshold sets for different communities

## File Structure

```
services/policy/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   ├── main.py                # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoints
│   └── engine/
│       ├── __init__.py
│       ├── thresholds.py      # Risk classification
│       ├── strikes.py         # Strike management
│       └── actions.py         # Enforcement logic
├── tests/
│   ├── __init__.py
│   ├── test_thresholds.py    # Threshold tests (67 tests)
│   ├── test_strikes.py       # Strike tests (43 tests)
│   └── test_api.py           # API tests (38 tests)
├── Dockerfile
├── pyproject.toml
├── run_tests.py              # Quick validation script
└── README.md                 # This file
```

## Contributing

When adding new features:
1. Add comprehensive tests (aim for >90% coverage)
2. Document new endpoints in this README
3. Update OpenAPI schema (auto-generated from FastAPI)
4. Add appropriate error handling
5. Include logging for debugging
6. Consider backward compatibility

## License

Internal use only - Contact Integrity System
