# Verification Report

**Executed:** 2026-08-22 (Asia/Taipei)  
**Policy:** GitHub Actions are disabled. Local named gates are required before PR merge.

| Gate | Result | Evidence |
|---|---|---|
| Full backend suite | PASS / SKIP | 59 passed; 1 real-PostgreSQL runtime gate skipped |
| Shared limiter tests | PASS | shared quota, HMAC persistence, fail-open and fail-closed |
| Four-process runtime smoke | PASS | quota 3; fourth independent process rejected |
| Python compile | PASS | application and migrations compile |
| Legacy frontend syntax | PASS | `app.js` and `webgl-viewer.js` |
| React source gate | PASS | package declarations, TS/TSX parse and helpers |
| Fresh migration | PASS | empty SQLite database upgraded through revision 003 |
| Seed idempotency | PASS | one database seeded twice with stable identifiers |
| Cable Schedule smoke | PASS | seeded CSV export and audit |

## Explicitly not executed

- ordinary-role Forced-RLS matrix against a real PostgreSQL service
- live Keycloak PKCE/refresh/logout/MFA/session-expiry browser lifecycle
- external TLS ingress and production multi-replica rate-limit load
- real S3/MinIO and ClamAV
- GPU, accessibility, load and DAST gates

A PASS applies only to the named boundary. The skipped Pytest item is the real PostgreSQL gate and is not converted into a success claim.
