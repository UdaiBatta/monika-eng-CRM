# Deployment boundary

Phase 1A–D defines the backend container and production-safe Django settings. A reverse proxy, TLS termination,
secret manager, observability, and an immutable frontend image are deployment-environment concerns and must be
configured before production release. The committed Compose file is for local integration and QA.
