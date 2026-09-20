# AI Data Analyst Platform

A production-style data analyst platform, built in deliberate phases to learn
the underlying engineering — not just wrap an LLM around a database.

## Phase 1 — Data Fundamentals (in progress)

Goal: **Upload a CSV → inspect it → understand its structure → perform
analysis through FastAPI.** No LLM yet.

### Design decisions (the *why*, not just the *what*)

**Dynamic tables over generic JSONB storage.** Each uploaded dataset gets its
own real Postgres table with inferred column types, created via SQLAlchemy
Core DDL at ingestion time. We chose this over a single generic
`dataset_rows(data JSONB)` table because it's the only approach that makes
later phases (NL→SQL generation, query validation) teach real SQL against
real schemas, rather than querying a JSON blob.

**Alembic manages the fixed schema only.** `datasets` and `dataset_columns`
(metadata *about* uploads) are Alembic-managed ORM models. The dynamic
per-upload tables (the actual row data) are created/dropped at runtime and
deliberately kept outside Alembic's scope — migrations can't reasonably
version tables that don't exist until a user uploads a file.

**`get_settings()` over a bare `settings` import.** Wrapped in `lru_cache` so
config is parsed once, but callable — this makes it trivial to override
settings in tests later via FastAPI's `dependency_overrides`.

### Local setup

```bash
# 1. Start Postgres
docker compose up -d

# 2. Backend setup
cd backend
python -m venv .venv && source .venv/bin/activate   # or your preferred env tool
pip install -r requirements.txt
cp .env.example .env

# 3. Run the first migration (creates `datasets` and `dataset_columns` tables)
alembic revision --autogenerate -m "create datasets and dataset_columns tables"
alembic upgrade head

# 4. Run the API
uvicorn app.main:app --reload
```

Then check `http://localhost:8000/health` and `http://localhost:8000/docs`.

### Project structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/v1/               # route handlers (empty until step 5)
│   ├── core/
│   │   ├── config.py         # Pydantic Settings, single source of truth
│   │   └── database.py       # engine, session factory, declarative Base
│   ├── models/                # Dataset, DatasetColumn (fixed schema, ORM)
│   ├── schemas/                # Pydantic request/response models (next)
│   ├── services/                # dataset_service.py — ingestion logic (next)
│   ├── analytics/                # profiling.py, statistics.py (Phase 1/2)
│   └── utils/
├── alembic/                   # migrations for the FIXED schema only
├── tests/
└── requirements.txt
```

### Status

**Phase 1 — Data Fundamentals: complete.**

- [x] Project scaffold
- [x] Config + database wiring
- [x] `Dataset` / `DatasetColumn` models
- [x] First Alembic migration
- [x] CSV/Excel ingestion service (dynamic table creation, type inference,
      identifier sanitization, savepoint-based partial-failure recovery)
- [x] Dataset profiling service (per-column stats, type-driven)
- [x] `POST /datasets/upload`, `GET /datasets`, `GET /datasets/{id}`,
      `GET /datasets/{id}/profile`
- [x] Tests (71 passing — type inference, naming/sanitization, ingestion,
      profiling, API layer)
- [x] Frontend scaffold (Vite + React + Tailwind v4) — dataset list,
      upload with drag-and-drop, dataset detail/profile view

### Real bugs hit and fixed along the way (worth remembering)

- **pandas 3.0's string dtype change**: type inference only checked
  `is_object_dtype`, missing pandas 3.0+'s dedicated `StringDtype`.
  Fixed by checking both.
- **Type detection vs. type coercion are different steps**: inferring a
  column is `DATETIME` doesn't convert its values — a column full of
  `"2024-01-01"` strings still needs an explicit `pd.to_datetime()` pass
  before it can bind to a SQLAlchemy `DateTime` column. Same for
  nullable-integer columns pandas stores as `float64`.
- **SQLite `:memory:` + FastAPI's `TestClient` run in different
  threads**: fixed with `StaticPool` + `check_same_thread=False` in test
  fixtures. Postgres doesn't have this issue — SQLite-only gotcha.
- **Ordering by timestamp alone breaks on ties**: two rows created
  within the same clock tick sort unpredictably; added `id` as a
  secondary sort key.

### Next: Phase 2 — Analytics Engine

Aggregations, descriptive statistics, correlations, distributions,
outlier detection, time-series analysis — building on the profiling
service's foundation.
