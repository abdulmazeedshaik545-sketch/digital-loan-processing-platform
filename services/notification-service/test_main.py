from fastapi.testclient import TestClient
from main import app, OUTBOX

client = TestClient(app)


def setup_function():
    OUTBOX.clear()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "notification-service"
    }


def test_create_notification():
    payload = {
        "customer_id": "C1001",
        "message": "Your loan application has been received"
    }

    response = client.post("/notify", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "C1001",
        "message": "Your loan application has been received",
        "delivery": "simulated"
    }


def test_notification_is_stored_in_outbox():
    payload = {
        "customer_id": "C1001",
        "message": "Loan application update"
    }

    client.post("/notify", json=payload)

    assert len(OUTBOX) == 1
    assert OUTBOX[0]["customer_id"] == "C1001"


def test_list_notifications():
    client.post(
        "/notify",
        json={
            "customer_id": "C1001",
            "message": "First notification"
        }
    )

    client.post(
        "/notify",
        json={
            "customer_id": "C1002",
            "message": "Second notification"
        }
    )

    response = client.get("/notifications")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["customer_id"] == "C1001"
    assert response.json()[1]["customer_id"] == "C1002"


def test_notification_missing_message():
    response = client.post(
        "/notify",
        json={"customer_id": "C1001"}
    )

    assert response.status_code == 422
