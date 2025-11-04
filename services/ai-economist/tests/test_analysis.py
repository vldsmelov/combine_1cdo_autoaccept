from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_budget_upload_and_analysis():
    budget_payload = {
        "budget_id": "demo",
        "categories": [
            {"name": "Оргтехника", "available": "600 000"},
            {"name": "Электроника", "available": "2 000 000"},
        ],
    }
    response = client.post("/budget", json=budget_payload)
    assert response.status_code == 200, response.text
    budget = response.json()
    assert budget["budget_id"] == "demo"
    assert len(budget["categories"]) == 2

    analyze_payload = {
        "budget_id": "demo",
        "items": [
            {"name": "Поставка МФУ Canon", "amount": "750 000"},
            {"name": "Сервер Lenovo", "amount": "1 200 000"},
        ],
    }
    response = client.post("/analyze", json=analyze_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["budget_id"] == "demo"
    summary = data["summary"]
    assert "Оргтехника" in summary["message"]
    assert summary["shortage"][0]["category"] == "Оргтехника"
    assert summary["shortage"][0]["enough"] is False
