# Phase 0 — Requirements and Domain Model

This directory is the mandatory architecture baseline for the production Monika Engineers Integrated ERP. The authoritative specification contains sections 0-140 and requires these artifacts before large-scale implementation.

## Deliverables

1. [System architecture](01-system-architecture.md)
2. [Module map](02-module-map.md)
3. [Entity relationship model](03-entity-relationship-model.md)
4. [Workflow and state diagrams](04-workflow-state-diagrams.md)
5. [API plan](05-api-plan.md)
6. [Migration and development plan](06-migration-development-plan.md)
7. [Requirements traceability register](07-requirements-traceability.md)

## Baseline decisions

- Modular monolith, not microservices.
- React/TypeScript/Vite frontend using Axis CRM as the visual standard.
- Django and Django REST Framework backend.
- PostgreSQL with transaction-based inventory and controlled revisions.
- Redis and Celery for background work.
- Private object storage through a provider-independent service.
- Explicit command endpoints for important state transitions.
- Configurable RBAC and approvals; final company roles are not invented.
- Project 360 is the central execution workspace, with controlled Drawing/BOM management.
- No AI assistant functionality at this stage.

## Review gate

These documents are an engineering baseline, not business approval. Phase 1 begins only after process owners review the assumptions and decisions listed in the architecture and development plan.
