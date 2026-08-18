# Requirements Traceability Register

Authority: Monika Engineers Integrated ERP specification received 2026-08-09
Status date: 2026-08-11

## 1. Status definitions

| Status | Meaning |
|---|---|
| NOT STARTED | No production implementation has begun |
| IN DEVELOPMENT | Design or implementation is active but Definition of Done is not satisfied |
| TESTING | Implementation exists and is undergoing required verification |
| COMPLETE | Production implementation, tests, documentation and integration satisfy Definition of Done |
| DEFERRED WITH EXPLICIT APPROVAL | A named approver accepted a documented deferral; no silent deferrals allowed |

The current Axis interface is a proof-of-concept. It can place a frontend requirement in development, but it cannot make a production requirement complete.

## 2. Mandatory pre-code artifacts

| ID | Artifact | Status | Evidence |
|---|---|---|---|
| P0-ARCH | System architecture | COMPLETE | `01-system-architecture.md` |
| P0-MOD | Module map | COMPLETE | `02-module-map.md` |
| P0-ER | Entity relationship model | COMPLETE | `03-entity-relationship-model.md` |
| P0-WF | Workflow/state diagrams | COMPLETE | `04-workflow-state-diagrams.md` |
| P0-API | API plan | COMPLETE | `05-api-plan.md` |
| P0-PLAN | Migration/development plan | COMPLETE | `06-migration-development-plan.md` |
| P0-TRACE | Requirements traceability checklist | COMPLETE | This register |

Completion here means the baseline artifact exists; business review is still required before Phase 1 implementation.

## 3. Authoritative requirement register

