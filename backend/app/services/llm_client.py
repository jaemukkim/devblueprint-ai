from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.schemas.blueprint import BlueprintResponse
from app.services.prompts import SYSTEM_PROMPT


class BlueprintGenerationError(RuntimeError):
    """설계도 생성 과정에서 복구 가능한 형태로 처리할 오류입니다."""


def request_blueprint_from_openai(
    user_prompt: str,
    validation_feedback: list[str] | None = None,
) -> BlueprintResponse:
    """OpenAI Responses API를 호출해 Pydantic 모델 형태의 설계도를 받습니다."""
    if not settings.openai_api_key:
        raise BlueprintGenerationError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = append_validation_feedback(user_prompt, validation_feedback)

    try:
        # OpenAI Python SDK의 structured output helper를 사용합니다.
        # BlueprintResponse를 text_format으로 넘기면 응답이 해당 Pydantic 모델로 파싱됩니다.
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text_format=BlueprintResponse,
        )
    except OpenAIError as exc:
        raise BlueprintGenerationError("OpenAI API 호출 중 오류가 발생했습니다.") from exc

    if response.output_parsed is None:
        raise BlueprintGenerationError("OpenAI 응답을 BlueprintResponse 형식으로 파싱하지 못했습니다.")

    return response.output_parsed


def append_validation_feedback(user_prompt: str, validation_feedback: list[str] | None) -> str:
    """이전 생성 결과가 품질 검증에 실패했을 때 재생성 지시를 프롬프트에 추가합니다."""
    if not validation_feedback:
        return user_prompt

    feedback_lines = "\n".join(f"- {error}" for error in validation_feedback)
    return f"""
{user_prompt}

The previous blueprint failed validation.
Regenerate the entire blueprint and fix every issue below:
{feedback_lines}
"""
