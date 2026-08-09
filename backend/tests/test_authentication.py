import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_login_requires_csrf_and_uses_session(user):
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(reverse("csrf"))
    token = response.cookies["csrftoken"].value

    rejected = client.post(reverse("login"), {"identifier": user.email, "password": "SafePassword-2741"})
    assert rejected.status_code == 403

    accepted = client.post(
        reverse("login"),
        {"identifier": user.email, "password": "SafePassword-2741"},
        HTTP_X_CSRFTOKEN=token,
    )
    assert accepted.status_code == 200
    assert accepted.data["email"] == user.email
    assert client.get(reverse("me")).status_code == 200


@pytest.mark.django_db
def test_login_failure_is_generic_and_rate_limited(user, settings):
    settings.LOGIN_FAILURE_LIMIT = 2
    client = APIClient(enforce_csrf_checks=True)
    token = client.get(reverse("csrf")).cookies["csrftoken"].value
    payload = {"identifier": user.email, "password": "wrong-password"}

    first = client.post(reverse("login"), payload, HTTP_X_CSRFTOKEN=token)
    second = client.post(reverse("login"), payload, HTTP_X_CSRFTOKEN=token)
    throttled = client.post(reverse("login"), payload, HTTP_X_CSRFTOKEN=token)

    assert first.status_code == second.status_code == 401
    assert first.data["error"]["message"] == "Invalid sign-in details."
    assert throttled.status_code == 429


@pytest.mark.django_db
def test_unauthenticated_api_uses_standard_401_error(api_client):
    response = api_client.get("/api/v1/employees/")
    assert response.status_code == 401
    assert response.data["error"]["status"] == 401
