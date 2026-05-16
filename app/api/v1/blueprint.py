from fastapi import APIRouter

from app.schemas.blueprint import BlueprintRequest, BlueprintResponse
from app.services.blueprint_generator import generate_blueprint


router = APIRouter(prefix="/blueprint", tags=["blueprint"])

@router.post("/generate", response_model=BlueprintResponse)
def create_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    return generate_blueprint(payload)
