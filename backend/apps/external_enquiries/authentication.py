import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from .models import IntegrationCredential

logger = logging.getLogger(__name__)


def canonical_signature_payload(timestamp, request_id, body):
    body_digest = hashlib.sha256(body).hexdigest()
    return f"{timestamp}\n{request_id}\n{body_digest}".encode()


def sign_payload(secret, timestamp, request_id, body):
    return hmac.new(
        secret.encode("utf-8"),
        canonical_signature_payload(timestamp, request_id, body),
        hashlib.sha256,
    ).hexdigest()


def verify_website_request(request):
    key_id = request.headers.get("X-Integration-Key", "").strip()
    timestamp = request.headers.get("X-Timestamp", "").strip()
    request_id = request.headers.get("X-Request-ID", "").strip()
    signature = request.headers.get("X-Signature", "").strip().lower()
    if not all((key_id, timestamp, request_id, signature)):
        raise AuthenticationFailed("Website integration authentication failed.")
    try:
        timestamp_value = int(timestamp)
    except ValueError as exc:
        raise AuthenticationFailed("Website integration authentication failed.") from exc
    if abs(int(time.time()) - timestamp_value) > settings.WEBSITE_INTAKE_SIGNATURE_TTL_SECONDS:
        logger.warning("Website integration timestamp rejected", extra={"key_id": key_id})
        raise AuthenticationFailed("Website integration authentication failed.")
    try:
        credential = IntegrationCredential.objects.select_related("company").get(
            key_id=key_id,
            integration_type=IntegrationCredential.IntegrationType.WEBSITE,
            is_active=True,
        )
    except IntegrationCredential.DoesNotExist as exc:
        logger.warning("Website integration credential rejected", extra={"key_id": key_id})
        raise AuthenticationFailed("Website integration authentication failed.") from exc
    secret = settings.INTEGRATION_SECRETS.get(key_id, "")
    if not secret or not hmac.compare_digest(credential.secret_hash, credential.hash_secret(secret)):
        logger.error("Website integration secret is unavailable or does not match", extra={"key_id": key_id})
        raise AuthenticationFailed("Website integration authentication failed.")
    source = request.headers.get("X-Integration-Source", "").strip()
    if credential.allowed_source and not hmac.compare_digest(source, credential.allowed_source):
        raise AuthenticationFailed("Website integration authentication failed.")
    expected = sign_payload(secret, timestamp, request_id, request.body)
    if not hmac.compare_digest(signature, expected):
        logger.warning("Website integration signature rejected", extra={"key_id": key_id})
        raise AuthenticationFailed("Website integration authentication failed.")
    IntegrationCredential.objects.filter(pk=credential.pk).update(last_used_at=timezone.now())
    return credential, request_id
