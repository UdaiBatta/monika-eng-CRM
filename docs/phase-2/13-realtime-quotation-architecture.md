# Realtime Collaboration, Incoming Enquiries, and Quotation Architecture

Implementation record finalized: 12 August 2026

Branch: `phase-2-quotation-realtime`

## Scope and boundary

This milestone adds the production foundation for realtime CRM collaboration, unified incoming enquiries, and the quotation lifecycle through **Ready for Sales Order**. It deliberately does not create a Sales Order, Project, Drawing Management, BOM, Purchase, Production, or customer portal module.

The production application remains a Django modular monolith with PostgreSQL and an Axis-based React/TypeScript frontend. Local development runs natively without Docker. Production settings use Redis for the Channels layer and shared cache.

## Realtime architecture

- `config.asgi.application` is a Channels `ProtocolTypeRouter` serving Django HTTP and `/ws/workspace/` WebSockets.
- `AllowedHostsOriginValidator` rejects untrusted origins and `AuthMiddlewareStack` uses the existing Django session. Anonymous users are closed with code `4401`.
- A connected employee joins a company group and a user group. Entity subscriptions additionally join permission-checked entity groups.
- The consumer resolves the employee's company from the authenticated account. Entity subscriptions verify company ownership and the normal RBAC `view` permission.
- Domain events are small metadata signals. Screens refetch authoritative REST data; event payloads do not contain quotation lines, prices, customer messages, or confidential estimate costs.
- Domain events are dispatched with `transaction.on_commit`, preventing clients from observing rolled-back work.
- Local development and tests use an in-memory channel layer and local-memory cache. Production settings use `channels_redis` and Redis database 2. Production Redis still needs environment-level validation on the deployment host.

### Event and frontend flow

1. A service completes an audited database transaction.
2. An after-commit domain event is routed to company, user, and/or entity groups.
3. The React realtime provider de-duplicates the event and maps its entity type to TanStack Query keys.
4. Active screens refetch REST resources rather than trusting the event body as state.
5. On disconnect, the header changes from **Live** to **Reconnecting** or **Offline**. Forms and normal REST operations remain usable.
6. Reconnect uses bounded backoff, restores subscriptions, and refetches queries.

## Presence and multi-user record safety

Presence is advisory. The browser sends entity subscription and heartbeat messages, while cache entries expire through a TTL. Presence exposes only user identifiers and display names within the same company and only to users permitted to view that entity.

Draft quotation revisions use `record_version` optimistic concurrency. A stale `update-draft` request returns HTTP 409 with the current version. The UI preserves unsaved text, disables the conflicting save, explains that a newer version exists, and requires **Load latest** before editing resumes.

Critical state-changing services also lock rows with `select_for_update`, including revision updates, finalization, revision creation, communication, negotiation, confirmation, and Ready-for-Sales-Order handoff. This protects invariants and double-click races independently of the advisory presence display.

## Unified incoming enquiries

`ExternalEnquirySubmission` remains the compatibility boundary for signed website requests and is generalized into the shared incoming queue. Supported source channels are Website, TradeIndia, WhatsApp, Phone, Email, In person, Manual, and Other.

- Website requests keep signed authentication, replay/idempotency protection, quarantine/review, and the existing conversion path.
- Manual capture records the employee, received time, original customer wording, source label, contact details, and attachments.
- TradeIndia and WhatsApp are source architectures/manual capture paths only; no live third-party integration is claimed.
- Duplicate intelligence is advisory and source history is immutable provenance.
- Queue filters support team, mine, and unassigned work. **Take ownership** is an explicit command.
- Conversion atomically links or creates Customer, Contact, and Enquiry records and preserves incoming attachments and source history.

## Quotation domain

The quotation aggregate consists of:

- `Quotation` for identity, customer/enquiry relationship, path, owner, and lifecycle status;
- `QuotationRevision` for immutable customer-facing commercial snapshots and optimistic versioning;
- `QuotationLine` for free-form or catalog-linked sell lines using `Decimal` values;
- `QuotationTemplate` and `QuotationTextTemplate` for controlled document and commercial wording defaults;
- `QuotationGeneratedDocument` for immutable generated artifacts linked to shared Documents;
- `QuotationCommunication`, `QuotationNegotiation`, and `CustomerCommercialConfirmation` for the customer history.

### Creation paths

The standard path requires an approved current commercial estimate. It imports only the approved customer-facing selling price and builds a new quotation snapshot; internal cost bases, gross margin, markup rules, and engineering-only data are never exposed to the quotation document context.

The quick path is separately permission-controlled and requires an explicit reason. It supports active customers and prospects, can link an enquiry, and creates an auditable draft with a required first line. It does not bypass later revision, communication, confirmation, or audit controls.

### Lifecycle

`Draft` -> optional `In approval` -> `Ready to send`/`Approved` -> `Sent` -> optional `Under negotiation` -> `Accepted` -> `Ready for Sales Order`.

Finalization uses the shared Approval Engine when an active workflow is selected. Without a workflow, the revision becomes ready to send. Recording outbound phone, WhatsApp, email, print, or in-person communication freezes that revision. A material negotiation requires a new revision. Human-readable revision comparison shows changes without exposing internal estimate data.

Customer confirmation may be verbal/phone, WhatsApp, email, or purchase order. A PO may be pending and attached later. The final command changes the enquiry to Won and the quotation to Ready for Sales Order; it does not create a Sales Order.

## Word/PDF document generation

Uploaded active DOCX templates are rendered with `docxtpl`. The context is an explicit customer-facing whitelist. Generated files are unique immutable artifacts and are registered in shared Documents.

PDF conversion is an optional LibreOffice adapter. If LibreOffice is unavailable or conversion fails, the Word document remains available and the generated record reports `WORD_ONLY`; the quotation workflow is not rolled back. The local machine currently has no active approved quotation template and no validated LibreOffice executable, so live document UAT remains an operational acceptance item even though generator, whitelist, storage, and failure paths are covered by backend tests.

## Security and audit

- REST querysets, commands, WebSocket subscriptions, and presence are company-scoped.
- RBAC permissions cover view, create, change, finalize, quick quotation, communicate, negotiate, confirm, Ready for Sales Order, templates, and document generation.
- Every controlled command uses the existing audit/domain-event services.
- Customer-facing generation receives no cost-estimate objects or internal margin fields.
- Production still requires real role assignments, secret management, HTTPS, Redis, secure cookies, logging/alerting, backups, restore testing, and an approved document template.

## Principal implementation locations

- Realtime server: `backend/apps/realtime/`, `backend/config/asgi.py`, and settings files.
- Domain-event commit boundary: `backend/apps/core/domain_events.py`.
- Unified intake: `backend/apps/external_enquiries/`.
- Quotation aggregate and services: `backend/apps/quotations/`.
- Realtime client: `frontend/src/production/lib/realtime.tsx`.
- Axis workspaces: `incoming-enquiries-page.tsx`, `quotations-page.tsx`, and `quotation-page.tsx`.
