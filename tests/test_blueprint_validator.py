import pytest

from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseTable,
    DesignConsideration,
    Feature,
    ImplementationStep,
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
            make_database_table("books"),
            make_database_table("book_events"),
            make_database_table("book_recommendations"),
        ],
        database_erd=(
            "erDiagram\n"
            "  books ||--o{ book_events : has\n"
            "  books ||--o{ book_recommendations : has"
        ),
        sequence_diagram="sequenceDiagram\n  participant User\n  User->>API: POST /api/v1/books\n  API-->>User: books",
        non_functional_requirements=make_design_considerations("reliability"),
        security_considerations=make_design_considerations("security"),
        implementation_plan=make_implementation_plan(),
    )


def make_api_spec(method: str, path: str) -> ApiSpec:
    return ApiSpec(
        method=method,
        path=path,
        description="테스트 API입니다.",
        request=[
            ApiField(
                name="title",
                type="string",
                description="도서 제목 입력입니다.",
                required=True,
            )
        ],
        response=[
            ApiField(
                name="title",
                type="string",
                description="저장된 도서 제목입니다.",
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
                name="title",
                type="varchar",
                description="도서 제목입니다.",
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


def make_design_considerations(category: str) -> list[DesignConsideration]:
    description = (
        "인증과 권한, 개인정보 암호화 관점에서 실제 구현 전에 확인해야 하는 설계 고려사항입니다."
        if category == "security"
        else f"{category} 관점에서 실제 구현 전에 확인해야 하는 설계 고려사항입니다."
    )

    return [
        DesignConsideration(
            category=category,
            title=f"{category} 항목 {index}",
            description=description,
            priority="medium",
        )
        for index in range(1, 4)
    ]


def make_implementation_plan() -> list[ImplementationStep]:
    return [
        ImplementationStep(
            phase=str(index),
            title=f"구현 단계 {index}",
            description="books API와 도서 데이터 모델을 기준으로 순서대로 진행하는 구현 단계 설명입니다.",
        )
        for index in range(1, 4)
    ]


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


def test_validate_blueprint_quality_rejects_too_few_security_considerations() -> None:
    blueprint = make_valid_blueprint()
    blueprint.security_considerations = blueprint.security_considerations[:2]

    with pytest.raises(BlueprintGenerationError, match="security_considerations must contain at least 3"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_short_implementation_plan_description() -> None:
    blueprint = make_valid_blueprint()
    blueprint.implementation_plan[0].description = "짧음"

    with pytest.raises(BlueprintGenerationError, match="implementation_plan description is too short"):
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
        "  books ||--o{ book_events : has\n"
        "  books {\n"
        "    uuid id PK\n"
        "  }"
    )

    with pytest.raises(BlueprintGenerationError, match="database_erd must include table"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_accepts_uppercase_erd_table_names() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "erDiagram\n"
        "  BOOKS ||--o{ BOOK_EVENTS : has\n"
        "  BOOKS ||--o{ BOOK_RECOMMENDATIONS : has"
    )

    validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_unique_erd_key_token() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "erDiagram\n"
        "  books {\n"
        "    uuid id PK\n"
        "    varchar external_id UNIQUE\n"
        "    timestamp created_at\n"
        "  }\n"
        "  book_events ||--o{ books : belongs_to\n"
        "  book_recommendations ||--o{ books : belongs_to"
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


def test_validate_blueprint_quality_rejects_api_resource_missing_from_database() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_schema[0].name = "reading_logs"
    blueprint.database_schema[1].name = "reading_events"
    blueprint.database_schema[2].name = "reading_recommendations"
    blueprint.database_erd = (
        "erDiagram\n"
        "  reading_logs ||--o{ reading_events : has\n"
        "  reading_logs ||--o{ reading_recommendations : has"
    )

    with pytest.raises(BlueprintGenerationError, match="api resource must be represented"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_api_fields_detached_from_database_columns() -> None:
    blueprint = make_valid_blueprint()
    for api in blueprint.api_spec:
        api.request[0].name = "summary"
        api.response[0].name = "summary"

    with pytest.raises(BlueprintGenerationError, match="api fields must overlap database columns"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_sequence_diagram_without_api_resource() -> None:
    blueprint = make_valid_blueprint()
    blueprint.sequence_diagram = "sequenceDiagram\n  participant User\n  User->>API: 요청\n  API-->>User: 응답"

    with pytest.raises(BlueprintGenerationError, match="sequence_diagram must reference"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_plan_detached_from_generated_design() -> None:
    blueprint = make_valid_blueprint()
    for step in blueprint.implementation_plan:
        step.description = "프로젝트 준비와 공통 개발 환경을 순서대로 구성하는 충분한 구현 단계 설명입니다."

    with pytest.raises(BlueprintGenerationError, match="implementation_plan must reference"):
        validate_blueprint_quality(blueprint)


def test_validate_blueprint_quality_rejects_auth_scope_without_security_coverage() -> None:
    blueprint = make_valid_blueprint()
    blueprint.features[0].description = "사용자가 password login으로 독서 기록을 보호할 수 있게 합니다."
    for item in blueprint.security_considerations:
        item.description = "서비스 안정성과 입력값 검증을 기준으로 운영 위험을 줄이는 설계 고려사항입니다."

    with pytest.raises(BlueprintGenerationError, match="authentication risks"):
        validate_blueprint_quality(blueprint)
