# API Plan

Status: Phase 0 baseline
Base path: `/api/v1/`

## 1. API principles

- REST resources for reading and ordinary draft-field editing.
- Explicit command endpoints for workflow transitions and irreversible operations.
- Backend authorization and scope filtering on every endpoint.
- Server-side validation for all critical rules.
- OpenAPI generated from the implementation and checked in CI for unintended breaking changes.
- Pagination, filters and sorting for every operational list.
- Decimal values serialized as strings; timestamps in ISO 8601 UTC.
- Stable UUIDs in URLs; human document numbers remain searchable display identifiers.

## 2. Browser authentication

The initial internal React application uses same-origin secure session cookies:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/login/` | Authenticate and establish session |
| `POST /api/v1/auth/logout/` | End current session |
| `GET /api/v1/auth/me/` | Current user, employee, scopes and effective capabilities |
| `POST /api/v1/auth/password-reset/request/` | Request reset flow |
| `POST /api/v1/auth/password-reset/confirm/` | Complete reset |
| `GET /api/v1/auth/sessions/` | View active sessions |
| `DELETE /api/v1/auth/sessions/{id}/` | Terminate a session |

CSRF protection is mandatory for unsafe browser requests. Mobile/partner token authentication is a separate future capability.

## 3. Response and error conventions

Successful single-resource responses return the resource directly. Collections return:

```json
{
  "results": [],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total": 0,
    "pages": 0
  }
}
```

Errors return a human-readable message, stable code, optional field errors and a correlation ID:

```json
{
  "error": {
    "code": "insufficient_available_stock",
    "message": "Cannot issue 10 units. Only 6 units are available after reservations.",
    "fields": {"quantity": ["Maximum available quantity is 6."]},
    "correlation_id": "01J..."
  }
}
```

Raw tracebacks and internal secrets are never returned.

## 4. List conventions

Example:

```text
GET /api/v1/projects/?search=PRJ-2026&status=in_progress&customer=<uuid>&ordering=-target_completion&page=1&page_size=25
```

Supported where relevant: `search`, `status`, `customer`, `project`, `date_from`, `date_to`, `employee`, `department`, `priority`, `branch`, `warehouse`, `ordering`, `page`, and `page_size`. URL query parameters are the shareable frontend filter state.

## 5. Command endpoint rule

Status fields are read-only in ordinary create/update serializers after a workflow starts. Commands follow:

```text
POST /api/v1/<resources>/{id}/<command>/
```

Examples:

| Resource | Commands |
|---|---|
| Enquiry | `receive`, `start-review`, `request-engineering-review`, `record-win`, `record-loss`, `cancel` |
| Quotation | `submit`, `approve`, `reject`, `send`, `create-revision`, `accept`, `cancel` |
| Drawing revision | `submit-for-check`, `pass-check`, `approve-and-release`, `reject`, `supersede` |
| Purchase requisition | `submit`, `approve`, `reject`, `convert`, `cancel` |
| Purchase order | `submit`, `approve`, `reject`, `send`, `close`, `cancel-open-balance` |
| Goods receipt | `post`, `submit-for-inspection`, `cancel` |
| Inventory | `reserve`, `release-reservation`, `issue`, `return`, `transfer`, `adjust` |
| Job card | `start`, `pause`, `resume`, `block`, `complete`, `cancel` |
| Inspection | `submit-result`, `approve-deviation`, `raise-ncr` |
| Dispatch | `submit`, `approve`, `dispatch`, `confirm-delivery`, `cancel-open-balance` |
| Service request | `assign`, `schedule`, `start`, `resolve`, `request-signoff`, `close`, `cancel` |
| AMC contract | `activate`, `generate-schedule`, `renew`, `expire`, `cancel` |

Every command re-reads and locks the necessary records, validates state, permission, scope, version, mandatory evidence and downstream constraints, then records audit events in the same transaction.

## 6. Concurrency and idempotency

- Mutable resources expose a monotonically increasing `version` or updated timestamp.
- Draft updates require the last-seen version and return `409 conflict` when stale.
- Commands that can be retried accept an `Idempotency-Key` header.
- Number allocation, approval decisions, GRN posting, stock operations and revision release use row-level locks.
- Duplicate official numbers are prevented by database constraints, not only application checks.

## 7. Endpoint map by phase

### Phase 1 — foundation

```text
/auth/                         /users/                 /employees/
/departments/                  /designations/          /branches/
/warehouses/                   /roles/                 /permissions/
/role-assignments/             /approval-rules/        /approval-requests/
/audit-events/                 /documents/             /notifications/
/numbering-sequences/          /masters/               /company-settings/
/feature-flags/
```

### Phase 2 — CRM to quotation

```text
/customers/                    /customers/{id}/timeline/
/customer-contacts/            /customer-addresses/    /crm-activities/
/tasks/                        /enquiries/              /engineering-reviews/
/estimates/                    /estimate-revisions/     /quotations/
/quotation-revisions/          /negotiation-events/
```

### Phase 3 — sales, project and engineering

```text
/sales-orders/                 /projects/               /projects/{id}/360/
/project-milestones/           /drawings/               /drawing-revisions/
/engineering-changes/          /boms/                   /bom-revisions/
/routings/                     /routing-revisions/
```

The Project 360 endpoint is an authorized aggregation/read model. Writes still go through owning resource endpoints.

### Phase 4 — planning and procurement

```text
/mrp-runs/                     /mrp-requirements/       /purchase-requisitions/
/vendors/                      /vendor-rfqs/            /vendor-quotes/
/vendor-comparisons/           /purchase-orders/
```

### Phase 5 — receiving, quality and inventory

```text
/goods-receipts/               /incoming-inspections/   /materials/
/stock-balances/               /stock-transactions/     /stock-reservations/
/material-issues/              /stock-transfers/        /cycle-counts/
```

Stock balances and transactions are read-only. Movement commands create ledger entries.

### Phases 6-8 — execution to installation

```text
/production-orders/            /job-cards/              /production-entries/
/wip/                          /scrap-records/           /job-work-orders/
/inspections/                  /ncrs/                    /capas/
/packing-lists/                /dispatches/              /delivery-confirmations/
/installation-jobs/
```

### Phases 9-10 — assets, service and AMC

```text
/assets/                       /assets/{id}/360/         /warranties/
/service-requests/             /service-job-cards/       /service-schedule/
/service-visits/               /service-expenses/        /service-reports/
/amc-opportunities/            /amc-proposals/           /amc-contracts/
/pm-schedules/                 /amc-billing-schedules/   /amc-renewals/
```

### Phases 11-14 — insights and corporate modules

```text
/dashboard/                    /reports/                 /exports/
/hr/                           /attendance/              /leave/
/payroll/                      /finance/                 /imports/
/barcode-lookup/               /integrations/
```

## 8. 360-degree read models

| Endpoint | Includes |
|---|---|
| `/projects/{id}/360/` | Summary, lifecycle, engineering, BOM, materials, purchase, inventory, production, quality, dispatch, installation, documents, cost, service and audit links |
| `/customers/{id}/360/` | Contacts, enquiries, quotations, orders, projects, outstanding, assets, service, AMC, documents and timeline |
| `/materials/{id}/360/` | Specification, balances, reservations, incoming, purchase/price history, consumption, vendors, projects and serial/batch data |
| `/assets/{id}/360/` | Customer, project, serial, installation, warranty, AMC, service, replaced parts, documents and timeline |

Large sections use paginated child endpoints; the 360 response contains summaries and links rather than unbounded histories.

## 9. Documents and storage

```text
POST /api/v1/documents/upload-intents/
POST /api/v1/documents/{id}/complete-upload/
POST /api/v1/documents/{id}/versions/
GET  /api/v1/documents/{id}/preview-url/
GET  /api/v1/documents/{id}/download-url/
GET  /api/v1/documents/{id}/audit/
```

The API checks access before issuing short-lived URLs. Files are private and document metadata remains in PostgreSQL.

## 10. Imports, exports and background jobs

- Imports use upload → validation preview → confirm commands; invalid rows never partially write unnoticed.
- Exports respect current filters, field permissions and record scopes.
- Large PDFs, spreadsheets and reports return a job ID and notify the requester when ready.
- Seed/demo data is limited to development environments.

## 11. Versioning and compatibility

Breaking changes require a new API version or an explicitly documented migration window. Additive fields remain backward compatible. API changes update OpenAPI, frontend types, tests, architecture documentation and requirement traceability in the same change.

## 12. Open decisions

- Final session duration, password policy, lockout and MFA policy.
- Default page sizes and export limits.
- Whether external customer/vendor portals share `/api/v1` or receive a separate public contract.
- Document retention periods and maximum file sizes/types.
- Which finance endpoints are implemented internally versus integration adapters.
