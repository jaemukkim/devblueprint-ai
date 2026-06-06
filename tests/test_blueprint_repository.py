from app.repositories.blueprint_repository import InMemoryBlueprintRepository
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


def make_repository_test_blueprint() -> BlueprintResponse:
    return BlueprintResponse(
        overview="저장소 테스트용 설계도입니다.",
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
            rationale="저장소 테스트용 기술 스택입니다.",
        ),
        api_spec=[
            ApiSpec(
                method="POST",
                path="/api/v1/items",
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
        ],
        database_schema=[
            DatabaseTable(
                name="test_items",
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
        ],
        database_erd="erDiagram\n  test_items { uuid id PK }",
        sequence_diagram="sequenceDiagram\n  participant User\n  User->>User: 테스트",
        non_functional_requirements=make_design_considerations("reliability"),
        security_considerations=make_design_considerations("security"),
        implementation_plan=make_implementation_plan(),
    )


def make_design_considerations(category: str) -> list[DesignConsideration]:
    return [
        DesignConsideration(
            category=category,
            title=f"{category} 항목 {index}",
            description=f"{category} 관점에서 실제 구현 전에 확인해야 하는 설계 고려사항입니다.",
            priority="medium",
        )
        for index in range(1, 4)
    ]


def make_implementation_plan() -> list[ImplementationStep]:
    return [
        ImplementationStep(
            phase=str(index),
            title=f"구현 단계 {index}",
            description="개발자가 순서대로 진행할 수 있는 충분한 구현 단계 설명입니다.",
        )
        for index in range(1, 4)
    ]


def test_in_memory_blueprint_repository_saves_and_gets_copy() -> None:
    repository = InMemoryBlueprintRepository()
    blueprint = make_repository_test_blueprint()

    repository.save("test-key", blueprint)
    cached_blueprint = repository.get("test-key")

    assert cached_blueprint == blueprint
    assert cached_blueprint is not blueprint
    assert repository.count() == 1


def test_in_memory_blueprint_repository_normalizes_legacy_mermaid_on_read() -> None:
    repository = InMemoryBlueprintRepository()
    blueprint = make_repository_test_blueprint()
    blueprint.database_erd = (
        "```mermaid\n"
        "erDiagram\n"
        "  test_items {\n"
        "    uuid owner_id PK FK\n"
        "    timestamp with time zone created_at\n"
        "  }\n"
        "```\n"
    )

    repository.save("legacy-key", blueprint)
    cached_blueprint = repository.get("legacy-key")
    stored_blueprint = repository.get_stored_by_key("legacy-key")

    assert cached_blueprint is not None
    assert stored_blueprint is not None
    assert cached_blueprint.database_erd.startswith("erDiagram")
    assert "uuid owner_id PK, FK" in cached_blueprint.database_erd
    assert "timestamp_with_time_zone created_at" in cached_blueprint.database_erd
    assert stored_blueprint.result.database_erd == cached_blueprint.database_erd
    assert repository._items["legacy-key"].result.database_erd.startswith("```mermaid")


def test_in_memory_blueprint_repository_clear_removes_items() -> None:
    repository = InMemoryBlueprintRepository()
    repository.save("test-key", make_repository_test_blueprint())
    stored_blueprint = repository.get_stored_by_key("test-key")

    assert stored_blueprint is not None
    repository.record_run_event(
        blueprint_id=stored_blueprint.id,
        run_type="blueprint_generation",
        node_name="validate_blueprint",
        phase="route",
        retry_count=1,
        route="complete",
        error_count=0,
    )

    repository.clear()

    assert repository.get("test-key") is None
    assert repository.list_run_events(stored_blueprint.id) == []
    assert repository.count() == 0


def test_in_memory_blueprint_repository_records_run_events() -> None:
    repository = InMemoryBlueprintRepository()
    stored_blueprint = repository.save("test-key", make_repository_test_blueprint())

    run_event = repository.record_run_event(
        blueprint_id=stored_blueprint.id,
        run_type="section_regeneration",
        section="features",
        node_name="validate_selected_section",
        phase="route",
        retry_count=2,
        route="retry",
        error_count=1,
    )
    run_events = repository.list_run_events(stored_blueprint.id)

    assert len(run_events) == 1
    assert run_events[0] == run_event
    assert run_events[0] is not run_event
    assert run_events[0].blueprint_id == stored_blueprint.id
    assert run_events[0].run_type == "section_regeneration"
    assert run_events[0].section == "features"
    assert run_events[0].route == "retry"


def test_in_memory_blueprint_repository_deletes_run_events_with_blueprint() -> None:
    repository = InMemoryBlueprintRepository()
    stored_blueprint = repository.save("test-key", make_repository_test_blueprint())
    repository.record_run_event(
        blueprint_id=stored_blueprint.id,
        run_type="blueprint_generation",
        node_name="validate_blueprint",
        phase="route",
    )

    deleted = repository.delete_by_id(stored_blueprint.id)

    assert deleted is True
    assert repository.list_run_events(stored_blueprint.id) == []
