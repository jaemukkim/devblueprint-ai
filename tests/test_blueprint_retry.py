import logging

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
from app.services.blueprint_generator import (
    BLUEPRINT_PIPELINE_STEPS,
    BlueprintPipelineState,
    analyze_idea_step,
    assemble_blueprint_step,
    design_api_step,
    design_database_step,
    design_features_step,
    generate_blueprint_pipeline_with_retry,
    generate_blueprint_with_retry,
    regenerate_blueprint_section_with_retry,
)
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


def count_calls(call_formats: list[tuple[type, list[str] | None]], text_format: type) -> int:
    return sum(1 for called_format, _ in call_formats if called_format is text_format)


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
    assert any("모든 API path는 '/'로 시작" in feedback for feedback in feedback_calls[1])
    assert any("일반 리소스 대신 서비스 도메인" in feedback for feedback in feedback_calls[1])


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
    section_output_by_format = {type(output): output for output in section_outputs}
    requested_formats = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        requested_formats.append(text_format)
        return section_output_by_format[text_format]

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = generate_blueprint_pipeline_with_retry(BlueprintRequest(idea="독서 기록 서비스"))

    assert result.overview == "테스트용 설계도입니다."
    assert result.api_spec[0].path == "/api/v1/books"
    assert len(result.non_functional_requirements) == 3
    assert requested_formats[:4] == [
        IdeaAnalysis,
        FeatureDesign,
        ApiDesign,
        DatabaseDesign,
    ]
    assert set(requested_formats[4:]) == {
        DiagramDesign,
        PlanningDesign,
    }


def test_blueprint_pipeline_steps_are_named_for_graph_migration() -> None:
    assert BLUEPRINT_PIPELINE_STEPS == (
        "analyze_idea",
        "design_features",
        "design_api",
        "design_database",
        "design_diagrams",
        "design_planning",
        "assemble_blueprint",
    )


def test_blueprint_pipeline_state_steps_pass_outputs_forward(monkeypatch) -> None:
    blueprint = make_blueprint()
    outputs = {
        IdeaAnalysis: IdeaAnalysis(
            service_summary="독서 기록 서비스입니다.",
            target_users=["독서 사용자"],
            core_entities=["books", "reading_logs"],
            mvp_scope=["독서 기록"],
            out_of_scope=["결제"],
        ),
        FeatureDesign: FeatureDesign(
            overview=blueprint.overview,
            features=blueprint.features,
            tech_stack=blueprint.tech_stack,
        ),
        ApiDesign: ApiDesign(api_spec=blueprint.api_spec),
        DatabaseDesign: DatabaseDesign(database_schema=blueprint.database_schema),
    }

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        return outputs[text_format]

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    state = BlueprintPipelineState(payload=BlueprintRequest(idea="독서 기록 서비스"))
    state = analyze_idea_step(state)
    state = design_features_step(state)
    state = design_api_step(state)
    state = design_database_step(state)
    state.diagram_design = DiagramDesign(
        database_erd=blueprint.database_erd,
        sequence_diagram=blueprint.sequence_diagram,
    )
    state.planning_design = PlanningDesign(
        non_functional_requirements=blueprint.non_functional_requirements,
        security_considerations=blueprint.security_considerations,
        implementation_plan=blueprint.implementation_plan,
    )
    state = assemble_blueprint_step(state)

    assert state.analysis is outputs[IdeaAnalysis]
    assert state.feature_design is outputs[FeatureDesign]
    assert state.api_design is outputs[ApiDesign]
    assert state.database_design is outputs[DatabaseDesign]
    assert state.blueprint is not None
    assert state.blueprint.api_spec[0].path == "/api/v1/books"


