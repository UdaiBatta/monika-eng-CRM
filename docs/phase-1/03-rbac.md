# Role-Based Access Control

## Model

The RBAC engine is data driven:

- `Permission` is the catalog entry identified by a stable code such as `organization.employee.view`.
- `Role` is a company-owned grouping.
- `RolePermission` associates a role with allowed capabilities.
- `RoleAssignment` grants a role to a user with a scope.
- `PermissionOverride` is a per-user allow or deny exception with a scope.

Assignments and overrides support company, branch, department, warehouse, and self scopes. Scope references are validated against the selected company.

## Evaluation rules

1. Superusers are allowed for all foundation capabilities.
2. Applicable role grants and user allow-overrides are collected for the target context.
3. Applicable user deny-overrides are evaluated last and win over every allow.
4. Querysets are restricted to the user's effective organization scope before serialization.
5. The frontend hides unavailable navigation, but every API endpoint independently enforces its permission code.

Deny precedence is deliberate: a broad company role cannot bypass a narrower explicit deny.

## Administrative behavior

The migration seeds the permission catalog only. It does not invent roles such as Sales Manager or Storekeeper because their responsibilities and scope are business decisions. Administrators can create roles, compose permissions, assign scoped access, and add carefully reviewed exceptions through the Axis UI or API.

## Permission families in Phase 1

Foundation codes cover user, employee, organization registers, RBAC administration, company settings, feature flags, masters, and numbering. View and manage actions are separated where the resource supports them.

## Tests

Tests verify role grants, scoped grants, user overrides, deny precedence, and company-restricted querysets. Permission-aware navigation is also exercised through authenticated browser QA.

## Limitations and future use

Object-specific collaboration rules and approval authority are not implemented. Later CRM, project, drawing/BOM, purchasing, production, quality, and service permissions must extend the catalog and reuse the same evaluator instead of introducing module-local role checks.
