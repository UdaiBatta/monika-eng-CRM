# Phase 1 Browser Acceptance

Status: COMPLETE on 2026-08-11.

The production application was verified against the local Django/PostgreSQL stack at `http://127.0.0.1:5173/app` using synthetic development users.

## Accepted scenarios

- Administrator login and logout completed successfully.
- `/api/v1/auth/me/` resolved the linked active employee in the application shell.
- Navigation displayed only capabilities granted to the signed-in user.
- A real active user with no role grants saw only the workspace link and received the plain-language **Access restricted** state when opening Documents.
- Documents, Notifications, Activity History and My Approvals loaded from live APIs.
- Desktop (1440 × 900 CSS pixels), tablet (820 × 1020) and mobile (390 × 844) layouts remained usable without horizontal page overflow.
- The tested application routes produced no browser console errors or warnings.

The database contained no document or approval records during this acceptance run, so their verified empty states were exercised. Command-level upload, versioning and approval behavior remains covered by the automated backend and frontend suites.

## Evidence boundary

This acceptance completes the Phase 1A–H shared-services browser gate. It does not mark CRM, Enquiry, Engineering, Estimation, Quotation or later operational modules complete.
