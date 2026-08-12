# Realtime and Quotation Acceptance Record

Assessment date: 12 August 2026

Branch: `phase-2-quotation-realtime`

Assessment: **Implementation complete; production acceptance conditional**

## Automated release gates

| Gate | Result |
|---|---|
| Frontend tests | PASS — 36/36 across 9 files |
| Frontend lint | PASS — exit 0; 10 warning-only Fast Refresh/exhaustive-dependency findings |
| TypeScript and Vite production build | PASS — 2,620 modules transformed |
| Backend PostgreSQL tests | PASS — 106/106 |
| Ruff | PASS — all checks passed |
| Django system check | PASS — no issues |
| Migration drift | PASS — no changes detected |
| Git whitespace check | PASS |

Pytest reported one teardown warning because two other local PostgreSQL sessions still had the test database open. No test failed, but those stale sessions should be closed before the next clean-room regression run.

## Browser acceptance completed

- Axis quotation register and workspace tested in the running local application.
- Standard quotation created from approved estimate `EST-2026-0001`; customer-facing value INR 1,304,400.
- Revision 1 finalized and shared through WhatsApp; outbound recording froze it.
- Material negotiation recorded, revision 2 created, edited, compared, finalized, and shared through email.
- Verbal confirmation recorded with PO pending; quotation moved to **Ready for Sales Order** without creating a Sales Order.
- Two-tab stale-draft scenario passed: a remote save surfaced immediately, unsaved text remained visible, stale save was disabled, and **Load latest** restored safe editing.
- Manual Phone incoming enquiry captured with original wording and source provenance, then taken into ownership.
- Quick quotation created for an eligible Prospect after correcting the customer filter; regression coverage was added.
- Desktop dark mode, narrow responsive layout, header live status, and browser console were checked. No console errors or warnings were present.

Local acceptance data includes standard quotation `QUO-2026-0001`, quick quotation `QUO-2026-0002`, and phone source `CALL-2026-0811-02`.

## Definition-of-done assessment

### Realtime collaboration

All code and automated requirements are complete: ASGI/Channels, session authentication, anonymous rejection, company isolation, safe after-commit events, centralized query invalidation, reconnection, visible state, graceful degradation, presence TTL, and permission checks.

Conditional items:

- production Redis configuration exists but was not exercised against a deployed Redis instance on this Docker-free local machine;
- browser collaboration was proven in two tabs under one signed-in employee, while the specification's final acceptance asks for two distinct employee accounts/sessions.

### Multi-user safety

Optimistic concurrency, HTTP 409 behavior, unsaved-change preservation, row locking, sequence collision protection, shared queues, ownership, and cache TTL have automated coverage. The two-tab browser conflict passed. Final acceptance still requires a named two-employee presence/reassignment session and its recorded evidence.

### Incoming enquiries

The unified page, website compatibility, Website Request Quote source, TradeIndia architecture, WhatsApp/Phone/Email/In-person/Manual sources, source labels, duplicate intelligence, source history, manual intake, realtime invalidation, and no-fake-integration boundary are implemented.

Phone capture received browser acceptance. The end-to-end WhatsApp-with-attachment and synthetic TradeIndia conversion scenarios remain acceptance exercises; no live WhatsApp or TradeIndia connector is claimed.

### Quotation

The complete data model, standard and quick paths, Decimal calculations, tax and terms, RBAC, shared approval integration, revisioning, communication, negotiation, confirmation, PO pending, customer/enquiry workspaces, audit, notification hooks, realtime, concurrency, and Ready-for-Sales-Order handoff are implemented and tested.

Conditional document items:

- DOCX rendering, whitelist protection, shared-Document storage, and graceful PDF failure are covered by automated tests;
- no customer-approved active DOCX template is configured in the local database;
- LibreOffice PDF conversion is not installed/validated locally;
- therefore a live browser-generated Word/PDF pair is not yet accepted.

## Remaining acceptance and go-live work

1. Configure and test production Redis for Channels/cache.
2. Create two named synthetic employee accounts with appropriate existing RBAC assignments, then record the two-user Sales, presence, reassignment, reconnect, and cross-department UAT evidence.
3. Upload and approve the Monika Engineers quotation DOCX template; validate every placeholder and commercial layout.
4. Install/configure LibreOffice on the deployment host and verify generated PDF fidelity and failure monitoring.
5. Run the complete manual WhatsApp and synthetic TradeIndia workflows, including attachments, duplicates, conversion, quoting, and source preservation.
6. Approve real roles, approval rules, quotation wording/defaults, tax/freight presentation, numbering ownership, and PO policy.
7. Complete production HTTPS, secrets, secure-cookie, logging, alerting, backup/restore, malware scanning, load/concurrency, and disaster-recovery gates.

These are explicit acceptance/operations items. No Sales Order or downstream ERP implementation was started.
