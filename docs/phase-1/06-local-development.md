# Local Development

## Prerequisites

- Windows with Docker Desktop
- Python 3.11 for host-side backend work
- Bun for the frontend
- Git

Copy `.env.example` to `.env` and replace example secrets for any environment beyond disposable local development.

## Docker services

From `D:\MonikaERP`:

```powershell
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose ps
```

Services are PostgreSQL, Redis, Django/Gunicorn, and Celery. The expected health endpoint is `http://127.0.0.1:8000/api/v1/health/`. Host PostgreSQL uses port `5433`; this avoids collision with a Windows PostgreSQL installation on `5432`.

Stop containers without deleting database data:

```powershell
docker compose stop
```

## Frontend

```powershell
Set-Location D:\MonikaERP\frontend
bun install
bun run dev
```

Open `http://127.0.0.1:5173/login`. Vite proxies `/api` to port 8000.

## Host-side backend

```powershell
Set-Location D:\MonikaERP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Set PostgreSQL and Redis environment values appropriate to the host before running commands. Tests use `config.settings.test` and require PostgreSQL for transaction/locking confidence.

## Development identity

Prefer `createsuperuser`. A repeatable `seed_development` command exists only for local UI QA. It requires `DEV_ADMIN_EMAIL` and `DEV_ADMIN_PASSWORD` and is rejected when `DEBUG=False`. Never store its password in source, migrations, screenshots, or documentation.

## Quality gates

```powershell
.\.venv\Scripts\python.exe -m pytest backend -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
Set-Location frontend
bun run lint
bun run test
bun run build
```

The generated `dist`, virtual environment, caches, `.env`, and local database artifacts are ignored by Git.
