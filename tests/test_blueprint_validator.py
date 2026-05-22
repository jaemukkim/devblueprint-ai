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
            Feature(name="도서 기록 작성", description="사용자가 읽은 책과 감상을 기록할 수 있게 합니다.", priority="high"),
            Feature(name="독서 목표 관리", description="월별 독서 목표와 진행률을 관리할 수 있게 합니다.", priority="medium"),
            Feature(name="AI 도서 추천", description="기록된 선호도를 바탕으로 다음에 읽을 책을 추천합니다.", priority="high"),
            Feature(name="평점 통계 조회", description="사용자가 남긴 평점과 장르별 독서 패턴을 요약합니다.", priority="low"),
            Feature(name="추천 피드백 저장", description="추천 결과에 대한 사용자의 반응을 저장해 품질을 개선합니다.", priority="medium"),
        ],
        tech_stack=TechStack(
            backend=["FastAPI"],
            frontend=["Streamlit"],
            database=["PostgreSQL"],
            ai=["OpenAI API"],
            rationale="테스트용 기술 스택입니다.",
        ),
        api_spec=[
            make_api_spec("POST", "/api/v1/books"),
            make_api_spec("GET", "/api/v1/books"),
            make_api_spec("GET", "/api/v1/books/{book_id}"),
            make_api_spec("DELETE", "/api/v1/books/{book_id}"),
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
            ),
            DatabaseColumn(
                name="created_at",
                type="timestamp",
                description="생성 시각입니다.",
                constraints=["not_null"],
            ),
            DatabaseColumn(
                name="updated_at",
                type="timestamp",
                description="수정 시각입니다.",
                constraints=["not_null"],
            ),
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


def test_validate_blueprint_quality_rejects_duplicate_api_endpoint() -> None:
    blueprint = make_valid_blueprint()
    blueprint.api_spec[1].method = blueprint.api_spec[0].method
    blueprint.api_spec[1].path = blueprint.api_spec[0].path

    with pytest.raises(BlueprintGenerationError, match="api endpoint must be unique"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_generic_api_resource() -> None:
    blueprint = make_valid_blueprint()
    blueprint.api_spec[0].path = "/api/v1/items"

    with pytest.raises(BlueprintGenerationError, match="api path is too generic"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_accepts_short_api_field_description() -> None:
    blueprint = make_valid_blueprint()
    blueprint.api_spec[0].request[0].name = "title"
    blueprint.api_spec[0].request[0].description = "제목"

    validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_generic_feature_name() -> None:
    blueprint = make_valid_blueprint()
    blueprint.features[0].name = "아이디어 분석"

    with pytest.raises(BlueprintGenerationError, match="feature name is too generic"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_short_feature_description() -> None:
    blueprint = make_valid_blueprint()
    blueprint.features[0].description = "짧음"

    with pytest.raises(BlueprintGenerationError, match="feature description is too short"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_invalid_database_name() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_schema[0].name = "TestItems"

    with pytest.raises(BlueprintGenerationError, match="table name must be snake_case"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_table_without_primary_key() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_schema[0].columns[0].constraints = ["not_null"]

    with pytest.raises(BlueprintGenerationError, match="primary_key"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_table_with_too_few_columns() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_schema[0].columns = blueprint.database_schema[0].columns[:2]

    with pytest.raises(BlueprintGenerationError, match="at least 3 columns"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_erd_missing_schema_table() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "erDiagram\n"
        "  test_items ||--o{ test_item_events : has\n"
        "  test_items {\n"
        "    uuid id PK\n"
        "  }"
    )

    with pytest.raises(BlueprintGenerationError, match="database_erd must include table"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_accepts_uppercase_erd_table_names() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "erDiagram\n"
        "  TEST_ITEMS ||--o{ TEST_ITEM_EVENTS : has\n"
        "  TEST_ITEMS ||--o{ TEST_ITEM_RESULTS : has"
    )

    validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_unique_erd_key_token() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "erDiagram\n"
        "  test_items {\n"
        "    uuid id PK\n"
        "    varchar external_id UNIQUE\n"
        "    timestamp created_at\n"
        "  }\n"
        "  test_item_events ||--o{ test_items : belongs_to\n"
        "  test_item_results ||--o{ test_items : belongs_to"
    )

    with pytest.raises(BlueprintGenerationError, match="UK"):
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