def test_generate_blueprint_pipeline_retries_with_validation_feedback(monkeypatch) -> None:
    """섹션별 생성 결과가 DB 검증에 실패하면 feedback을 포함해 pipeline을 한 번 더 시도합니다."""
    valid_blueprint = make_blueprint()
    invalid_database = DatabaseDesign(
        database_schema=[
            DatabaseTable(
                name="books",
                description="테스트용으로 일부러 primary key가 빠진 잘못된 테이블입니다.",
                columns=[
                    DatabaseColumn(
                        name="title",
                        type="varchar",
                        description="도서 제목입니다.",
                        constraints=["not_null"],
                    ),
                    DatabaseColumn(
                        name="created_at",
                        type="timestamp",
                        description="생성 시각입니다.",
                        constraints=["not_null"],
                    ),
                ],
            ),
            *valid_blueprint.database_schema[1:],
        ]
    )
    feedback_calls = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        feedback_calls.append((text_format, validation_feedback))
        if text_format is IdeaAnalysis:
            return IdeaAnalysis(
                service_summary="독서 기록 서비스입니다.",
                target_users=["독서 사용자"],
                core_entities=["books", "reading_logs"],
                mvp_scope=["독서 기록"],
                out_of_scope=["결제"],
            )
        if text_format is FeatureDesign:
            return FeatureDesign(
                overview=valid_blueprint.overview,
                features=valid_blueprint.features,
                tech_stack=valid_blueprint.tech_stack,
            )
        if text_format is ApiDesign:
            return ApiDesign(api_spec=valid_blueprint.api_spec)
        if text_format is DatabaseDesign:
            if validation_feedback:
                return DatabaseDesign(database_schema=valid_blueprint.database_schema)
            return invalid_database
        if text_format is DiagramDesign:
            return DiagramDesign(
                database_erd=valid_blueprint.database_erd,
                sequence_diagram=valid_blueprint.sequence_diagram,
            )
        if text_format is PlanningDesign:
            return PlanningDesign(
                non_functional_requirements=make_design_considerations("reliability"),
                security_considerations=make_design_considerations("security"),
                implementation_plan=make_implementation_plan(),
            )
        raise AssertionError(f"unexpected text_format: {text_format}")

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = generate_blueprint_pipeline_with_retry(BlueprintRequest(idea="독서 기록 서비스"))
    feedback_values = [feedback for _, feedback in feedback_calls if feedback]

    assert result.database_schema[0].columns[0].constraints == ["primary_key"]
    assert any("primary_key 컬럼" in " ".join(feedback) for feedback in feedback_values)
    assert any("최소 3개 컬럼" in " ".join(feedback) for feedback in feedback_values)


def test_langgraph_retry_routes_api_errors_to_api_and_downstream_nodes(monkeypatch, caplog) -> None:
    valid_blueprint = make_blueprint()
    invalid_api_design = ApiDesign(
        api_spec=[
            make_api_spec("POST", "api/v1/items"),
            *valid_blueprint.api_spec[1:],
        ]
    )
    call_formats = []
    caplog.set_level(logging.INFO, logger="app.services.blueprint_generator")

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        call_formats.append((text_format, validation_feedback))
        if text_format is IdeaAnalysis:
            return IdeaAnalysis(
                service_summary="독서 기록 서비스입니다.",
                target_users=["독서 사용자"],
                core_entities=["books", "reading_logs"],
                mvp_scope=["독서 기록"],
                out_of_scope=["결제"],
            )
        if text_format is FeatureDesign:
            return FeatureDesign(
                overview=valid_blueprint.overview,
                features=valid_blueprint.features,
                tech_stack=valid_blueprint.tech_stack,
            )
        if text_format is ApiDesign:
            if validation_feedback:
                return ApiDesign(api_spec=valid_blueprint.api_spec)
            return invalid_api_design
        if text_format is DatabaseDesign:
            return DatabaseDesign(database_schema=valid_blueprint.database_schema)
        if text_format is DiagramDesign:
            return DiagramDesign(
                database_erd=valid_blueprint.database_erd,
                sequence_diagram=valid_blueprint.sequence_diagram,
            )
        if text_format is PlanningDesign:
            return PlanningDesign(
                non_functional_requirements=make_design_considerations("reliability"),
                security_considerations=make_design_considerations("security"),
                implementation_plan=make_implementation_plan(),
            )
        raise AssertionError(f"unexpected text_format: {text_format}")

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = generate_blueprint_pipeline_with_retry(BlueprintRequest(idea="독서 기록 서비스"))

    assert result.api_spec[0].path == "/api/v1/books"
    assert count_calls(call_formats, IdeaAnalysis) == 1
    assert count_calls(call_formats, FeatureDesign) == 1
    assert count_calls(call_formats, ApiDesign) == 2
    assert count_calls(call_formats, DatabaseDesign) == 2
    assert count_calls(call_formats, DiagramDesign) == 2
    assert count_calls(call_formats, PlanningDesign) == 2
    assert any(
        text_format is ApiDesign and validation_feedback and "API path" in " ".join(validation_feedback)
        for text_format, validation_feedback in call_formats
    )
    assert "langgraph graph=blueprint_pipeline node=validate_blueprint phase=route retry=1 route=api" in caplog.text
    assert "langgraph graph=blueprint_pipeline node=design_api phase=start retry=1" in caplog.text


