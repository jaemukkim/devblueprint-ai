from app.repositories.blueprint_repository import InMemoryBlueprintRepository
from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseTable,
    Feature,
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
    )


def test_in_memory_blueprint_repository_saves_and_gets_copy() -> None:
    repository = InMemoryBlueprintRepository()
    blueprint = make_repository_test_blueprint()

    repository.save("test-key", blueprint)
    cached_blueprint = repository.get("test-key")

    assert cached_blueprint == blueprint
    assert cached_blueprint is not blueprint
    assert repository.count() == 1


def test_in_memory_blueprint_repository_clear_removes_items() -> None:
    repository = InMemoryBlueprintRepository()
    repository.save("test-key", make_repository_test_blueprint())

    repository.clear()

    assert repository.get("test-key") is None
    assert repository.count() == 0
