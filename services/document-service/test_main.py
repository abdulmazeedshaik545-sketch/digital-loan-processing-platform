from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "document-service"
    }


def test_validate_single_document():
    response = client.post(
        "/validate",
        json={"document_ids": ["DOC001"]}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["count"] == 1


def test_validate_multiple_documents():
    response = client.post(
        "/validate",
        json={"document_ids": ["DOC001", "DOC002", "DOC003"]}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["count"] == 3


def test_validate_empty_document_list():
    response = client.post(
        "/validate",
        json={"document_ids": []}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["count"] == 0
