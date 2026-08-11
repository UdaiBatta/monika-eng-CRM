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
| Quotation and downstream ERP work | DEFERRED BY SCOPE | Quotation, Project, Drawing Management, BOM, and later operations were explicitly excluded from these milestones |

## Decisions required before the next phase

- confirm real sales, engineering, and approval roles and their employee assignments;
- approve approval thresholds and escalation rules;
- approve document categories, retention, and production malware-scanning policy;
- confirm enquiry source, priority, loss-reason, and response-SLA masters;
- approve the Quotation input contract, commercial template, tax/freight presentation, validity, terms, and approval thresholds;
- confirm which roles may see Estimate cost, selling price, and gross margin in production;
- confirm the production website credential owner, source restriction, CAPTCHA policy, and malware-scanning service;
- complete production hosting, secret management, logging, backup, restore, and disaster-recovery decisions.

## Known boundary and technical debt

- Generated OpenAPI schema publication remains pending; the versioned \`/api/v1/\` contract is implemented.
- Production malware scanning is not enabled. The UI says so; file validation, private storage, checksum, and authorization are implemented.
- Website integration secrets are environment-managed; production secret storage and rotation ownership remain go-live decisions.
- Business role assignments are intentionally not seeded into production data.
- Acceptance data and the PDF are synthetic local fixtures.
- Preliminary drawing, BOM, and routing notes are engineering assessment fields only. There is no Drawing Management or BOM module.
- The accepted Project 360 and drawing-viewer mockups remain non-production visual references.
- Generated OpenAPI publication, production logging/alerting, load testing, backup/restore, and disaster recovery remain separate gates.

## Next safe slice

Do not begin Quotation until the user reviews the completion report and approves its document template, numbering, revision/validity rules, commercial terms, taxes, approval matrix, PDF strategy, and the exact contract consumed from the approved current Estimate. The Ready for Quotation state is a handoff only; no Quotation record or action exists.

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
| Quotation implementation | NOT STARTED by explicit stop condition |
