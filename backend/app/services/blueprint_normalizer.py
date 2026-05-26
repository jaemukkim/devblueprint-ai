import re

from app.schemas.blueprint import BlueprintResponse


ERD_KEY_GROUP_PATTERN = re.compile(r"\b(PK|FK|UK)(?:\s+(PK|FK|UK))+\b")
ERD_UNIQUE_TOKEN_PATTERN = re.compile(r"\b(UNIQUE|UQ)\b", re.IGNORECASE)


# LLM 응답에 섞일 수 있는 Markdown code fence를 제거해 Mermaid 본문만 남깁니다.
def strip_mermaid_code_fence(source: str) -> str:
    stripped_source = source.strip()
    if not stripped_source.startswith("```"):
        return source

    lines = stripped_source.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


# Mermaid ERD 속성 라인의 key token을 Mermaid 파서가 받는 표기로 정리합니다.
def normalize_mermaid_erd_source(source: str) -> str:
    unfenced_source = strip_mermaid_code_fence(source)
    if not unfenced_source.strip().startswith("erDiagram"):
        return unfenced_source

    normalized_lines: list[str] = []
    in_entity_block = False

    for line in unfenced_source.splitlines():
        stripped_line = line.strip()

        if stripped_line.endswith("{"):
            in_entity_block = True
            normalized_lines.append(line)
            continue

        if stripped_line == "}":
            in_entity_block = False
            normalized_lines.append(line)
            continue

        normalized_lines.append(normalize_mermaid_erd_line(line) if in_entity_block else line)

    return "\n".join(normalized_lines)


# UNIQUE와 공백으로 이어진 복수 key token을 Mermaid 호환 문법으로 바꿉니다.
def normalize_mermaid_erd_line(line: str) -> str:
    normalized_line = ERD_UNIQUE_TOKEN_PATTERN.sub("UK", line)
    normalized_line = ERD_KEY_GROUP_PATTERN.sub(lambda key_group: ", ".join(key_group.group(0).split()), normalized_line)
    return normalize_mermaid_erd_attribute_type(normalized_line)


# Mermaid ERD attribute type은 공백 없는 한 단어여야 하므로 SQL 복합 타입을 underscore로 합칩니다.
def normalize_mermaid_erd_attribute_type(line: str) -> str:
    indentation_match = re.match(r"^\s*", line)
    indentation = indentation_match.group(0) if indentation_match else ""
    stripped_line = line.strip()
    tokens = stripped_line.split()
    key_start_index = next(
        (index for index, token in enumerate(tokens) if token.strip(",").upper() in {"PK", "FK", "UK"}),
        -1,
    )

    if key_start_index > 2:
        column_type = "_".join(tokens[: key_start_index - 1])
        column_name = tokens[key_start_index - 1]
        return f"{indentation}{' '.join([column_type, column_name, *tokens[key_start_index:]])}"

    if key_start_index == -1 and len(tokens) > 2 and '"' not in stripped_line:
        column_type = "_".join(tokens[:-1])
        column_name = tokens[-1]
        return f"{indentation}{column_type} {column_name}"

    return line


# 생성된 설계도 전체에서 자동 보정 가능한 표현을 저장/검증 전에 정규화합니다.
def normalize_blueprint_output(blueprint: BlueprintResponse) -> BlueprintResponse:
    normalized_blueprint = blueprint.model_copy(deep=True)
    normalized_blueprint.database_erd = normalize_mermaid_erd_source(normalized_blueprint.database_erd)
    normalized_blueprint.sequence_diagram = strip_mermaid_code_fence(normalized_blueprint.sequence_diagram)
    return normalized_blueprint
