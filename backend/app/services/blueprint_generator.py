from copy import deepcopy

from app.core.config import settings
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
from app.services.blueprint_validator import validate_blueprint_quality
from app.services.llm_client import request_blueprint_from_openai
from app.services.prompts import build_blueprint_prompt


# 같은 idea를 반복 생성할 때 OpenAI 토큰을 다시 쓰지 않기 위한 간단한 in-memory cache입니다.
# 서버를 재시작하면 비워지므로, 장기 저장이 필요해지면 DB나 파일 캐시로 교체하면 됩니다.
_BLUEPRINT_CACHE: dict[str, BlueprintResponse] = {}


def generate_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """서비스 아이디어를 받아 시스템 설계도 응답을 생성합니다."""
    cache_key = build_cache_key(payload.idea)

    if cache_key in _BLUEPRINT_CACHE:
        # 캐시된 Pydantic 모델을 그대로 반환하면 이후 코드가 객체를 수정할 때 캐시도 오염될 수 있습니다.
        return deepcopy(_BLUEPRINT_CACHE[cache_key])

    # USE_OPENAI=false이면 API key가 있더라도 실제 OpenAI 호출을 하지 않습니다.
    # 개발 중 화면 확인이나 반복 테스트를 할 때 토큰 비용을 막기 위한 안전장치입니다.
    if not settings.use_openai:
        blueprint = build_placeholder_blueprint(payload)
    else:
        user_prompt = build_blueprint_prompt(payload)
        blueprint = request_blueprint_from_openai(user_prompt)

    validate_blueprint_quality(blueprint)
    _BLUEPRINT_CACHE[cache_key] = deepcopy(blueprint)
    return blueprint


def normalize_idea(idea: str) -> str:
    """같은 의미의 반복 입력을 최대한 같은 cache key로 묶기 위해 공백을 정리합니다."""
    return " ".join(idea.strip().split()).lower()


def build_cache_key(idea: str) -> str:
    """OpenAI 사용 여부와 모델이 다른 결과가 같은 캐시에 섞이지 않도록 cache key를 만듭니다."""
    source = "openai" if settings.use_openai else "placeholder"
    return f"{source}:{settings.openai_model}:{normalize_idea(idea)}"


def build_placeholder_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """OpenAI 연동 없이도 API와 화면을 검증할 수 있는 예시 응답을 생성합니다."""
    idea = payload.idea.strip()

    return BlueprintResponse(
        overview=f"'{idea}'에 대한 초기 시스템 설계도입니다.",
        features=[
            Feature(
                name="아이디어 분석",
                description="사용자가 입력한 서비스 아이디어를 분석하고 핵심 요구사항을 추출합니다.",
                priority="high",
            ),
            Feature(
                name="설계도 생성",
                description="분석 결과를 바탕으로 구현에 참고할 수 있는 구조화된 설계도를 생성합니다.",
                priority="high",
            ),
            Feature(
                name="결과 시각화",
                description="생성된 기능, API, DB 설계, 시퀀스 다이어그램을 화면에서 읽기 쉽게 보여줍니다.",
                priority="medium",
            ),
        ],
        tech_stack=TechStack(
            backend=["Python", "FastAPI", "Pydantic"],
            frontend=["Streamlit"],
            database=[],
            ai=["OpenAI API"],
            rationale="초기 MVP는 저장 기능 없이 단순한 요청/응답 흐름과 structured output 검증에 집중합니다.",
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
            )
        ],
        database_schema=[
            DatabaseTable(
                name="future_blueprints",
                description="생성된 설계도를 저장하는 기능을 추가할 때 사용할 수 있는 미래 확장용 테이블입니다.",
                columns=[
                    DatabaseColumn(
                        name="id",
                        type="uuid",
                        description="설계도 고유 식별자입니다.",
                        constraints=["primary_key"],
                    ),
                    DatabaseColumn(
                        name="idea",
                        type="text",
                        description="사용자가 입력한 원본 서비스 아이디어입니다.",
                        constraints=["not_null"],
                    ),
                    DatabaseColumn(
                        name="result",
                        type="jsonb",
                        description="생성된 설계도 JSON 결과입니다.",
                        constraints=["not_null"],
                    ),
                ],
            )
        ],
        sequence_diagram=(
            "sequenceDiagram\n"
            "  participant User as 사용자\n"
            "  participant UI as Streamlit 화면\n"
            "  participant API as FastAPI 서버\n"
            "  participant LLM as OpenAI API\n"
            "  User->>UI: 서비스 아이디어 입력\n"
            "  UI->>API: POST /api/v1/blueprint/generate\n"
            "  API->>LLM: 구조화된 설계도 요청\n"
            "  LLM-->>API: JSON 설계도 반환\n"
            "  API-->>UI: 설계도 응답 반환\n"
            "  UI-->>User: 결과 화면 표시\n"
        ),
    )
