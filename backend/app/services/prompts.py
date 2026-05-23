from app.schemas.blueprint import BlueprintRequest, BlueprintResponse


BLUEPRINT_PROMPT_VERSION = "quality-v5-pipeline"


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
- Include 3 to 6 non-functional requirements covering reliability, performance, observability, scalability, accessibility, or maintainability.
- Include 3 to 6 security considerations covering authentication, authorization, data validation, privacy, audit logging, rate limiting, or abuse prevention when relevant.
- Include 3 to 6 implementation plan steps that a developer could follow in order.
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
For non_functional_requirements, avoid generic advice and explain concrete engineering constraints for this product.
For security_considerations, include only relevant risks and mitigations for the service idea.
For implementation_plan, describe sequential milestones from first backend/API slice to UI, persistence, validation, and release readiness.
Use resource names that clearly reveal the product domain, such as books, reading_logs, reservations, chat_rooms, posts, or trades.
Avoid one-column tables and avoid API endpoints that cannot be mapped to any feature or table.
"""


def build_idea_analysis_prompt(payload: BlueprintRequest) -> str:
    """섹션별 생성을 시작하기 전에 서비스의 도메인과 MVP 경계를 먼저 정리합니다."""
    return f"""
Analyze the following service idea before any detailed design work.

Service idea:
{payload.idea.strip()}

Return the product domain, target users, core entities, MVP scope, and explicit out-of-scope items.
Keep the analysis specific to this service idea.
Write user-facing descriptions in Korean and keep technical identifiers in English where useful.
"""


def build_feature_design_prompt(idea: str, analysis: object) -> str:
    """분석 결과를 바탕으로 기능과 기술 스택만 생성하도록 지시합니다."""
    return f"""
Design only the overview, core features, and recommended tech stack for this service.

Service idea:
{idea.strip()}

Idea analysis JSON:
{_dump_context(analysis)}

Return 5 to 8 concrete MVP features and a practical tech stack.
Do not design APIs, database tables, diagrams, security items, or implementation plan in this step.
"""


def build_api_design_prompt(idea: str, analysis: object, feature_design: object) -> str:
    """확정된 기능 목록을 기준으로 API만 생성하도록 지시합니다."""
    return f"""
Design only the REST API endpoints for this service.

Service idea:
{idea.strip()}feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가feat: 설계도 계획 섹션 추가

Idea analysis JSON:
{_dump_context(analysis)}

Feature design JSON:
{_dump_context(feature_design)}

Return 4 to 8 domain-specific REST API endpoints.
Each endpoint must map to the feature design and include realistic request and response fields.
Do not design database tables, diagrams, security items, or implementation plan in this step.
"""


def build_database_design_prompt(idea: str, analysis: object, feature_design: object, api_design: object) -> str:
    """기능과 API를 기준으로 DB schema만 생성하도록 지시합니다."""
    return f"""
Design only the database schema for this service.

Service idea:
{idea.strip()}

Idea analysis JSON:
{_dump_context(analysis)}

Feature design JSON:
{_dump_context(feature_design)}

API design JSON:
{_dump_context(api_design)}

Return 3 to 6 PostgreSQL-friendly tables that support the proposed features and APIs.
Use snake_case table and column names, practical primary keys, foreign keys, timestamps, status fields, and uniqueness constraints when relevant.
Do not design Mermaid diagrams or implementation plan in this step.
"""


def build_diagram_design_prompt(idea: str, analysis: object, api_design: object, database_design: object) -> str:
    """확정된 API와 DB를 기준으로 Mermaid 다이어그램만 생성하도록 지시합니다."""
    return f"""
Create only the Mermaid diagrams for this service.

Service idea:
{idea.strip()}

Idea analysis JSON:
{_dump_context(analysis)}

API design JSON:
{_dump_context(api_design)}

Database design JSON:
{_dump_context(database_design)}

Return a valid Mermaid erDiagram that includes every database table.
Return a valid Mermaid sequenceDiagram focused on the main user flow and major backend steps.
Do not invent tables or endpoints that are not in the provided API and database design.
"""


def build_planning_design_prompt(
    idea: str,
    analysis: object,
    feature_design: object,
    api_design: object,
    database_design: object,
) -> str:
    """설계 결과를 구현 가능한 계획과 운영 체크리스트로 보강합니다."""
    return f"""
Design only the implementation and operational planning sections for this service.

Service idea:
{idea.strip()}

Idea analysis JSON:
{_dump_context(analysis)}

Feature design JSON:
{_dump_context(feature_design)}

API design JSON:
{_dump_context(api_design)}

Database design JSON:
{_dump_context(database_design)}

Return 3 to 6 non-functional requirements, 3 to 6 security considerations, and 3 to 6 ordered implementation steps.
Make every item specific to this service and avoid generic advice.
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
Also update non_functional_requirements, security_considerations, and implementation_plan when the revision changes scope, user roles, data sensitivity, or operational risk.
Do not mention that this is a revision in the overview unless it helps explain the service.
"""


def _dump_context(value: object) -> str:
    """다른 생성 단계의 Pydantic 결과를 다음 프롬프트에서 읽기 쉬운 JSON으로 전달합니다."""
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json(indent=2)
    return str(value)
