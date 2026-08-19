# UX workflow consolidation completion report

Date: 2026-08-19  
Branch: `ux-workflow-consolidation`  
Boundary: pre-Phase-4 staff workflow consolidation  
Design rule: **Simple for staff. Structured underneath. Guide, do not punish.**

## 1. Git state

- Starting point: Owner Control foundation at `435fec1`.
- Audit commit: `150b540 docs: audit ERP workflow consistency`.
- Frontend checkpoint: `bf864de feat: consolidate staff workflow UX`.
- Backend/security checkpoint: `b9b4800 test: secure consolidated staff workflows`.
- Documentation is committed separately after this report.
- No work was pushed during this milestone.
- No Phase 4 implementation was started.

## 2. UX problems found

The audit found a module-heavy sidebar, Home content dominated by counts/readiness/future concepts, operational Workshop and estimate work under Tools & Settings, employee-facing Engineering terminology for practical Workshop work, competing workflow indicators/actions/tabs, duplicated record actions, and manual register-hopping between otherwise related records. The complete catalogue is in `docs/ux-workflow-consistency-audit.md`.

## 3. Workshop terminology changes

Operational employee copy now uses Workshop Review, My Workshop Work, Workshop owner, Send to Workshop, Workshop Approved, Workshop Cannot Approve, and Workshop clarification. A small presentation adapter maps stable internal values such as `ENGINEERING_REVIEW`, `READY_FOR_ENGINEERING`, and `NOT_FEASIBLE` to current employee labels.

Internal API paths, permission codes, model names, migrations, audit event identifiers, and historical enums intentionally retain compatibility-safe `engineering` identifiers. Legitimate future **Detailed Engineering** terminology remains distinct and is not presented as implemented Phase 4 functionality.

## 4. Navigation changes

Navigation is derived from effective permissions rather than hard-coded role names.

- Sales responsibilities: My Work, Enquiries, Customers, Quotations & Orders, Follow-ups, and Documents when permitted.
- Workshop responsibilities: My Work, My Workshop Work, Projects, and Documents when permitted; clarification queues remain inside Workshop workspaces.
- Owner responsibilities: Owner Centre, Approvals, and administrative Tools & Settings when permitted.
- Enquiries now groups incoming and active enquiry registers.
- Quotations & Orders groups quotations, customer confirmations/POs, and Sales Orders.
- Employees and operational Workshop/estimate work no longer compete in the ordinary configuration navigation.
- Warehouse master data is not mislabeled as live inventory transactions.

## 5. My Work

`/app` now loads real, permission-scoped records rather than illustrative KPIs. Available sources are assigned incoming enquiries, open customer follow-ups, owned quotations, owned Sales Orders, assigned Workshop Reviews, and owned projects. Needs Attention brings forward urgent/high enquiries, overdue follow-ups, quotations near validity expiry, approved or PO-pending orders, Workshop clarifications, project clarifications, and commercial-change alerts. Attention records are not duplicated in the ordinary work list.

An Owner Centre shortcut appears only with Owner Control permission. Empty, partial-error, and loading states use shared production components.

## 6. Next Action system

A reusable `NextActionPanel` now answers current status, what must happen next, and the one dominant permitted action. It reuses existing backend domain commands; no generic workflow engine or arbitrary status selector was added.

It is applied to Enquiry, Workshop Review, Estimate, Quotation, Sales Order, and Project 360. Secondary/destructive actions remain available with lower visual emphasis.

## 7. Workflow improvements

- Enquiry progression uses Received -> Commercial Review -> Workshop Review -> Workshop Approved -> Estimate -> Quotation -> Customer Decision.
- Workshop approval links directly to a preselected Estimate flow.
- Approved Estimate links directly to a preselected Quotation flow.
- Quotation uses one four-step read-only journey and four information tabs: Quotation, Documents, Activity, Revisions.
- Communication, negotiation, and customer decision are consolidated under Activity and domain dialogs instead of competing permanent tabs.
- Accepted quotations continue to Sales Order without reselecting the known quotation/customer context.
- Released Sales Orders continue to Project creation when required.
- Project 360 has one authoritative handoff action instead of duplicated Take/Accept buttons.

## 8. Consistency work

- Shared page headers, status badges, loading/error/empty states, permission checks, and domain buttons remain the default production patterns.
- Status presentation no longer exposes selected operational enum names.
- Tools & Settings contains genuine configuration/support areas only.
- Owner work/data-quality/notification presentation uses Workshop wording while retaining existing safety architecture.
- The Axis CRM visual system, responsive tables/cards, dark/light switch, and semantic status colours were preserved.