def test_langgraph_retry_routes_diagram_errors_to_diagram_node_only(monkeypatch) -> None:
    valid_blueprint = make_blueprint()
    call_formats = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        call_formats.append((text_format, validation_feedback))
        if text_format is IdeaAnalysis:
            return IdeaAnalysis(
                service_summary="독서 기록 서비스입니다.",
                target_users=["독서 사용자"],
                core_entities=["books", "reading_logs"],
                mvp_scope=["독서 기록"],
                out_of_scope=["결제"],
            )
        if text_format is FeatureDesign:
            return FeatureDesign(
                overview=valid_blueprint.overview,
                features=valid_blueprint.features,
                tech_stack=valid_blueprint.tech_stack,
            )
        if text_format is ApiDesign:
            return ApiDesign(api_spec=valid_blueprint.api_spec)
        if text_format is DatabaseDesign:
            return DatabaseDesign(database_schema=valid_blueprint.database_schema)
        if text_format is DiagramDesign:
            if validation_feedback:
                return DiagramDesign(
                    database_erd=valid_blueprint.database_erd,
                    sequence_diagram=valid_blueprint.sequence_diagram,
                )
            return DiagramDesign(
                database_erd="broken erd",
                sequence_diagram=valid_blueprint.sequence_diagram,
            )
        if text_format is PlanningDesign:
            return PlanningDesign(
                non_functional_requirements=make_design_considerations("reliability"),
                security_considerations=make_design_considerations("security"),
                implementation_plan=make_implementation_plan(),
            )
        raise AssertionError(f"unexpected text_format: {text_format}")

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = generate_blueprint_pipeline_with_retry(BlueprintRequest(idea="독서 기록 서비스"))

    assert result.database_erd.startswith("erDiagram")
    assert count_calls(call_formats, IdeaAnalysis) == 1
    assert count_calls(call_formats, FeatureDesign) == 1
    assert count_calls(call_formats, ApiDesign) == 1
    assert count_calls(call_formats, DatabaseDesign) == 1
    assert count_calls(call_formats, DiagramDesign) == 2
    assert count_calls(call_formats, PlanningDesign) == 1


def test_regenerate_feature_section_adds_requested_feature_when_llm_omits_it(monkeypatch) -> None:
    current_blueprint = make_blueprint()
    unchanged_feature_design = FeatureDesign(
        overview=current_blueprint.overview,
        features=current_blueprint.features,
        tech_stack=current_blueprint.tech_stack,
    )
    feedback_calls = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        feedback_calls.append(validation_feedback)
        return unchanged_feature_design

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = regenerate_blueprint_section_with_retry(
        "독서 기록 서비스",
        current_blueprint,
        "features",
        "독서 모임 공유 기능을 추가해줘",
    )

    assert len(result.features) == len(current_blueprint.features) + 1
    assert feedback_calls[0] is None
    assert result.features[-1].name == "독서 모임 공유 기능"
    assert "독서 모임 공유 기능을 추가해줘" in result.features[-1].description


