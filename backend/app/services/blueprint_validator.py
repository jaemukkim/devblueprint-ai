import re

from app.schemas.blueprint import BlueprintResponse
from app.services.llm_client import BlueprintGenerationError


SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_blueprint_quality(blueprint: BlueprintResponse) -> None:
    """Pydantic schema 통과 후에도 확인해야 하는 설계 품질 규칙을 검증합니다."""
    errors: list[str] = []

    validate_collection_size("features", blueprint.features, 5, 8, errors)
    validate_collection_size("api_spec", blueprint.api_spec, 4, 8, errors)
    validate_collection_size("database_schema", blueprint.database_schema, 3, 6, errors)
    validate_api_paths(blueprint, errors)
    validate_database_names(blueprint, errors)
    validate_database_erd(blueprint, errors)
    validate_sequence_diagram(blueprint, errors)

    if errors:
        joined_errors = "; ".join(errors)
        raise BlueprintGenerationError(f"설계도 품질 검증에 실패했습니다: {joined_errors}")


def validate_collection_size(
    name: str,
    items: list,
    min_count: int,
    max_count: int,
    errors: list[str],
) -> None:
    """LLM이 너무 빈약하거나 과도한 설계를 만들지 않도록 항목 개수를 제한합니다."""
    if len(items) < min_count:
        errors.append(f"{name} must contain at least {min_count} items")
    if len(items) > max_count:
        errors.append(f"{name} must contain at most {max_count} items")


def validate_api_paths(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """API path가 REST API로 사용할 수 있는 기본 형태인지 확인합니다."""
    for api in blueprint.api_spec:
        if not api.path.startswith("/"):
            errors.append(f"api path must start with '/': {api.path}")
        if " " in api.path:
            errors.append(f"api path must not contain spaces: {api.path}")


def validate_database_names(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """DB table과 column 이름이 snake_case 규칙을 따르는지 확인합니다."""
    for table in blueprint.database_schema:
        if not SNAKE_CASE_PATTERN.match(table.name):
            errors.append(f"table name must be snake_case: {table.name}")

        for column in table.columns:
            if not SNAKE_CASE_PATTERN.match(column.name):
                errors.append(f"column name must be snake_case: {table.name}.{column.name}")


def validate_sequence_diagram(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """Mermaid 시퀀스 다이어그램으로 렌더링 가능한 최소 형식을 확인합니다."""
    if not blueprint.sequence_diagram.strip().startswith("sequenceDiagram"):
        errors.append("sequence_diagram must start with 'sequenceDiagram'")


def validate_database_erd(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """Mermaid ERD로 렌더링 가능한 최소 형식을 확인합니다."""
    if not blueprint.database_erd.strip().startswith("erDiagram"):
        errors.append("database_erd must start with 'erDiagram'")
