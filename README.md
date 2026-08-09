# Monika Engineers Integrated ERP

Production foundation for the Monika Engineers ERP and future CRM. Phase 1A-D is implemented as an Axis CRM-based React application backed by a Django modular monolith, PostgreSQL, Redis, and Celery.

The current boundary is deliberate: identity, organization, scoped access control, company configuration, foundation masters, and concurrency-safe numbering are production foundations. Customer, enquiry, project execution, drawing/BOM, purchasing, production, quality, dispatch, service, documents, audit, approvals, and notifications remain later phases.

## Architecture

- `frontend/` - Vite, React 19, TypeScript, TanStack Query, React Hook Form, Zod, shadcn/ui and the preserved Axis visual system.
- `backend/` - Django 5.2 and Django REST Framework modular monolith.
- PostgreSQL - system of record.
- Redis - cache, rate-limit state, and Celery transport.
- Celery - asynchronous work foundation; no later-phase jobs are invented yet.
- `docs/phase-0/` - approved architecture and requirements baseline.
- `docs/phase-1/` - implementation decisions, API and operating notes.
- `deploy/` - deployment notes; production provisioning remains a go-live activity.

The browser uses same-origin session authentication and CSRF protection. Django owns authorization, validation, transactions, and persistence. `User` and `Employee` are separate records with an optional one-to-one link.

## Local URLs

| Surface | URL |
|---|---|
| Production foundation | `http://127.0.0.1:5173/app` |
| Sign in | `http://127.0.0.1:5173/login` |
| Preserved Axis mockup | `http://127.0.0.1:5173/mockups/axis?view=home` |
| Project 360 reference | `http://127.0.0.1:5173/mockups/axis?view=project` |
| Django health | `http://127.0.0.1:8000/api/v1/health/` |
| Django admin | `http://127.0.0.1:8000/admin/` |

## Configure

```powershell
Copy-Item .env.example .env
```

Replace the example secret and database password outside local development. PostgreSQL is published on host port `5433` because port `5432` is commonly occupied by a Windows PostgreSQL service; containers still use port `5432` internally.

## Start the backend services

Install Docker Desktop, then from the repository root:

```powershell
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose ps
```

Create an administrator interactively:

```powershell
docker compose exec backend python manage.py createsuperuser
```

For disposable local QA only, an environment-gated seed command is available. It refuses to run when Django debug mode is off:

```powershell
$env:DEV_ADMIN_EMAIL = "admin@example.local"
$env:DEV_ADMIN_PASSWORD = "choose-a-local-password"
docker compose exec -e DEV_ADMIN_EMAIL=$env:DEV_ADMIN_EMAIL -e DEV_ADMIN_PASSWORD=$env:DEV_ADMIN_PASSWORD backend python manage.py seed_development
```

## Start the frontend

Install Bun, then:

```powershell
Set-Location frontend
bun install
bun run dev
```

Vite proxies `/api` to Django on `127.0.0.1:8000`, keeping session cookies and CSRF same-origin from the browser's perspective.

## Run the backend without Docker

Use Python 3.11 and point the environment at an accessible PostgreSQL and Redis instance:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

## Verification

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest backend -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
```

Frontend:

```powershell
Set-Location frontend
bun run lint
bun run test
bun run build
```

## Requirements and phase boundary

The approved requirement register is [`docs/phase-0/07-requirements-traceability.md`](docs/phase-0/07-requirements-traceability.md). Phase 1 evidence is in [`docs/phase-1`](docs/phase-1). The Axis mockups remain visual regression/reference material and were not replaced by production routes.

Do not treat the foundation as a completed CRM. It is intentionally shaped so customer, contact, enquiry, activity, project, drawing/BOM and service domains can be added without changing the identity, organization, authorization, configuration, or numbering contracts.
