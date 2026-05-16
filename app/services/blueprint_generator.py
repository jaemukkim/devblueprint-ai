from app.schemas.blueprint import (
    ApiSpec,
    BlueprintRequest,
    BlueprintResponse,
    DatabaseTable,
    Feature,
    TechStack,
)


def generate_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """OpenAI 연동 전까지 사용할 고정된 예시 응답을 생성합니다."""
    # 앞뒤 공백을 제거해 같은 아이디어가 불필요하게 다른 입력처럼 처리되지 않게 합니다.
    idea = payload.idea.strip()

    # 지금은 LLM 호출 대신 예측 가능한 응답을 반환합니다.
    # 이 덕분에 API와 프론트엔드 화면을 먼저 안정적으로 개발할 수 있습니다.
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
        ],
        tech_stack=TechStack(
            backend=["Python", "FastAPI", "Pydantic"],
            frontend=["Streamlit"],
            database=[],
            ai=["OpenAI API"],
            rationale="초기 MVP는 저장 기능 없이 단순한 요청/응답 흐름에 집중합니다.",
        ),
        api_spec=[
            ApiSpec(
                method="POST",
                path="/api/v1/blueprint/generate",
                description="자연어 서비스 아이디어를 받아 시스템 설계도를 생성합니다.",
                request={"idea": "string"},
                response={"overview": "string", "features": "array"},
            )
        ],
        database_schema=[
            DatabaseTable(
                name="future_blueprints",
                description="생성된 설계도를 저장하는 기능을 추가할 때 사용할 수 있는 미래 확장용 테이블입니다.",
                columns=[
                    {"name": "id", "type": "uuid", "constraints": ["primary_key"]},
                    {"name": "idea", "type": "text", "constraints": ["not_null"]},
                    {"name": "result", "type": "jsonb", "constraints": ["not_null"]},
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
