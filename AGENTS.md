# AGENTS.md — lab-tooling

This file describes the repository structure, key components, and best practices for AI agents and developers working in this codebase.

---

## Repository Overview

**`lab-tooling`** is a full-stack monorepo scaffold demonstrating a modern development toolchain. It is structured as a reference implementation rather than a domain application, combining:

- **Angular 21** frontend with SSR
- **FastAPI** backend (Python 3.12)
- **SQLite** database via SQLAlchemy 2
- **Nx 22** monorepo orchestration

The application exposes a minimal CRUD "items" API and a single-page Angular frontend that consumes it. The primary purpose is to provide a working baseline for tooling experiments.

---

## Monorepo Structure

```
lab-tooling/
├── apps/
│   ├── backend/          # FastAPI Python application
│   ├── frontend/         # Angular 21 SSR application
│   └── frontend-e2e/     # Playwright end-to-end tests
├── libs/                 # Shared libraries (currently empty)
├── data/
│   └── sqlite/           # Local SQLite database files (dev)
├── infra/
│   └── compose/
│       └── docker-compose.yml
├── nx.json
├── package.json
├── tsconfig.base.json
├── jest.config.ts
├── jest.preset.js
├── eslint.config.mjs
└── .env.example
```

---

## Key Components

### Frontend (`apps/frontend/`)

| Aspect | Detail |
|---|---|
| Framework | Angular 21.2, SSR enabled (`@angular/ssr` + Express) |
| Rendering | All routes use `RenderMode.Prerender` — effectively static prerender |
| HTTP client | `provideHttpClient(withFetch())` — uses native fetch |
| Change detection | Zone-based, `eventCoalescing: true` |
| Forms | Template-driven with `FormsModule` / `[(ngModel)]` |
| Template syntax | Modern Angular control flow: `@if`, `@for` |
| Unit tests | Jest 30 + `jest-preset-angular` |
| E2E tests | Playwright (`apps/frontend-e2e/`) |
| Linting | ESLint 9 flat config + `angular-eslint` |

**`AppComponent`** (`src/app/app.component.ts`):
- Calls `GET /health` and `GET /api/items` on init
- Displays backend health status with CSS class toggle (`.ok` / `.error`)
- Item creation form (name required, description optional)
- Items list rendered with `@for … track item.id`

**`ApiService`** (`src/app/services/api.service.ts`):
- `getHealth()` → `GET /health`
- `getItems()` → `GET /api/items`
- `createItem(item)` → `POST /api/items`
- Base URL read from `environment.apiUrl` (default: `http://localhost:8000`)

**Environment files** (`src/environments/`):
- `environment.ts` — development (apiUrl: `http://localhost:8000`)
- `environment.prod.ts` — production (same value; update for real deployments)

---

### Backend (`apps/backend/`)

| Aspect | Detail |
|---|---|
| Framework | FastAPI ≥ 0.115 + Uvicorn |
| Python version | 3.12 |
| ORM | SQLAlchemy ≥ 2.0 (sync sessions, `DeclarativeBase`) |
| Validation | Pydantic ≥ 2.0 schemas |
| Database | SQLite at `data/sqlite/app.db` (dev) or `/data/app.db` (Docker) |
| Startup | `init_db()` runs on lifespan — creates the directory and calls `Base.metadata.create_all()` |

**API Endpoints:**

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/health` | Liveness probe | `{"status": "ok"}` |
| `GET` | `/api/items` | List all items | `list[ItemRead]` |
| `POST` | `/api/items` | Create an item | `ItemRead` (201) |

**CORS configuration** (priority order):
1. `CORS_ALLOW_ALL=true` → `allow_origins=["*"]`
2. `CORS_ALLOWED_ORIGINS` → comma-separated list
3. Default: `http://localhost:4200,http://127.0.0.1:4200`

**Data model (`Item`):** `id` (int PK), `name` (str, required), `description` (str, nullable)

**Schemas:**
- `ItemCreate`: `name: str`, `description: str | None = None`
- `ItemRead`: adds `id: int`, `model_config = ConfigDict(from_attributes=True)`

---

### Infrastructure

**Docker Compose** (`infra/compose/docker-compose.yml`):

| Service | Build context | Host port | Volumes |
|---|---|---|---|
| `backend` | `apps/backend/` | `${BACKEND_PORT:-8000}` | `apps/backend` → `/app`; `data/sqlite` → `/data` |
| `frontend` | workspace root | `${FRONTEND_PORT:-4200}` | `apps/frontend/src` → `/app/apps/frontend/src` |

- `frontend` depends on `backend`
- Both services restart `unless-stopped`
- `DATABASE_URL` is injected from `.env`

**Environment variables** (copy `.env.example` → `.env`):

```dotenv
DATABASE_URL=sqlite:////data/app.db   # four slashes = absolute path inside Docker
BACKEND_PORT=8000
FRONTEND_PORT=4200
```

Additional runtime variables (not in `.env.example`):

| Variable | Effect |
|---|---|
| `CORS_ALLOW_ALL` | Set to `true`/`1`/`yes` to allow all CORS origins |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins |

---

### Tooling

