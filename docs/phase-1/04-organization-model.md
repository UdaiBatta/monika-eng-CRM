# Organization Model

## Entities

- `Company` is the top-level legal/operating scope.
- `Branch` belongs to a company.
- `Department` belongs to a company and may be associated with a branch.
- `Designation` belongs to a company.
- `Warehouse` belongs to a company and may be associated with a branch.
- `Employee` belongs to a company and may reference branch, department, designation, reporting manager, and a user account.

Employees include a company-unique employee code, name, work contact data, joining/leaving dates, employment type, and employment status. Employment state is separate from the linked user's active/security state.

## Integrity rules

Every cross-reference must remain inside the employee or resource company. A department from one company cannot be attached to an employee in another; the same applies to branches, designations, warehouses, reporting managers, RBAC scopes, settings, and numbering. Validation is applied before save and is covered by tests.

Human-readable codes use company-scoped uniqueness where applicable. UUIDs remain the stable API identifiers.

## Lifecycle decisions

Records are not silently deleted when an employee leaves. Employment status and leaving date express that lifecycle. A user account can be disabled independently so organization history is not erased.

Creating a company automatically creates its `CompanySettings` record with conservative India/INR defaults. This does not create commercial masters, roles, employees, customers, or operational transactions.

## API and UI

Company, branch, department, designation, warehouse, and employee resources are exposed under `/api/v1/`. Lists support search, filters, ordering, and pagination. The production UI includes registers and editors, with a dedicated employee profile and form flow.

## Future integration

CRM customer ownership, project teams, drawing actors, warehouse transactions, service engineers, and approval participants should reference employee/user and organization scopes rather than duplicating identity fields.
