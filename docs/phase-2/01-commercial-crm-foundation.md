# Phase 2 Commercial CRM Foundation

Status: complete for the Customer to Engineering Feasibility vertical slice on 11 August 2026.

## Delivered boundary

The production path is:

`Customer -> Contact/Site -> Enquiry/RFQ -> Requirements/Items -> Activities/Documents -> Engineering Review -> Clarification -> Decision -> Ready for Estimation`.

The browser uses live Django REST APIs and PostgreSQL records. The implementation does not contain static production data. Secure Website Enquiry Intake and Commercial Estimation are now production routes; Quotation, Project, Drawing Management, BOM, and downstream operations remain intentionally absent.

## Architecture

- React, TypeScript, TanStack Query, React Hook Form, shadcn/ui, and the preserved Axis industrial visual language.
- Django modular monolith with command services for lifecycle transitions.
- PostgreSQL row locks and database constraints for numbering, revisions, and concurrent decisions.
- Existing shared RBAC, documents, audit, notifications, approvals, numbering, organization, and employee services.
- Company-scoped querysets and relationship validation at the API and service layers.

## Production contracts

- Human-readable numbers identify customers and enquiries; UUIDs remain routing details.
- Status changes use explicit commands, not editable status fields.
- Decimal values remain strings over the API and Decimal values in Django.
- Completed engineering revisions are immutable. Reassessment creates a new revision.
- An enquiry is only ready for estimation after a feasible decision, no unresolved clarification, and any configured approval is approved.

## Performance posture

Operational lists are paginated and searchable. Customer, enquiry, and engineering querysets use `select_related` and `prefetch_related` for their displayed relationships. No speculative cache was added.
