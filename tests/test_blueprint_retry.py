import pytest

from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    ApiDesign,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseDesign,
    DatabaseTable,
    DesignConsideration,
    DiagramDesign,
    Feature,
    FeatureDesign,
    IdeaAnalysis,
    ImplementationStep,
    PlanningDesign,
    TechStack,
)
from app.schemas.blueprint import BlueprintRequest
from app.services.blueprint_generator import generate_blueprint_pipeline_with_retry, generate_blueprint_with_retry
from app.services.llm_client import BlueprintGenerationError


def make_blueprint(api_path: str = "/api/v1/books") -> BlueprintResponse:
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
            make_api_spec("POST", api_path),
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

    assert result.api_spec[0].path == "/api/v1/books"
    assert feedback_calls[0] is None
    assert "api path must start with '/': api/v1/items" in feedback_calls[1]
    assert "api path is too generic: api/v1/items" in feedback_calls[1]


def test_generate_blueprint_with_retry_fails_after_max_attempts(monkeypatch) -> None:
    def fake_request_blueprint(user_prompt: str, validation_feedback: list[str] | None = None):
        return make_blueprint(api_path="api/v1/items")

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_blueprint_from_openai",
        fake_request_blueprint,
    )

    with pytest.raises(BlueprintGenerationError, match="재시도에 실패"):
        generate_blueprint_with_retry("테스트 프롬프트")


def test_generate_blueprint_pipeline_assembles_section_outputs(monkeypatch) -> None:
    section_outputs = [
        IdeaAnalysis(
            service_summary="독서 기록 서비스입니다.",
            target_users=["독서 사용자"],
            core_entities=["books", "reading_logs"],
            mvp_scope=["도서 기록"],
            out_of_scope=["결제"],
        ),
        FeatureDesign(
            overview="테스트용 설계도입니다.",
            features=make_blueprint().features,
            tech_stack=make_blueprint().tech_stack,
        ),
        ApiDesign(api_spec=make_blueprint().api_spec),
        DatabaseDesign(database_schema=make_blueprint().database_schema),
        DiagramDesign(
            database_erd=make_blueprint().database_erd,
            sequence_diagram=make_blueprint().sequence_diagram,
        ),
        PlanningDesign(
            non_functional_requirements=make_design_considerations("reliability"),
            security_considerations=make_design_considerations("security"),
            implementation_plan=make_implementation_plan(),
        ),
    ]
    requested_formats = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        requested_formats.append(text_format)
        return section_outputs.pop(0)

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = generate_blueprint_pipeline_with_retry(BlueprintRequest(idea="독서 기록 서비스"))

    assert result.overview == "테스트용 설계도입니다."
    assert result.api_spec[0].path == "/api/v1/books"
    assert len(result.non_functional_requirements) == 3
    assert requested_formats == [
        IdeaAnalysis,
        FeatureDesign,
        ApiDesign,
        DatabaseDesign,
        DiagramDesign,
        PlanningDesign,
    ]