def test_regenerate_feature_section_ignores_unrelated_api_validation_errors(monkeypatch) -> None:
    current_blueprint = make_blueprint()
    current_blueprint.api_spec[0].request[0].name = "unmatched_field"
    current_blueprint.implementation_plan[0].description = "공통 개발 환경을 순서대로 구성하는 충분한 구현 단계 설명입니다."
    feature_design = FeatureDesign(
        overview=current_blueprint.overview,
        features=current_blueprint.features,
        tech_stack=current_blueprint.tech_stack,
    )

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        return feature_design

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = regenerate_blueprint_section_with_retry(
        "독서 기록 서비스",
        current_blueprint,
        "features",
        "요리 유튜브 채널 기능",
    )

    assert result.features[-1].name == "요리 유튜브 채널 기능"


def test_regenerate_feature_section_retries_with_friendly_feedback(monkeypatch) -> None:
    current_blueprint = make_blueprint()
    first_feature_design = FeatureDesign(
        overview="첫 번째 재생성 결과입니다.",
        features=current_blueprint.features[:4],
        tech_stack=current_blueprint.tech_stack,
    )
    valid_features = [
        *current_blueprint.features[:-1],
        Feature(
            name="독서 모임 공유",
            description="사용자가 독서 기록을 모임 구성원에게 공유하고 함께 읽을 책을 조율할 수 있게 합니다.",
            priority="medium",
        ),
    ]
    second_feature_design = FeatureDesign(
        overview="두 번째 재생성 결과입니다.",
        features=valid_features,
        tech_stack=current_blueprint.tech_stack,
    )
    responses = [first_feature_design, second_feature_design]
    feedback_calls = []

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        feedback_calls.append(validation_feedback)
        return responses.pop(0)

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = regenerate_blueprint_section_with_retry(
        "독서 기록 서비스",
        current_blueprint,
        "features",
        None,
    )

    assert result.features[-1].name == "독서 모임 공유"
    assert feedback_calls[0] is None
    assert any("기능 섹션" in feedback for feedback in feedback_calls[1])
    assert any("5~8개의 구체적인 MVP 기능" in feedback for feedback in feedback_calls[1])


def test_section_regeneration_graph_fails_after_retry_limit(monkeypatch, caplog) -> None:
    current_blueprint = make_blueprint()
    invalid_api_design = ApiDesign(api_spec=[make_api_spec("POST", "api/v1/items")])
    feedback_calls = []
    caplog.set_level(logging.INFO, logger="app.services.blueprint_generator")

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        feedback_calls.append(validation_feedback)
        return invalid_api_design

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    with pytest.raises(BlueprintGenerationError, match="섹션 재생성 품질 검증 재시도에 실패"):
        regenerate_blueprint_section_with_retry(
            "독서 기록 서비스",
            current_blueprint,
            "api",
            None,
        )

    assert len(feedback_calls) == 3
    assert feedback_calls[0] is None
    assert feedback_calls[1] is not None
    assert "langgraph graph=section_regeneration node=validate_selected_section phase=route retry=3 route=fail" in caplog.text
    assert "langgraph graph=section_regeneration node=fail_section_regeneration phase=failed retry=3 route=api" in caplog.text


def test_regenerate_feature_section_does_not_duplicate_similar_feature(monkeypatch) -> None:
    current_blueprint = make_blueprint()
    changed_blueprint = current_blueprint.model_copy(deep=True)
    changed_blueprint.features.append(
        Feature(
            name="요리 유튜브 채널 추천",
            description="추천된 요리에 연관된 인기 요리 유튜브 채널을 제공해 영상으로 조리법을 배울 수 있게 합니다.",
            priority="medium",
        )
    )
    feature_design = FeatureDesign(
        overview=changed_blueprint.overview,
        features=changed_blueprint.features,
        tech_stack=changed_blueprint.tech_stack,
    )

    def fake_request_structured_output(user_prompt, text_format, validation_feedback=None):
        return feature_design

    monkeypatch.setattr(
        "app.services.blueprint_generator.request_structured_output_from_openai",
        fake_request_structured_output,
    )

    result = regenerate_blueprint_section_with_retry(
        "독서 기록 서비스",
        current_blueprint,
        "features",
        "요리유튜브 채널 추천 기능",
    )

    matching_features = [feature for feature in result.features if "요리" in feature.name and "유튜브" in feature.name]
    assert len(matching_features) == 1
    assert matching_features[0].name == "요리 유튜브 채널 추천"
