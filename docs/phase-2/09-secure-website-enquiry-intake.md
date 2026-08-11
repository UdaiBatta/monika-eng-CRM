# Secure Website Enquiry Intake

## Purpose and boundary

The public website now submits quote/contact requests into a review queue instead of creating CRM records directly. A sales employee must review and convert each accepted submission. The module reuses the production Customer, Contact, Enquiry, Documents, Audit, Notifications, Numbering, RBAC, and company-scope services.

Frontend routes:

- `/app/crm/website-enquiries`
- `/app/crm/website-enquiries/:submissionId`

Public endpoint:

- `POST /api/v1/integrations/website/enquiries/`

Internal APIs use `/api/v1/external-enquiries/` and require authenticated RBAC permissions.

## Staging records and lifecycle

`IntegrationCredential` binds one active website key to one company and stores only a digest of the secret. `ExternalEnquirySubmission` stores source metadata, normalized contact details, privacy-hashed IP data, spam/review state, duplicate suggestions, ownership, and conversion links. `ExternalEnquiryAttachment` stores validated private staged files with checksums, scan state, and an optional promoted `Document` link.

Review states are New, Needs review, Possible duplicate, Accepted, Converted, Rejected, and Spam. Reject, spam, restore, assignment, and conversion are controlled commands. A converted submission is immutable and links to exactly one CRM Enquiry.

## Duplicate and conversion behavior

Duplicate intelligence checks normalized email and phone values within the credential's company and suggests matching Customers and Contacts. The human reviewer chooses an existing or new Customer and Contact; no fuzzy match silently changes production CRM data.

Conversion is atomic and row-locked. It allocates controlled Customer/Enquiry numbers, creates or reuses the selected CRM records, promotes accepted attachments through the private document service, writes audit events, emits notifications, and locks the source submission. Concurrent conversion calls return the one existing Enquiry rather than creating duplicates.

## Attachment boundary

- Maximum three files per submission.
- Allowed types: PDF, PNG, JPG, and JPEG.
- Default maximum: 5 MB per file and 8 MB for the full request.
- Filenames are sanitized; MIME/extension, size, and content are validated.
- Files stay in private staged storage and carry a scan status.
- Production malware scanning is not configured yet. Quarantined or failed files are never promoted.

## Permissions

Separate permissions cover viewing, reviewing, assigning, converting, rejecting, marking spam, and viewing/downloading documents. Querysets and relationship validation enforce company isolation independently of the UI.

