# Monika Engineers Integrated ERP

Production ERP workspace for Monika Engineers Pvt. Ltd. The current executable is a frontend proof-of-concept built with Vite, React, TypeScript, shadcn/ui, and the StyleUI Axis CRM template. Production architecture is a Django modular monolith with PostgreSQL, Redis, Celery, private object storage, Nginx and Docker.

## Production program status

Phase 0 architecture and traceability are documented in [`docs/phase-0`](docs/phase-0/README.md). The production backend, authentication, database and business workflows have not started; the running interface remains a design and workflow reference.

## UI proof-of-concept

Open the isolated ERP mockup at:

```text
http://127.0.0.1:5173/mockups/axis?view=home
```

Available views are `home`, `sales`, `project`, `purchase`, and `service`. The screens use realistic static demonstration data and do not call an API.

The generated visual references used to guide the implementation are stored in `design-references/`.

## Run locally

```powershell
bun install
bun run dev
```

## Architecture direction

The backend will use Django and Django REST Framework. No backend, API, authentication, database, or production business logic is included in the UI experiment yet.

The production boundary is an Axis CRM-based React frontend consuming versioned Django REST API endpoints. Django owns authentication, permissions, validation, workflows, audit history and persistence. PostgreSQL is never exposed to employee browsers.

Active Git branch: `ui-axis-experiment`.
