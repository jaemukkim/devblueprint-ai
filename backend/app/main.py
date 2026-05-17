from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.blueprint import router as blueprint_router
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
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 버전 관리를 위해 모든 v1 라우터는 /api/v1 아래에 묶습니다.
# 이후 v2가 필요해지면 기존 엔드포인트를 유지하면서 새 버전을 추가할 수 있습니다.
app.include_router(blueprint_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    # 배포 환경이나 로컬 개발 중 서버가 정상적으로 떠 있는지 확인하는 상태 점검용 엔드포인트입니다.
    return {"status": "ok"}
