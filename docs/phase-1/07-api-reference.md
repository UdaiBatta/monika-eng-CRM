# Phase 1 API Reference

Base path: `/api/v1/`

All resource identifiers are UUIDs. List endpoints use DRF pagination and accept `search`, `ordering`, and declared filter fields. Unsafe methods require an authenticated session and CSRF token. Errors use a consistent JSON envelope with a human-readable message and field details when available.

## Platform endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `health/` | Database and cache readiness |
| GET | `auth/csrf/` | Establish CSRF cookie |
| POST | `auth/login/` | Email/password session login |
| POST | `auth/logout/` | End current session |
| GET | `auth/me/` | Identity, employee context, effective permissions |
| POST | `auth/change-password/` | Change current user's password |

## CRUD resources

The following router resources support standard `GET collection`, `POST collection`, `GET detail`, `PUT/PATCH detail`, and `DELETE detail` operations subject to their permission map:

| Domain | Resources |
|---|---|
| Accounts | `users` |
| Organization | `companies`, `branches`, `departments`, `designations`, `warehouses`, `employees` |
| RBAC | `permissions`, `roles`, `role-permissions`, `role-assignments`, `permission-overrides` |
| Configuration | `company-settings`, `feature-flags` |
| Masters | `currencies`, `units-of-measure`, `tax-rates`, `payment-terms`, `delivery-terms` |
| Numbering | `document-sequences` |

`permissions` is a catalog and should be treated as platform-controlled in normal operation. Business administrators compose roles from catalog entries; they should not invent ad hoc permission strings.

## Number preview

`GET /api/v1/document-sequences/{uuid}/preview/` returns:

```json
{
  "preview": "PRJ-0001",
  "next_number": 1
}
```

Preview does not consume the counter. Number consumption is an internal service operation intended to be called by later document-creation transactions.

## Authorization and scoping

Each viewset maps actions to explicit foundation permission codes and applies scoped queryset filtering. A successful list response therefore reflects both resource permission and organization scope. Per-user deny overrides take precedence over role grants.

## Versioning and future compatibility

New foundation-compatible fields should be additive within `/api/v1/`. Breaking changes require a new API version and migration plan. Phase 1E-H engines and later CRM/ERP modules must add separate domain endpoints rather than overloading these foundation resources.
