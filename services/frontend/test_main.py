
import pytest
import httpx
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "frontend"
    }


def test_apply_invalid_amount():
    response = client.post(
        "/apply",
        json={
            "customer_id": "CUST001",
            "amount": -1000,
            "annual_income": 500000,
            "employment_type": "salaried",
            "document_ids": []
        }
    )

    assert response.status_code == 422


def test_apply_success(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"loan_id": "LOAN001", "status": "submitted"}

    class MockAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(
        "main.httpx.AsyncClient",
        MockAsyncClient
    )

    response = client.post(
        "/apply",
        json={
            "customer_id": "CUST001",
            "amount": 100000,
            "annual_income": 600000,
            "employment_type": "salaried",
            "document_ids": []
        }
    )

    assert response.status_code == 200
    assert response.json()["loan_id"] == "LOAN001"


def test_apply_loan_service_failure(monkeypatch):
    class MockAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(
        "main.httpx.AsyncClient",
        MockAsyncClient
    )

    response = client.post(
        "/apply",
        json={
            "customer_id": "CUST001",
            "amount": 100000,
            "annual_income": 600000,
            "employment_type": "salaried",
            "document_ids": []
        }
    )

    assert response.status_code == 502
    assert "Loan service unavailable" in response.json()["detail"]