| ID | Requirement section | Phase | Status | Evidence / next gate |
|---|---|---:|---|---|
| R-000 | Primary objective | All | IN DEVELOPMENT | Production foundation through Project Ready for Detailed Engineering is implemented; downstream operational ERP remains phased |
| R-001 | Technology architecture | 1 | COMPLETE | React/Django/PostgreSQL/Redis/Celery workspace and Docker services implemented |
| R-002 | System architecture principles | 1 | COMPLETE | Modular-monolith boundaries, versioned API and separate frontend implemented |
| R-003 | Controlled state transitions | 1+ | COMPLETE | Explicit document, approval, CRM, quotation, Customer PO, Sales Order, Project, and handoff commands enforce tested transitions; mutable status PATCH is rejected |
| R-004 | User, employee and organization foundation | 1 | COMPLETE | Separate User/Employee and organization models, APIs, UI and tests implemented |
| R-005 | RBAC framework | 1 | COMPLETE | Data-driven roles, scoped assignments, allow/deny overrides and tests implemented; business roles intentionally unseeded |
| R-006 | Common data model | 1 | COMPLETE | UUID/timestamp base models and Django migrations implemented |
| R-007 | Numbering engine | 1 | COMPLETE | Atomic row-locked sequence service and non-consuming preview tested on PostgreSQL |
| R-008 | Master data | 1+ | IN DEVELOPMENT | Currency, UOM, tax, payment and delivery foundation masters complete; downstream masters remain phased |
| R-009 | CRM module | 2 | COMPLETE | Customer/Contact/Site plus secure Website Enquiry staging/conversion, production APIs, Axis registers, and Customer 360 verified |
| R-010 | Enquiry/RFQ management | 2 | COMPLETE | Controlled enquiry workflow, requirements/items, documents, activities, Enquiry 360 and tests verified |
| R-011 | Engineering feasibility review | 2 | COMPLETE | Controlled reviews, revisions, clarifications, assessment, decisions, readiness gate, tests and browser acceptance verified |
| R-012 | Drawing management | 3 | NOT STARTED | Revision and release authority required |
| R-013 | Engineering change management | 3 | NOT STARTED | ECR/ECN policy required |
| R-014 | BOM management | 3 | NOT STARTED | BOM ownership/release policy required |
| R-015 | Routing | 3 | NOT STARTED | Work centres and operations required |
| R-016 | Estimation and costing | 2 | COMPLETE | Controlled revisions/cost lines, Decimal pricing, Engineering gate, shared approval, confidential RBAC, Axis workspaces, concurrency tests, and live UAT |
| R-017 | Quotation module | 2 | COMPLETE | Controlled quotation revisions, Decimal lines/tax, approval, documents, communication, confirmation, PO pending, and Sales Order handoff are implemented and tested |
| R-018 | Customer negotiation history | 2 | COMPLETE | Customer/enquiry activities and immutable history are linked and visible in context |
| R-019 | Sales order | 3 | COMPLETE | Quote-based and permission-controlled direct entry, immutable releases, amendments, shared approval, PO pending/linking, Project bootstrap, security, and tests implemented; fulfillment is explicitly deferred |
| R-020 | Project management | 3 | COMPLETE | Project 360 core, numbering, idempotent bootstrap, ownership, commercial baseline, Engineering handoff, clarification, acceptance, hold/cancel, and tests implemented |
| R-021 | Project document repository | 3 | IN DEVELOPMENT | Project 360 reads permission-controlled shared Document links; project-specific upload/link ergonomics and final category/retention policy remain |
| R-022 | Material master | 4-5 | NOT STARTED | Material coding/UOM policy required |
| R-023 | MRP | 4 | NOT STARTED | Planning calculation acceptance tests required |
| R-024 | Purchase requisition | 4 | NOT STARTED | PR approval matrix required |
| R-025 | Vendor management | 4 | NOT STARTED | Vendor masters and rating policy required |
| R-026 | Vendor RFQ | 4 | NOT STARTED | Procurement process required |
| R-027 | Vendor comparison | 4 | NOT STARTED | Recommendation/approval separation required |
| R-028 | Purchase order | 4 | NOT STARTED | PO template and approval policy required |
| R-029 | Goods receipt/GRN | 5 | NOT STARTED | Receiving and partial receipt rules required |
| R-030 | Incoming quality | 5 | NOT STARTED | Inspection/disposition policy required |
| R-031 | Transaction-based inventory | 5 | NOT STARTED | Ledger model and reconciliation tests required |
| R-032 | Multiple warehouses | 5 | NOT STARTED | Launch warehouse/bin hierarchy required |
| R-033 | Material reservation | 5 | NOT STARTED | Reservation priority/release rules required |
| R-034 | Material issue | 5 | NOT STARTED | Issue authorization and handoff required |
| R-035 | Production order | 6 | NOT STARTED | Production release rules required |
| R-036 | Job cards | 6 | NOT STARTED | Shop-floor workflow required |
| R-037 | Production tracking | 6 | NOT STARTED | Status/operation recording policy required |
| R-038 | WIP | 6 | NOT STARTED | WIP definitions required |
| R-039 | Production costing | 6 | NOT STARTED | Labour/machine costing policy required |
| R-040 | Scrap management | 6 | NOT STARTED | Scrap authorization/recovery policy required |
| R-041 | Subcontracting/job work | 6 | NOT STARTED | Challan and return process required |
| R-042 | In-process quality | 7 | NOT STARTED | Inspection plans required |
| R-043 | Final quality | 7 | NOT STARTED | Dispatch release criteria required |
| R-044 | NCR | 7 | NOT STARTED | Disposition authority required |
| R-045 | CAPA | 7 | NOT STARTED | CAPA applicability and verification required |
| R-046 | Packing | 8 | NOT STARTED | Package/serial policy required |
| R-047 | Dispatch | 8 | NOT STARTED | Dispatch documents and partial rules required |
| R-048 | Delivery confirmation | 8 | NOT STARTED | Proof/discrepancy process required |
| R-049 | Installation and commissioning | 8 | NOT STARTED | Checklist and sign-off policy required |
| R-050 | Customer asset register | 9 | NOT STARTED | Asset numbering and creation rules required |
| R-051 | Warranty management | 9 | NOT STARTED | Warranty calculation/policy required |
| R-052 | Service request management | 9 | IN DEVELOPMENT | Service UI proof-of-concept only |
| R-053 | Service job card | 9 | NOT STARTED | Field execution rules required |
| R-054 | Engineer scheduling | 9 | NOT STARTED | Availability/conflict rules required |
| R-055 | GPS check-in/out | 14 | NOT STARTED | Feature remains disabled pending policy |
| R-056 | Service execution report | 9 | NOT STARTED | Mandatory content/template required |
| R-057 | Job photo upload | 9 | NOT STARTED | File/privacy policy required |
| R-058 | Customer sign-off | 9 | NOT STARTED | Signature acceptance policy required |
| R-059 | Travel/expense entry | 9 | NOT STARTED | Expense categories/approval required |
| R-060 | Service history | 9 | NOT STARTED | Asset 360 implementation required |
| R-061 | Service closure | 9 | NOT STARTED | Closure configuration required |
| R-062 | AMC management | 10 | IN DEVELOPMENT | AMC UI proof-of-concept only |
| R-063 | AMC proposal/quotation | 10 | NOT STARTED | Commercial policy required |
| R-064 | AMC contract | 10 | NOT STARTED | Contract/SLA policy required |
| R-065 | Preventive maintenance | 10 | NOT STARTED | Schedule generation rules required |
| R-066 | AMC reminders | 10-11 | NOT STARTED | Recipient/escalation policy required |
| R-067 | AMC visit report | 10 | NOT STARTED | Template required |
| R-068 | AMC billing | 10/13 | NOT STARTED | Finance integration decision required |
| R-069 | AMC renewal | 10 | NOT STARTED | Renewal ownership/process required |
| R-070 | Approval engine | 1 | COMPLETE | Generic versioned workflows, safe conditions, commands, row locks, supporting files, notifications, Axis UI and signed-in browser acceptance complete |
| R-071 | Notification engine | 1/11 | COMPLETE | Recipient-isolated in-app notifications, preferences, deduplication, post-commit rules and signed-in browser acceptance complete |
| R-072 | Audit logging | 1 | COMPLETE | Immutable audit service, context, redaction, read-only scoped API, entity timeline, Axis UI and signed-in browser acceptance complete |
| R-073 | Document management | 1 | COMPLETE | Private storage, secure downloads, versions, checksums, validation, links, archive/restore and signed-in Axis acceptance complete; drawing management remains R-012 |
| R-074 | Global search | 11 | NOT STARTED | PostgreSQL-first plan documented |
| R-075 | Filtering | 2+ | COMPLETE | Customer, enquiry, website-intake, activity, engineering, and estimate registers support searchable operational filter states |
| R-076 | Dashboard | 11 | IN DEVELOPMENT | Employee-home UI proof-of-concept only |
| R-077 | Sales reporting | 11 | NOT STARTED | KPI definitions required |
| R-078 | Procurement reporting | 11 | NOT STARTED | KPI definitions required |
| R-079 | Inventory reporting | 11 | NOT STARTED | Stock definitions required |
| R-080 | Production reporting | 11 | NOT STARTED | KPI definitions required |
| R-081 | Quality reporting | 11 | NOT STARTED | KPI definitions required |
| R-082 | Project reporting | 11 | NOT STARTED | KPI definitions required |
| R-083 | Service reporting | 11 | NOT STARTED | KPI definitions required |
| R-084 | AMC reporting | 11 | NOT STARTED | KPI definitions required |
| R-085 | Permission-aware exports | 2+ | NOT STARTED | Export policy/limits required |
| R-086 | HR master | 12 | NOT STARTED | Sensitive data policy required |
| R-087 | Attendance | 12 | NOT STARTED | Attendance method/shift policy required |
| R-088 | Leave | 12 | NOT STARTED | Leave policy required |
| R-089 | Payroll | 12 | NOT STARTED | Statutory/payroll policy required |
| R-090 | Finance/accounting | 13 | NOT STARTED | Internal vs integration decision required |
| R-091 | Customer credit control | 13 | NOT STARTED | Credit authority/process required |
| R-092 | Project costing | 3-13 | NOT STARTED | Cost-source mapping required |
| R-093 | Serial traceability | 5-9 | NOT STARTED | Material tracking policy required |
| R-094 | Batch traceability | 5 | NOT STARTED | Batch policy required |
| R-095 | Barcode/QR readiness | 14 | NOT STARTED | Data/API readiness planned |
| R-096 | Responsive web application | 1+ | COMPLETE | Production Axis foundation and Phase 2 Website/Estimation workspaces browser-tested on desktop and narrow mobile; dialogs are viewport bounded |
| R-097 | Human-readable error handling | 1+ | COMPLETE | Shared API error envelope and typed frontend normalization implemented and tested |
| R-098 | Concurrency protection | 1+ | COMPLETE | PostgreSQL locking tests cover numbering, documents, approvals, engineering, website conversion, and one-current-estimate creation |
| R-099 | Server-side data validation | 1+ | COMPLETE | Foundation serializers/models reject invalid and cross-company relationships |
| R-100 | Transaction safety | 1+ | COMPLETE | Numbering, website conversion, enquiry/engineering handoffs, estimate calculations, submission, approval sync, and revisions are atomic and lock protected |
| R-101 | Security | 1+ | IN DEVELOPMENT | Session/CSRF/RBAC plus HMAC website authentication, replay/idempotency/rate controls, private staging, and confidential costing complete; production threat review remains a go-live gate |
| R-102 | Login security | 1 | COMPLETE | Django password framework, generic failures, CSRF, sessions and login throttling tested |
| R-103 | Backups | 1/Go-live | NOT STARTED | Destination and restore test required |
| R-104 | Disaster recovery | Go-live | NOT STARTED | Runbooks and exercise required |
| R-105 | Logging | 1 | NOT STARTED | Log routing/retention required |
| R-106 | Performance | All | NOT STARTED | Load targets and tests required |
| R-107 | Database indexing | Each phase | IN DEVELOPMENT | Customer/activity/enquiry/engineering plus website queue and estimation operational indexes implemented; later modules retain their own review gates |
| R-108 | Versioned API/OpenAPI | 1+ | IN DEVELOPMENT | `/api/v1/` implemented and documented; generated OpenAPI schema remains pending |
| R-109 | Enterprise frontend design | 1+ | COMPLETE | Axis CRM visual system applied to live foundation, Customer/Enquiry/Engineering, Website Enquiry, and Commercial Estimate routes |
| R-110 | Permission-aware navigation | 1+ | COMPLETE | Navigation consumes effective permission codes while APIs enforce authorization independently |
| R-111 | Project 360 view | 3 | COMPLETE | Production Axis Project 360 shows overview, commercial baseline, Customer PO, Engineering handoff, Documents, Activity, ownership, next action, presence, and controlled actions |
| R-112 | Customer 360 view | 2 | COMPLETE | Live production Customer 360 with Overview, Contacts, Sites, Enquiries, Activities, Documents and History |
| R-113 | Material 360 view | 5 | NOT STARTED | UI/data contract required |
| R-114 | Asset 360 view | 9 | NOT STARTED | UI/data contract required |
| R-115 | Activity timelines | 2+ | COMPLETE | Authorized audit and CRM activity timelines are integrated into Customer and Enquiry workspaces |
| R-116 | Comments/internal notes | 2+ | NOT STARTED | Visibility/attachment policy required |
| R-117 | Tasks/follow-ups | 2+ | COMPLETE | Production follow-up ownership, due dates, priority, queues, controlled completion and contextual UI verified |
| R-118 | UTC and timezone handling | 1 | COMPLETE | Django timezone-aware UTC storage with Asia/Kolkata presentation setting |
| R-119 | Decimal currency/INR | 1+ | COMPLETE | Decimal financial masters plus server-authoritative estimate line, category, cost, price, markup, margin, and gross-margin calculations implemented |
| R-120 | Decimal quantity precision | 3+ | COMPLETE | Enquiry item quantities use Django Decimal fields and string-safe API/UI handling |
| R-121 | Configurable taxes | 1/2+ | COMPLETE | Company-scoped TaxRate master and administration UI implemented |
| R-122 | Controlled data import | Each launch | NOT STARTED | Staging/preview plan documented |
| R-123 | Opening inventory | 5 | NOT STARTED | Cutover process required |
| R-124 | Migration strategy | All | IN DEVELOPMENT | Baseline documented; data discovery pending |
| R-125 | Company configuration | 1 | COMPLETE | Automatic CompanySettings with editable India/INR defaults implemented |
| R-126 | Feature flags | 1 | COMPLETE | Company-scoped feature flag model, API and UI implemented |
| R-127 | Testing | Every phase | TESTING | Website-to-approved-Estimation automated regression, PostgreSQL concurrency, security, checks, lint/build, signed-in browser, and responsive QA complete; repeat for every later phase |
| R-128 | Permission testing | 1+ | COMPLETE | Grants, scopes, overrides, deny precedence and scoped querysets tested |
| R-129 | Seed/demo data | 1+ | COMPLETE | Explicit environment-gated debug-only seed command; no production demo migration |
| R-130 | Django migrations only | 1+ | COMPLETE | All database schema and seed changes use reviewed Django migrations |
| R-131 | One-command development environment | 1 | COMPLETE | Docker Compose remains available; native Windows PostgreSQL/Django/Vite mode runs the current local milestone without Docker or Redis/Celery workers |
| R-132 | Ubuntu VPS production deployment | Go-live | NOT STARTED | Hosting decision pending |
| R-133 | Maintained documentation | All | COMPLETE | README, Phase 1 guides, twelve Phase 2 guides, integration/acceptance records, and this traceability register maintained with code |
| R-134 | Change management | All | IN DEVELOPMENT | Process documented; enforcement pending |
| R-135 | Future architecture readiness | All | IN DEVELOPMENT | Boundaries documented; features not implemented |
| R-136 | Prohibited practices | All | IN DEVELOPMENT | Architectural guardrails documented |
| R-137 | Development order | All | IN DEVELOPMENT | Phase 1A-H and Phase 2 Website-to-approved-Estimation milestones completed in order and stopped before Quotation |
| R-138 | Definition of Done | Every module | IN DEVELOPMENT | Phase 1, Customer-to-Engineering, Website Intake, and Commercial Estimation gates satisfied; Quotation and later modules retain independent gates |
| R-139 | Requirement traceability | All | COMPLETE | This register covers sections 0-140 |
| R-140 | Final engineering principle | Every workflow | IN DEVELOPMENT | Mandatory design questions adopted |

