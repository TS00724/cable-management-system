.PHONY: test verify seed run

test:
	cd apps/api && PYTHONPATH=. pytest -q

verify: test
	cd apps/api && PYTHONPATH=. python -m compileall -q app migrations
	node --check apps/web/app.js
	node --check apps/web/webgl-viewer.js

seed:
	cd apps/api && PYTHONPATH=. python -m app.seed

run:
	cd apps/api && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
