from app.schemas.blueprint import BlueprintRequest


# 시스템 프롬프트는 모델의 역할과 출력 품질 기준을 고정합니다.
# 실제 출력 형식은 Pydantic structured output이 강제하므로, 여기서는 판단 기준에 집중합니다.
SYSTEM_PROMPT = """
You are a senior backend architect helping a developer turn a service idea into an implementation-ready system blueprint.

Follow these rules:
- Keep the MVP small and realistic.
- Prefer FastAPI, Streamlit, Pydantic, and OpenAI API unless the user's idea clearly needs something else.
- Do not include authentication, payment, Kubernetes, microservices, or complex infrastructure unless required by the idea.
- Write user-facing descriptions in Korean.
- Keep technical identifiers, API paths, HTTP methods, JSON types, database types, and constraints in English.
- Return a valid Mermaid sequence diagram in sequenceDiagram format.
"""


def build_blueprint_prompt(payload: BlueprintRequest) -> str:
    """사용자의 아이디어를 LLM에게 전달할 프롬프트로 변환합니다."""
    return f"""
Create a developer-ready system blueprint for the following service idea.

Service idea:
{payload.idea.strip()}

The output should be practical enough for a developer to start implementing the MVP.
"""
