# Website Intake and Estimation Acceptance Record

Acceptance date: 11 August 2026

## Automated gates

- Backend: 96/96 tests passed in the definitive full PostgreSQL regression run.
- Frontend: 32/32 tests passed across eight files in the definitive full run.
- Ruff: all checks passed.
- Django system check: no issues.
- Migration drift: no changes detected after applying all final migrations.
- TypeScript/Vite production build: passed.
- oxlint: exit 0 with eight existing non-blocking Fast Refresh/exhaustive-dependency warnings.
- Deployment check: six expected development-only warnings for HSTS, HTTPS redirect, secret strength, secure cookies, and DEBUG.

## Website intake browser UAT

A signed database-backed request `WEB-UAT-2026-0001` appeared in the Axis Website Enquiry Inbox. The reviewer opened it, inspected source/security and duplicate intelligence, assigned it to Development Administrator, selected the Customer/Contact outcome, and converted it to `ENQ-2026-0001`. The submission became locked and linked to the production CRM records. Idempotent retry, invalid signature, replay, bad attachment, cross-company access, spam, and concurrent double-conversion are covered by backend tests.

## Estimation browser UAT

The live scenario used `ENQ-2026-0001` and its FEASIBLE Engineering review (24 engineering hours, 120 manufacturing hours, no open clarifications):

1. Created controlled estimate `EST-2026-0001`, revision 1.
2. Added Material and Labour cost bases and selected 20% markup.
3. Verified persisted cost INR 964,000, price INR 1,156,800, gross margin INR 192,800 / 16.67%.
4. Submitted through the shared approval engine and approved it; editing locked.
5. Created revision 2 and verified revision 1 remained in history.
6. Added Machine, Subcontract, Packing, and Freight lines through the responsive UI.
7. Refreshed and verified six persisted lines, cost INR 1,087,000, price INR 1,304,400, gross margin INR 217,400 / 16.67%.
8. Submitted and approved revision 2 through a second permanent approval record.
9. Verified Enquiry 360 shows Estimation complete and Ready for quotation while explicitly stating Quotation is not implemented.

The responsive 390-pixel/narrow layout remained usable. A cost-line dialog overflow found during UAT was fixed with viewport-bounded scrolling. A dormant shared-approval serializer tuple defect was also found, fixed, and regression-tested. No Docker container was needed: native PostgreSQL, Django, and Vite were used.

## Scope stop

Quotation, quotation documents/PDFs, negotiation, Sales Order, Project, BOM, Purchase, and Production remain unimplemented by explicit milestone scope.
