# Phase 3 Requirements Traceability

| Requirement | Status | Evidence |
|---|---|---|
| Customer PO register and simple entry | COMPLETE | Production API, Axis register/dialog, document selection/upload callback, focused frontend test |
| Customer PO revisions and private documents | COMPLETE | Versioned model/service, shared Document FK, immutable revision list, backend tests |
| PO duplicate protection | COMPLETE | Company/customer/case-insensitive PO checks and PostgreSQL test |
| PO-to-Quotation matching and variance review | COMPLETE | Structured comparison snapshot, friendly status, review/accept commands, test |
| PO received later / PO pending | COMPLETE | Optional PO on confirmation and Sales Order; later link command/UI |
| Sales Order model/revision/lines/numbering | COMPLETE | Production models, migrations, Decimal calculations, shared Numbering Engine, tests |
| Quotation-based Sales Order | COMPLETE | Accepted revision snapshot service, quotation and register UI, tests |
| Direct Sales Order | COMPLETE | Separate permission, mandatory reason/evidence, lightweight CRM history, UI, tests |
| Approval/release/immutability | COMPLETE | Existing Approval Engine integration, explicit release, protected revisions, tests |
| Amendments and comparison | COMPLETE | Snapshot-copy amendment, revision comparison API/UI, commercial-change warning, tests |
| Hold/resume/cancel | COMPLETE | Explicit audited commands for Sales Order and Project, permission enforcement, tests |
| Project creation/numbering/idempotency | COMPLETE | Release bootstrap, shared numbering, OneToOne protection, row locks, tests |
| Project register and Project 360 core | COMPLETE | Production Axis register; Overview, Commercial, PO, Handoff, Documents, Activity tabs |
| Engineering work queue and ownership | COMPLETE | Engineering/unassigned/mine filters, concurrency-safe `Take This`, PostgreSQL race test |
| Clarification and acceptance | COMPLETE | Request/respond/accept commands, UI, notifications/audit/realtime, tests |
| Commercial baseline change and acknowledgement | COMPLETE | Project previous/current baseline, warning, acknowledgement command/UI, amendment test |
| Realtime invalidation and presence | COMPLETE (automated) | Safe domain events, Phase 3 query roots, Project presence, backend regression suite |
| Company isolation and confidential data | COMPLETE (automated) | Scoped querysets, company validation, permission-filtered internal notes, tests |
| Customer 360, quotation, and Home integration | COMPLETE | Customer Sales Order/Project tabs, quote Create/Open Sales Order, Phase 3 dashboard queues |
| Signed-in browser and two-account UAT | PENDING MANUAL | Browser control unavailable; no session extraction attempted |
| Drawing Management | NOT STARTED | Explicitly outside Phase 3 |
| BOM | NOT STARTED | Explicitly outside Phase 3 |
| MRP and purchasing | NOT STARTED | Explicitly outside Phase 3 |
| Inventory transactions | NOT STARTED | Existing register/import visibility only; no stock ledger or movements |
| Production and quality | NOT STARTED | Explicitly outside Phase 3 |
| Dispatch, service, and AMC | NOT STARTED | Explicitly outside Phase 3 |
