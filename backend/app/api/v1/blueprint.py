from fastapi import APIRouter, HTTPException, Response, status

from app.repositories.blueprint_repository import StoredBlueprint, StoredBlueprintRunEvent, blueprint_repository
from app.schemas.blueprint import (
    BlueprintListResponse,
    BlueprintRequest,
    BlueprintRevisionRequest,
    BlueprintRunEventListResponse,
    BlueprintRunEventResponse,
    BlueprintResponse,
    BlueprintSectionApplyRequest,
    BlueprintSectionRegenerationRequest,
    BlueprintSectionRegenerationResponse,
    BlueprintSummary,
    StoredBlueprintResponse,
)
from app.services.llm_client import BlueprintGenerationError
from app.services.blueprint_generator import (
    DuplicateBlueprintRevisionError,
    apply_blueprint_section_preview,
    flush_blueprint_run_events,
    generate_blueprint,
    normalize_section_name,
    regenerate_blueprint_section,
    reset_blueprint_run,
    revise_blueprint,
    start_blueprint_run,
)


router = APIRouter(prefix="/blueprint", tags=["blueprint"])
blueprints_router = APIRouter(prefix="/blueprints", tags=["blueprint"])


@router.post("/generate", response_model=BlueprintResponse)
def create_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    try:
        return generate_blueprint(payload)
    except BlueprintGenerationError as exc:
        # LLM 연동 오류는 클라이언트 입력 문제가 아닐 수 있으므로 503으로 응답합니다.
        raise build_generation_http_error(exc) from exc


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
        raise build_not_found_error("저장된 설계도를 찾을 수 없습니다.")

    return StoredBlueprintResponse(
        id=stored_blueprint.id,
        idea=stored_blueprint.idea,
        revision_instruction=stored_blueprint.revision_instruction,
        created_at=stored_blueprint.created_at,
        result=stored_blueprint.result,
    )


@blueprints_router.get("/{blueprint_id}/runs", response_model=BlueprintRunEventListResponse)
def list_blueprint_run_events(blueprint_id: str) -> BlueprintRunEventListResponse:
    stored_blueprint = blueprint_repository.get_by_id(blueprint_id)

    if stored_blueprint is None:
        raise build_not_found_error("실행 이력을 조회할 설계도를 찾을 수 없습니다.")

    run_events = blueprint_repository.list_run_events(blueprint_id)
    return BlueprintRunEventListResponse(
        items=[to_blueprint_run_event_response(run_event) for run_event in run_events]
    )


@blueprints_router.post("/{blueprint_id}/revise", response_model=StoredBlueprintResponse)
def revise_stored_blueprint(blueprint_id: str, payload: BlueprintRevisionRequest) -> StoredBlueprintResponse:
    stored_blueprint = blueprint_repository.get_by_id(blueprint_id)

    if stored_blueprint is None:
        raise build_not_found_error("수정할 설계도를 찾을 수 없습니다.")

    try:
        revised_blueprint = revise_blueprint(
            stored_blueprint.idea,
            stored_blueprint.result,
            payload.instruction,
        )
    except DuplicateBlueprintRevisionError as exc:
        raise build_conflict_error(str(exc), "duplicate_revision") from exc
    except BlueprintGenerationError as exc:
        # 수정 요청도 LLM 생성과 검증 과정을 거치므로 생성 실패와 같은 방식으로 안내합니다.
        raise build_generation_http_error(exc) from exc

    return StoredBlueprintResponse(
        id=revised_blueprint.id,
        idea=revised_blueprint.idea,
        revision_instruction=revised_blueprint.revision_instruction,
        created_at=revised_blueprint.created_at,
        result=revised_blueprint.result,
    )


@blueprints_router.post(
    "/{blueprint_id}/sections/{section}/regenerate",
    response_model=BlueprintSectionRegenerationResponse,
)
def regenerate_stored_blueprint_section(
    blueprint_id: str,
    section: str,
    payload: BlueprintSectionRegenerationRequest | None = None,
) -> BlueprintSectionRegenerationResponse:
    stored_blueprint = blueprint_repository.get_by_id(blueprint_id)

    if stored_blueprint is None:
        raise build_not_found_error("재생성할 설계도를 찾을 수 없습니다.")

    normalized_section = normalize_section_name(section)
    run_token = start_blueprint_run("section_regeneration", normalized_section)
    try:
        regenerated_blueprint = regenerate_blueprint_section(
            stored_blueprint.idea,
            stored_blueprint.result,
            section,
            payload.instruction if payload else None,
        )
        flush_blueprint_run_events(stored_blueprint.id)
    except ValueError as exc:
        flush_blueprint_run_events(stored_blueprint.id)
        raise build_not_found_error(str(exc), "unsupported_section") from exc
    except BlueprintGenerationError as exc:
        # 부분 재생성도 전체 설계 품질 검증을 통과해야 preview로 사용할 수 있습니다.
        flush_blueprint_run_events(stored_blueprint.id)
        raise build_generation_http_error(exc) from exc
    finally:
        reset_blueprint_run(run_token)

    return BlueprintSectionRegenerationResponse(
        section=normalized_section,
        result=regenerated_blueprint,
    )