## 4. Expansion rule

Before a phase begins, each section assigned to that phase is decomposed into acceptance-level requirement IDs. For example, `R-012 Drawing management` becomes separate trace items for numbering, metadata, revisions, current-release uniqueness, file security, prepared/checked/approved actors, release, supersession, audit, UI, API, permissions and tests. The parent cannot become COMPLETE until every child is COMPLETE or DEFERRED WITH EXPLICIT APPROVAL.

## 5. Deferral register

No requirement is currently marked DEFERRED WITH EXPLICIT APPROVAL.

## 6. Phase 1A-D acceptance evidence

| ID | Scope | Status | Evidence |
|---|---|---|---|
| P1-AUTH | Session authentication and User/Employee separation | COMPLETE | `docs/phase-1/02-authentication.md`, backend authentication tests |
| P1-ORG | Company organization and cross-company integrity | COMPLETE | `docs/phase-1/04-organization-model.md`, organization tests |
| P1-RBAC | Permission catalog, scoped roles and deny precedence | COMPLETE | `docs/phase-1/03-rbac.md`, RBAC tests |
| P1-CONFIG | Company settings and feature flags | COMPLETE | Live CRUD API/UI and browser QA |
| P1-MASTER | Currency, UOM, TaxRate, PaymentTerm, DeliveryTerm | COMPLETE | Django models/migrations/API and tabbed Axis UI |
| P1-NUMBER | Transaction-safe numbering foundation | COMPLETE | `docs/phase-1/05-numbering-engine.md`, PostgreSQL locking tests |
| P1-UI | Axis production foundation application | COMPLETE | `/app` plus desktop/mobile browser verification; mockup routes preserved |
| P1-OPS | PostgreSQL, Redis, Django and Celery local stack | COMPLETE | Docker health checks and `/api/v1/health/` |
| P1-AUDIT | Immutable business audit and controlled entity timeline | COMPLETE | Backend/API/integration tests and signed-in Activity History acceptance pass |
| P1-DOCS | Private versioned document management | COMPLETE | Security/concurrency tests and signed-in permission/empty-state acceptance pass |
| P1-APPROVAL | Generic configurable approval engine | COMPLETE | Command/concurrency/integration tests and signed-in approval-area acceptance pass |
| P1-NOTIFY | In-app notification engine | COMPLETE | Isolation/deduplication/post-commit tests and signed-in notification-center acceptance pass |
| P1-SHARED-UI | Axis shared-service production screens | COMPLETE | Desktop, tablet and mobile browser acceptance passes with no application console errors |

