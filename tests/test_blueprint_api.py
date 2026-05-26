from fastapi.testclient import TestClient

from app.core.config import settings
from app.api.v1 import blueprint as blueprint_api
from app.main import app
from app.repositories.blueprint_repository import blueprint_repository
from app.schemas.blueprint import BlueprintResponse
from app.services.llm_client import BlueprintGenerationError


client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["use_openai"] == settings.use_openai
    assert data["repository_backend"] == settings.repository_backend


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
    assert len(data["non_functional_requirements"]) >= 3
    assert len(data["security_considerations"]) >= 3
    assert len(data["implementation_plan"]) >= 3


def test_blueprint_response_accepts_legacy_saved_result_without_planning_fields(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "레거시 저장 설계도 호환성 테스트 서비스"},
    )
    legacy_result = create_response.json()
    legacy_result.pop("non_functional_requirements")
    legacy_result.pop("security_considerations")
    legacy_result.pop("implementation_plan")

    parsed_result = BlueprintResponse.model_validate(legacy_result)

    assert parsed_result.non_functional_requirements == []
    assert parsed_result.security_considerations == []
    assert parsed_result.implementation_plan == []


def test_generate_blueprint_rejects_short_idea() -> None:
    response = client.post("/api/v1/blueprint/generate", json={"idea": "abc"})

    assert response.status_code == 422


def test_generate_blueprint_returns_structured_openai_error(monkeypatch) -> None:
    # 생성 실패 응답은 프론트가 원인을 구분할 수 있도록 error_code와 hint를 포함합니다.
    def raise_openai_error(_payload):
        raise BlueprintGenerationError("OpenAI API 호출 중 오류가 발생했습니다.")

    monkeypatch.setattr(blueprint_api, "generate_blueprint", raise_openai_error)

    response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "구조화된 오류 응답을 확인하는 테스트 서비스"},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_code"] == "openai_call_failed"
    assert detail["message"] == "OpenAI API 호출 중 오류가 발생했습니다."
    assert detail["hint"]


def test_generate_blueprint_returns_structured_validation_error(monkeypatch) -> None:
    # 품질 검증 실패도 별도 error_code로 내려 UI가 재시도 안내를 다르게 보여줄 수 있게 합니다.
    def raise_validation_error(_payload):
        raise BlueprintGenerationError("설계도 품질 검증에 실패했습니다: database_erd must start with 'erDiagram'")

    monkeypatch.setattr(blueprint_api, "generate_blueprint", raise_validation_error)

    response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "검증 실패 응답을 확인하는 테스트 서비스"},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_code"] == "blueprint_validation_failed"
    assert "품질 기준" in detail["hint"]


def test_generate_blueprint_reuses_cached_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    payload = {"idea": "  스포츠  야구 분석 및 승부 예측 서비스  "}
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
        json={"idea": "개인 학습 기록을 분석하는 AI 플랫폼"},
    )
    list_response = client.get("/api/v1/blueprints")

    assert create_response.status_code == 200
    assert list_response.status_code == 200

    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"]
    assert items[0]["idea"] == "개인 학습 기록을 분석하는 AI 플랫폼"
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


def test_revise_blueprint_creates_new_saved_blueprint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "팀 회고 내용을 분석하는 협업 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    revise_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/revise",
        json={"instruction": "관리자용 통계 기능을 추가해줘"},
    )

    assert create_response.status_code == 200
    assert revise_response.status_code == 200

    data = revise_response.json()
    assert data["id"] != blueprint_id
    assert data["idea"] == "팀 회고 내용을 분석하는 협업 서비스"
    assert "관리자용 통계 기능을 추가해줘" in data["result"]["overview"]
    assert blueprint_repository.count() == 2


def test_revise_blueprint_rejects_duplicate_instruction(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "카페 공유 커뮤니티 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    first_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/revise",
        json={"instruction": "관리자 기능 추가해줘"},
    )
    second_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/revise",
        json={"instruction": "관리자 기능 추가해줘"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert blueprint_repository.count() == 2


def test_revise_blueprint_returns_404_when_missing() -> None:
    blueprint_repository.clear()

    response = client.post(
        "/api/v1/blueprints/missing-blueprint-id/revise",
        json={"instruction": "관리자 기능을 추가해줘"},
    )

    assert response.status_code == 404


def test_regenerate_blueprint_section_returns_preview_without_saving(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "독서 기록을 분석하는 AI 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    regenerate_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/sections/planning/regenerate",
        json={"instruction": "일정을 더 현실적으로 조정해줘"},
    )

    assert create_response.status_code == 200
    assert regenerate_response.status_code == 200

    data = regenerate_response.json()
    assert data["section"] == "planning"
    assert "일정을 더 현실적으로 조정해줘" in data["result"]["implementation_plan"][0]["description"]
    assert data["result"]["features"] == create_response.json()["features"]
    assert blueprint_repository.count() == 1


def test_apply_regenerated_section_preview_saves_new_blueprint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "섹션 미리보기 적용 테스트 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    regenerate_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/sections/planning/regenerate",
        json={"instruction": "구현 일정을 더 현실적으로 정리해줘"},
    )
    preview = regenerate_response.json()

    apply_response = client.post(
        f"/api/v1/blueprints/{blueprint_id}/sections/planning/apply",
        json={
            "instruction": "구현 일정을 더 현실적으로 정리해줘",
            "result": preview["result"],
        },
    )

    assert create_response.status_code == 200
    assert regenerate_response.status_code == 200
    assert apply_response.status_code == 200
    data = apply_response.json()
    assert data["id"] != blueprint_id
    assert data["revision_instruction"] == "계획 섹션 재생성 적용: 구현 일정을 더 현실적으로 정리해줘"
    assert data["result"] == preview["result"]
    assert blueprint_repository.count() == 2


def test_regenerate_blueprint_section_accepts_alias(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "운동 루틴을 추천하는 AI 코치 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    response = client.post(f"/api/v1/blueprints/{blueprint_id}/sections/api_spec/regenerate")

    assert response.status_code == 200
    assert response.json()["section"] == "api"


def test_regenerate_blueprint_section_returns_404_when_missing() -> None:
    blueprint_repository.clear()

    response = client.post("/api/v1/blueprints/missing-blueprint-id/sections/planning/regenerate")

    assert response.status_code == 404


def test_regenerate_blueprint_section_rejects_unknown_section(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "카페 공유 커뮤니티 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    response = client.post(f"/api/v1/blueprints/{blueprint_id}/sections/unknown/regenerate")

    assert response.status_code == 404


def test_delete_blueprint_removes_saved_blueprint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "use_openai", False)
    blueprint_repository.clear()

    create_response = client.post(
        "/api/v1/blueprint/generate",
        json={"idea": "삭제 테스트용 설계도 서비스"},
    )
    blueprint_id = client.get("/api/v1/blueprints").json()["items"][0]["id"]
    delete_response = client.delete(f"/api/v1/blueprints/{blueprint_id}")
    detail_response = client.get(f"/api/v1/blueprints/{blueprint_id}")

    assert create_response.status_code == 200
    assert delete_response.status_code == 204
    assert detail_response.status_code == 404
    assert blueprint_repository.count() == 0


def test_delete_blueprint_returns_404_when_missing() -> None:
    blueprint_repository.clear()

    response = client.delete("/api/v1/blueprints/missing-blueprint-id")

    assert response.status_code == 404
