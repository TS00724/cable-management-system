# Third-Party Software Register

| Package / image | Intended range | License | Repository | Purpose | Modifications | Redistribution notes |
|---|---:|---|---|---|---|---|
| FastAPI | 0.128.x | MIT | fastapi/fastapi | Typed REST API | None | Retain notice |
| SQLAlchemy | 2.0.x | MIT | sqlalchemy/sqlalchemy | ORM and transactions | None | Retain notice |
| Alembic | 1.18.x | MIT | sqlalchemy/alembic | Database migrations | None | Retain notice |
| PostgreSQL | 17.x | PostgreSQL | postgres/postgres | Primary database and RLS | None | Retain notice |
| Keycloak | 26.x | Apache-2.0 | keycloak/keycloak | OIDC/SSO/MFA scaffold | Realm configuration | Retain notices |
| qrcode | 8.x | BSD-3-Clause | lincolnloop/python-qrcode | Permission-protected QR SVG | None | Retain notice |

The browser client uses native Web APIs and WebGL, so the delivered vertical slice has no JavaScript runtime dependency.
Production release must generate lockfiles, an SBOM, and a final license review.
