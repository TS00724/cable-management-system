# Third-Party Software Register

| Package / component | Version range / pin | License | Purpose | Modifications / redistribution notes |
|---|---|---|---|---|
| FastAPI | >=0.128,<0.129 | MIT | API framework | no vendoring |
| SQLAlchemy | >=2.0.50,<2.1 | MIT | relational ORM | no vendoring |
| Alembic | >=1.18,<1.19 | MIT | migrations | no vendoring |
| PostgreSQL | supported deployment | PostgreSQL License | production database/RLS | external service |
| Keycloak | deployment image | Apache-2.0 | OIDC identity provider | realm configuration only |
| PyJWT[crypto] | >=2.10,<3 | MIT | JWT/JWK verification | no vendoring |
| HTTPX | >=0.28,<0.29 | BSD-3-Clause | OIDC discovery/JWKS HTTP | redirects disabled |
| qrcode | >=8,<9 | BSD | QR SVG labels | no vendoring |
| React / Refine / Ant Design stack | exact pins in `apps/web-react/package.json` | MIT/Apache-2.0 | isolated enterprise WebUI scaffold | no copied branding/assets; lockfile and transitive notice still required |

See `THIRD_PARTY_NOTICES.md` and `docs/OPEN_SOURCE_INVENTORY.md` for direct frontend details.
