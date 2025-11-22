from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_predict_endpoint():
    response = client.get("/api/predict")
    assert response.status_code == 200
    data = response.json()
    assert "recommend" in data


def test_add_and_history_flow():
    add_response = client.post("/api/add", json={"result": "B"})
    assert add_response.status_code == 200

    history_response = client.get("/api/history")
    assert history_response.status_code == 200
    body = history_response.json()
    assert body["total"] >= 1
