# Immutable Business Audit Engine

Status: implementation and automated verification complete on 2026-08-10; final signed-in browser acceptance pending.

## Policy

`AuditEvent` is the permanent business answer to who changed what, when and how. It is separate from application and security logs. The model and queryset block application-level updates and deletes, the REST interface is read-only, and there are no PUT, PATCH or DELETE audit routes.

Critical business commands publish synchronous domain events inside their database transaction. The audit subscriber writes before commit; an audit failure therefore fails the critical command instead of allowing an unaudited transition. Post-commit notification failure follows a different policy and never invalidates an already committed decision.

## Context and data handling

Request middleware establishes actor, employee, correlation/request ID, IP and user-agent context without making domain services depend on HTTP. `record_event` is the authoritative writer. It stores normalized action, module, controlled entity type/ID/reference, readable summary, structured field changes and supplementary metadata.

Password, password hash, tokens, CSRF values, secrets, credentials and private keys are recursively redacted. User/employee snapshot names preserve understandable history after account changes.

## API, UI and permissions

- `GET /api/v1/audit/events/`
- `GET /api/v1/audit/events/{id}/`
- `GET /api/v1/audit/entities/{entity_type}/{entity_id}/`

The API is paginated, company scoped and supports date, actor, action, module, entity and text filters. `audit.event.view` controls access; `audit.event.export` reserves future governed export capability. The Axis route `/app/activity-history` shows plain-language Activity History and readable before/after changes rather than raw JSON.

## Extension rule

A future domain must register its entity type and supported capabilities in the controlled entity registry, mutate data through an explicit service/command, and publish one meaningful `DomainEvent`. It must not create module-specific history tables or call `AuditEvent.objects.create` throughout business code.