@blueprints_router.post(
    "/{blueprint_id}/sections/{section}/apply",
    response_model=StoredBlueprintResponse,
)
def apply_stored_blueprint_section_preview(
    blueprint_id: str,
    section: str,
    payload: BlueprintSectionApplyRequest,
) -> StoredBlueprintResponse:
    stored_blueprint = blueprint_repository.get_by_id(blueprint_id)

    if stored_blueprint is None:
        raise build_not_found_error("적용할 설계도를 찾을 수 없습니다.")

    try:
        applied_blueprint = apply_blueprint_section_preview(
            stored_blueprint.idea,
            section,
            payload.result,
            payload.instruction,
        )
    except ValueError as exc:
        raise build_not_found_error(str(exc), "unsupported_section") from exc
    except BlueprintGenerationError as exc:
        # 클라이언트가 보낸 미리보기라도 저장 전 전체 품질 검증을 다시 통과해야 합니다.
        raise build_generation_http_error(exc) from exc

    return StoredBlueprintResponse(
        id=applied_blueprint.id,
        idea=applied_blueprint.idea,
        revision_instruction=applied_blueprint.revision_instruction,
        created_at=applied_blueprint.created_at,
        result=applied_blueprint.result,
    )


@blueprints_router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blueprint(blueprint_id: str) -> Response:
    deleted = blueprint_repository.delete_by_id(blueprint_id)

    if not deleted:
        raise build_not_found_error("삭제할 설계도를 찾을 수 없습니다.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def to_blueprint_summary(stored_blueprint: StoredBlueprint) -> BlueprintSummary:
    """저장된 설계도 상세 정보에서 목록에 필요한 필드만 추립니다."""
    return BlueprintSummary(
        id=stored_blueprint.id,
        idea=stored_blueprint.idea,
        revision_instruction=stored_blueprint.revision_instruction,
        created_at=stored_blueprint.created_at,
    )


def to_blueprint_run_event_response(run_event: StoredBlueprintRunEvent) -> BlueprintRunEventResponse:
    """저장된 실행 이력을 API 응답 모델로 변환합니다."""
    return BlueprintRunEventResponse(
        id=run_event.id,
        blueprint_id=run_event.blueprint_id,
        run_type=run_event.run_type,
        section=run_event.section,
        node_name=run_event.node_name,
        specialist_id=run_event.specialist_id,
        phase=run_event.phase,
        retry_count=run_event.retry_count,
        route=run_event.route,
        error_count=run_event.error_count,
        error_messages=run_event.error_messages,
        duration_ms=run_event.duration_ms,
        created_at=run_event.created_at,
    )


# 프론트가 문자열 파싱 없이 오류 유형과 조치 문구를 구분할 수 있도록 표준 detail 구조를 만듭니다.
def build_error_detail(message: str, error_code: str, hint: str, extra: dict | None = None) -> dict:
    return {
        "message": message,
        "error_code": error_code,
        "hint": hint,
        "extra": extra,
    }


# 생성 계열 오류 메시지를 원인별 코드로 나누어 API 응답에 담습니다.
def classify_generation_error(message: str) -> tuple[str, str]:
    if "OPENAI_API_KEY" in message:
        return "openai_api_key_missing", "backend .env의 OPENAI_API_KEY 값을 확인해 주세요."
    if "status=401" in message:
        return "openai_auth_failed", "OPENAI_API_KEY가 유효한지 확인해 주세요."
    if "status=403" in message:
        return "openai_permission_denied", "현재 API key가 요청한 모델이나 기능을 사용할 권한이 있는지 확인해 주세요."
    if "status=404" in message:
        return "openai_model_not_found", "OPENAI_MODEL 값이 실제 사용 가능한 모델명인지 확인해 주세요."
    if "status=429" in message:
        return "openai_rate_limited", "OpenAI 사용량 한도, 결제 상태, rate limit을 확인한 뒤 다시 시도해 주세요."
    if "OpenAI API 호출" in message:
        return "openai_call_failed", "API key, 모델 권한, 네트워크, 프록시 설정을 확인해 주세요."
    if "파싱" in message:
        return "openai_parse_failed", "OpenAI 응답 형식이 예상한 JSON 구조와 맞지 않습니다. 다시 생성해 보세요."
    if "품질 검증" in message:
        return "blueprint_validation_failed", "생성 결과가 품질 기준을 통과하지 못했습니다. 같은 요청을 다시 시도하거나 아이디어를 더 구체화해 주세요."
    return "blueprint_generation_failed", "생성 중 복구 가능한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."


# BlueprintGenerationError를 표준 503 HTTPException 객체로 변환합니다.
def build_generation_http_error(exc: BlueprintGenerationError) -> HTTPException:
    message = str(exc)
    error_code, hint = classify_generation_error(message)
    return HTTPException(
        status_code=503,
        detail=build_error_detail(message, error_code, hint),
    )


# 없는 설계도나 지원하지 않는 섹션에 대해 표준 404 응답 객체를 만듭니다.
def build_not_found_error(message: str, error_code: str = "blueprint_not_found") -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=build_error_detail(message, error_code, "요청한 설계도 ID나 섹션 이름을 다시 확인해 주세요."),
    )


# 중복 수정 요청처럼 사용자가 바로 조정할 수 있는 충돌 응답 객체를 만듭니다.
def build_conflict_error(message: str, error_code: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=build_error_detail(message, error_code, "이미 반영된 요청이면 다른 변경 내용을 입력해 주세요."),
    )
