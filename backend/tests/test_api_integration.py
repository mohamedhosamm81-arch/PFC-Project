"""HTTP contract smoke test through the full FastAPI stack."""

from __future__ import annotations

import pytest

pytest.importorskip("greenlet")

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import SessionFactory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import Location, UserRole  # noqa: E402
from tests.helpers import create_user  # noqa: E402

pytestmark = pytest.mark.integration


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://testserver")


async def test_authentication_is_required(database):
    async with await _client() as client:
        response = await client.get("/api/queues")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_login_issue_transfer_queue_and_session_flow(database):
    async with SessionFactory() as session:
        await create_user(
            session,
            "reception",
            UserRole.RECEPTION,
            Location.RECEPTION,
            password="Reception123!",
        )

    async with await _client() as client:
        login = await client.post(
            "/api/auth/login",
            json={"username": "reception", "password": "Reception123!"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = await client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == "reception"

        blocked = await client.post(
            "/api/tickets/issue",
            json={"initial_destination": "Cashier"},
            headers=headers,
        )
        assert blocked.status_code == 422
        assert blocked.json()["error"]["code"] == "CASHIER_NOT_INITIAL_DESTINATION"

        issued = await client.post(
            "/api/tickets/issue",
            json={"initial_destination": "Reception"},
            headers=headers,
        )
        assert issued.status_code == 201, issued.text
        ticket = issued.json()["ticket"]
        assert ticket["ticket_code"] == 1
        assert ticket["status"] == "WAITING"

        queue = await client.get("/api/queues/Reception", headers=headers)
        assert queue.status_code == 200
        assert queue.json()["waiting_count"] == 1

        transferred = await client.post(
            "/api/tickets/transfer",
            json={"ticket_code": 1, "to_location": "Cashier"},
            headers=headers,
        )
        assert transferred.status_code == 200, transferred.text
        assert transferred.json()["ticket"]["current_location"] == "Cashier"
        assert transferred.json()["previous_location"] == "Reception"

        started = await client.post("/api/sessions/start", json={}, headers=headers)
        assert started.status_code == 201, started.text

        ended = await client.post("/api/sessions/end", headers=headers)
        assert ended.status_code == 200, ended.text
        assert ended.json()["end_session_at"] is not None


async def test_validation_errors_use_the_standard_envelope(database):
    async with SessionFactory() as session:
        await create_user(
            session,
            "reception",
            UserRole.RECEPTION,
            Location.RECEPTION,
            password="Reception123!",
        )

    async with await _client() as client:
        login = await client.post(
            "/api/auth/login",
            json={"username": "reception", "password": "Reception123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        bad = await client.post(
            "/api/tickets/issue",
            json={"initial_destination": "NotAStation"},
            headers=headers,
        )
        assert bad.status_code == 422
        body = bad.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["details"]

        missing_locator = await client.post(
            "/api/tickets/done", json={}, headers=headers
        )
        assert missing_locator.status_code == 422
