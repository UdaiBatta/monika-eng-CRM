# Phase 1A-D Foundation Implementation

Status: COMPLETE for the approved Phase 1A-D boundary on 2026-08-10.

## Delivered boundary

The repository is now a production-oriented workspace with separate `frontend`, `backend`, `docs`, and `deploy` boundaries. The backend is a Django modular monolith with apps for accounts, organization, RBAC, configuration, masters, numbering, and shared core behavior. PostgreSQL is the source of truth, Redis supports cache and rate limiting, and Celery is connected for future asynchronous work.

The production React application is separate from the preserved Axis proof-of-concept. `/app` and its child routes use live Django data. `/mockups/axis?view=home` and `/mockups/axis?view=project` remain unchanged design references.

## Important decisions

- UUID primary keys and created/updated timestamps are used across the foundation.
- User authentication identity and employee organization identity are separate, optionally linked records.
- Authorization is data driven and evaluated server-side; frontend permission-aware navigation is a convenience, not a security boundary.
- Company ownership is explicit and cross-company references are rejected by model and serializer validation.
- No default business roles were invented. The permission catalog is seeded; administrators define role composition when business decisions are available.
- INR is the only seeded business master. Other company masters require explicit input.
- Feature flags are company-scoped release controls, not hard-coded feature switches.
- The drawing/BOM workspace remains a product direction for a later engineering phase; Phase 1 does not create fake drawing documents.

## Production UI

The Axis-derived shell provides responsive navigation, login, live service health, foundation metrics, employee list/detail/forms, and generic searchable, sortable and paginated administration for organization, access, settings, masters, and numbering. Forms use React Hook Form and Zod; server data uses TanStack Query; route bundles are lazy loaded.

## Known limitations

- The backend currently exposes the DRF browsable API in development; production settings disable debug behavior.
- OpenAPI schema generation is not yet installed.
- Celery is operational but has no business tasks in this phase.
- File/object storage, audit history, approvals, notifications, backups, disaster recovery, and production monitoring are outside Phase 1A-D.
- The development seed creates deliberately synthetic local records and is blocked when `DEBUG=False`.

## Phase 1E-H integration points

Later foundation engines should attach through services and versioned APIs: document metadata/storage, immutable audit events, configurable approval workflows, and notification delivery. They must reuse the current user/employee split, organization scopes, effective permission evaluation, feature flags, and transaction conventions without weakening deny precedence.
