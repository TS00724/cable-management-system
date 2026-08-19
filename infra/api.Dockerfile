FROM python:3.13-slim
WORKDIR /srv/sim
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY apps/api ./apps/api
COPY apps/web ./apps/web
WORKDIR /srv/sim/apps/api
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
