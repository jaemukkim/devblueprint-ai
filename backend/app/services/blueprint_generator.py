from app.core.config import settings
from app.repositories.blueprint_repository import blueprint_repository
from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    BlueprintRequest,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseTable,
    Feature,
    TechStack,
)
from app.services.blueprint_validator import collect_blueprint_quality_errors, validate_blueprint_quality
from app.services.llm_client import BlueprintGenerationError, request_blueprint_from_openai
from app.services.prompts import build_blueprint_prompt


MAX_OPENAI_GENERATION_ATTEMPTS = 3


def generate_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """서비스 아이디어를 받아 시스템 설계도 응답을 생성합니다."""
    cache_key = build_cache_key(payload.idea)

    cached_blueprint = blueprint_repository.get(cache_key)
    if cached_blueprint is not None:
        return cached_blueprint

    # USE_OPENAI=false이면 API key가 있더라도 실제 OpenAI 호출을 하지 않습니다.
    # 개발 중 화면 확인이나 반복 테스트를 할 때 토큰 비용을 막기 위한 안전장치입니다.
    if not settings.use_openai:
        blueprint = build_placeholder_blueprint(payload)
    else:
        user_prompt = build_blueprint_prompt(payload)
        blueprint = generate_blueprint_with_retry(user_prompt)

    validate_blueprint_quality(blueprint)
    blueprint_repository.save(cache_key, blueprint, idea=payload.idea.strip())
    return blueprint


def generate_blueprint_with_retry(user_prompt: str) -> BlueprintResponse:
    """품질 검증에 실패한 OpenAI 결과를 feedback과 함께 재생성합니다."""
    validation_feedback: list[str] | None = None
    last_errors: list[str] = []

    for _ in range(MAX_OPENAI_GENERATION_ATTEMPTS):
        blueprint = request_blueprint_from_openai(user_prompt, validation_feedback)
        errors = collect_blueprint_quality_errors(blueprint)

        if not errors:
            return blueprint

        last_errors = errors
        validation_feedback = errors

    joined_errors = "; ".join(last_errors)
    raise BlueprintGenerationError(f"설계도 품질 검증 재시도에 실패했습니다: {joined_errors}")


def normalize_idea(idea: str) -> str:
    """같은 의미의 반복 입력을 최대한 같은 cache key로 묶기 위해 공백을 정리합니다."""
    return " ".join(idea.strip().split()).lower()


def build_cache_key(idea: str) -> str:
    """OpenAI 사용 여부와 모델이 다른 결과가 같은 캐시에 섞이지 않도록 cache key를 만듭니다."""
    source = "openai" if settings.use_openai else "placeholder"
    return f"{source}:{settings.openai_model}:{normalize_idea(idea)}"


