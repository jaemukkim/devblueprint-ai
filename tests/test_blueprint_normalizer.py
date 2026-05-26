from app.services.blueprint_normalizer import normalize_blueprint_output
from app.services.blueprint_validator import validate_blueprint_quality

from test_blueprint_validator import make_valid_blueprint


# Mermaid ERD에서 자주 발생하는 key token 흔들림을 검증 전에 보정하는지 확인합니다.
def test_normalize_blueprint_output_fixes_mermaid_erd_key_tokens() -> None:
    blueprint = make_valid_blueprint()
    blueprint.database_erd = (
        "```mermaid\n"
        "erDiagram\n"
        "  books ||--o{ book_events : has\n"
        "  books ||--o{ book_recommendations : has\n"
        "  books {\n"
        "    uuid id PK\n"
        "    uuid owner_id PK FK\n"
        "    varchar external_id UNIQUE\n"
        "  }\n"
        "```\n"
    )

    normalized_blueprint = normalize_blueprint_output(blueprint)

    assert normalized_blueprint.database_erd.startswith("erDiagram")
    assert "uuid owner_id PK, FK" in normalized_blueprint.database_erd
    assert "varchar external_id UK" in normalized_blueprint.database_erd
    validate_blueprint_quality(normalized_blueprint)


# 시퀀스 다이어그램도 Markdown code fence 없이 API 응답에 담기도록 보정합니다.
def test_normalize_blueprint_output_strips_sequence_diagram_code_fence() -> None:
    blueprint = make_valid_blueprint()
    blueprint.sequence_diagram = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "  participant User\n"
        "  User->>API: GET /api/v1/books\n"
        "```\n"
    )

    normalized_blueprint = normalize_blueprint_output(blueprint)

    assert normalized_blueprint.sequence_diagram.startswith("sequenceDiagram")
    validate_blueprint_quality(normalized_blueprint)
