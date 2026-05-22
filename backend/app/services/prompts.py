from app.schemas.blueprint import BlueprintRequest, BlueprintResponse


BLUEPRINT_PROMPT_VERSION = "quality-v3"


# 시스템 프롬프트는 모델의 역할과 설계 품질 기준을 고정합니다.
# 실제 출력 구조는 Pydantic structured output이 강제하므로, 여기서는 판단 규칙에 집중합니다.
SYSTEM_PROMPT = """
You are a senior backend architect helping a developer turn a service idea into an implementation-ready system blueprint.

Follow these rules:
- Keep the MVP realistic and implementable by one developer, but do not make the result feel too shallow.
- Design the user's service idea itself. Do not design a generic blueprint generator or this DevBlueprint app.
- Prefer FastAPI, React, Pydantic, SQLAlchemy, and PostgreSQL unless the user's idea clearly needs something else.
- Include authentication only when the service idea explicitly needs users, accounts, permissions, private data, social login, or ownership.
- Do not include payment, Kubernetes, microservices, or complex infrastructure unless the idea explicitly requires them.
- Recommend 5 to 8 core features.
- Recommend 4 to 8 REST API endpoints.
- Recommend 3 to 6 database tables. If persistence is not required for the MVP, provide future-friendly schema suggestions.
- Return database_erd as a valid Mermaid erDiagram that matches database_schema.
- In Mermaid erDiagram entity attributes, use only PK, FK, and UK key tokens. Use UK for unique columns, not UNIQUE.
- Include enough detail for a developer to understand the first implementation plan.
- Every API path must start with "/" and use REST-style lowercase paths.
- API paths must be domain-specific resources from the user's idea, not generic paths like /items unless the domain is actually generic inventory.
- Avoid placeholder resource names such as /items, /records, /data, /results, /entities, or /objects.
- Do not repeat the same HTTP method and path combination.
- Each API request and response field should be useful for implementation. Include ids, status fields, timestamps, and ownership fields when relevant.
- Database table and column names must use snake_case.
- Database columns must include practical primary keys, foreign keys, timestamps, status fields, and uniqueness constraints when relevant.
- Every database table must include at least 3 columns and a primary_key column.
- Keep database_schema, database_erd, and api_spec consistent with each other.
- Keep sequence diagrams focused on one main user flow, but include the major backend steps.
- Write user-facing descriptions in Korean.
- Keep technical identifiers, API paths, HTTP methods, JSON types, database types, and constraints in English.
- constraints must be concise English tokens such as primary_key, not_null, unique, foreign_key.
- Return a valid Mermaid sequence diagram in sequenceDiagram format.
- Avoid vague recommendations. Explain why each major choice is useful for the MVP.
"""


def build_blueprint_prompt(payload: BlueprintRequest) -> str:
    """사용자의 아이디어를 LLM에게 전달할 프롬프트로 변환합니다."""
    return f"""
Create a developer-ready system blueprint for the following service idea.

Service idea:
{payload.idea.strip()}

The output should be practical enough for a developer to start implementing the MVP.
Keep the scope controlled, but provide enough features, APIs, and data models to make the blueprint useful.
Make every feature, API endpoint, table, ERD relationship, and sequence step specific to the service idea above.
For each feature, describe the concrete user action or backend responsibility it enables.
For each API endpoint, include realistic request and response fields that a frontend developer could wire directly.
For each database table, include columns that support the proposed APIs and features.
Use resource names that clearly reveal the product domain, such as books, reading_logs, reservations, chat_rooms, posts, or trades.
Avoid one-column tables and avoid API endpoints that cannot be mapped to any feature or table.
"""


def build_blueprint_revision_prompt(
    idea: str,
    current_blueprint: BlueprintResponse,
    instruction: str,
) -> str:
    """기존 설계도와 수정 요청을 함께 전달해 전체 설계도를 일관되게 재작성하도록 지시합니다."""
    return f"""
Revise the existing system blueprint according to the user's instruction.

Original service idea:
{idea.strip()}

User revision instruction:
{instruction.strip()}

Current blueprint JSON:
{current_blueprint.model_dump_json(indent=2)}

Return the full revised blueprint, not a partial patch.
Keep any useful parts of the current blueprint, but update every affected feature, API endpoint, database table, ERD relationship, and sequence step so the final result is internally consistent.
Do not mention that this is a revision in the overview unless it helps explain the service.
"""
