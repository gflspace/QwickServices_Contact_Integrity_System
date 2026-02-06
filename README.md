# QwickService Contact Integrity System (CIS)

A modular system that detects, scores, and prevents off-platform contact exchange in QwickService marketplace chat.

## Architecture

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Interceptor | Node.js/TypeScript | 8000 | WebSocket chat middleware, sync pre-send hook |
| Detection | Python/FastAPI | 8001 | NLP + rules engine, 3-stage detection pipeline |
| Policy | Python/FastAPI | 8002 | Risk thresholds, strike escalation, enforcement |
| Review | Python/FastAPI | 8003 | Moderation queue, case management, appeals |
| Dashboard | React/TypeScript | 3000 | Admin UI (moderator, ops, executive views) |
| PostgreSQL | PostgreSQL 15 | 5432 | Primary data store |
| Redis | Redis 7 | 6379 | Message streams, caching |

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build

# Or run individual services for development
cd services/detection && pip install -e ".[dev]" && uvicorn src.main:app --reload --port 8001
```

## Detection Pipeline

1. **Stage 1 (Rules)**: Deterministic regex patterns — phone numbers, emails, URLs, social handles, obfuscation detection
2. **Stage 2 (NLP)**: spaCy intent classifier for off-platform intent
3. **Stage 3 (Behavioral)**: Repetition and escalation analysis per user/thread

## Risk Score Actions

| Score | Action | Type |
|-------|--------|------|
| 0.00–0.39 | Allow + log | Automatic |
| 0.40–0.64 | In-chat nudge | Automatic |
| 0.65–0.84 | Soft block / quarantine | Auto (reversible) |
| 0.85–1.00 | Hard block + strike + review | Auto + human review |

## Testing

```bash
./scripts/run-tests.sh
```