def build_placeholder_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """OpenAI 연동 없이도 API와 화면을 검증할 수 있는 충분한 예시 응답을 생성합니다."""
    idea = payload.idea.strip()

    return BlueprintResponse(
        overview=f"'{idea}'에 대한 MVP 중심 시스템 설계도입니다.",
        features=[
            Feature(
                name="아이디어 분석",
                description="사용자가 입력한 서비스 아이디어를 분석하고 핵심 요구사항을 추출합니다.",
                priority="high",
            ),
            Feature(
                name="기능 요구사항 정리",
                description="MVP에서 먼저 구현할 기능과 이후 확장할 기능을 구분합니다.",
                priority="high",
            ),
            Feature(
                name="API 설계 생성",
                description="FastAPI로 구현할 수 있는 REST API 초안을 생성합니다.",
                priority="high",
            ),
            Feature(
                name="데이터 모델 제안",
                description="초기 저장이 필요하지 않아도 향후 확장 가능한 DB schema를 제안합니다.",
                priority="medium",
            ),
            Feature(
                name="시퀀스 다이어그램 생성",
                description="주요 사용자 흐름을 Mermaid sequenceDiagram으로 표현합니다.",
                priority="medium",
            ),
            Feature(
                name="결과 다운로드",
                description="생성된 설계도를 Markdown 문서로 내려받을 수 있게 합니다.",
                priority="low",
            ),
        ],
        tech_stack=TechStack(
            backend=["Python", "FastAPI", "Pydantic"],
            frontend=["Streamlit"],
            database=["PostgreSQL"],
            ai=["OpenAI API"],
            rationale="FastAPI와 Pydantic은 structured output 검증에 적합하고, Streamlit은 MVP 화면을 빠르게 검증하기 좋습니다. PostgreSQL은 생성 결과 저장과 이력 관리가 필요해질 때 자연스럽게 확장할 수 있습니다.",
        ),
        api_spec=[
            ApiSpec(
                method="POST",
                path="/api/v1/blueprint/generate",
                description="자연어 서비스 아이디어를 받아 시스템 설계도를 생성합니다.",
                request=[
                    ApiField(
                        name="idea",
                        type="string",
                        description="사용자가 만들고 싶은 서비스 아이디어입니다.",
                        required=True,
                    )
                ],
                response=[
                    ApiField(
                        name="overview",
                        type="string",
                        description="생성된 시스템 설계도의 요약입니다.",
                        required=True,
                    ),
                    ApiField(
                        name="features",
                        type="array",
                        description="핵심 기능 목록입니다.",
                        required=True,
                    ),
                ],
            ),
            ApiSpec(
                method="GET",
                path="/api/v1/blueprint/examples",
                description="사용자가 빠르게 테스트할 수 있는 샘플 아이디어 목록을 반환합니다.",
                request=[],
                response=[
                    ApiField(
                        name="examples",
                        type="array",
                        description="샘플 서비스 아이디어 목록입니다.",
                        required=True,
                    )
                ],
            ),
            ApiSpec(
                method="GET",
                path="/api/v1/blueprint/{blueprint_id}",
                description="저장 기능을 추가했을 때 특정 설계도 결과를 조회합니다.",
                request=[
                    ApiField(
                        name="blueprint_id",
                        type="string",
                        description="조회할 설계도 ID입니다.",
                        required=True,
                    )
                ],
                response=[
                    ApiField(
                        name="blueprint",
                        type="object",
                        description="저장된 설계도 결과입니다.",
                        required=True,
                    )
                ],
            ),
            ApiSpec(
                method="GET",
                path="/api/v1/blueprints",
                description="저장 기능을 추가했을 때 최근 생성된 설계도 목록을 조회합니다.",
                request=[],
                response=[
                    ApiField(
                        name="items",
                        type="array",
                        description="최근 생성된 설계도 목록입니다.",
                        required=True,
                    )
                ],
            ),
        ],
        database_schema=[
            DatabaseTable(
                name="blueprints",
                description="사용자가 생성한 설계도 결과를 저장하는 중심 테이블입니다.",
                columns=[
                    DatabaseColumn(name="id", type="uuid", description="설계도 고유 식별자입니다.", constraints=["primary_key"]),
                    DatabaseColumn(name="idea", type="text", description="사용자가 입력한 원본 서비스 아이디어입니다.", constraints=["not_null"]),
                    DatabaseColumn(name="result", type="jsonb", description="생성된 설계도 JSON 결과입니다.", constraints=["not_null"]),
                    DatabaseColumn(name="created_at", type="timestamp", description="설계도 생성 시각입니다.", constraints=["not_null"]),
                ],
            ),
            DatabaseTable(
                name="blueprint_features",
                description="설계도에 포함된 핵심 기능을 검색하거나 비교하기 위해 분리 저장하는 테이블입니다.",
                columns=[
                    DatabaseColumn(name="id", type="uuid", description="기능 항목 고유 식별자입니다.", constraints=["primary_key"]),
                    DatabaseColumn(name="blueprint_id", type="uuid", description="blueprints 테이블 참조 ID입니다.", constraints=["not_null", "foreign_key"]),
                    DatabaseColumn(name="name", type="varchar", description="기능 이름입니다.", constraints=["not_null"]),
                    DatabaseColumn(name="priority", type="varchar", description="기능 우선순위입니다.", constraints=["not_null"]),
                ],
            ),
            DatabaseTable(
                name="blueprint_api_specs",
                description="생성된 API 설계 항목을 endpoint 단위로 저장하는 테이블입니다.",
                columns=[
                    DatabaseColumn(name="id", type="uuid", description="API 설계 항목 고유 식별자입니다.", constraints=["primary_key"]),
                    DatabaseColumn(name="blueprint_id", type="uuid", description="blueprints 테이블 참조 ID입니다.", constraints=["not_null", "foreign_key"]),
                    DatabaseColumn(name="method", type="varchar", description="HTTP method입니다.", constraints=["not_null"]),
                    DatabaseColumn(name="path", type="varchar", description="API endpoint path입니다.", constraints=["not_null"]),
                ],
            ),
        ],
        database_erd=(
            "erDiagram\n"
            "  blueprints ||--o{ blueprint_features : contains\n"
            "  blueprints ||--o{ blueprint_api_specs : contains\n"
            "  blueprints {\n"
            "    uuid id PK\n"
            "    text idea\n"
            "    jsonb result\n"
            "    timestamp created_at\n"
            "  }\n"
            "  blueprint_features {\n"
            "    uuid id PK\n"
            "    uuid blueprint_id FK\n"
            "    varchar name\n"
            "    varchar priority\n"
            "  }\n"
            "  blueprint_api_specs {\n"
            "    uuid id PK\n"
            "    uuid blueprint_id FK\n"
            "    varchar method\n"
            "    varchar path\n"
            "  }\n"
        ),
        sequence_diagram=(
            "sequenceDiagram\n"
            "  participant User as 사용자\n"
            "  participant UI as Streamlit 화면\n"
            "  participant API as FastAPI 서버\n"
            "  participant Store as Blueprint Repository\n"
            "  participant LLM as OpenAI API\n"
            "  User->>UI: 서비스 아이디어 입력\n"
            "  UI->>API: POST /api/v1/blueprint/generate\n"
            "  API->>Store: 같은 idea 결과 확인\n"
            "  alt cached result exists\n"
            "    Store-->>API: 저장된 설계도 반환\n"
            "  else cache miss\n"
            "    API->>LLM: 구조화된 설계도 요청\n"
            "    LLM-->>API: JSON 설계도 반환\n"
            "    API->>Store: 결과 저장\n"
            "  end\n"
            "  API-->>UI: 설계도 응답 반환\n"
            "  UI-->>User: 결과 화면 표시\n"
        ),
    )
