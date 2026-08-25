# 🏆 Ranking Platform — Backend

FastAPI + MongoDB service powering the gamified leaderboard.

## Run (development)

```bash
pip install -r requirements-dev.txt
export MOCK_DB=1          # in-memory Mongo - zero dependencies (demo only)
uvicorn main:app --reload
```

Interactive docs: http://localhost:8000/api/docs · Health: `/api/health`

Without `MOCK_DB=1`, set `MONGODB_URI` and `DATABASE_NAME` (defaults:
`mongodb://localhost:27017` / `ranking_page_dev`).

## Test

```bash
ruff check .
pytest
```

## Production

```bash
ENVIRONMENT=production SECRET_KEY=... MONGODB_URI=... DATABASE_NAME=... \
ADMIN_EMAIL=... ADMIN_PASSWORD=... \
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Production startup **fails fast** if required settings are missing/unsafe
(see `config.validate_production_config()`).

## Layout

```text
config.py                  typed settings (dev defaults, prod validation)
database.py                Mongo client, indexes, admin seed, auth helpers
main.py                    app wiring, middleware, exception handlers
models/                    pydantic schemas + game rules (points/actions)
middleware/                auth (sessions/CSRF/RBAC) + system (rate limit, headers)
routes/                    auth, leaderboard, members, contributions, points
utils.py                   levels, badges, ledger recomputation
tests/                     pytest suite w/ in-memory MongoDB
```
