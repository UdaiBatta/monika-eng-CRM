# Enquiry and RFQ

## User routes

- `/app/crm/enquiries`
- `/app/crm/enquiries/new`
- `/app/crm/enquiries/:enquiryId`

The register is searchable, filterable, paginated, and based on live APIs. Enquiry 360 shows customer, contact, site, RFQ reference, owner, priority, dates, value, requirements, Decimal item quantities, engineering context, activities, documents, and readable history.

## Controlled commercial path

`DRAFT -> RECEIVED -> UNDER_REVIEW -> ENGINEERING_REVIEW`

Commands receive the enquiry, start commercial review, send it to engineering, mark it lost, or cancel it. Direct status PATCH is rejected. Sending to engineering atomically creates exactly one current Engineering Feasibility Review.

The stage tracker continues through Ready for Estimation, Commercial Estimation, and the approved Ready for Quotation handoff. Estimation has controlled production routes. Quotation is explicitly shown as not implemented and has no route, record, or fake action.

## Main APIs

- `GET/POST /api/v1/enquiries/`
- `GET/PATCH /api/v1/enquiries/{id}/`
- `GET /api/v1/enquiries/{id}/workspace/`
- `POST /api/v1/enquiries/{id}/receive/`
- `POST /api/v1/enquiries/{id}/start-review/`
- `POST /api/v1/enquiries/{id}/send-to-engineering/`
- outcome commands for lost/cancelled
- `/api/v1/enquiry-requirements/`
- `/api/v1/enquiry-items/`

Documents use the shared private document service. Activities use `CrmActivity`. History uses immutable AuditEvent records.
