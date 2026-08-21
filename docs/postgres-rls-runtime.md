# PostgreSQL Forced-RLS runtime proof

The migration enables and forces RLS for tenant-owned tables. Execute the new real-database gate:

```bash
export RLS_TEST_APPLICATION_DSN='postgresql://sim_app:...@localhost/sim'
export RLS_TEST_PLATFORM_DSN='postgresql://sim_platform:...@localhost/sim'
make postgres-rls
```

The application connection is rejected as proof unless it is all of the following:

- not superuser
- not `BYPASSRLS`
- not owner of `locations`
- connected to a table with RLS enabled
- connected to a table with `FORCE ROW LEVEL SECURITY`

The platform connection creates temporary Tenant A/B fixtures. Tenant A then performs this matrix
through the ordinary application connection:

| Attack | Required result |
|---|---|
| list locations | Tenant B hidden, Tenant A visible |
| direct Tenant B UUID lookup | zero rows |
| update Tenant B | zero rows |
| delete Tenant B | zero rows |
| insert Tenant B while scoped as A | PostgreSQL RLS violation |
| insert Tenant A | succeeds |

Fixtures are removed in a `finally` block by the platform role. Role-precondition unit tests pass,
but the current environment has no configured PostgreSQL DSNs. The actual attack matrix is
**NOT EXECUTED**, so PostgreSQL RLS confidence remains below 100%.
