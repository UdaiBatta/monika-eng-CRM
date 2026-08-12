# Phase 2 Traceability and Handoff

## Milestone coverage

| Milestone requirement | Status | Evidence |
|---|---|---|
| Customer, contacts, and sites | COMPLETE | Production models/APIs, Customer 360, lifecycle validation, tests, and browser acceptance |
| Enquiry/RFQ, requirements, and items | COMPLETE | Controlled commands, Decimal quantities, Enquiry 360, tests, and live ENQ-2026-0001 |
| Documents and activities | COMPLETE | Shared private document and activity services linked in both workspaces |
| Engineering feasibility | COMPLETE | Controlled revisions, clarification lifecycle, assessment, decision, queue/workspace, concurrency tests |
| Optional approval reuse | COMPLETE | Existing approval engine gates completion when configured; no parallel approval system |
| Ready for Estimation milestone | COMPLETE | Computed gate verified in the browser after feasible decision and closed clarifications |
| Secure website enquiry intake | COMPLETE | Signed/idempotent public intake, staging/quarantine, duplicate review, atomic conversion, Axis inbox, tests, and live WEB-UAT-2026-0001 |
| Commercial estimation | COMPLETE | Controlled Decimal cost build-up, pricing, revisioning, shared approval, confidential permissions, tests, and live approved EST-2026-0001 Rev 2 |
| Estimation-to-Enquiry handoff | COMPLETE | Approved current Estimate moves Enquiry to Estimation Complete and visibly Ready for Quotation |
| Desktop/mobile Axis CRM interface | COMPLETE | Responsive browser acceptance and permission-aware navigation |
| Realtime collaboration foundation | IMPLEMENTED; CONDITIONAL ACCEPTANCE | ASGI/Channels, authenticated company-scoped WebSocket, safe after-commit events, centralized query invalidation, reconnect, presence, tests, and two-tab browser conflict UAT. Production Redis and two-distinct-employee UAT remain. |
| Unified incoming enquiries | IMPLEMENTED; CONDITIONAL ACCEPTANCE | Website compatibility plus TradeIndia/WhatsApp/Phone/Email/In-person/Manual sources, shared queues, provenance, duplicates, ownership, conversion, tests, and live Phone capture. Full WhatsApp/TradeIndia browser scenarios remain. |
| Internal quotation lifecycle | IMPLEMENTED; CONDITIONAL ACCEPTANCE | Standard/quick paths, revisions, Decimal totals, approval reuse, communication, negotiation, confirmation, PO pending, Ready for Sales Order, tests, and live end-to-end UAT. Approved DOCX/PDF operations remain. |
| Sales Order and downstream ERP work | NOT STARTED | Sales Order, Project, Drawing Management, BOM, and later operations remain explicitly outside scope. |

## Decisions required before the next phase

- confirm real sales, engineering, and approval roles and their employee assignments;
- approve approval thresholds and escalation rules;
- approve document categories, retention, and production malware-scanning policy;
- confirm enquiry source, priority, loss-reason, and response-SLA masters;
- approve the final quotation DOCX, wording/defaults, tax/freight presentation, validity, terms, numbering ownership, and approval thresholds;
- confirm which roles may see Estimate cost, selling price, and gross margin in production;
- confirm the production website credential owner, source restriction, CAPTCHA policy, and malware-scanning service;
- complete production hosting, secret management, logging, backup, restore, and disaster-recovery decisions.

## Known boundary and technical debt

- Generated OpenAPI schema publication remains pending; the versioned `/api/v1/` contract is implemented.
- Production malware scanning is not enabled. The UI says so; file validation, private storage, checksum, and authorization are implemented.
- Website integration secrets are environment-managed; production secret storage and rotation ownership remain go-live decisions.
- Business role assignments are intentionally not seeded into production data.
- Acceptance records and business data are synthetic local fixtures; no approved quotation template or live PDF artifact is configured.
- Preliminary drawing, BOM, and routing notes are engineering assessment fields only. There is no Drawing Management or BOM module.
- The accepted Project 360 and drawing-viewer mockups remain non-production visual references.
- Production Redis, distinct-user/cross-department UAT, LibreOffice PDF validation, generated OpenAPI publication, production logging/alerting, load testing, backup/restore, and disaster recovery remain separate gates.

## Next safe slice

Do not begin Sales Order or Project until the realtime/quotation completion report is reviewed and the conditional acceptance items are closed. First approve the Sales Order input contract from the accepted current quotation, numbering, revision/cancellation rules, commercial controls, inventory commitments, authorization matrix, and exact Ready-for-Sales-Order handoff behavior.

## Website intake and estimation acceptance evidence

| Evidence | Result |
|---|---|
| Website intake security/concurrency tests | PASS |
| Signed live website submission and human conversion | PASS |
| Engineering eligibility gate | PASS |
| Estimate Decimal calculation tests | PASS |
| Estimate creation concurrency | PASS; one current revision |
| Shared approval and immutable approved revision | PASS |
| Revision 1 to revision 2 preservation | PASS |
| Axis desktop/mobile UAT | PASS; viewport-bounded line editor |
| Enquiry Estimation Complete / Ready for Quotation handoff | PASS |
| Quotation backend/frontend implementation | PASS; 106 backend and 36 frontend tests in the final regression |
| Realtime two-tab conflict UAT | PASS; unsaved work preserved and stale overwrite prevented |
| Standard and quick quotation browser UAT | PASS; includes revision, communication, negotiation, confirmation, and handoff |
| Production Redis / two-employee UAT | PENDING operational acceptance |
| Approved DOCX / LibreOffice PDF UAT | PENDING operational acceptance |
