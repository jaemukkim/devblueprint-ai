import re

from app.schemas.blueprint import BlueprintResponse
from app.services.llm_client import BlueprintGenerationError


SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
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
MERMAID_ERD_KEY_TOKENS = {"PK", "FK", "UK"}
GENERIC_FIELD_NAMES = {"id", "item", "items", "result", "results", "overview", "created_at", "updated_at", "deleted_at"}
AUTH_SCOPE_KEYWORDS = {"auth", "login", "password", "session", "token", "role", "permission", "인증", "권한", "로그인"}
PRIVACY_SCOPE_KEYWORDS = {"email", "phone", "address", "profile", "personal", "privacy", "pii", "개인", "이메일", "주소"}
PAYMENT_SCOPE_KEYWORDS = {"payment", "billing", "invoice", "card", "subscription", "결제", "청구", "카드", "구독"}
AUTH_SECURITY_KEYWORDS = {"auth", "authorization", "session", "token", "password", "role", "permission", "인증", "인가", "권한", "토큰"}
PRIVACY_SECURITY_KEYWORDS = {"privacy", "personal", "pii", "encrypt", "mask", "retention", "개인정보", "암호화", "마스킹", "보관"}
PAYMENT_SECURITY_KEYWORDS = {"payment", "billing", "card", "pci", "webhook", "signature", "결제", "카드", "웹훅", "서명"}


def collect_blueprint_quality_errors(blueprint: BlueprintResponse) -> list[str]:
    """Pydantic schema 통과 후에도 확인해야 하는 설계 품질 오류 목록을 수집합니다."""
    errors: list[str] = []

    validate_collection_size("features", blueprint.features, 5, 8, errors)
    validate_collection_size("api_spec", blueprint.api_spec, 4, 8, errors)
    validate_collection_size("database_schema", blueprint.database_schema, 3, 6, errors)
    validate_collection_size("non_functional_requirements", blueprint.non_functional_requirements, 3, 6, errors)
    validate_collection_size("security_considerations", blueprint.security_considerations, 3, 6, errors)
    validate_collection_size("implementation_plan", blueprint.implementation_plan, 3, 6, errors)
    validate_feature_quality(blueprint, errors)
    validate_design_considerations(blueprint, errors)
    validate_implementation_plan(blueprint, errors)
    validate_api_paths(blueprint, errors)
    validate_api_fields(blueprint, errors)
    validate_database_names(blueprint, errors)
    validate_database_primary_keys(blueprint, errors)
    validate_database_depth(blueprint, errors)
    validate_database_erd(blueprint, errors)
    validate_sequence_diagram(blueprint, errors)
    validate_cross_section_consistency(blueprint, errors)

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