This milestone concentrated on the major daily workflow surfaces. A real non-technical staff session is still required before claiming that every form and secondary administrative page is optimally understandable.

## 9. Security review

New automated regression coverage proves:

- a Sales-only user receives HTTP 403 from Owner overview and feature APIs;
- direct PATCH attempts cannot force quotation, Sales Order, or project workflow status (HTTP 405); and
- the protected records keep their authoritative status afterward.

Existing passing tests cover CSRF-protected login/session behavior, role-grant escalation prevention, cross-company and scope isolation, read-only immutable audit history, released quotation/Sales Order revision protection, stale-edit conflicts, transaction-safe Take This/concurrent conversion, approval double-decision safety, private document download scoping, dangerous/disguised/oversize document rejection, cross-company document links, import size/header/row limits, invalid-file rollback, and confidential estimate field permissions.

Source inspection found no `dangerouslySetInnerHTML` or equivalent unsafe React HTML rendering in production code. React therefore renders stored customer/notes text as text by default. XLSX imports load cached values in read-only/data-only mode and do not execute formulas. Formula-injection escaping must be added and tested if downloadable CSV export is implemented later. Malware scanning remains an explicit production gate.

These results are evidence for the tested surfaces, not a claim that the entire application is universally secure.

## 10. Automated test results

| Check | Result |
| --- | --- |
| Backend pytest | 136 passed |
| Frontend Vitest | 19 files, 69 tests passed |
| Ruff | passed |
| Django system check | passed |
| Django production deployment check | passed with temporary production-safe environment values |
| Migration consistency | no changes detected |
| TypeScript + Vite production build | passed; 2,637 modules transformed |
| Docker Compose configuration | passed |
| Git whitespace check | passed; Windows LF/CRLF conversion notices only |
| Frontend lint | exit 0 with 10 known warnings |

The 10 lint warnings are Fast Refresh export-layout warnings in existing shared/shadcn files plus one existing theme-hook dependency warning. No lint errors were introduced.

## 11. Manual UAT

Local service verification succeeded:

- `http://127.0.0.1:5173/app` returned HTTP 200 HTML.
- `http://127.0.0.1:8000/api/v1/health/` returned HTTP 200 with application, database, and cache all `ok`.

The in-app browser could not connect because its trusted runtime dependency failed before page selection. Therefore visual, responsive, keyboard, blind-usability, and real Sales/Workshop/Owner multi-account UAT were **not completed and are not claimed**. The temporary Django and Vite servers were stopped after HTTP verification.

## 12. Remaining issues

- Perform human Sales, Workshop, and Owner journeys in separate sessions.
- Exercise presence, realtime updates, Take This race feedback, permission changes, feature changes, stale-edit recovery, clarification, approval, quotation communication, confirmation, PO, Sales Order, and project handoff in the browser.
- Conduct a blind usability session with non-technical staff and record confusing labels/actions.
- Review dense secondary forms and administrative resources with actual operators.
- Consider splitting remaining long page components only when a concrete maintenance or performance problem justifies it.

## 13. Production gates still open

- Approved real roles, scopes, responsibilities, and approval policies.
- Production HTTPS, secret rotation, secure cookies, HSTS, Redis/Channels/Celery, backups, monitoring, and deployment operations.
- Malware scanning for uploaded documents.
- Live website/TradeIndia/WhatsApp/email integrations where later authorized.
- Real browser multi-account and concurrency acceptance evidence.
- Drawing Management, BOM, purchasing, inventory transactions, GRN, production, quality, dispatch, service, and AMC.

## 14. Routes changed

- `/app` -> real My Work.
- `/app/enquiries` -> grouped Enquiry workspace.
- `/app/sales` -> Quotations & Orders workspace.
- `/app/workshop` -> My Workshop Work.
- `/app/workshop/reviews/:reviewId` -> Workshop Review detail.
- Existing `/app/crm/*`, `/app/sales/*`, `/app/projects/*`, and legacy engineering aliases remain compatible.

No screenshots are attached because the browser-control connection failed before a trustworthy visual capture could be made.

## 15. Recommendation

The branch is ready for stakeholder browser review, not yet for production acceptance or Phase 4. Merge/advance only after the real Sales, Workshop, and Owner UAT is completed and any usability findings are resolved. The implementation deliberately chose the smallest compatible solution: a presentation terminology layer, permission-derived workspace grouping, real queue composition, and one reusable Next Action component over model renames or a new workflow engine.
