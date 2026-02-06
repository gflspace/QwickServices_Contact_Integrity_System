# QwickService Contact Integrity System (CIS)

## Project Overview
Monorepo for the Contact Integrity System — detects, scores, and prevents off-platform contact exchange in QwickService marketplace chat.

## Architecture
- **Interceptor** (Node.js/TS): WebSocket middleware plugin, pre-send hook, <100ms sync path
- **Detection** (Python/FastAPI): NLP + rules engine, 3-stage pipeline (regex → spaCy → behavioral)
- **Policy** (Python/FastAPI): Risk thresholds, strike escalation, enforcement actions
- **Review** (Python/FastAPI): Moderation queue, case management, appeals
- **Dashboard** (React/TS/Vite): Admin UI with role-based views (moderator/ops/executive)
- **Database**: PostgreSQL 15+ with 5 core tables, Redis 7+ for streams/caching

## Service Communication
```
Chat → Interceptor (sync, Stage 1 only) → Redis Stream → Detection (async, full pipeline)
  → Policy Engine → Enforcement Actions + Review Cases
```

## Key Conventions
- All services fail-open (allow messages if downstream is unavailable)
- Moderation action table is append-only / immutable (no UPDATE/DELETE)
- Risk scores are 0.000–1.000; thresholds: 0.40 (nudge), 0.65 (block), 0.85 (hard block + strike)
- Strikes use 30-day rolling window
- All timestamps in UTC (TIMESTAMPTZ)

## Development Commands
- **Full stack**: `docker-compose up --build`
- **Detection tests**: `cd services/detection && python -m pytest tests/`
- **Policy tests**: `cd services/policy && python -m pytest tests/`
- **Review tests**: `cd services/review && python -m pytest tests/`
- **Interceptor tests**: `cd services/interceptor && npm test`
- **Dashboard dev**: `cd services/dashboard && npm run dev`
- **Dashboard tests**: `cd services/dashboard && npm test`

## Environment
- Copy `.env.example` to `.env` for local development
- PostgreSQL on port 5432, Redis on port 6379
- Detection on :8001, Policy on :8002, Review on :8003, Dashboard on :3000, Interceptor on :8000
