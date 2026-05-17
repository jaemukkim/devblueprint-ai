from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_blueprint_returns_expected_shape(monkeypatch) -> None:
    # API 테스트는 외부 네트워크에 의존하지 않도록 placeholder 응답 경로를 사용합니다.
    monkeypatch.setattr(settings, "openai_api_key", "")

    response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "스포츠 야구 분석 및 승부 예측 서비스"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["overview"]
    assert data["features"]
    assert data["tech_stack"]["backend"]
    assert data["api_spec"][0]["method"] == "POST"
    assert data["database_schema"][0]["columns"][0]["constraints"] == ["primary_key"]
    assert data["sequence_diagram"].startswith("sequenceDiagram")


def test_generate_blueprint_rejects_short_idea() -> None:
    response = client.post("/api/v1/blueprint/generate", json={"idea": "abc"})

    assert response.status_code == 422
