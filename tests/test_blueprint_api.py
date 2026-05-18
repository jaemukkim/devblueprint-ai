from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.blueprint_repository import blueprint_repository


client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_react_dev_origin() -> None:
    response = client.options(
        "/api/v1/blueprint/generate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_generate_blueprint_returns_expected_shape(monkeypatch) -> None:
    # API 테스트는 외부 네트워크에 의존하지 않도록 placeholder 응답 경로를 사용합니다.
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

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
    assert data["database_erd"].startswith("erDiagram")
    assert data["sequence_diagram"].startswith("sequenceDiagram")


def test_generate_blueprint_rejects_short_idea() -> None:
    response = client.post("/api/v1/blueprint/generate", json={"idea": "abc"})

    assert response.status_code == 422


def test_generate_blueprint_reuses_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    payload = {"idea": "  스포츠   야구 분석 및 승부 예측 서비스  "}
    first_response = client.post("/api/v1/blueprint/generate", json=payload)
    second_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "스포츠 야구 분석 및 승부 예측 서비스"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert blueprint_repository.count() == 1
    assert first_response.json() == second_response.json()


def test_list_blueprints_returns_saved_blueprint_summary(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "개인 학습 기록을 분석하는 AI 플래너"},
    )
    list_response = client.get("/api/v1/blueprints")

    assert create_response.status_code == 200
    assert list_response.status_code == 200

    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"]
    assert items[0]["idea"] == "개인 학습 기록을 분석하는 AI 플래너"
    assert items[0]["created_at"]


def test_get_blueprint_returns_saved_blueprint_detail(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "운동 루틴을 추천하는 AI 코치 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    detail_response = client.get(f"/api/v1/blueprints/{blueprint_id}")

    assert create_response.status_code == 200
    assert detail_response.status_code == 200

    data = detail_response.json()
    assert data["id"] == blueprint_id
    assert data["idea"] == "운동 루틴을 추천하는 AI 코치 서비스"
    assert data["result"] == create_response.json()


def test_get_blueprint_returns_404_when_missing() -> None:
    blueprint_repository.clear()

    response = client.get("/api/v1/blueprints/missing-blueprint-id")

    assert response.status_code == 404
