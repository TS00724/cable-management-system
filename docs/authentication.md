# OIDC authentication and Principal mapping

## Implemented request path

```text
Browser / service
  -> Authorization: Bearer <JWT> or configured same-site auth cookie
  -> PyJWT verification against configured/discovered JWKS
  -> algorithm + kid + signature + issuer + audience + expiry + required claims
  -> UserIdentity.oidc_subject mapping
  -> optional verified-email linking (off by default)
  -> token tenant claim consistency check
  -> existing TenantMembership / AccessGrant Principal resolution
  -> permission + project + location authorization
```

JWT claims identify a provisioned user. They do not replace application authorization. The same
`resolve_principal` service still evaluates tenant membership or explicit scoped contractor grants.

## Auth modes

- `demo`: development-only `X-Actor-ID`; an OIDC token is rejected.
- `oidc`: bearer/cookie JWT is mandatory; demo headers are not credentials.
- `hybrid`: prefer OIDC and allow `X-Actor-ID` only when no token exists and `DEMO_MODE=true`.

Production settings reject anything except `AUTH_MODE=oidc` and `DEMO_MODE=false`.

## Verified token properties

The API validates signing algorithm, `kid`, JWKS key, signature, issuer, audience, expiry, clock
skew, required claims and optional `tenant_id` consistency. Authentication failures return 401
with `WWW-Authenticate: Bearer`; a tenant-claim mismatch is a 403 authorization failure.

## Key loading

Keys may come from `OIDC_JWKS_JSON`, a configured `OIDC_JWKS_URL`, or issuer discovery. Discovery
redirects are rejected and the discovery issuer must exactly equal the configured issuer. Cache
keys include issuer, JWKS URL and inline JWKS content so test or tenant configurations cannot
reuse another key set accidentally.

## Browser scaffold

`apps/web-react/` implements Authorization Code + PKCE helpers. Access tokens are held in
`sessionStorage` and attached to API requests; decoded browser claims are never used as an
authorization decision. The target route is `/app-next/`; `/app/` remains the verified legacy UI.

## Remaining identity work

- live Keycloak login, refresh, expiry, logout and MFA proof
- identity provisioning and subject-linking administration UI
- external IdP federation, SAML and SCIM
- browser E2E and session-expiry UX
