import re

from app.schemas.blueprint import BlueprintResponse
from app.services.llm_client import BlueprintGenerationError


SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
GENERIC_API_RESOURCES = {"items", "records", "data", "results", "entities", "objects"}
GENERIC_FEATURE_NAMES = {
    "아이디어 분석",
    "기능 요구사항 정리",
    "API 설계 생성",
    "데이터 모델 제안",
    "시퀀스 다이어그램 생성",
    "결과 다운로드",
}
MIN_FEATURE_DESCRIPTION_LENGTH = 20
MIN_TABLE_COLUMN_COUNT = 3


def collect_blueprint_quality_errors(blueprint: BlueprintResponse) -> list[str]:
    """Pydantic schema 통과 후에도 확인해야 하는 설계 품질 오류 목록을 수집합니다."""
    errors: list[str] = []

    validate_collection_size("features", blueprint.features, 5, 8, errors)
    validate_collection_size("api_spec", blueprint.api_spec, 4, 8, errors)
    validate_collection_size("database_schema", blueprint.database_schema, 3, 6, errors)
    validate_feature_quality(blueprint, errors)
    validate_api_paths(blueprint, errors)
    validate_api_fields(blueprint, errors)
    validate_database_names(blueprint, errors)
    validate_database_primary_keys(blueprint, errors)
    validate_database_depth(blueprint, errors)
    validate_database_erd(blueprint, errors)
    validate_sequence_diagram(blueprint, errors)

    return errors


def validate_blueprint_quality(blueprint: BlueprintResponse) -> None:
    """설계 품질 규칙을 검증하고 실패하면 생성 오류로 변환합니다."""
    errors = collect_blueprint_quality_errors(blueprint)

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
    seen_endpoints: set[tuple[str, str]] = set()

    for api in blueprint.api_spec:
        if not api.path.startswith("/"):
            errors.append(f"api path must start with '/': {api.path}")
        if " " in api.path:
            errors.append(f"api path must not contain spaces: {api.path}")

        endpoint_key = (api.method, api.path)
        if endpoint_key in seen_endpoints:
            errors.append(f"api endpoint must be unique: {api.method} {api.path}")
        seen_endpoints.add(endpoint_key)

        resource_name = extract_primary_resource_name(api.path)
        if resource_name in GENERIC_API_RESOURCES:
            errors.append(f"api path is too generic: {api.path}")


def validate_feature_quality(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """기능 목록이 placeholder처럼 얕거나 설명이 너무 짧지 않은지 확인합니다."""
    for feature in blueprint.features:
        if feature.name in GENERIC_FEATURE_NAMES:
            errors.append(f"feature name is too generic: {feature.name}")

        if len(feature.description.strip()) < MIN_FEATURE_DESCRIPTION_LENGTH:
            errors.append(f"feature description is too short: {feature.name}")


def validate_api_fields(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """API 입출력 필드가 실제 구현 참고에 필요한 최소 정보를 갖췄는지 확인합니다."""
    for api in blueprint.api_spec:
        if not api.response:
            errors.append(f"api response fields must not be empty: {api.method} {api.path}")

        for field in [*api.request, *api.response]:
            if not field.name.strip():
                errors.append(f"api field name must not be empty: {api.method} {api.path}")
            if not field.type.strip():
                errors.append(f"api field type must not be empty: {api.method} {api.path}.{field.name}")


def validate_database_names(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """DB table과 column 이름이 snake_case 규칙을 따르는지 확인합니다."""
    for table in blueprint.database_schema:
        if not SNAKE_CASE_PATTERN.match(table.name):
            errors.append(f"table name must be snake_case: {table.name}")

        for column in table.columns:
            if not SNAKE_CASE_PATTERN.match(column.name):
                errors.append(f"column name must be snake_case: {table.name}.{column.name}")


def validate_database_primary_keys(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """각 테이블이 구현 가능한 기본 식별자를 갖고 있는지 확인합니다."""
    for table in blueprint.database_schema:
        has_primary_key = any(
            normalize_constraint(constraint) == "primary_key"
            for column in table.columns
            for constraint in column.constraints
        )

        if not has_primary_key:
            errors.append(f"table must include a primary_key column: {table.name}")


def validate_database_depth(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """각 테이블이 실제 구현에 참고할 수 있을 만큼 충분한 컬럼을 갖는지 확인합니다."""
    for table in blueprint.database_schema:
        if len(table.columns) < MIN_TABLE_COLUMN_COUNT:
            errors.append(f"table must include at least {MIN_TABLE_COLUMN_COUNT} columns: {table.name}")


def validate_database_erd(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """Mermaid ERD로 렌더링 가능한 최소 형식을 확인합니다."""
    erd = blueprint.database_erd.strip()
    if not erd.startswith("erDiagram"):
        errors.append("database_erd must start with 'erDiagram'")
        return

    normalized_erd = erd.lower()
    table_names = {table.name for table in blueprint.database_schema}
    missing_tables = sorted(table_name for table_name in table_names if table_name.lower() not in normalized_erd)

    for table_name in missing_tables:
        errors.append(f"database_erd must include table from database_schema: {table_name}")


def validate_sequence_diagram(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """Mermaid 시퀀스 다이어그램으로 렌더링 가능한 최소 형식을 확인합니다."""
    if not blueprint.sequence_diagram.strip().startswith("sequenceDiagram"):
        errors.append("sequence_diagram must start with 'sequenceDiagram'")


def normalize_constraint(constraint: str) -> str:
    """constraint 표기를 비교하기 쉽게 snake_case 소문자로 정규화합니다."""
    return constraint.strip().lower().replace(" ", "_")


def extract_primary_resource_name(path: str) -> str:
    """API path에서 버전 prefix와 path parameter를 제외한 첫 resource 이름을 추출합니다."""
    parts = [part for part in path.strip("/").split("/") if part and not part.startswith("{")]
    resource_parts = [part for part in parts if part not in {"api", "v1", "v2", "v3"}]
    return resource_parts[0] if resource_parts else ""
