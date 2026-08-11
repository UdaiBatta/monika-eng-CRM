# Website Integration Guide

## Create or rotate a credential

Use the Django command for the target company:

```powershell
.\.venv\Scripts\python.exe backend\manage.py create_website_credential --company-code ME --key-id monika-website --name "Monika website"
```

The command prints the secret once. Put it in the backend secret manager/environment as an entry in `INTEGRATION_SECRETS_JSON`; never commit it. The database contains only its SHA-256 digest. Rotation replaces the credential secret and invalidates the old value.

## Signing a request

Send these headers:

- `X-Integration-Key`: issued key ID
- `X-Timestamp`: current Unix timestamp in seconds
- `X-Request-ID`: unique request identifier
- `X-Signature`: lowercase hexadecimal HMAC-SHA256
- `X-Integration-Source`: configured source value, when the credential restricts it

The JSON body carries `submission_id`, optional `idempotency_key` (defaults to `submission_id`), `source_type`, `name`, contact email or phone, `subject`, and `message`. Product/page/UTM metadata and up to three base64 attachments are optional.

Build the canonical bytes as:

```text
timestamp + "\n" + request_id + "\n" + sha256(raw_request_body)
```

Then calculate `HMAC-SHA256(secret, canonical_bytes)`. Sign the exact UTF-8 bytes sent over HTTP. The default replay window is 300 seconds.

## Retry contract

Retry with the same external submission ID, request ID, idempotency key, and identical request body. The service returns the existing staged submission. Reusing an identity with different content is rejected. Database uniqueness covers company/submission, credential/idempotency, and credential/request ID, including simultaneous retries.

## Operational limits

- Default rate limit: 30 accepted attempts per credential per minute.
- Default signature TTL: 300 seconds.
- Default maximum request: 8 MB.
- Default attachment limit: three files, 5 MB each.
- Generic authentication failures do not disclose which credential/signature check failed.
- Secrets, raw IP addresses, and public write access to CRM records are not stored or exposed.

The website should show a neutral success message after a successful response. Internal assignment, duplicate decisions, and conversion remain in the ERP inbox.
