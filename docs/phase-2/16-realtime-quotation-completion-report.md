# Phase 2 Realtime and Quotation Completion Report

Report date: 18 August 2026

1. **Overall summary.** The realtime, unified incoming-enquiry, and internal quotation vertical slice is implemented through Ready for Sales Order. Post-milestone work also added spreadsheet migration paths, simpler CRM navigation, a focused Sales workspace, inventory/workshop visibility, and a uniform role-permission editor. Automated gates pass; production acceptance remains conditional on Redis, distinct-user UAT, and approved DOCX/PDF operations.
2. **Branch.** Work is isolated on `phase-2-quotation-realtime` from the accepted website/estimation baseline.
3. **Commits.** Core milestone: `1701e4b` realtime foundation; `e7ffd5e` unified intake; `340edd7` quotation lifecycle; `10a6731` realtime intake UI; `564fac5` Axis quotation workspace; `257e6bd` realtime draft protection; `89bf3b8` numbering seed; `206c289` prospect quick-quote fix; `56a49db` milestone documentation. Subsequent operational refinements: spreadsheet imports and work queues through `219b193`, simplified navigation `c82aea7`, inventory/workshop visibility `b31b75a`, focused Sales workspace `c46907d`, and standardized role permissions `08224c4`.
4. **Working tree status.** The target handoff state is clean after the documentation checkpoint; verified separately with `git status --short`.
5. **Baseline verification.** The inherited Phase 2 website/estimation slice was preserved. The definitive 18 August gate is 113 backend and 48 frontend tests, both fully passing.
6. **Realtime architecture.** Django Channels publishes small signals while REST/PostgreSQL remain authoritative. The client refetches server state through TanStack Query.
7. **ASGI configuration.** `config.asgi.application` uses `ProtocolTypeRouter` for HTTP and WebSocket traffic.
8. **Django Channels configuration.** Channels/Daphne are installed, the workspace route is `/ws/workspace/`, and HTTP remains standard Django ASGI.
9. **Redis channel layer.** Production settings use `channels_redis` and Redis database 2; development/tests use in-memory layers. Deployment-host Redis execution is still an acceptance requirement.
10. **WebSocket authentication.** Existing Django session authentication is reused through `AuthMiddlewareStack`; anonymous sockets close with 4401.
11. **Company isolation.** Connections derive company from the linked employee, groups are company-scoped, and entity subscriptions resolve company ownership.
12. **Realtime event architecture.** Controlled domain events are routed by entity type and carry identifiers/action metadata, not complete business records.
13. **Event routing/groups.** Company, user, and permission-checked entity groups support broad refresh signals, targeted work, and presence.
14. **Permission-safe payload strategy.** Events exclude customer messages, lines, prices, estimate cost, margin, and other confidential values; clients refetch authorized REST resources.
15. **`transaction.on_commit` behavior.** Domain-event dispatch is registered after transaction commit so rolled-back work cannot appear live.
16. **TanStack Query invalidation.** A central entity-to-query-key map invalidates incoming, quotation, customer, enquiry, engineering, estimate, approval, document, activity, and notification data.
17. **Reconnect handling.** The client uses bounded retry/backoff, heartbeat, re-subscription, event de-duplication, and refetch after reconnection.
18. **Connection indicator.** The Axis header displays Live, Reconnecting, or Offline with non-technical help text.
19. **Offline/degraded behavior.** Realtime failure does not block REST reads or controlled writes; staff can refresh safely.
20. **Presence architecture.** Entity subscription heartbeats maintain company/entity/user cache entries and broadcast permitted viewer lists.
21. **Presence TTL.** Cache expiry removes abandoned presence even if a browser disappears without a clean disconnect; automated TTL coverage passes.
22. **Presence UI.** Quotation and incoming detail surfaces show active viewers without using presence as a record lock.
23. **Optimistic concurrency strategy.** Editable revisions carry `record_version`; every draft update submits the loaded version.
24. **Version conflict API behavior.** A stale version raises the central `VersionConflict` and returns HTTP 409 with the current version.
25. **Version conflict frontend UX.** The UI preserves unsaved values, blocks the stale save, explains the newer version, and offers Load latest.
26. **Critical row-locking strategy.** `select_for_update` protects draft updates, finalization, revision creation, communication, negotiation, confirmation, and final handoff.
27. **Ownership/assignment.** Incoming records retain assigned employee and capture employee; unassigned items can be taken explicitly.
28. **Shared work queues.** Incoming supports team/mine/unassigned filters; quotation supports owner-aware filtering and home counters.
29. **Current-module realtime retrofit.** The shared domain-event subscriber covers registered audited CRM entities, not only quotation records.
30. **Incoming Enquiries refactor.** The secure website submission model was retained and generalized into one source-aware queue and detail workspace.
31. **Website source behavior.** Signing, idempotency, quarantine/review, duplicate intelligence, and atomic conversion remain intact.
32. **TradeIndia architecture.** TradeIndia is a supported source/adapter boundary and manual fixture path; live connectivity is explicitly not claimed.
33. **WhatsApp architecture.** WhatsApp enquiries and quotation communications are recorded as human actions; the system does not impersonate a messaging connector.
34. **Phone/manual flow.** Staff can record source, original wording, contact details, received time, attachments, and owner from the Axis inbox.
35. **Duplicate matching.** Intake surfaces customer/contact duplicate suggestions without automatic destructive merging.
36. **Source-history preservation.** Channel/source type and original message remain attached through review and CRM conversion.
37. **Quotation models.** Quotation, revision, line, template, text template, generated document, communication, negotiation, and commercial confirmation models exist.
38. **Quotation revision architecture.** One current revision is referenced by the quotation; customer-communicated revisions are immutable and later changes create a new revision.
39. **Quotation lines.** Lines support free-form or catalog-style descriptions, Decimal quantity/rate/tax, unit, ordering, and customer-facing grouping.
40. **Standard quotation path.** Only an approved current commercial estimate is eligible and becomes a customer-facing snapshot.
41. **Quick quotation path.** A controlled direct draft can be created for an active customer/prospect with an initial line and optional enquiry link.
42. **Quick quotation permission.** `crm.quotation.quick_create` is separate from normal quotation creation and is enforced server-side and in the UI.
43. **Estimate integration.** Approved sell value is imported while estimate costs, margin, and internal build-up remain outside the quotation context.
44. **Numbering.** The `QUOTATION` sequence produces `QUO-{year}-{number}` values under row lock; development seeding includes the sequence.
45. **Decimal calculations.** Quantity, rate, discount, tax, subtotal, and grand total use Django `DecimalField`/Python Decimal and are regression-tested.
46. **Tax handling.** Line tax rates and revision totals are stored as Decimal values; commercial presentation still needs stakeholder sign-off.
47. **Payment/delivery/warranty.** Revision snapshots store plain-language payment, delivery, warranty, validity, and additional terms.
48. **Commercial text templates.** Reusable company-scoped text templates are modelled and permission-controlled.
49. **Quotation template model.** Company-scoped active DOCX templates, version labels, and upload metadata are supported; an approved business template is not yet configured locally.
50. **DOCX generation.** `docxtpl` renders a unique Word artifact from the active revision and explicit context.
51. **PDF generation.** An optional LibreOffice conversion adapter produces PDF when the executable is available.
52. **PDF failure behavior.** Conversion failure preserves the Word artifact, records Word-only status/error, and does not roll back the quotation.
53. **Shared Document integration.** Generated artifacts are registered in the existing private shared Documents system.
54. **Customer-facing whitelist.** Document context is assembled from explicit quotation/customer/terms/line keys rather than serializing domain objects.
55. **Internal data protection.** Estimate cost, markup, gross margin, engineering-only data, and internal notes are absent from the generation context and covered by tests.
56. **Quotation communication model.** Communication records revision, channel, date, reference, notes, and employee, preserving what was sent.
57. **Phone communication.** Phone/verbal sharing can be recorded without forcing a PDF or customer portal.
58. **WhatsApp communication.** Manual WhatsApp sharing is recordable and freezes the communicated revision; it does not send a message automatically.
59. **Email communication.** Manual email sharing is recordable with reference and notes and is visible in quotation history.
60. **Negotiation.** Customer requests and material/non-material classification are captured against the quotation and current revision.
61. **Follow-up integration.** Negotiation can create/associate follow-up timing in the existing CRM activity flow.
62. **Revision creation.** The service locks the quotation, copies the current customer-facing snapshot and lines, and increments the revision number.
63. **Revision comparison.** The API/UI presents human-readable changes between consecutive revisions.
64. **Customer confirmation.** Commercial acceptance is a separate audited command after sharing and before final handoff.
65. **Verbal confirmation.** Phone/verbal acceptance is supported with date, employee, reference, notes, and PO-pending choice.
66. **WhatsApp confirmation.** WhatsApp acceptance is supported as a recorded human confirmation method.
67. **Email confirmation.** Email acceptance is supported as a recorded human confirmation method.
68. **Customer PO handling.** PO number/date/document can be attached to confirmation and the shared document system.
69. **PO Pending.** Acceptance can proceed with PO pending; the UI clearly shows the pending state and allows the PO later.
70. **Ready-for-Sales-Order handoff.** The command sets the quotation to Ready for Sales Order and enquiry to Won, and deliberately creates no order.
71. **Approval integration.** Finalization can start an active workflow in the existing shared Approval Engine; no parallel approval model exists.
72. **Audit.** Controlled services use existing actor/context/audit infrastructure and immutable history records.
73. **Notifications.** Shared notification/domain-event hooks are reused for relevant changes; notification preference behavior remains centralized.
74. **Customer 360.** Customer detail includes a permission-aware quotation tab with latest value, status, revision, and link.
75. **Enquiry workspace.** Enquiry detail includes its quotation trail and the approved-estimate-to-quotation handoff.
76. **Employee Home.** Home shows incoming/quotation work counts and actions according to permissions. The Sales role receives a focused daily-work view instead of the full administrative dashboard.
77. **Realtime counters.** Entity events invalidate active counter queries; the server is not trusted to push precomputed secret counts.
78. **Team activity.** Communication, negotiation, approval, confirmation, and domain events feed the shared activity/audit visibility foundation.
79. **Permissions.** Migration `0008_quotation_permissions` registers granular quotation, quick-path, template, generation, communication, negotiation, confirmation, and handoff permissions. Migration `0009_deactivate_legacy_quotation_permissions` removes obsolete duplicates from the active catalogue; the role editor now loads all pages and presents 112 active permissions in consistent responsibility groups.
80. **Company isolation tests.** Cross-company REST/entity access and realtime subscription behavior have automated coverage.
81. **WebSocket tests.** Authentication, anonymous close, company group isolation, safe routing, and consumer behavior are covered.
82. **Presence tests.** Heartbeat, cache TTL, removal, permission checks, and company boundaries are covered.
83. **Optimistic concurrency tests.** Stale versions return 409 and cannot overwrite the newer draft; the frontend conflict state also has regression coverage.
84. **PostgreSQL concurrency tests.** Real two-thread quotation-number creation verifies unique sequence allocation under database locking.
85. **Backend test command/result.** `.\.venv\Scripts\python.exe -m pytest backend -q` -> 113 passed in the 18 August verification run.
86. **Frontend test command/result.** `bun x vitest run` -> 14 files and 48 tests passed in the 18 August verification run.
87. **Ruff.** `.\.venv\Scripts\ruff.exe check backend` -> all checks passed.
88. **Django checks.** `manage.py check` -> no issues. `manage.py check --deploy` completes with the six expected local-development warnings for HSTS, HTTPS redirect, production secret, secure session/CSRF cookies, and `DEBUG=False`; these are go-live configuration gates.
89. **Migration consistency.** `manage.py makemigrations --check --dry-run` -> no changes detected; all new migrations are applied locally.
90. **Docker validation.** `docker compose config --quiet` passes. Docker services were not started because local development is intentionally Docker-free; native PostgreSQL, Daphne/Django, and Vite have run successfully. Container runtime/deployment validation remains a separate environment gate.
91. **Frontend lint.** `bun run lint` exits 0 with ten warning-only findings: nine Fast Refresh export warnings and one existing effect-dependency warning.
92. **TypeScript/build.** `bun run build` passes and Vite transforms 2,622 modules.
93. **Multi-user Sales UAT.** Two-tab live/conflict behavior passed under one real signed-in local employee; the required two-distinct-employee session remains pending.
94. **Cross-department realtime UAT.** Architecture/tests cover cross-module events, but a named Sales-to-Engineering two-user browser exercise remains pending.
95. **Formal quotation UAT.** Approved estimate -> standard quotation -> revise -> communicate -> negotiate -> confirm -> Ready for Sales Order passed; live Word/PDF was blocked by missing active template/LibreOffice.
96. **Quick/Phone quotation UAT.** Phone intake, ownership, prospect quick quotation, controlled reason, line value, and saved draft passed.
97. **WhatsApp workflow UAT.** WhatsApp outbound recording and revision freeze passed; a separate incoming WhatsApp attachment/conversion and second-user live observation remains pending.
98. **TradeIndia workflow UAT.** Source architecture and fixtures/tests exist; the complete synthetic browser conversion/quote exercise remains pending and no live connector is claimed.
99. **Disconnect/reconnect UAT.** Reconnect/offline client behavior is implemented/tested; a timed manual network-disconnect recording remains pending.
100. **Responsive QA.** Desktop dark mode and narrow viewport remained usable; dense headers truncate conservatively on very narrow screens.
101. **Browser console.** Checked quotation/incoming flows produced no console errors or warnings.
102. **User-friendliness review.** Axis CRM shell, human labels, progressive disclosure, explicit ownership, safe conflict language, responsive cards/tables, restrained status messaging, simpler navigation, spreadsheet migration actions, focused Sales home, and grouped role permissions are in place.
103. **Documentation.** Architecture, staff guide, acceptance record, traceability, and this completion report are stored under `docs/phase-2/`.
104. **Traceability.** Realtime, incoming enquiries, and quotation are marked implemented with conditional operational acceptance; Sales Order, Project, and downstream ERP remain Not Started.
105. **Business decisions still required.** Approve quotation DOCX design, wording/defaults, GST/freight display, validity, numbering ownership, real role assignments, approval thresholds, PO policy, and retention.
106. **Security/go-live requirements.** Configure production secrets, HTTPS/HSTS, secure cookies, Redis, allowed hosts/origins, malware scanning, logging/alerts, backups/restore, DR, and deployment smoke/load tests.
107. **Known technical debt.** Ten warning-only frontend lint items, no generated OpenAPI publication, no production Redis UAT, and no local LibreOffice/template validation.
108. **Explicitly deferred work.** Live WhatsApp/TradeIndia connectors, customer portal/acceptance links, Sales Order, Project, Drawing Management, BOM, Purchase, Production, Inventory execution, Quality, Dispatch, and Service are not implemented.
109. **Recommendation for Sales Order / Project milestone.** Review and accept this report, finish the conditional operational/UAT items, and approve the Sales Order input contract before starting that milestone. Do not create Sales Order or Project code from this branch yet.