def validate_design_considerations(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """비기능/보안 항목이 제목만 있는 얕은 체크리스트가 되지 않도록 확인합니다."""
    for group_name, items in [
        ("non_functional_requirements", blueprint.non_functional_requirements),
        ("security_considerations", blueprint.security_considerations),
    ]:
        for item in items:
            if len(item.title.strip()) < 4:
                errors.append(f"{group_name} title is too short: {item.title}")
            if len(item.description.strip()) < MIN_FEATURE_DESCRIPTION_LENGTH:
                errors.append(f"{group_name} description is too short: {item.title}")


def validate_implementation_plan(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """구현 계획이 실제 순서와 설명을 가진 단계인지 확인합니다."""
    for step in blueprint.implementation_plan:
        if not step.phase.strip():
            errors.append(f"implementation_plan phase must not be empty: {step.title}")
        if len(step.title.strip()) < 4:
            errors.append(f"implementation_plan title is too short: {step.title}")
        if len(step.description.strip()) < MIN_FEATURE_DESCRIPTION_LENGTH:
            errors.append(f"implementation_plan description is too short: {step.title}")


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

    validate_erd_attribute_keys(erd, errors)


def validate_erd_attribute_keys(erd: str, errors: list[str]) -> None:
    """Mermaid ERD 속성 줄에서 렌더링 가능한 key token만 쓰는지 확인합니다."""
    in_entity_block = False

    for line in erd.splitlines():
        stripped_line = line.strip()

        if not stripped_line or stripped_line == "erDiagram":
            continue

        if stripped_line.endswith("{"):
            in_entity_block = True
            continue

        if stripped_line == "}":
            in_entity_block = False
            continue

        if not in_entity_block:
            continue

        tokens = stripped_line.split()
        if len(tokens) < 3:
            continue

        for token in tokens[2:]:
            normalized_token = token.strip(",").upper()
            if normalized_token in MERMAID_ERD_KEY_TOKENS:
                continue
            if normalized_token == "UNIQUE":
                errors.append("database_erd must use Mermaid key token 'UK' instead of 'UNIQUE'")


def validate_sequence_diagram(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """Mermaid 시퀀스 다이어그램으로 렌더링 가능한 최소 형식을 확인합니다."""
    if not blueprint.sequence_diagram.strip().startswith("sequenceDiagram"):
        errors.append("sequence_diagram must start with 'sequenceDiagram'")


def validate_cross_section_consistency(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """API, DB, 다이어그램, 계획 섹션이 같은 제품 설계를 설명하는지 확인합니다."""
    api_resources = collect_api_resource_tokens(blueprint)
    table_tokens = collect_database_table_tokens(blueprint)
    column_names = collect_database_column_names(blueprint)

    validate_api_database_alignment(api_resources, table_tokens, errors)
    validate_api_field_database_alignment(blueprint, column_names, errors)
    validate_sequence_api_alignment(blueprint, api_resources, errors)
    validate_plan_alignment(blueprint, api_resources, table_tokens, errors)
    validate_contextual_security_coverage(blueprint, errors)


def validate_api_database_alignment(
    api_resources: set[str],
    table_tokens: set[str],
    errors: list[str],
) -> None:
    """API resource와 DB table 이름이 핵심 도메인 단어를 공유하는지 확인합니다."""
    unmatched_resources = sorted(resource for resource in api_resources if resource not in table_tokens)

    for resource in unmatched_resources:
        errors.append(f"api resource must be represented in database_schema: {resource}")


def validate_api_field_database_alignment(
    blueprint: BlueprintResponse,
    column_names: set[str],
    errors: list[str],
) -> None:
    """API 입출력 필드가 DB 컬럼과 완전히 동떨어지지 않았는지 확인합니다."""
    if not column_names:
        return

    for api in blueprint.api_spec:
        field_names = {normalize_name_token(field.name) for field in [*api.request, *api.response]}
        comparable_field_names = {field_name for field_name in field_names if field_name and field_name not in GENERIC_FIELD_NAMES}

        if comparable_field_names and comparable_field_names.isdisjoint(column_names):
            errors.append(f"api fields must overlap database columns: {api.method} {api.path}")


def validate_sequence_api_alignment(
    blueprint: BlueprintResponse,
    api_resources: set[str],
    errors: list[str],
) -> None:
    """시퀀스 다이어그램이 실제 API 흐름의 핵심 resource를 언급하는지 확인합니다."""
    if not api_resources:
        return

    sequence_text = blueprint.sequence_diagram.lower()
    if not any(resource in sequence_text for resource in api_resources):
        errors.append("sequence_diagram must reference at least one api resource")


def validate_plan_alignment(
    blueprint: BlueprintResponse,
    api_resources: set[str],
    table_tokens: set[str],
    errors: list[str],
) -> None:
    """구현 계획이 생성된 기능/API/DB 설계와 연결된 단어를 포함하는지 확인합니다."""
    anchor_tokens = {token for token in api_resources | table_tokens if len(token) >= 4}
    if not anchor_tokens:
        return

    plan_text = " ".join(f"{step.title} {step.description}" for step in blueprint.implementation_plan).lower()
    if not any(token in plan_text for token in anchor_tokens):
        errors.append("implementation_plan must reference generated feature, api, or database concepts")


def validate_contextual_security_coverage(blueprint: BlueprintResponse, errors: list[str]) -> None:
    """도메인에 인증/개인정보/결제 위험이 있으면 보안 고려사항에 해당 대응이 있는지 확인합니다."""
    blueprint_text = collect_blueprint_text(blueprint)
    security_text = " ".join(
        f"{item.category} {item.title} {item.description}" for item in blueprint.security_considerations
    ).lower()

    for scope_name, scope_keywords, security_keywords in [
        ("authentication", AUTH_SCOPE_KEYWORDS, AUTH_SECURITY_KEYWORDS),
        ("privacy", PRIVACY_SCOPE_KEYWORDS, PRIVACY_SECURITY_KEYWORDS),
        ("payment", PAYMENT_SCOPE_KEYWORDS, PAYMENT_SECURITY_KEYWORDS),
    ]:
        if contains_any_keyword(blueprint_text, scope_keywords) and not contains_any_keyword(security_text, security_keywords):
            errors.append(f"security_considerations must cover {scope_name} risks")


def normalize_constraint(constraint: str) -> str:
    """constraint 표기를 비교하기 쉽게 snake_case 소문자로 정규화합니다."""
    return constraint.strip().lower().replace(" ", "_")


def extract_primary_resource_name(path: str) -> str:
    """API path에서 버전 prefix와 path parameter를 제외한 첫 resource 이름을 추출합니다."""
    parts = [part for part in path.strip("/").split("/") if part and not part.startswith("{")]
    resource_parts = [part for part in parts if part not in {"api", "v1", "v2", "v3"}]
    return resource_parts[0] if resource_parts else ""


def collect_api_resource_tokens(blueprint: BlueprintResponse) -> set[str]:
    """API path의 첫 resource를 비교 가능한 단수 토큰으로 모읍니다."""
    return {
        normalize_name_token(extract_primary_resource_name(api.path))
        for api in blueprint.api_spec
        if extract_primary_resource_name(api.path)
    }


def collect_database_table_tokens(blueprint: BlueprintResponse) -> set[str]:
    """DB table 이름을 구성하는 도메인 토큰을 모읍니다."""
    tokens: set[str] = set()

    for table in blueprint.database_schema:
        for token in table.name.split("_"):
            normalized_token = normalize_name_token(token)
            if normalized_token and normalized_token not in GENERIC_API_RESOURCES:
                tokens.add(normalized_token)

    return tokens


def collect_database_column_names(blueprint: BlueprintResponse) -> set[str]:
    """DB column 이름을 API field와 비교 가능한 토큰으로 모읍니다."""
    return {
        normalize_name_token(column.name)
        for table in blueprint.database_schema
        for column in table.columns
        if normalize_name_token(column.name)
    }


def normalize_name_token(value: str) -> str:
    """복수형과 path parameter 표기를 느슨하게 맞추기 위해 이름 토큰을 정규화합니다."""
    normalized = value.strip("{}").strip().lower().replace("-", "_")
    if normalized.endswith("_id"):
        normalized = normalized[:-3]
    if normalized.endswith("ies") and len(normalized) > 4:
        return f"{normalized[:-3]}y"
    if normalized.endswith("s") and not normalized.endswith("ss") and len(normalized) > 3:
        return normalized[:-1]
    return normalized


def collect_blueprint_text(blueprint: BlueprintResponse) -> str:
    """보안 맥락 탐지를 위해 설계도 전체 텍스트를 하나로 합칩니다."""
    values = [
        blueprint.overview,
        blueprint.tech_stack.rationale,
        blueprint.database_erd,
        blueprint.sequence_diagram,
    ]

    values.extend(f"{feature.name} {feature.description}" for feature in blueprint.features)
    values.extend(f"{api.method} {api.path} {api.description}" for api in blueprint.api_spec)
    values.extend(
        f"{field.name} {field.type} {field.description}"
        for api in blueprint.api_spec
        for field in [*api.request, *api.response]
    )
    values.extend(f"{table.name} {table.description}" for table in blueprint.database_schema)
    values.extend(
        f"{column.name} {column.type} {column.description}"
        for table in blueprint.database_schema
        for column in table.columns
    )

    return " ".join(values).lower()


def contains_any_keyword(text: str, keywords: set[str]) -> bool:
    """영문 토큰과 한국어 부분 문자열을 함께 비교합니다."""
    english_tokens = set(TOKEN_PATTERN.findall(text))
    return any(keyword in text if not keyword.isascii() else keyword in english_tokens for keyword in keywords)
