# Requirements Traceability Register

Authority: Monika Engineers Integrated ERP specification received 2026-08-09
Status date: 2026-08-10

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
| R-000 | Primary objective | All | NOT STARTED | Production ERP not yet implemented |
| R-001 | Technology architecture | 1 | IN DEVELOPMENT | Architecture baseline defined; backend/deployment not scaffolded |
| R-002 | System architecture principles | 1 | IN DEVELOPMENT | Modular-monolith boundaries defined |
| R-003 | Controlled state transitions | 1+ | NOT STARTED | Service/API command tests required |
| R-004 | User, employee and organization foundation | 1 | NOT STARTED | Identity policy confirmation required |
| R-005 | RBAC framework | 1 | NOT STARTED | Configurable engine; roles still awaiting input |
| R-006 | Common data model | 1 | NOT STARTED | Physical base models/migrations required |
| R-007 | Numbering engine | 1 | NOT STARTED | Numbering conventions required |
| R-008 | Master data | 1+ | NOT STARTED | Master ownership and initial values required |
| R-009 | CRM module | 2 | NOT STARTED | Customer workflow confirmation required |
| R-010 | Enquiry/RFQ management | 2 | NOT STARTED | Sales process workshop required |
| R-011 | Engineering feasibility review | 2 | NOT STARTED | Sales/engineering handoff confirmation required |
| R-012 | Drawing management | 3 | NOT STARTED | Revision and release authority required |
| R-013 | Engineering change management | 3 | NOT STARTED | ECR/ECN policy required |
| R-014 | BOM management | 3 | NOT STARTED | BOM ownership/release policy required |
| R-015 | Routing | 3 | NOT STARTED | Work centres and operations required |
| R-016 | Estimation and costing | 2 | NOT STARTED | Cost model and visibility policy required |
| R-017 | Quotation module | 2 | NOT STARTED | Template and approval policy required |
| R-018 | Customer negotiation history | 2 | NOT STARTED | Activity rules required |
| R-019 | Sales order | 3 | NOT STARTED | Conversion and partial-delivery rules required |
| R-020 | Project management | 3 | IN DEVELOPMENT | Project 360 UI proof-of-concept only |
| R-021 | Project document repository | 3 | NOT STARTED | Category/access/retention policy required |
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
| R-070 | Approval engine | 1 | NOT STARTED | Approval matrix inputs required |
| R-071 | Notification engine | 1/11 | NOT STARTED | Internal notifications first |
| R-072 | Audit logging | 1 | NOT STARTED | Audit retention/access policy required |
| R-073 | Document management | 1 | NOT STARTED | Storage/retention decision required |
| R-074 | Global search | 11 | NOT STARTED | PostgreSQL-first plan documented |
| R-075 | Filtering | 2+ | IN DEVELOPMENT | URL-filter patterns exist in UI proof-of-concept |
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
| R-096 | Responsive web application | 1+ | IN DEVELOPMENT | Axis mockup tested on desktop/mobile; production app pending |
| R-097 | Human-readable error handling | 1+ | NOT STARTED | API convention documented |
| R-098 | Concurrency protection | 1+ | NOT STARTED | Lock/version tests required |
| R-099 | Server-side data validation | 1+ | NOT STARTED | Domain validation tests required |
| R-100 | Transaction safety | 1+ | NOT STARTED | Atomic workflow tests required |
| R-101 | Security | 1+ | NOT STARTED | Threat model and implementation required |
| R-102 | Login security | 1 | NOT STARTED | Policy decisions required |
| R-103 | Backups | 1/Go-live | NOT STARTED | Destination and restore test required |
| R-104 | Disaster recovery | Go-live | NOT STARTED | Runbooks and exercise required |
| R-105 | Logging | 1 | NOT STARTED | Log routing/retention required |
| R-106 | Performance | All | NOT STARTED | Load targets and tests required |
| R-107 | Database indexing | Each phase | NOT STARTED | Query plans reviewed per module |
| R-108 | Versioned API/OpenAPI | 1+ | IN DEVELOPMENT | API plan complete; implementation pending |
| R-109 | Enterprise frontend design | 1+ | IN DEVELOPMENT | Axis CRM declared visual source of truth |
| R-110 | Permission-aware navigation | 1+ | IN DEVELOPMENT | Mockup navigation exists; RBAC integration pending |
| R-111 | Project 360 view | 3 | IN DEVELOPMENT | Axis UI proof-of-concept exists; production data/actions pending |
| R-112 | Customer 360 view | 2 | NOT STARTED | UI/data contract required |
| R-113 | Material 360 view | 5 | NOT STARTED | UI/data contract required |
| R-114 | Asset 360 view | 9 | NOT STARTED | UI/data contract required |
| R-115 | Activity timelines | 2+ | IN DEVELOPMENT | UI abstraction exists; audited event source pending |
| R-116 | Comments/internal notes | 2+ | NOT STARTED | Visibility/attachment policy required |
| R-117 | Tasks/follow-ups | 2+ | NOT STARTED | Lifecycle/notification policy required |
| R-118 | UTC and timezone handling | 1 | NOT STARTED | Architecture baseline defined |
| R-119 | Decimal currency/INR | 1+ | NOT STARTED | Model implementation required |
| R-120 | Decimal quantity precision | 3+ | NOT STARTED | Precision policy required |
| R-121 | Configurable taxes | 1/2+ | NOT STARTED | Finance masters required |
| R-122 | Controlled data import | Each launch | NOT STARTED | Staging/preview plan documented |
| R-123 | Opening inventory | 5 | NOT STARTED | Cutover process required |
| R-124 | Migration strategy | All | IN DEVELOPMENT | Baseline documented; data discovery pending |
| R-125 | Company configuration | 1 | NOT STARTED | Settings values required |
| R-126 | Feature flags | 1 | NOT STARTED | Initial flags identified |
| R-127 | Testing | Every phase | IN DEVELOPMENT | Gates documented; production suites pending |
| R-128 | Permission testing | 1+ | NOT STARTED | Role definitions pending |
| R-129 | Seed/demo data | 1+ | NOT STARTED | Environment segregation required |
| R-130 | Django migrations only | 1+ | NOT STARTED | Backend not scaffolded |
| R-131 | One-command development environment | 1 | IN DEVELOPMENT | Frontend runs locally; Docker stack pending |
| R-132 | Ubuntu VPS production deployment | Go-live | NOT STARTED | Hosting decision pending |
| R-133 | Maintained documentation | All | IN DEVELOPMENT | Phase 0 documentation created |
| R-134 | Change management | All | IN DEVELOPMENT | Process documented; enforcement pending |
| R-135 | Future architecture readiness | All | IN DEVELOPMENT | Boundaries documented; features not implemented |
| R-136 | Prohibited practices | All | IN DEVELOPMENT | Architectural guardrails documented |
| R-137 | Development order | All | IN DEVELOPMENT | Phased plan documented; Phase 1 not started |
| R-138 | Definition of Done | Every module | IN DEVELOPMENT | Gates documented; no production module complete |
| R-139 | Requirement traceability | All | COMPLETE | This register covers sections 0-140 |
| R-140 | Final engineering principle | Every workflow | IN DEVELOPMENT | Mandatory design questions adopted |

## 4. Expansion rule

Before a phase begins, each section assigned to that phase is decomposed into acceptance-level requirement IDs. For example, `R-012 Drawing management` becomes separate trace items for numbering, metadata, revisions, current-release uniqueness, file security, prepared/checked/approved actors, release, supersession, audit, UI, API, permissions and tests. The parent cannot become COMPLETE until every child is COMPLETE or DEFERRED WITH EXPLICIT APPROVAL.

## 5. Deferral register

No requirement is currently marked DEFERRED WITH EXPLICIT APPROVAL.

Every future deferral must include requirement ID, scope, reason, impact, approving person, approval date, target reconsideration phase and any architectural compatibility work retained.

## 6. Change record

| Date | Change | Impact |
|---|---|---|
| 2026-08-10 | Initial register created from authoritative sections 0-140 | Establishes honest baseline; production implementation remains largely not started |
