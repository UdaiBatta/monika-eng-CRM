# Shared Services Integration and Operations

Status: Phase 1A–H foundation complete; CRM and operational modules are not started.

## Integration contract

Future domains register controlled entity capabilities, use explicit transaction-safe command services and publish lightweight in-process `DomainEvent` values. Synchronous subscribers create mandatory audit evidence. `transaction.on_commit` subscribers create retryable notifications only for committed work. Documents, audit, approvals and notifications do not depend on future CRM, Engineering or Procurement apps.

## API summary

All endpoints remain under `/api/v1/` with session authentication, CSRF protection, the shared error envelope, pagination and server-side RBAC. Major new route groups are `/documents`, `/document-categories`, `/audit/events`, `/audit/entities`, `/approval-workflows`, `/approval-workflow-versions`, `/approval-step-definitions`, `/approval-conditions`, `/approvals/requests`, `/notifications` and `/notification-preferences`.

Business error codes such as `SELF_APPROVAL_NOT_ALLOWED`, `APPROVAL_NOT_ASSIGNED`, `APPROVAL_ALREADY_DECIDED`, `INVALID_APPROVAL_TRANSITION` and `INACTIVE_APPROVER` are preserved in the API envelope so the UI can explain failures without database terminology.

## Security review

- UUID access is always followed by permission and company-scope checks.
- Private files have no public local URL; download and historical-version download reauthorize.
- Size, extension, detected file signature/MIME and normalized names limit spoofing/path traversal.
- Approval state changes require both assignment and permission, use row locks and default to no self-approval.
- Inactive recipients are excluded from new notifications; recipient IDs are server-owned.
- Audit queries are company scoped and audit records cannot be mutated through the application.
- Session command endpoints retain CSRF protection.
- Lists are paginated and indexed; related records are selected/prefetched on high-use queues.

## Configuration and recovery

The local Docker stack is PostgreSQL, Redis, Django and Celery. R2 settings are documented in `.env.example`; local private storage is the default. PostgreSQL backups cover metadata, approvals, audit and notifications. Complete document recovery additionally requires the object store and matching version. Feature flags may later hide documents, approvals or notifications safely, but core audit infrastructure is not optional.

## Verification commands

```powershell
$env:POSTGRES_PORT = "5433"
.\.venv\Scripts\python.exe -m pytest backend -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run

Set-Location frontend
bun run lint
bun run test
bun run build
```

The preserved design references remain `/mockups/axis?view=home` and `/mockups/axis?view=project`; the production shared-service routes use real Django/PostgreSQL data.
