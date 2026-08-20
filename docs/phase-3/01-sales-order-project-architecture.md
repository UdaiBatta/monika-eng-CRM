# Phase 3 Sales Order and Project Architecture

Report date: 19 August 2026

## Business boundary

Phase 3 implements the real operational bridge from customer confirmation to Project Ready for Detailed Engineering:

Customer confirmation -> Customer PO received or pending -> Sales Order -> controlled release -> Project 360 when required -> Sales-to-Engineering handoff -> clarification when required -> Engineering acceptance.

Drawing Management, BOM, MRP, purchasing, inventory transactions, production, quality, dispatch, service, AMC, and live external messaging connectors are not implemented.

## Customer Purchase Order

`CustomerPurchaseOrder` is the stable company/customer record and `CustomerPurchaseOrderRevision` preserves each received amendment. A revision stores dates, currency, stated value, tax/line snapshots, delivery/payment/warranty terms, notes, and an optional private shared `Document`. Company/customer/PO number is duplicate protected. Quote-linked POs expose structured, human-readable differences and controlled review/acceptance commands; they never overwrite a quotation or released Sales Order.

## Sales Order

`SalesOrder` owns identity, company/customer links, order mode, responsible Sales employee, PO pending, current revision, and lifecycle status. `SalesOrderRevision` snapshots the commercial agreement and `SalesOrderLine` stores free-form Decimal lines without requiring Product Master. Orders can start from an accepted quotation or a permission-controlled Direct Sales Order with a mandatory reason and CRM history.

The shared Numbering Engine allocates Sales Order numbers. Generic status PATCH is unavailable. Submit, release, hold, resume, cancel, amendment, PO link, and Project creation are explicit commands. Released revisions are immutable. Amendments copy the previous snapshot into a new draft; releasing it warns the Project that its commercial baseline changed.

## Project 360 and Engineering handoff

Releasing a project-required Sales Order creates one idempotent `Project` using the shared Numbering Engine. Project 360 reads the released commercial snapshot, linked PO, shared Documents, and audited activity. `ProjectEngineeringHandoff` holds the plain-language Sales handoff. `ProjectHandoffClarification` keeps Engineering questions and Sales responses in the operational record.

The Engineering queue provides all, unassigned, and assigned-to-me views. `Take This` uses PostgreSQL row locks, so two engineers cannot claim the same handoff. Engineering can request clarification, Sales can respond, and Engineering can accept only when open questions are resolved. Acceptance records the exact Sales Order and Customer PO revisions.

## Shared infrastructure

- PostgreSQL remains authoritative.
- Controlled services use `transaction.atomic` and `select_for_update` for critical transitions.
- Existing Approval, Documents, Audit, Notifications, Numbering, RBAC, realtime, presence, and optimistic-concurrency systems are reused.
- Realtime messages contain safe identifiers/metadata and publish after transaction commit; TanStack Query refetches authorized server state.
- Internal notes are removed from Sales Order API output without the dedicated permission.
- Company-scoped querysets and company validation protect tenant boundaries.

## Routes

- `/app/sales/customer-pos`
- `/app/sales/orders`
- `/app/sales/orders/:salesOrderId`
- `/app/projects`
- `/app/projects/:projectId`
- `/app/engineering/work`

The UI follows the existing Axis CRM system, responsive card/table patterns, permission-aware navigation, human status labels, and progressive disclosure.
