from __future__ import annotations


SECTION_FEEDBACK_PREFIX = {
    "features": "기능 섹션",
    "api": "API 섹션",
    "database": "DB 섹션",
    "diagrams": "다이어그램 섹션",
    "planning": "계획 섹션",
}


def build_quality_feedback(errors: list[str], section: str | None = None) -> list[str]:
    """validator 오류를 LLM이 수정 방향으로 바로 이해할 수 있는 피드백으로 바꿉니다."""
    return [build_single_quality_feedback(error, section) for error in errors]


def build_single_quality_feedback(error: str, section: str | None = None) -> str:
    """원본 오류 한 줄을 섹션 맥락이 담긴 재생성 지시로 변환합니다."""
    prefix = SECTION_FEEDBACK_PREFIX.get(section or "", "설계도")

    if error.startswith("features must contain at least"):
        return f"{prefix}: 기능은 5~8개의 구체적인 MVP 기능으로 작성하고, 각 기능은 사용자 행동이나 백엔드 책임을 설명해야 합니다."
    if error.startswith("features must contain at most"):
        return f"{prefix}: 기능 수를 8개 이하로 줄이고 MVP 우선순위가 낮은 항목은 합쳐 주세요."
    if error.startswith("feature name is too generic"):
        return f"{prefix}: 기능 이름을 서비스 도메인이 드러나는 구체적인 이름으로 바꿔 주세요. 원본 오류: {error}"
    if error.startswith("feature description is too short"):
        return f"{prefix}: 기능 설명은 구현자가 이해할 수 있게 사용자 행동, 데이터, 처리 책임을 포함해 충분히 구체화해 주세요. 원본 오류: {error}"

    if error.startswith("api_spec must contain at least"):
        return f"{prefix}: API는 4~8개의 도메인 리소스 기반 REST endpoint를 포함해야 합니다."
    if error.startswith("api_spec must contain at most"):
        return f"{prefix}: API endpoint 수를 줄이고 중복되거나 MVP 범위를 벗어난 endpoint는 제거해 주세요."
    if error.startswith("api path must start with"):
        return f"{prefix}: 모든 API path는 '/'로 시작하는 REST path여야 합니다. 예: /api/v1/books"
    if error.startswith("api path must not contain spaces"):
        return f"{prefix}: API path에는 공백을 넣지 말고 lowercase kebab-case 또는 path parameter를 사용해 주세요. 원본 오류: {error}"
    if error.startswith("api endpoint must be unique"):
        return f"{prefix}: 같은 HTTP method와 path 조합을 반복하지 말고 endpoint마다 고유한 책임을 부여해 주세요. 원본 오류: {error}"
    if error.startswith("api path is too generic"):
        return f"{prefix}: /items, /records 같은 일반 리소스 대신 서비스 도메인을 드러내는 리소스명을 사용해 주세요. 원본 오류: {error}"
    if error.startswith("api response fields must not be empty"):
        return f"{prefix}: 각 API response에는 id, status, timestamp, 주요 도메인 필드 등 프론트엔드가 사용할 필드를 포함해 주세요. 원본 오류: {error}"
    if error.startswith("api field name must not be empty") or error.startswith("api field type must not be empty"):
        return f"{prefix}: 모든 API request/response field에는 구현 가능한 name과 type을 채워 주세요. 원본 오류: {error}"
    if error.startswith("api fields must overlap database columns"):
        return f"{prefix}: API request/response 필드가 관련 DB 컬럼과 의미 있게 연결되도록 이름과 데이터 모델을 맞춰 주세요. 원본 오류: {error}"

    if error.startswith("database_schema must contain at least"):
        return f"{prefix}: DB schema는 MVP 데이터를 저장할 3~6개의 PostgreSQL 친화적 테이블을 포함해야 합니다."
    if error.startswith("database_schema must contain at most"):
        return f"{prefix}: DB table 수를 줄이고 작은 lookup table은 owning table의 status/type 컬럼으로 합쳐 주세요."
    if error.startswith("table name must be snake_case") or error.startswith("column name must be snake_case"):
        return f"{prefix}: 모든 table과 column 이름은 snake_case English identifier로 작성해 주세요. 원본 오류: {error}"
    if error.startswith("table must include a primary_key column"):
        return f"{prefix}: 모든 table에는 id 같은 primary_key 컬럼을 포함해 주세요. 원본 오류: {error}"
    if error.startswith("table must include at least"):
        return f"{prefix}: 각 table은 최소 3개 컬럼을 가져야 하며 id, 도메인 필드, created_at/status 같은 구현 필드를 포함해 주세요. 원본 오류: {error}"
    if error.startswith("api resource must be represented in database_schema"):
        return f"{prefix}: DB schema가 API 리소스를 저장하거나 조회할 수 있도록 관련 table을 추가하거나 table 이름을 맞춰 주세요. 원본 오류: {error}"

    if error.startswith("database_erd must start with"):
        return f"{prefix}: database_erd는 반드시 Mermaid erDiagram으로 시작해야 합니다."
    if error.startswith("database_erd must include table"):
        return f"{prefix}: ERD에는 database_schema의 모든 table이 포함되어야 합니다. 원본 오류: {error}"
    if "Mermaid key token 'UK'" in error:
        return f"{prefix}: Mermaid ERD의 unique key token은 UNIQUE가 아니라 UK로 표기해 주세요."
    if error.startswith("sequence_diagram must start with"):
        return f"{prefix}: sequence_diagram은 반드시 Mermaid sequenceDiagram으로 시작해야 합니다."
    if error.startswith("sequence_diagram must reference"):
        return f"{prefix}: sequenceDiagram에는 실제 API resource나 주요 backend 처리 흐름을 명시해 주세요."

    if error.startswith("non_functional_requirements must contain at least"):
        return f"{prefix}: 비기능 요구사항은 3~6개로 작성하고 이 서비스의 성능, 신뢰성, 관측성, 확장성 제약을 구체화해 주세요."
    if error.startswith("security_considerations must contain at least"):
        return f"{prefix}: 보안 고려사항은 3~6개로 작성하고 인증, 권한, 검증, 개인정보, abuse prevention 중 관련 항목을 포함해 주세요."
    if error.startswith("implementation_plan must contain at least"):
        return f"{prefix}: 구현 계획은 3~6개의 순서 있는 단계로 작성하고 backend/API, DB, UI, 검증, 운영 준비 흐름을 포함해 주세요."
    if "title is too short" in error or "description is too short" in error:
        return f"{prefix}: 계획/운영/보안 항목은 제목과 설명을 구현자가 실행할 수 있을 만큼 구체적으로 작성해 주세요. 원본 오류: {error}"
    if error.startswith("implementation_plan phase must not be empty"):
        return f"{prefix}: 각 구현 계획 단계에는 phase 값을 채워 순서를 알 수 있게 해 주세요. 원본 오류: {error}"
    if error.startswith("implementation_plan must reference"):
        return f"{prefix}: 구현 계획이 생성된 기능, API, DB 개념을 직접 언급하도록 단계 설명을 구체화해 주세요."
    if error.startswith("security_considerations must cover"):
        return f"{prefix}: 서비스 범위에서 드러난 인증, 개인정보, 결제 같은 위험에 맞는 보안 대응을 추가해 주세요. 원본 오류: {error}"

    if "section must change during regeneration" in error:
        return f"{prefix}: 재생성 결과는 원본과 실질적으로 달라야 합니다. 기능명, endpoint, table, 다이어그램, 계획 중 해당 섹션의 핵심 내용을 개선해 주세요."
    if "features regeneration must add a new feature" in error:
        return f"{prefix}: 사용자가 기능 추가를 요청했으므로 기존 기능을 다시 쓰는 대신 새로운 구체적 기능을 목록에 추가해 주세요."

    return f"{prefix}: 다음 품질 오류를 수정해 주세요. 원본 오류: {error}"
