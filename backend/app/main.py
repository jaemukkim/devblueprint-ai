from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.blueprint import blueprints_router, router as blueprint_router
from app.core.config import settings


# FastAPI 애플리케이션의 시작점입니다.
# 이 객체를 Uvicorn이 읽어서 HTTP 서버로 실행합니다.
app = FastAPI(
    title="DevBlueprint AI",
    description="AI 기반 시스템 설계도 생성기입니다.",
    version="0.1.0",
)

# React/Vite 개발 서버와 Streamlit 화면에서 FastAPI를 호출할 수 있도록 CORS를 허용합니다.
# 운영 환경에서는 frontend_origins에 실제 배포 도메인만 넣는 방식으로 좁히면 됩니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 버전 관리를 위해 모든 v1 라우터는 /api/v1 아래에 묶습니다.
# 이후 v2가 필요해지면 기존 엔드포인트를 유지하면서 새 버전을 추가할 수 있습니다.
app.include_router(blueprint_router, prefix="/api/v1")
app.include_router(blueprints_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str | bool | dict[str, str | bool]]:
    # 배포 환경이나 로컬 개발 중 서버가 정상적으로 떠 있는지 확인하는 상태 점검용 엔드포인트입니다.
    # 민감한 API key 값은 노출하지 않고, 환경 설정 반영 여부만 확인할 수 있게 합니다.
    return {
        "status": "ok",
        "use_openai": settings.use_openai,
        "openai": build_openai_health(),
        "repository_backend": settings.repository_backend,
    }


def build_openai_health() -> dict[str, str | bool]:
    """OpenAI 호출 전 확인할 수 있는 설정 상태를 민감값 없이 요약합니다."""
    has_key = bool(settings.openai_api_key)

    if not settings.use_openai:
        status = "disabled"
        message = "USE_OPENAI=false라서 placeholder 응답을 사용합니다."
    elif not has_key:
        status = "missing_key"
        message = "USE_OPENAI=true지만 OPENAI_API_KEY가 설정되어 있지 않습니다."
    else:
        status = "configured"
        message = "OpenAI 호출 설정이 준비되어 있습니다. 실제 권한과 쿼터는 호출 시 확인됩니다."

    return {
        "status": status,
        "message": message,
        "model": settings.openai_model,
        "api_key_configured": has_key,
    }
