.PHONY: test dry-run verify seed run

DRY_RUN_DB ?= /tmp/sim-dry-run.db

test:
	cd apps/api && PYTHONPATH=. pytest -q

dry-run: test
	cd apps/api && PYTHONPATH=. python -m compileall -q app migrations
	node --check apps/web/app.js
	node --check apps/web/webgl-viewer.js
	rm -f $(DRY_RUN_DB)
	cd apps/api && DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PLATFORM_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) MIGRATION_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PYTHONPATH=. alembic upgrade head
	cd apps/api && DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PLATFORM_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) MIGRATION_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PYTHONPATH=. python -m app.seed
	cd apps/api && DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PLATFORM_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) MIGRATION_DATABASE_URL=sqlite+pysqlite:///$(DRY_RUN_DB) PYTHONPATH=. python -m app.seed
	rm -f $(DRY_RUN_DB)

verify: dry-run

seed:
	cd apps/api && PYTHONPATH=. python -m app.seed

run:
	cd apps/api && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
