# Shared Atomic Rate Limiting

## Implemented boundary

`RATE_LIMIT_BACKEND=database` selects a SQL-backed fixed-window counter. Every request key combines the tenant, actor and effective client address. The complete value is HMAC-SHA256 pseudonymized before persistence.

The `(key_hash, window_start_epoch)` primary key is updated through a dialect-native atomic upsert on PostgreSQL and SQLite. A transaction-based fallback exists for other SQL dialects. Expired rows are removed opportunistically.

Configuration:

```text
RATE_LIMIT_BACKEND=memory|database
RATE_LIMIT_DATABASE_URL=<optional dedicated SQL URL>
RATE_LIMIT_KEY_SECRET=<required non-default secret in production>
RATE_LIMIT_FAIL_MODE=open|closed
RATE_LIMIT_RETENTION_SECONDS=3600
RATE_LIMIT_CLEANUP_INTERVAL_SECONDS=60
```

Production configuration rejects the in-memory backend and the default rate-limit secret.

## Failure policy

- `closed`: an unavailable shared backend returns HTTP 503.
- `open`: the request continues and returns `X-RateLimit-Policy: degraded-open` so the degraded state can be logged and alerted.

## Verification

The local runtime smoke launches four independent processes against one SQL database. With a quota of three, the first three calls are accepted and the fourth is rejected. Unit tests also prove cross-instance sharing, HMAC persistence and both failure policies.

## Remaining production proof

This batch does not claim production completion. It still requires a real multi-replica deployment using PostgreSQL or another atomic shared backend, concurrency/load testing, cleanup monitoring, and external TLS/trusted-proxy/cookie-CSRF verification.
