from fastapi import APIRouter, HTTPException

from app.schemas.blueprint import BlueprintRequest, BlueprintResponse
from app.services.llm_client import BlueprintGenerationError
from app.services.blueprint_generator import generate_blueprint


router = APIRouter(prefix="/blueprint", tags=["blueprint"])


@router.post("/generate", response_model=BlueprintResponse)
def create_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    try:
        return generate_blueprint(payload)
    except BlueprintGenerationError as exc:
        # LLM 연동 오류는 클라이언트 입력 문제가 아닐 수 있으므로 503으로 응답합니다.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
