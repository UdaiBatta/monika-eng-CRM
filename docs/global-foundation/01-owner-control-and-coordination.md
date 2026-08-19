# Owner Control and Multi-user Coordination Foundation

## Purpose

This milestone adds shared business-administration and work-coordination infrastructure without creating a generic database editor. PostgreSQL remains authoritative, Audit records historical evidence, notifications remain persistent attention items, and realtime remains an optional delivery mechanism.

## Implemented architecture

- `/app/owner` is the dedicated Owner Control Centre. It is permission-gated and intentionally absent from the ordinary employee sidebar.
- `system.owner_control.view/manage`, `system.access_explanation.view`, `system.work.reassign`, `system.data_quality.view`, `system.system_health.view`, and `system.override.perform` extend the existing RBAC catalogue.
- Business Owner access is represented through RBAC. Django superuser remains a distinct technical emergency capability. Normal code does not test role names.
- The final active business Owner cannot be disabled or stripped through normal role, assignment, override, user, or employee lifecycle APIs.
- An administrator cannot grant permissions they do not possess. Technical superuser bypass remains deliberate and auditable.
- `VersionedUpdateMixin` provides row-locked optimistic concurrency for administrative records. A missing/stale `record_version` is rejected; stale updates return HTTP 409.
- Existing domain ownership fields remain intact. `owner_services.py` presents a shared coordination view over incoming enquiries, enquiries, engineering reviews, quotations, Customer POs, Sales Orders, and Project engineering handoffs.
- Reassignment locks the affected domain record, accepts 1–100 items, executes atomically, requires a reason, increments version where available, and publishes the existing Audit/domain event flow. Reassigning to the current employee is an idempotent no-op.
- Employee/login deactivation first reports assigned open work. The controlled action either reassigns that work or explicitly leaves it assigned temporarily; it never silently deletes history.
- Implemented feature controls are backend-authoritative, company-scoped, versioned and audited. Unfinished modules are returned as `Not available yet` and cannot be enabled.
- Auth state includes enabled feature keys. TanStack Query periodically refreshes it and realtime configuration/permission events invalidate it.
- System health performs real safe checks for database, cache and document-storage initialization, and reports configuration/unknown state for realtime, workers, website credentials and backups without exposing secrets.
- Data-quality checks are deterministic and non-mutating: employee organization/login gaps, scoped accounts without an employee, exact customer-name duplicates, ownerless projects, and open work assigned to inactive employees.

## Data integrity rules

1. Domain state, not presence or UI state, decides whether an action is available.
2. Unrelated records are never globally locked.
3. Reassignment changes current responsibility but keeps the Audit/assignment history.
4. Completed records are excluded from bulk reassignment.
5. Historical commercial/approval/document records continue to use revision, amendment, cancellation or archive mechanisms already present in their domains.
6. Feature disablement blocks future creation and does not remove existing records.
7. Realtime failure cannot make a committed HTTP transaction invalid.

## Current phase boundary

This is a reusable foundation, not a claim that unbuilt ERP modules now exist. Drawing Management, BOM, purchasing, stock transactions, production, quality, dispatch, service/AMC, HR and finance remain future business modules. They must adopt these shared concurrency, RBAC, Audit, ownership and realtime conventions when implemented.

The following broader milestone items remain deliberately open: universal before-create duplicate suggestions, universal unsaved-change comparison, a generic role impact preview/role duplication tool, persisted import-job history/checksums, background-job retry administration, external backup/restore telemetry, integration credential rotation UI, and multi-account/browser UAT on production-like Redis/Channels infrastructure.
