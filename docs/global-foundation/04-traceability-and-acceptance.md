# Global Foundation Traceability and Acceptance

Status terms: **Implemented** means code and automated evidence exist in this branch. **Partial** means reusable infrastructure/current-module coverage exists but the milestone's universal or operational acceptance is still open. **Deferred** means no false implementation is claimed.

| Requirement area | Status | Evidence / boundary |
|---|---|---|
| Dedicated Owner Control Centre | Implemented | `/app/owner`, owner layout, permission-filtered control groups and header entry |
| Business Owner vs superuser | Implemented foundation | RBAC Owner permissions/continuity; superuser remains technical bypass. Production Owner assignments remain deployment data |
| Privilege escalation/final Owner | Implemented | Server guard and security tests |
| Administrative optimistic concurrency | Implemented | Shared `VersionedUpdateMixin`, 409 conflict, versioned admin models/tests |
| Current operational ownership/work registry | Implemented | Seven current work types mapped without a polymorphic ownership model |
| Bulk reassignment/history/idempotency | Implemented | Sorted row locks, atomic 1–100 batch, mandatory reason, Audit/domain events/tests |
| Employee/login disable safety | Implemented | Impact endpoint/dialog, reassign-or-leave choice, final-owner/self guard, reactivate path/tests |
| Access explanation | Implemented | Backend service/API and Owner UI, Deny precedence test |
| Feature controls | Implemented | Company-scoped/versioned/audited controls; stale browser blocked by backend; unfinished modules unavailable |
| Data quality | Implemented initial checks | Non-mutating current-module checks and remediation links |
| System health | Implemented safe checks | Database/cache/storage real checks; honest Configured/Unknown/Not configured states |
| Realtime/auth refresh | Implemented foundation | Existing Channels/presence/invalidation reused; admin/feature events invalidate auth/owner roots; 60-second auth refresh |
| Numbering and approval administration | Reused | Existing row-locked numbering UI and versioned approval workflow UI linked from Owner Control |
| Imports | Partial | Existing CSV/XLSX templates and atomic imports reused; persisted import-job history/checksum/preview remains open |
| Role editor | Partial | Grouped/searchable/section and individual selection exists; duplicate-role and affected-user impact preview remain open |
| Audit governance | Implemented foundation | Existing immutable Audit plus owner lifecycle, configuration and reassignment events. Rich sensitive-action filter remains open |
| Universal conflict/unsaved comparison | Partial | Backend protection and current focused frontend conflict UX exist; not every form has a reusable review-my-changes dialog |
| Universal archive/restore | Partial | Current domain lifecycle rules reused; not every administrative master has explicit archive/restore UI |
| Background jobs and backup visibility | Deferred/accurate | Health reports Unknown/Not configured; no fake worker heartbeat, retry console, backup time or restore-test result |
| Integration administration | Partial | Website credential status is masked; credential configure/rotate/test screens and other integrations remain future work |
| Future ERP modules | Deferred | Drawing/BOM/purchase/inventory transactions/production/quality/dispatch/service/AMC/HR/finance are not enabled or fabricated |
| Multi-account/browser UAT | Open production gate | Requires distinct real accounts plus stable browser automation/manual session on production-like Channels/Redis |

## Automated evidence to record at handoff

- Backend full suite, Ruff, Django checks, migration consistency and deployment check.
- Frontend full suite, lint, TypeScript/Vite build and whitespace check.
- PostgreSQL concurrency and realtime suites are part of the backend suite.
- Docker Compose is configuration-validated only; Docker is not required for the user's lightweight local workflow.

## Acceptance decision

This branch delivers a substantial reusable foundation and a real Owner Control Centre, but it must not be represented as satisfying every universal checkbox in the 181-section milestone. The future-module implementations, production integration/backup telemetry, universal conflict UX, persisted import administration, role-impact tooling, and distinct-account browser UAT are explicit open gates.

Recommended next milestone: **Owner Administration Completion & Multi-account UAT**—finish role/permission impact flows, persisted import jobs, universal conflict component coverage, integration/backup telemetry adapters, then run recorded Owner/Sales/Engineering sessions against production-like PostgreSQL + Redis/Channels.
