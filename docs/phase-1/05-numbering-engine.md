# Numbering Engine

## Purpose

`DocumentSequence` defines company-scoped, optionally branch-scoped numbering rules. It stores a stable code, prefix, suffix, padding, next number, optional financial year, and active state. The engine is infrastructure for later documents; Phase 1 does not create operational documents.

## Safety contract

Number consumption runs inside `transaction.atomic()` and locks the sequence row with `select_for_update()`. The number is formatted and `next_number` is incremented only while the lock is held. Concurrent requests therefore cannot receive the same value.

Previewing is read-only. `GET /api/v1/document-sequences/{id}/preview/` returns the next formatted value and counter without consuming it.

Sequence uniqueness includes company, branch, code, and financial-year context. References are cross-company validated and inactive sequences cannot be consumed.

## Formatting

The formatted number combines prefix, zero-padded counter, and suffix. Financial-year helpers are centralized so later modules do not calculate periods independently. Actual business prefixes and reset conventions remain administrator-owned input.

## Authorization

Viewing and previewing require `numbering.sequence.view`; creating or changing rules requires `numbering.sequence.manage`. Querysets remain within the caller's allowed company/branch context.

## Tests

Tests cover formatting, preview non-consumption, actual consumption, and row-lock-backed progression against PostgreSQL. SQLite is not used to claim locking behavior.

## Future integration

Later CRM enquiries, quotations, projects, drawings, purchase orders, production orders, NCRs, dispatches, service requests, and invoices should request numbers through this service inside their own creation transaction. They must never increment sequence fields directly.
