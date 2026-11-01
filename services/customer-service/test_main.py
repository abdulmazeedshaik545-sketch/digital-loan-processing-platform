from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "customer-service"
    }


def test_get_customer_c1001():
    response = client.get("/customers/C1001")

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "C1001",
        "name": "Sample Customer",
        "segment": "retail"
    }


def test_get_customer_c1002():
    response = client.get("/customers/C1002")

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "C1002",
        "name": "Demo Customer",
        "segment": "retail"
    }


def test_get_unknown_customer():
    response = client.get("/customers/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Customer not found in demo directory"
    )
