# Authentication

## Contract

Authentication uses Django sessions with same-origin CSRF protection. The React client sends credentials on every request, obtains a CSRF cookie before unsafe operations, and includes `X-CSRFToken` for POST, PUT, PATCH, and DELETE requests.

`User` is the login/security record. `Employee` is the organization record. An employee may link to one user, but neither model duplicates the responsibility of the other.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/auth/csrf/` | Establish the CSRF cookie |
| POST | `/api/v1/auth/login/` | Authenticate by email/password and create a session |
| POST | `/api/v1/auth/logout/` | Destroy the current session |
| GET | `/api/v1/auth/me/` | Return identity, employee context, and effective permission codes |
| POST | `/api/v1/auth/change-password/` | Verify the current password and set a new one |

Unauthenticated API access returns HTTP 401 with the shared error envelope. Login failures are intentionally generic. A cache-backed login throttle limits repeated attempts without revealing whether an account exists.

## Security decisions

- Password storage and validation use Django's password framework.
- Session cookies are HTTP-only; secure-cookie settings are enabled in production settings.
- CSRF trusted origins and allowed hosts are configured by environment.
- Passwords and secret keys are never committed or seeded in migrations.
- `seed_development` requires email/password environment values and refuses to run outside debug mode.
- Logout and password changes are unsafe operations and therefore CSRF protected.

## Operational bootstrap

Use `python manage.py createsuperuser` for an interactive administrator. Django Admin is a bootstrap, emergency support, and diagnostic surface; normal office workflows belong in the Axis frontend.

## Tests

Backend tests cover CSRF rejection, successful login/session creation, the `/me` capability response, generic failure behavior, logout, and password change. Frontend tests cover CSRF attachment, normalized API errors, and login-form behavior.

## Future integration

Audit events, forced session revocation, password reset delivery, optional MFA, and SSO can be added in later approved phases. They must preserve server-side permission evaluation and must not move secrets to browser storage.
