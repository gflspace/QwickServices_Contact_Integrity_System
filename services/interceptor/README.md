# Chat Interceptor Plugin

Production-grade pre-send hook for the Contact Integrity System. Performs inline Stage 1 detection with <100ms response time and fail-open semantics.

## Architecture

### Components

1. **config.ts** - Configuration management with environment variable validation
2. **interceptor.ts** - Core pattern detection and risk scoring engine
3. **async-emitter.ts** - Redis Stream publisher for async processing pipeline
4. **circuit-breaker.ts** - Protection against cascading failures
5. **index.ts** - WebSocket server and HTTP health endpoints

### Design Principles

- **Fail-open**: System defaults to allowing messages if any component fails
- **Low latency**: Stage 1 detection optimized for <100ms response time
- **Resilient**: Circuit breaker prevents cascading failures
- **Observable**: Comprehensive logging and health endpoints

## Installation

```bash
npm install
```

## Configuration

Environment variables with defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_THRESHOLD` | `0.65` | Risk score above this blocks synchronously |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `DETECTION_HOST` | `localhost` | Detection service host |
| `DETECTION_PORT` | `8000` | Detection service port |
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Failures before circuit opens |
| `CIRCUIT_BREAKER_RESET_MS` | `30000` | Time before circuit retry |
| `MAX_MESSAGE_LENGTH` | `10000` | Maximum message length |
| `WS_PORT` | `8080` | WebSocket server port |
| `HEALTH_PORT` | `8081` | Health check HTTP port |

## Usage

### Development

```bash
npm run dev
```

### Production

```bash
npm run build
npm start
```

### Testing

```bash
npm test
```

## WebSocket API

### Request Format

```json
{
  "type": "intercept",
  "request_id": "optional-request-id",
  "message": {
    "message_id": "msg-123",
    "thread_id": "thread-456",
    "user_id": "user-789",
    "content": "Message text here",
    "timestamp": "2025-01-01T12:00:00Z",
    "gps_lat": 37.7749,
    "gps_lon": -122.4194
  }
}
```

### Response Format

```json
{
  "type": "intercept_result",
  "request_id": "optional-request-id",
  "processing_ms": 45,
  "result": {
    "allowed": false,
    "action": "hard_block",
    "risk_score": 0.75,
    "labels": ["contact_info_phone"],
    "block_reason": "Message blocked: detected phone number"
  }
}
```

### Response Actions

- `allow` - Message passes (risk_score < 0.4)
- `nudge` - Message allowed with warning (0.4 ≤ risk_score < 0.65)
- `hard_block` - Message blocked (risk_score ≥ 0.65)

## Pattern Detection

### Stage 1 Inline Patterns

**Phone Numbers**
- International: `+44 20 7123 4567`
- US formats: `(555) 123-4567`, `555-123-4567`, `555.123.4567`
- Condensed: `5551234567`

**Emails**
- Standard: `user@example.com`
- Obfuscated: `user (at) example (dot) com`
- Spaced: `u s e r @ e x a m p l e . c o m`

**URLs**
- With protocol: `https://example.com`
- Without protocol: `www.example.com`
- Shorteners: `bit.ly/abc123`, `tinyurl.com/xyz`

**Social Platforms**
- Keywords: `whatsapp`, `telegram`, `snapchat`, `discord`, `kik`, `signal`
- Patterns: `DM me`, `text me`, `contact me at`

**Obfuscation**
- Excessive spacing: `5  5  5  1  2  3  4  5  6  7`
- Character substitution: `(at)`, `(dot)`
- Number spelling: `five five five`

## Risk Scoring

Risk scores are calculated using weighted pattern matching:

- **Phone**: 0.4 weight
- **Email**: 0.35 weight
- **URL**: 0.3 weight
- **Social**: 0.25 weight
- **Obfuscation**: 0.15 weight

Scores are normalized to 0.0-1.0 range with diminishing returns for multiple matches.

## Circuit Breaker

Protects against cascading failures with three states:

1. **CLOSED** - Normal operation
2. **OPEN** - Too many failures, fail-open (allow all)
3. **HALF_OPEN** - Testing recovery

Configuration:
- Opens after 5 consecutive failures (configurable)
- Resets after 30 seconds (configurable)
- Fail-open semantics: allows messages when open

## Async Processing

Messages are emitted to Redis Stream `cis:messages` for async Stage 2+ analysis:

```
Stream Key: cis:messages
Event Format:
{
  message_id: string
  thread_id: string
  user_id: string
  content: string
  timestamp: string
  gps_lat?: number
  gps_lon?: number
  intercept_result: {
    allowed: boolean
    action: string
    risk_score: number
    labels: string[]
  }
  emitted_at: string
}
```

## Health & Monitoring

### Health Check

```
GET http://localhost:8081/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00Z",
  "checks": {
    "websocket": "ok",
    "circuit_breaker": "closed",
    "redis": "connected"
  }
}
```

### Metrics

```
GET http://localhost:8081/metrics
```

Response:
```json
{
  "circuit_breaker": {
    "state": "closed",
    "failure_count": 0
  },
  "redis": {
    "connected": true,
    "stream_length": 1234,
    "stream_last_id": "1234567890-0"
  },
  "websocket": {
    "active_connections": 5
  }
}
```

## Error Handling

### Fail-Open Scenarios

The interceptor fails open (allows messages) in these cases:

1. Circuit breaker is OPEN
2. Interceptor throws exception
3. Redis unavailable (async emit only)
4. Invalid message format

All failures are logged with appropriate context.

### Error Response

```json
{
  "type": "error",
  "request_id": "optional-request-id",
  "error": "processing_error",
  "message": "Internal server error"
}
```

## Performance

Target metrics:
- **Latency**: <100ms p99 for clean messages
- **Throughput**: >1000 messages/sec per instance
- **Availability**: 99.9% with fail-open semantics

## Security Considerations

1. **Input Validation**: Max message length enforced
2. **DoS Protection**: Circuit breaker prevents overload
3. **Privacy**: Content patterns are hashed in async pipeline
4. **Fail-Safe**: Fail-open prevents accidental censorship

## Testing

Test coverage includes:
- Clean message handling
- Phone/email/URL detection
- Social platform detection
- Nudge message generation
- Circuit breaker behavior
- Edge cases (empty, oversized, invalid)
- Fail-open scenarios

Run tests with coverage:
```bash
npm test
```

## Deployment

### Docker

```bash
docker build -t cis-interceptor .
docker run -p 8080:8080 -p 8081:8081 \
  -e REDIS_HOST=redis \
  -e SYNC_THRESHOLD=0.65 \
  cis-interceptor
```

### Environment Requirements

- Node.js 20+
- Redis 6+ (for async processing)
- TypeScript 5+

## Troubleshooting

### Circuit Breaker Open

Check logs for failure pattern. Reset threshold or timeout if needed.

### Redis Connection Issues

Verify Redis connectivity. Service continues with fail-open if Redis unavailable.

### High Latency

Review pattern complexity. Consider adjusting sync threshold to move more work async.

## Contributing

Follow these principles:
- Maintain fail-open semantics
- Add tests for new patterns
- Document configuration changes
- Preserve <100ms latency target

## License

Proprietary - QwickServices Contact Integrity System
