from datetime import date

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organization.models import Company, Employee
from apps.realtime.groups import company_group
from apps.realtime.presence import list_presence, touch_presence
from config.asgi import application


def _employee(user, company, code):
    return Employee.objects.create(
        user=user,
        company=company,
        employee_code=code,
        first_name=code,
        joining_date=date(2026, 1, 1),
        employment_type=Employee.EmploymentType.PERMANENT,
    )


def _session_headers(user):
    client = APIClient()
    client.force_login(user)
    cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    return [
        (b"host", b"localhost"),
        (b"origin", b"http://localhost"),
        (b"cookie", f"{settings.SESSION_COOKIE_NAME}={cookie}".encode()),
    ]


@pytest.mark.django_db(transaction=True)
def test_websocket_requires_authenticated_employee():
    async def scenario():
        communicator = WebsocketCommunicator(
            application,
            "/ws/workspace/",
            headers=[(b"host", b"localhost"), (b"origin", b"http://localhost")],
        )
        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 4401

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_company_groups_do_not_leak_events():
    first_company = Company.objects.create(name="Realtime one", code="RT-ONE")
    second_company = Company.objects.create(name="Realtime two", code="RT-TWO")
    first_user = User.objects.create_user(email="one@realtime.test", password="SafePassword-2741")
    second_user = User.objects.create_user(email="two@realtime.test", password="SafePassword-2741")
    _employee(first_user, first_company, "RT-001")
    _employee(second_user, second_company, "RT-002")
    first_headers = _session_headers(first_user)
    second_headers = _session_headers(second_user)

    async def scenario():
        first = WebsocketCommunicator(application, "/ws/workspace/", headers=first_headers)
        second = WebsocketCommunicator(application, "/ws/workspace/", headers=second_headers)
        assert (await first.connect())[0]
        assert (await second.connect())[0]
        assert (await first.receive_json_from())["type"] == "connection.ready"
        assert (await second.receive_json_from())["type"] == "connection.ready"
        await get_channel_layer().group_send(
            company_group(first_company.pk),
            {
                "type": "domain.event",
                "payload": {
                    "event_id": "event-1",
                    "event_name": "test.updated",
                    "entity_type": "test",
                    "entity_id": "1",
                },
            },
        )
        assert (await first.receive_json_from())["event_id"] == "event-1"
        assert await second.receive_nothing(timeout=0.1)
        await first.disconnect()
        await second.disconnect()

    async_to_sync(scenario)()


@pytest.mark.django_db
def test_presence_expires_after_ttl(monkeypatch, employee, user, settings):
    settings.REALTIME_PRESENCE_TTL_SECONDS = 60
    monkeypatch.setattr("apps.realtime.presence.time.time", lambda: 100.0)
    touch_presence(employee.company_id, "enquiry", "abc", user)
    assert len(list_presence(employee.company_id, "enquiry", "abc")) == 1
    monkeypatch.setattr("apps.realtime.presence.time.time", lambda: 161.0)
    assert list_presence(employee.company_id, "enquiry", "abc") == []