No later module is marked complete merely because these foundations can support it. CRM, Project 360, drawing/BOM and other operational domains retain their original phase status.

Every future deferral must include requirement ID, scope, reason, impact, approving person, approval date, target reconsideration phase and any architectural compatibility work retained.

## 6. Change record

| Date | Change | Impact |
|---|---|---|
| 2026-08-10 | Initial register created from authoritative sections 0-140 | Establishes honest baseline; production implementation remains largely not started |
| 2026-08-10 | Phase 1E–H implementation reached final browser acceptance | Automated gates and Docker health pass; signed-in real-data browser walkthrough remains before COMPLETE; CRM and operational modules remain not started |
| 2026-08-11 | Phase 1A–H signed-in browser acceptance completed | Real PostgreSQL administrator and restricted-user scenarios passed across desktop, tablet and mobile; Phase 2 retains independent gates |
| 2026-08-11 | Phase 2 Customer-to-Engineering vertical slice completed | Live RFQ, follow-up, document, clarification, decision and Ready for Estimation path passed; downstream modules remain unimplemented |
| 2026-08-11 | Phase 2 secure Website Enquiry Intake completed | Signed intake, staging, duplicate review, human conversion, security/concurrency tests, Axis inbox, and live WEB-UAT-2026-0001 passed |
| 2026-08-11 | Phase 2 Commercial Estimation completed | Two live approved revisions, six cost categories, Decimal pricing, shared approval, confidentiality/concurrency tests, and Ready for Quotation handoff passed; Quotation remains not started |
