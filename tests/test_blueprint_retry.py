import pytest

from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseTable,
    Feature,
    TechStack,
)
from app.services.blueprint_generator import generate_blueprint_with_retry
from app.services.llm_client import BlueprintGenerationError


def make_blueprint(api_path: str = "/api/v1/items") -> BlueprintResponse:
    return BlueprintResponse(
        overview="테스트용 설계도입니다.",
        features=[
            Feature(name="기능 A", description="설명 A", priority="high"),
            Feature(name="기능 B", description="설명 B", priority="medium"),
            Feature(name="기능 C", description="설명 C", priority="low"),
            Feature(name="기능 D", description="설명 D", priority="medium"),
            Feature(name="기능 E", description="설명 E", priority="low"),
        ],
        tech_stack=TechStack(
            backend=["FastAPI"],
            frontend=["Streamlit"],
            database=["PostgreSQL"],
            ai=["OpenAI API"],
            rationale="테스트용 기술 스택입니다.",
        ),
        api_spec=[
            make_api_spec("POST", api_path),
            make_api_spec("GET", "/api/v1/items"),
            make_api_spec("GET", "/api/v1/items/{item_id}"),
            make_api_spec("DELETE", "/api/v1/items/{item_id}"),
        ],
        database_schema=[
            make_database_table("test_items"),
            make_database_table("test_item_events"),
            make_database_table("test_item_results"),
        ],
        database_erd=(
            "erDiagram\n"
            "  test_items ||--o{ test_item_events : has\n"
            "  test_items ||--o{ test_item_results : has"
        ),
        sequence_diagram="sequenceDiagram\n  participant User\n  User->>User: 테스트",
    )


def make_api_spec(method: str, path: str) -> ApiSpec:
    return ApiSpec(
        method=method,
        path=path,
        description="테스트 API입니다.",
        request=[
            ApiField(
                name="idea",
                type="string",
                description="테스트 입력입니다.",
                required=True,
            )
        ],
        response=[
            ApiField(
                name="result",
                type="string",
                description="테스트 응답입니다.",
                required=True,
            )
        ],
    )


def make_database_table(name: str) -> DatabaseTable:
    return DatabaseTable(
        name=name,
        description="테스트 테이블입니다.",
        columns=[
            DatabaseColumn(
                name="id",
                type="uuid",
                description="식별자입니다.",
                constraints=["primary_key"],
            )
        ],
    )


def test_generate_blueprint_with_retry_returns_second_valid_result(monkeypatch) -> None:
    responses = [make_blueprint(api_path="api/v1/items"), make_blueprint()]
    feedback_calls = []

    def fake_request_blueprint(user_prompt: str, validation_feedback: list[str] | None = None):
        feedback_calls.append(validation_feedback)
        return responses.pop(0)

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_blueprint_from_openai",
        fake_request_blueprint,
    )

    result = generate_blueprint_with_retry("테스트 프롬프트")

    assert result.api_spec[0].path == "/api/v1/items"
    assert feedback_calls[0] is None
    assert feedback_calls[1] == ["api path must start with '/': api/v1/items"]


def test_generate_blueprint_with_retry_fails_after_max_attempts(monkeypatch) -> None:
    def fake_request_blueprint(user_prompt: str, validation_feedback: list[str] | None = None):
        return make_blueprint(api_path="api/v1/items")

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_blueprint_from_openai",
        fake_request_blueprint,
    )

    with pytest.raises(BlueprintGenerationError, match="재시도에 실패"):
        generate_blueprint_with_retry("테스트 프롬프트")