| Tool | Version | Purpose |
|---|---|---|
| Nx | 22.6.3 | Monorepo task orchestration & caching |
| TypeScript | ~5.9.0 | Shared config in `tsconfig.base.json` |
| Jest | 30.x | Unit tests (frontend + future shared libs) |
| Playwright | ^1.36.0 | E2E tests (Chromium, Firefox, WebKit) |
| ESLint | 9.x (flat config) | TypeScript/HTML linting + module boundary enforcement |
| SWC | ~1.15 | Faster TS compilation for Nx |
| flake8 | — | Python linting |
| pytest | — | Python unit tests |

**Nx task caching:** `build`, `lint`, and `test` outputs are cached. Avoid side effects in these tasks.

**Nx named inputs:**
- `default` — all project files + shared globals
- `production` — excludes spec files, configs, and test-setup files (used for build caching)

---

## Common Commands

```bash
# Install dependencies
npm install

# Serve frontend (http://localhost:4200)
npx nx serve frontend

# Serve backend (http://localhost:8000)
npx nx serve backend

# Run all unit tests
npx nx run-many -t test

# Run frontend unit tests only
npx nx test frontend

# Run E2E tests
npx nx e2e frontend-e2e

# Lint all projects
npx nx run-many -t lint

# Start full stack with Docker Compose
cp .env.example .env
docker compose -f infra/compose/docker-compose.yml up --build
```

---

## Best Practices

### General

- **Run tasks through Nx** (`npx nx run <project>:<target>`) to benefit from caching and consistent configuration.
- **Keep `libs/` for shared code.** Place any logic shared between frontend and future apps inside `libs/` as Nx libraries. Do not duplicate code across `apps/`.
- **Do not commit `.env`** — use `.env.example` as the source of truth for required variables.

### Frontend

- **Use modern Angular control flow** (`@if`, `@for`, `@switch`) instead of `*ngIf` / `*ngFor` structural directives.
- **Track items by identity in `@for`** — always use `track item.id` (or another stable key) to avoid unnecessary DOM re-renders.
- **Keep environment config in `environments/`** — never hard-code API URLs or flags in components or services.
- **Add new routes to `app.routes.ts`** and update `app.routes.server.ts` accordingly when introducing server-side rendering considerations.
- **Prefer `inject()` for dependency injection** in new components over constructor injection.
- **SSR awareness** — avoid browser-only APIs (`window`, `document`, `localStorage`) at the top level; guard them with `isPlatformBrowser()`.
- **Prefer signals** for new reactive state instead of `BehaviorSubject` once the codebase grows.
- **Budget enforcement** — keep initial bundle under 500 KB (warning) / 1 MB (error) as configured in `project.json`.

### Backend

- **Use Pydantic schemas** for all request bodies and response models; never expose SQLAlchemy models directly to the API layer.
- **Session management** — always use the `get_db` dependency (yields a session and closes it after the request). Do not create sessions manually in route handlers.
- **Schema evolution** — the current setup uses `create_all()` only. For any schema change introduce Alembic migrations rather than relying on drop-and-recreate.
- **CORS** — set `CORS_ALLOWED_ORIGINS` explicitly in production; avoid `CORS_ALLOW_ALL=true` outside of local development.
- **No auth currently** — all endpoints are public. Add authentication (e.g., OAuth2 / JWT) before any non-local deployment.
- **Docker containers run with `--reload`** — this is development-only. Use a production-grade Uvicorn configuration (workers, no reload) for deployments.

### Infrastructure / Docker

- **Volume mounts for hot reload** — both services mount source directories, so code changes reflect without rebuilding the image in dev.
- **Do not use `--disable-host-check`** in production Angular builds; it is present only for the Docker dev workflow.
- **Use the `${VARIABLE:-default}` form** in `docker-compose.yml` to keep defaults explicit and allow easy overriding via `.env`.

### Testing

- **Unit tests co-located** — spec files live next to the source file they test (`*.spec.ts`, `test_*.py`).
- **Use Nx's `production` named input** for build tasks to exclude test files from build cache keys.
- **Playwright traces** are captured on the first retry — inspect the `playwright-report/` directory after a failed E2E run.
- **Backend tests** run with `pytest`; add new test files under `apps/backend/` following the `test_*.py` convention.

### TypeScript / Linting

- **Strict mode is enabled** — do not disable `strict`, `noImplicitOverride`, or `strictTemplates`.
- **Module boundaries** — ESLint enforces Nx module boundaries. Do not import across apps directly; route shared logic through `libs/`.
- **Path aliases** — `tsconfig.base.json` has an empty `paths` object. When adding a shared library, register its path alias there.

---

## Current Limitations & Known Gaps

| Area | Status |
|---|---|
| Authentication | None — all endpoints are public |
| Database migrations | No Alembic — schema managed by `create_all()` only |
| Shared libraries | `libs/` is empty — no shared code yet |
| Angular signals | Not yet used — uses RxJS Observables |
| Production Docker configs | Both Dockerfiles are dev-mode (hot reload, no hardening) |
| Frontend routing | `app.routes.ts` is empty — only the root route exists |
| Path aliases | `tsconfig.base.json` paths is empty — no `@lib/*` aliases configured |
