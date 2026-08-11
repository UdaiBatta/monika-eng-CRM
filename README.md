# Monika Engineers Integrated ERP

Production Monika Engineers ERP/CRM foundation. Phase 1A-H and the Phase 2 incoming-enquiry-to-Ready-for-Sales-Order commercial CRM vertical slice are implemented as an Axis CRM-based React application backed by a Django modular monolith and PostgreSQL, with Channels/Redis/Celery available for production realtime and asynchronous workloads.

The current production path is unified Incoming Enquiry -> Human Review -> Customer/Contact -> Enquiry/RFQ -> Engineering Feasibility -> Commercial Estimation -> optional Shared Approval -> Quotation -> Communication/Negotiation -> Customer Confirmation -> Ready for Sales Order. Sales Order, Project execution, Drawing Management, BOM, purchasing, production, quality, dispatch, and service remain later phases.

## Architecture

- `frontend/` - Vite, React 19, TypeScript, TanStack Query, React Hook Form, Zod, shadcn/ui and the preserved Axis visual system.
- `backend/` - Django 5.2 and Django REST Framework modular monolith.
- PostgreSQL - system of record.
- Redis - production Channels layer, cache/rate-limit state, and Celery transport; local development uses native in-memory substitutes.
- Celery - asynchronous work foundation; no later-phase jobs are invented yet.
- `docs/phase-0/` - approved architecture and requirements baseline.
- `docs/phase-1/` - implementation decisions, API and operating notes.
- `docs/phase-2/` - commercial CRM design, operator guide, acceptance evidence, and traceability.
- `deploy/` - deployment notes; production provisioning remains a go-live activity.

The browser uses same-origin session authentication and CSRF protection. Django owns authorization, validation, transactions, and persistence. `User` and `Employee` are separate records with an optional one-to-one link.

## Local URLs

| Surface | URL |
|---|---|
| Production foundation | `http://127.0.0.1:5173/app` |
| Customers | `http://127.0.0.1:5173/app/crm/customers` |
| Enquiries and RFQs | `http://127.0.0.1:5173/app/crm/enquiries` |
| Engineering reviews | `http://127.0.0.1:5173/app/crm/engineering` |
| Incoming enquiries | `http://127.0.0.1:5173/app/crm/incoming-enquiries` |
| Commercial estimates | `http://127.0.0.1:5173/app/crm/estimates` |
| Quotations | `http://127.0.0.1:5173/app/crm/quotations` |
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

Use Python 3.11 and point the environment at an accessible PostgreSQL instance. Development settings use in-process cache and eager tasks, so Redis/Celery are not required for this local workflow:

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

The approved requirement register is [`docs/phase-0/07-requirements-traceability.md`](docs/phase-0/07-requirements-traceability.md). Phase 1 evidence is in [`docs/phase-1`](docs/phase-1), and the Phase 2 handoff is in [`docs/phase-2`](docs/phase-2). The Axis mockups remain visual regression/reference material and were not replaced by production routes.

The commercial CRM implementation reaches the explicit Ready for Sales Order handoff. Production acceptance still requires the approved quotation DOCX template, LibreOffice/Redis deployment validation, and distinct-employee realtime UAT recorded in [`docs/phase-2/15-realtime-quotation-acceptance.md`](docs/phase-2/15-realtime-quotation-acceptance.md). Do not treat this as a completed ERP lifecycle: no Sales Order, Project, Drawing Management, or BOM production module exists yet.
