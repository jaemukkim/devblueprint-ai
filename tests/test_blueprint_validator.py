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
from app.services.blueprint_validator import validate_blueprint_quality
from app.services.llm_client import BlueprintGenerationError


def make_valid_blueprint() -> BlueprintResponse:
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
            make_api_spec("POST", "/api/v1/items"),
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


def test_validate_blueprint_quality_accepts_valid_blueprint() -> None:
    validate_blueprint_quality(make_valid_blueprint())


def test_validate_blueprint_quality_rejects_too_few_features() -> None:
    blueprint = make_valid_blueprint()
    blueprint.features = blueprint.features[:4]

    with pytest.raises(BlueprintGenerationError, match="features must contain at least 5"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_invalid_api_path() -> None:
    blueprint = make_valid_blueprint()
    blueprint.api_spec[0].path = "api/v1/items"

    with pytest.raises(BlueprintGenerationError, match="api path must start"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_invalid_database_name() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_schema[0].name = "TestItems"

    with pytest.raises(BlueprintGenerationError, match="table name must be snake_case"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_invalid_sequence_diagram() -> None:
    blueprint = make_valid_blueprint()
    blueprint.sequence_diagram = "flowchart TD\n  A --> B"

    with pytest.raises(BlueprintGenerationError, match="sequence_diagram"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_invalid_database_erd() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = "flowchart TD\n  A --> B"

    with pytest.raises(BlueprintGenerationError, match="database_erd"):
        validate_blueprint_quality(blueprint)
