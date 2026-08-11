# Phase 2 Acceptance Record

Acceptance date: 11 August 2026

## Automated gates

- Backend: `80 passed in 26.47s` against PostgreSQL, including concurrency tests.
- Frontend: four files and `19 passed`.
- Production build: TypeScript and Vite completed; 2,612 modules transformed.
- Ruff: all checks passed.
- oxlint: exit 0 with eight existing non-blocking React fast-refresh/exhaustive-dependency warnings.
- Django: `check` reported no issues and `makemigrations --check --dry-run` reported no changes.
- Docker Compose configuration validated. Django, PostgreSQL, and Redis were healthy; Celery worker and beat were running.
- Browser: signed-in functional, responsive, and permission acceptance completed with no warning/error console entries.

`manage.py check --deploy` correctly reported six development-configuration warnings: HSTS, HTTPS redirect, production secret key, secure session cookie, secure CSRF cookie, and `DEBUG=False`. These are explicit go-live gates.

One verification attempt used an overlong Windows temporary path and caused 17 document-test `FileNotFoundError` results. The identical suite passed all 80 tests when rerun with a short `%TEMP%` base; no application change was required.

## Signed-in vertical-slice walkthrough

The administrator completed this real PostgreSQL path through the production UI and APIs:

1. Created ABC Industries Pvt. Ltd. with primary contact Asha Rao and Pune Plant.
2. Created enquiry ENQ-2026-0001 / RFQ-2026-431 with one structured requirement and one Decimal-quantity item.
3. Uploaded a synthetic PDF through the authenticated production document endpoint and linked it to the enquiry.
4. Verified the RFQ in Enquiry Documents and Engineering Documents.
5. Recorded the follow-up “Confirm RFQ document receipt” and verified it in Enquiry 360.
6. Received and reviewed the enquiry, then sent it to engineering exactly once.
7. Assigned and started revision 1, saved the structured assessment, requested a PLC-protocol clarification, recorded the Profinet response, and closed it.
8. Completed the review as FEASIBLE and verified the computed READY FOR ESTIMATION gate.

The upload used authenticated HTTP against the same production API because the browser test driver cannot select a local file. Category/file validation and both live linked-document views were verified in the browser.

## Access, responsive, and quality acceptance

- A restricted signed-in user did not see Customers, Enquiries, or Engineering navigation.
- Direct navigation to the engineering review produced the access-restricted screen.
- Desktop and 390-pixel mobile layouts were checked; the mobile document width matched its viewport and had no page-level horizontal overflow.
- The mobile navigation drawer opened and remained usable.
- The final browser log contained no application warnings or errors.
- The final desktop screen retained the Axis industrial layout and displayed live customer, enquiry, clarification, document, and engineering data.

## Defects found and closed during acceptance

- Foundation master audit registration was added and regression-tested.
- Document category audit registration was added and regression-tested.
- Linked-document serialization was corrected and regression-tested.

No defect was hidden or deferred from this milestone.
