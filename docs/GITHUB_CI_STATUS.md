# GitHub Publication / Validation Status

GitHub Actions are intentionally **disabled** by repository policy.

- no `.github/workflows/*.yml` file is introduced
- the reproducible development gate is `make dry-run`
- dry-run evidence is recorded in [`DRY_RUN_STATUS.md`](DRY_RUN_STATUS.md)
- confidence boundaries are recorded in [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md)
- validated commits may advance `main` only by non-force fast-forward

## Current publication attempt

- last readable remote `main`: `2536ee32b76cc70d9e6efa172fd24881288568b6`
- local P0 dry-run: PASS — 56 passed, 1 real-PostgreSQL gate skipped
- branch/file/ref writes: explicitly attempted after user authorization
- connector result: `Resource not found` for write resources
- remote `main` advanced: **no**
- Actions used: **no**

The clean source archive and a non-force Git object pack are produced so the verified batch is
recoverable without rewriting history. This file must be updated after the next successful remote
fast-forward.
