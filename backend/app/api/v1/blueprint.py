from fastapi import APIRouter, HTTPException, Response, status

from app.repositories.blueprint_repository import StoredBlueprint, blueprint_repository
from app.schemas.blueprint import (
    BlueprintListResponse,
    BlueprintRequest,
    BlueprintResponse,
    BlueprintSummary,
    StoredBlueprintResponse,
)
from app.services.llm_client import BlueprintGenerationError
from app.services.blueprint_generator import generate_blueprint


router = APIRouter(prefix="/blueprint", tags=["blueprint"])
blueprints_router = APIRouter(prefix="/blueprints", tags=["blueprint"])


@router.post("/generate", response_model=BlueprintResponse)
def create_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    try:
        return generate_blueprint(payload)
    except BlueprintGenerationError as exc:
        # LLM 연동 오류는 클라이언트 입력 문제가 아닐 수 있으므로 503으로 응답합니다.
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@blueprints_router.get("", response_model=BlueprintListResponse)
def list_blueprints() -> BlueprintListResponse:
    stored_blueprints = blueprint_repository.list_recent()
    return BlueprintListResponse(
        items=[to_blueprint_summary(stored_blueprint) for stored_blueprint in stored_blueprints]
    )


@blueprints_router.get("/{blueprint_id}", response_model=StoredBlueprintResponse)
def get_blueprint(blueprint_id: str) -> StoredBlueprintResponse:
    stored_blueprint = blueprint_repository.get_by_id(blueprint_id)

    if stored_blueprint is None:
        raise HTTPException(status_code=404, detail="저장된 설계도를 찾을 수 없습니다.")

    return StoredBlueprintResponse(
        id=stored_blueprint.id,
        idea=stored_blueprint.idea,
        created_at=stored_blueprint.created_at,
        result=stored_blueprint.result,
    )


@blueprints_router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blueprint(blueprint_id: str) -> Response:
    deleted = blueprint_repository.delete_by_id(blueprint_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="삭제할 설계도를 찾을 수 없습니다.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def to_blueprint_summary(stored_blueprint: StoredBlueprint) -> BlueprintSummary:
    """저장된 설계도 상세 정보에서 목록에 필요한 필드만 추립니다."""
    return BlueprintSummary(
        id=stored_blueprint.id,
        idea=stored_blueprint.idea,
        created_at=stored_blueprint.created_at,
    )
