# Customer Master and Customer 360

## User routes

- `/app/crm/customers`
- `/app/crm/customers/:customerId`

The register supports search, status/type filters, pagination, empty/loading/error states, and permission-controlled creation. Customer 360 has exactly these live tabs: Overview, Contacts, Sites, Enquiries, Activities, Documents, and History.

## Data and lifecycle

The existing Customer, CustomerContact, CustomerSite, and CrmActivity models remain authoritative. Customer codes use the company numbering service. Contacts and sites preserve their own active/default/primary rules for later installation, dispatch, and service reuse.

Lifecycle commands are explicit:

- activate
- block with context
- deactivate

The API continues to validate company relationships, GSTIN/PAN format and uniqueness, email, phone, sensitive commercial fields, and permissions.

## Customer 360 answers

- who the customer is and how to contact them;
- which site is relevant;
- which enquiries are active;
- what follow-up needs attention;
- which documents are linked;
- what changed and who changed it.

No fake order, invoice, project, service, or revenue data is displayed.

## Main APIs

- `GET/POST /api/v1/customers/`
- `GET/PATCH /api/v1/customers/{id}/`
- `GET /api/v1/customers/{id}/workspace/`
- customer lifecycle command actions
- `/api/v1/customer-contacts/`
- `/api/v1/customer-sites/`
- `/api/v1/crm-activities/`

All unsafe requests use authenticated same-origin sessions and CSRF protection.
