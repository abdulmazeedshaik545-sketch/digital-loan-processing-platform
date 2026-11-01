
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import main


@pytest.fixture
def client(monkeypatch):
    # Prevent database initialization during test startup.
    monkeypatch.setattr(main.app.router, "on_startup", [])
    return TestClient(main.app)


@pytest.fixture
def mock_db(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection

    monkeypatch.setattr(main, "get_connection", lambda: connection)
    return connection


def test_health_success(client, mock_db):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "loan-service",
        "database": "connected"
    }


def test_health_database_unavailable(client, monkeypatch):
    def failed_connection():
        raise main.psycopg.OperationalError("Database unavailable")

    monkeypatch.setattr(main, "get_connection", failed_connection)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


def test_list_loans_success(client, mock_db):
    mock_db.execute.return_value.fetchall.return_value = [
        {
            "loan_id": "LN-1234567890",
            "customer_id": "CUST001",
            "amount": 100000,
            "status": "eligible_for_review"
        }
    ]

    response = client.get("/loans")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["customer_id"] == "CUST001"


def test_list_loans_database_failure(client, monkeypatch):
    def failed_connection():
        raise main.psycopg.OperationalError("Database unavailable")

    monkeypatch.setattr(main, "get_connection", failed_connection)

    response = client.get("/loans")

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not retrieve loans"


def test_create_loan_success(client, monkeypatch, mock_db):
    class FakeResponse:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

        def raise_for_status(self):
            pass

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return FakeResponse({"customer_id": "CUST001"})

        async def post(self, url, json=None):
            if url.endswith("/validate"):
                return FakeResponse({"valid": True})
            return FakeResponse({"sent": True})

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    payload = {
        "customer_id": "CUST001",
        "amount": 100000,
        "annual_income": 500000,
        "employment_type": "salaried",
        "document_ids": ["DOC001"]
    }

    response = client.post("/loans", json=payload)

    assert response.status_code == 200
    assert response.json()["customer_id"] == "CUST001"
    assert response.json()["status"] == "eligible_for_review"
    assert response.json()["loan_id"].startswith("LN-")
    mock_db.execute.assert_called()


def test_create_loan_invalid_amount(client):
    response = client.post("/loans", json={
        "customer_id": "CUST001",
        "amount": 0,
        "annual_income": 500000
    })

    assert response.status_code == 422


def test_create_loan_unknown_customer(client, monkeypatch):
    class FakeResponse:
        status_code = 404

        def json(self):
            return {}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return FakeResponse()

        async def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post("/loans", json={
        "customer_id": "UNKNOWN",
        "amount": 100000,
        "annual_income": 500000
    })

    assert response.status_code == 400
    assert "Unknown customer_id" in response.json()["detail"]


def test_create_loan_document_validation_failure(client, monkeypatch):
    class FakeResponse:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return FakeResponse({"customer_id": "CUST001"})

        async def post(self, url, json=None):
            return FakeResponse({"valid": False})

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post("/loans", json={
        "customer_id": "CUST001",
        "amount": 100000,
        "annual_income": 500000,
        "document_ids": ["DOC001"]
    })

    assert response.status_code == 200
    assert response.json()["status"] == "pending_documents"
