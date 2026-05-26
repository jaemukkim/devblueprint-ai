from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

from app.core.config import settings
from app.repositories.blueprint_repository import StoredBlueprint, blueprint_repository
from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    ApiDesign,
    BlueprintRequest,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseDesign,
    DatabaseTable,
    DesignConsideration,
    DiagramDesign,
    Feature,
    FeatureDesign,
    IdeaAnalysis,
    ImplementationStep,
    PlanningDesign,
    TechStack,
)
from app.services.blueprint_validator import (
    collect_blueprint_quality_errors,
    collect_blueprint_section_quality_errors,
    validate_blueprint_quality,
)
from app.services.blueprint_normalizer import normalize_blueprint_output
from app.services.llm_client import (
    BlueprintGenerationError,
    request_blueprint_from_openai,
    request_structured_output_from_openai,
)
from app.services.prompts import (
    BLUEPRINT_PROMPT_VERSION,
    build_api_design_prompt,
    build_blueprint_revision_prompt,
    build_database_design_prompt,
    build_diagram_design_prompt,
    build_feature_design_prompt,
    build_idea_analysis_prompt,
    build_planning_design_prompt,
    build_section_regeneration_prompt,
)


MAX_OPENAI_GENERATION_ATTEMPTS = 3
MAX_OPENAI_PIPELINE_ATTEMPTS = 1
REGENERATABLE_SECTIONS = {"features", "api", "database", "diagrams", "planning"}
REVISION_MARKER = "수정:"
REVISION_STOPWORDS = {
    "같은",
    "기능",
    "추가",
    "추가해",
    "추가해줘",
    "수정",
    "변경",
    "반영",
    "해줘",
    "해주세요",
    "만들어",
    "만들어줘",
    "넣어줘",
}


class DuplicateBlueprintRevisionError(RuntimeError):
    """이미 반영된 수정 요청을 다시 생성하지 않도록 알려주는 예외입니다."""


def generate_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """서비스 아이디어를 받아 시스템 설계도 응답을 생성합니다."""
    cache_key = build_cache_key(payload.idea)

    cached_blueprint = blueprint_repository.get(cache_key)
    if cached_blueprint is not None:
        return cached_blueprint

    # USE_OPENAI=false이면 API key가 있어도 실제 OpenAI 호출을 하지 않습니다.
    # 개발 중 화면 확인이나 반복 테스트 시 불필요한 토큰 비용을 막기 위한 안전장치입니다.
    if not settings.use_openai:
        blueprint = build_placeholder_blueprint(payload)
    else:
        blueprint = generate_blueprint_pipeline_with_retry(payload)

    blueprint = normalize_blueprint_output(blueprint)
    validate_blueprint_quality(blueprint)
    blueprint_repository.save(cache_key, blueprint, idea=payload.idea.strip())
    return blueprint


def revise_blueprint(idea: str, current_blueprint: BlueprintResponse, instruction: str) -> StoredBlueprint:
    """기존 설계도와 사용자의 수정 요청을 바탕으로 검증 가능한 새 설계도를 생성합니다."""
    base_idea = strip_revision_suffix(idea)
    revision_instruction = instruction.strip()
    revision_cache_key = build_revision_cache_key(base_idea, revision_instruction)
    cached_revision = blueprint_repository.get_stored_by_key(revision_cache_key)

    if cached_revision is not None or is_instruction_already_reflected(current_blueprint, revision_instruction):
        raise DuplicateBlueprintRevisionError("이미 해당 수정 요청이 설계도에 반영되어 있습니다.")

    if not settings.use_openai:
        blueprint = build_placeholder_revision_blueprint(current_blueprint, revision_instruction)
    else:
        user_prompt = build_blueprint_revision_prompt(base_idea, current_blueprint, revision_instruction)
        blueprint = generate_blueprint_with_retry(user_prompt)

    blueprint = normalize_blueprint_output(blueprint)
    validate_blueprint_quality(blueprint)
    return blueprint_repository.save(
        revision_cache_key,
        blueprint,
        idea=base_idea,
        revision_instruction=revision_instruction,
    )


def regenerate_blueprint_section(
    idea: str,
    current_blueprint: BlueprintResponse,
    section: str,
    instruction: str | None = None,
) -> BlueprintResponse:
    """저장된 설계도를 덮어쓰지 않고 특정 섹션만 다시 생성한 미리보기 설계도를 반환합니다."""
    normalized_section = normalize_section_name(section)

    if normalized_section not in REGENERATABLE_SECTIONS:
        raise ValueError("지원하지 않는 설계도 섹션입니다.")

    if not settings.use_openai:
        blueprint = build_placeholder_section_regeneration(current_blueprint, normalized_section, instruction)
    else:
        blueprint = regenerate_blueprint_section_with_retry(
            idea,
            current_blueprint,
            normalized_section,
            instruction,
        )

    blueprint = normalize_blueprint_output(blueprint)
    section_errors = collect_blueprint_section_quality_errors(blueprint, normalized_section)
    if section_errors:
        joined_errors = "; ".join(section_errors)
        raise BlueprintGenerationError(f"섹션 재생성 품질 검증에 실패했습니다: {joined_errors}")
    return blueprint


def apply_blueprint_section_preview(
    idea: str,
    section: str,
    preview_blueprint: BlueprintResponse,
    instruction: str | None = None,
) -> StoredBlueprint:
    """섹션 재생성 미리보기를 검증한 뒤 원본을 덮어쓰지 않는 새 개선안으로 저장합니다."""
    normalized_section = normalize_section_name(section)

    if normalized_section not in REGENERATABLE_SECTIONS:
        raise ValueError("지원하지 않는 설계도 섹션입니다.")

    blueprint = normalize_blueprint_output(preview_blueprint)
    validate_blueprint_quality(blueprint)
    revision_instruction = build_section_apply_instruction(normalized_section, instruction)
    cache_key = build_section_apply_cache_key(idea, normalized_section, blueprint, instruction)
    return blueprint_repository.save(
        cache_key,
        blueprint,
        idea=strip_revision_suffix(idea),
        revision_instruction=revision_instruction,
    )


def regenerate_blueprint_section_with_retry(
    idea: str,
    current_blueprint: BlueprintResponse,
    section: str,
    instruction: str | None = None,
) -> BlueprintResponse:
    """부분 재생성 결과가 전체 설계 품질을 깨뜨리면 feedback과 함께 같은 섹션을 재시도합니다."""
    validation_feedback: list[str] | None = None
    last_errors: list[str] = []

    for _ in range(MAX_OPENAI_GENERATION_ATTEMPTS):
        blueprint = normalize_blueprint_output(
            regenerate_blueprint_section_once(idea, current_blueprint, section, instruction, validation_feedback)
        )
        errors = [
            *collect_blueprint_section_quality_errors(blueprint, section),
            *collect_section_regeneration_errors(current_blueprint, blueprint, section, instruction),
        ]

        if not errors:
            return blueprint

        last_errors = errors
        validation_feedback = errors

    joined_errors = "; ".join(last_errors)
    raise BlueprintGenerationError(f"섹션 재생성 품질 검증 재시도에 실패했습니다: {joined_errors}")


def regenerate_blueprint_section_once(
    idea: str,
    current_blueprint: BlueprintResponse,
    section: str,
    instruction: str | None,
    validation_feedback: list[str] | None = None,
) -> BlueprintResponse:
    """선택한 섹션의 structured output만 받아 기존 설계도에 합칩니다."""
    prompt = build_section_regeneration_prompt(idea, current_blueprint, section, instruction)
    blueprint = current_blueprint.model_copy(deep=True)

    if section == "features":
        feature_design = request_structured_output_from_openai(prompt, FeatureDesign, validation_feedback)
        blueprint.overview = feature_design.overview
        blueprint.features = feature_design.features
        blueprint.tech_stack = feature_design.tech_stack
        ensure_feature_instruction_is_visible(blueprint, instruction)
    elif section == "api":
        api_design = request_structured_output_from_openai(prompt, ApiDesign, validation_feedback)
        blueprint.api_spec = api_design.api_spec
    elif section == "database":
        database_design = request_structured_output_from_openai(prompt, DatabaseDesign, validation_feedback)
        blueprint.database_schema = database_design.database_schema
    elif section == "diagrams":
        diagram_design = request_structured_output_from_openai(prompt, DiagramDesign, validation_feedback)
        blueprint.database_erd = diagram_design.database_erd
        blueprint.sequence_diagram = diagram_design.sequence_diagram
    elif section == "planning":
        planning_design = request_structured_output_from_openai(prompt, PlanningDesign, validation_feedback)
        blueprint.non_functional_requirements = planning_design.non_functional_requirements
        blueprint.security_considerations = planning_design.security_considerations
        blueprint.implementation_plan = planning_design.implementation_plan

    return blueprint


def collect_section_regeneration_errors(
    current_blueprint: BlueprintResponse,
    regenerated_blueprint: BlueprintResponse,
    section: str,
    instruction: str | None = None,
) -> list[str]:
    """부분 재생성 결과가 선택 섹션을 실제로 바꿨는지 확인합니다."""
    errors: list[str] = []

    if get_section_fingerprint(current_blueprint, section) == get_section_fingerprint(regenerated_blueprint, section):
        errors.append(f"{section} section must change during regeneration")

    if section == "features" and instruction_mentions_addition(instruction):
        current_count = len(current_blueprint.features)
        regenerated_count = len(regenerated_blueprint.features)
        if current_count < 8 and regenerated_count <= current_count:
            errors.append("features regeneration must add a new feature when the instruction asks for one")

    return errors


def ensure_feature_instruction_is_visible(blueprint: BlueprintResponse, instruction: str | None) -> None:
    """기능 재생성 요청이 결과 목록에서 바로 보이도록 요청 기반 기능 항목을 보강합니다."""
    if not instruction:
        return

    if is_feature_instruction_reflected(blueprint.features, instruction):
        return

    requested_feature = Feature(
        name=build_requested_feature_name(instruction),
        description=f"사용자가 요청한 '{instruction.strip()}' 내용을 핵심 기능으로 반영해 화면, API, 데이터 모델에서 구현 범위를 추적할 수 있게 합니다.",
        priority="medium",
    )

    if len(blueprint.features) < 8:
        blueprint.features.append(requested_feature)
    elif blueprint.features:
        blueprint.features[-1] = requested_feature


def build_requested_feature_name(instruction: str) -> str:
    """사용자 입력을 기능 제목으로 읽기 좋게 다듬습니다."""
    cleaned_instruction = clean_feature_instruction(instruction)
    if not cleaned_instruction:
        return "요청 반영 기능"

    characters = list(cleaned_instruction)
    title = "".join(characters[:18])
    return title if title.endswith("기능") else f"{title} 기능"


def clean_feature_instruction(instruction: str) -> str:
    """기능 제목/비교에 쓰기 위해 요청 문장에서 명령형 표현을 제거합니다."""
    cleaned_instruction = instruction.strip().replace("\n", " ")
    for suffix in ["기능을 추가해줘", "기능 추가해줘", "기능을 추가", "기능 추가", "추가해줘", "해주세요", "해줘"]:
        cleaned_instruction = cleaned_instruction.replace(suffix, "")

    return " ".join(cleaned_instruction.split()).strip(".,!? ")


def is_feature_instruction_reflected(features: list[Feature], instruction: str) -> bool:
    """요청 핵심 단어가 기존 기능에 충분히 들어 있으면 이미 반영된 것으로 봅니다."""
    requested_tokens = extract_feature_instruction_tokens(instruction)
    if not requested_tokens:
        return False

    for feature in features:
        feature_text = normalize_revision_text(f"{feature.name} {feature.description}")
        matched_count = sum(1 for token in requested_tokens if token in feature_text)
        if matched_count >= min(2, len(requested_tokens)):
            return True

    return False


def extract_feature_instruction_tokens(instruction: str) -> list[str]:
    """기능 중복 판단에 쓸 핵심 단어만 추립니다."""
    cleaned_instruction = clean_feature_instruction(instruction)
    raw_tokens = [token.strip(".,!?()[]{}") for token in cleaned_instruction.split()]
    return [
        normalize_revision_text(token)
        for token in raw_tokens
        if len(normalize_revision_text(token)) >= 2 and normalize_revision_text(token) not in {"기능", "추천", "관리", "제공"}
    ]


def get_section_fingerprint(blueprint: BlueprintResponse, section: str) -> str:
    """섹션 변경 여부를 비교하기 위해 선택 섹션만 안정적인 JSON 문자열로 변환합니다."""
    if section == "features":
        value = {
            "overview": blueprint.overview,
            "features": [feature.model_dump() for feature in blueprint.features],
            "tech_stack": blueprint.tech_stack.model_dump(),
        }
    elif section == "api":
        value = [api.model_dump() for api in blueprint.api_spec]
    elif section == "database":
        value = [table.model_dump() for table in blueprint.database_schema]
    elif section == "diagrams":
        value = {
            "database_erd": blueprint.database_erd,
            "sequence_diagram": blueprint.sequence_diagram,
        }
    elif section == "planning":
        value = {
            "non_functional_requirements": [item.model_dump() for item in blueprint.non_functional_requirements],
            "security_considerations": [item.model_dump() for item in blueprint.security_considerations],
            "implementation_plan": [step.model_dump() for step in blueprint.implementation_plan],
        }
    else:
        value = {}

    return str(value)


def instruction_mentions_addition(instruction: str | None) -> bool:
    """사용자 요청이 추가 의도인지 느슨하게 판별합니다."""
    if not instruction:
        return False

    normalized = instruction.lower()
    return any(keyword in normalized for keyword in ["추가", "add", "new", "include"])


def generate_blueprint_with_retry(user_prompt: str) -> BlueprintResponse:
    """품질 검증에 실패한 OpenAI 결과를 feedback과 함께 재생성합니다."""
    validation_feedback: list[str] | None = None
    last_errors: list[str] = []

    for _ in range(MAX_OPENAI_GENERATION_ATTEMPTS):
        blueprint = normalize_blueprint_output(request_blueprint_from_openai(user_prompt, validation_feedback))
        errors = collect_blueprint_quality_errors(blueprint)

        if not errors:
            return blueprint

        last_errors = errors
        validation_feedback = errors

    joined_errors = "; ".join(last_errors)
    raise BlueprintGenerationError(f"설계도 품질 검증 재시도에 실패했습니다: {joined_errors}")


def generate_blueprint_pipeline_with_retry(payload: BlueprintRequest) -> BlueprintResponse:
    """섹션별 OpenAI 생성 결과를 조립하고 전체 품질 검증에 실패하면 파이프라인을 재시도합니다."""
    validation_feedback: list[str] | None = None
    last_errors: list[str] = []

    for _ in range(MAX_OPENAI_PIPELINE_ATTEMPTS):
        blueprint = generate_blueprint_pipeline(payload, validation_feedback)
        errors = collect_blueprint_quality_errors(blueprint)

        if not errors:
            return blueprint

        last_errors = errors
        validation_feedback = errors

    joined_errors = "; ".join(last_errors)
    raise BlueprintGenerationError(f"섹션별 설계도 품질 검증 재시도에 실패했습니다: {joined_errors}")


def generate_blueprint_pipeline(
    payload: BlueprintRequest,
    validation_feedback: list[str] | None = None,
) -> BlueprintResponse:
    """서비스 분석부터 계획까지 작은 structured output 단계로 나누어 설계도를 생성합니다."""
    idea = payload.idea.strip()

    analysis = request_structured_output_from_openai(
        build_idea_analysis_prompt(payload),
        IdeaAnalysis,
        validation_feedback=validation_feedback,
    )
    feature_design = request_structured_output_from_openai(
        build_feature_design_prompt(idea, analysis),
        FeatureDesign,
        validation_feedback=validation_feedback,
    )
    api_design = request_structured_output_from_openai(
        build_api_design_prompt(idea, analysis, feature_design),
        ApiDesign,
        validation_feedback=validation_feedback,
    )
    database_design = request_structured_output_from_openai(
        build_database_design_prompt(idea, analysis, feature_design, api_design),
        DatabaseDesign,
        validation_feedback=validation_feedback,
    )
    diagram_design, planning_design = generate_final_blueprint_sections(
        idea,
        analysis,
        feature_design,
        api_design,
        database_design,
        validation_feedback,
    )

    return assemble_blueprint(feature_design, api_design, database_design, diagram_design, planning_design)


def generate_final_blueprint_sections(
    idea: str,
    analysis: IdeaAnalysis,
    feature_design: FeatureDesign,
    api_design: ApiDesign,
    database_design: DatabaseDesign,
    validation_feedback: list[str] | None = None,
) -> tuple[DiagramDesign, PlanningDesign]:
    """서로 독립적인 다이어그램/계획 섹션을 병렬 생성해 전체 대기 시간을 줄입니다."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 두 섹션 모두 앞선 산출물만 읽기 때문에 동시에 요청해도 결과 일관성이 깨지지 않습니다.
        diagram_future = executor.submit(
            request_structured_output_from_openai,
            build_diagram_design_prompt(idea, analysis, api_design, database_design),
            DiagramDesign,
            validation_feedback,
        )
        planning_future = executor.submit(
            request_structured_output_from_openai,
            build_planning_design_prompt(idea, analysis, feature_design, api_design, database_design),
            PlanningDesign,
            validation_feedback,
        )

        return diagram_future.result(), planning_future.result()


def assemble_blueprint(
    feature_design: FeatureDesign,
    api_design: ApiDesign,
    database_design: DatabaseDesign,
    diagram_design: DiagramDesign,
    planning_design: PlanningDesign,
) -> BlueprintResponse:
    """섹션별 생성 결과를 기존 API 응답 계약인 BlueprintResponse로 조립합니다."""
    return normalize_blueprint_output(
        BlueprintResponse(
            overview=feature_design.overview,
            features=feature_design.features,
            tech_stack=feature_design.tech_stack,
            api_spec=api_design.api_spec,
            database_schema=database_design.database_schema,
            database_erd=diagram_design.database_erd,
            sequence_diagram=diagram_design.sequence_diagram,
            non_functional_requirements=planning_design.non_functional_requirements,
            security_considerations=planning_design.security_considerations,
            implementation_plan=planning_design.implementation_plan,
        )
    )


def normalize_idea(idea: str) -> str:
    """같은 의미의 반복 입력을 최대한 같은 cache key로 묶기 위해 공백을 정리합니다."""
    return " ".join(idea.strip().split()).lower()


def build_cache_key(idea: str) -> str:
    """OpenAI 사용 여부나 모델이 다른 결과가 같은 캐시에 섞이지 않도록 cache key를 만듭니다."""
    source = "openai" if settings.use_openai else "placeholder"
    return f"{source}:{settings.openai_model}:{BLUEPRINT_PROMPT_VERSION}:{normalize_idea(idea)}"


def build_revision_cache_key(idea: str, instruction: str) -> str:
    """같은 원본 아이디어라도 수정 요청별로 별도 저장본을 두도록 revision cache key를 만듭니다."""
    source = "openai" if settings.use_openai else "placeholder"
    normalized_source = normalize_idea(f"{idea} {instruction}")
    return f"{source}:{settings.openai_model}:{BLUEPRINT_PROMPT_VERSION}:revision:{normalized_source}"


def build_section_apply_cache_key(
    idea: str,
    section: str,
    blueprint: BlueprintResponse,
    instruction: str | None = None,
) -> str:
    """같은 섹션 미리보기를 반복 적용해도 저장본이 중복 생성되지 않도록 cache key를 만듭니다."""
    source = "openai" if settings.use_openai else "placeholder"
    fingerprint_source = f"{get_section_fingerprint(blueprint, section)}:{instruction or ''}"
    fingerprint = sha256(fingerprint_source.encode("utf-8")).hexdigest()
    return (
        f"{source}:{settings.openai_model}:{BLUEPRINT_PROMPT_VERSION}:"
        f"section-apply:{normalize_idea(idea)}:{section}:{fingerprint}"
    )


def build_section_apply_instruction(section: str, instruction: str | None = None) -> str:
    """최근 설계도 목록에서 적용한 섹션과 요청 내용을 알아볼 수 있는 설명을 만듭니다."""
    section_labels = {
        "features": "기능",
        "api": "API",
        "database": "DB",
        "diagrams": "다이어그램",
        "planning": "계획",
    }
    base_instruction = f"{section_labels.get(section, section)} 섹션 재생성 적용"

    if instruction and instruction.strip():
        return f"{base_instruction}: {instruction.strip()}"

    return base_instruction


def strip_revision_suffix(idea: str) -> str:
    """이전 수정 저장명이 원본 아이디어에 섞이지 않도록 수정 표시 이후 문구를 제거합니다."""
    return idea.split(REVISION_MARKER, 1)[0].replace("·", "").strip()


def normalize_revision_text(value: str) -> str:
    """중복 판단을 위해 공백과 대소문자 차이를 제거한 비교 문자열을 만듭니다."""
    return "".join(value.lower().split())


def extract_revision_keywords(instruction: str) -> list[str]:
    """수정 요청에서 이미 반영 여부를 판단할 수 있는 핵심 단어만 추립니다."""
    normalized_words = [word.strip(".,!?·:;()[]{}") for word in instruction.lower().split()]
    return [
        word
        for word in normalized_words
        if len(word) >= 2 and word not in REVISION_STOPWORDS and not word.endswith("해줘")
    ]


def is_instruction_already_reflected(blueprint: BlueprintResponse, instruction: str) -> bool:
    """수정 요청의 핵심 단어가 기존 설계도 주요 설명에 이미 있으면 중복 요청으로 간주합니다."""
    keywords = extract_revision_keywords(instruction)

    if not keywords:
        return False

    searchable_text = normalize_revision_text(
        " ".join(
            [
                blueprint.overview,
                " ".join(f"{feature.name} {feature.description}" for feature in blueprint.features),
                " ".join(f"{api.path} {api.description}" for api in blueprint.api_spec),
                " ".join(f"{table.name} {table.description}" for table in blueprint.database_schema),
            ]
        )
    )

    return all(normalize_revision_text(keyword) in searchable_text for keyword in keywords)



def build_placeholder_revision_blueprint(
    current_blueprint: BlueprintResponse,
    instruction: str,
) -> BlueprintResponse:
    """OpenAI 없이도 수정 요청 UI 흐름을 확인할 수 있도록 기존 설계도에 수정 흔적을 반영합니다."""
    blueprint = current_blueprint.model_copy(deep=True)
    blueprint.overview = f"{blueprint.overview} 수정 요청 '{instruction}'을 반영한 개선 설계입니다."

    if blueprint.features:
        blueprint.features[0].description = (
            f"{blueprint.features[0].description} 추가 수정 요청인 '{instruction}'을 우선 반영합니다."
        )

    return blueprint


def build_placeholder_section_regeneration(
    current_blueprint: BlueprintResponse,
    section: str,
    instruction: str | None = None,
) -> BlueprintResponse:
    """OpenAI 없이도 섹션별 재생성 preview 흐름을 확인할 수 있게 선택 섹션에만 변경 흔적을 남깁니다."""
    blueprint = current_blueprint.model_copy(deep=True)
    suffix = f" 추가 지시사항 '{instruction.strip()}'을 반영했습니다." if instruction else " 섹션 재생성 preview를 반영했습니다."

    if section == "features" and blueprint.features:
        added_feature = Feature(
            name="추가된 기능 개선안",
            description=(
                "선택한 기능 섹션을 다시 검토해 사용자 행동, 백엔드 책임, 구현 범위를 더 선명하게 정리합니다."
                f"{suffix}"
            ),
            priority="medium",
        )
        if len(blueprint.features) < 8:
            blueprint.features.append(added_feature)
        else:
            blueprint.features[-1] = added_feature
        blueprint.features[0].name = "재생성된 핵심 기능 정리"
        blueprint.features[0].description = (
            "기존 핵심 기능도 다시 검토해 사용자 행동과 구현 범위를 더 명확하게 정리합니다."
            f"{suffix}"
        )
    elif section == "api" and blueprint.api_spec:
        blueprint.api_spec[0].description = f"{blueprint.api_spec[0].description}{suffix}"
    elif section == "database" and blueprint.database_schema:
        blueprint.database_schema[0].description = f"{blueprint.database_schema[0].description}{suffix}"
    elif section == "diagrams":
        blueprint.sequence_diagram = f"{blueprint.sequence_diagram.rstrip()}\n  User->>UI: 재생성된 다이어그램 확인"
    elif section == "planning" and blueprint.implementation_plan:
        blueprint.implementation_plan[0].description = f"{blueprint.implementation_plan[0].description}{suffix}"

    return blueprint


def build_placeholder_blueprint(payload: BlueprintRequest) -> BlueprintResponse:
    """OpenAI 연동 없이도 API와 화면을 검증할 수 있는 예시 설계도를 생성합니다."""
    idea = payload.idea.strip()

    return BlueprintResponse(
        overview=f"'{idea}'에 대한 MVP 중심 시스템 설계도입니다.",
        features=[
            Feature(name="아이디어 제출", description="사용자가 만들고 싶은 서비스 아이디어를 자연어로 제출합니다.", priority="high"),
            Feature(name="설계 결과 저장", description="생성된 설계도와 원본 아이디어를 저장해 이후 다시 조회할 수 있게 합니다.", priority="high"),
            Feature(name="도메인 API 초안", description="입력된 서비스 성격에 맞는 REST API endpoint와 입출력 필드를 제안합니다.", priority="high"),
            Feature(name="데이터 모델 설계", description="서비스 구현에 필요한 테이블, 컬럼, 관계를 PostgreSQL 기준으로 정리합니다.", priority="medium"),
            Feature(name="주요 흐름 시각화", description="사용자 요청이 화면, API, 저장소를 거치는 과정을 시퀀스로 표현합니다.", priority="medium"),
            Feature(name="Markdown 문서화", description="완성된 설계도를 개발자가 공유하기 쉬운 Markdown 문서로 내려받게 합니다.", priority="low"),
        ],
        tech_stack=TechStack(
            backend=["Python", "FastAPI", "Pydantic"],
            frontend=["React", "Vite"],
            database=["PostgreSQL"],
            ai=["OpenAI API"],
            rationale="FastAPI와 Pydantic은 구조화된 API 응답 검증에 적합하고, React는 설계 결과를 탭과 다이어그램 중심으로 보여주기 좋습니다. PostgreSQL은 저장된 설계도와 버전 관리를 안정적으로 확장할 수 있습니다.",
        ),
        api_spec=[
            ApiSpec(method="POST", path="/api/v1/blueprint/generate", description="서비스 아이디어를 받아 시스템 설계도를 생성합니다.", request=[ApiField(name="idea", type="string", description="사용자가 만들고 싶은 서비스 아이디어입니다.", required=True)], response=[ApiField(name="overview", type="string", description="생성된 설계도의 요약입니다.", required=True), ApiField(name="features", type="array", description="핵심 기능 목록입니다.", required=True)]),
            ApiSpec(method="GET", path="/api/v1/blueprints", description="최근 생성된 설계도 목록을 조회합니다.", request=[], response=[ApiField(name="items", type="array", description="최근 생성된 설계도 목록입니다.", required=True)]),
            ApiSpec(method="GET", path="/api/v1/blueprints/{blueprint_id}", description="저장된 특정 설계도 상세 결과를 조회합니다.", request=[ApiField(name="blueprint_id", type="string", description="조회할 설계도 ID입니다.", required=True)], response=[ApiField(name="result", type="object", description="저장된 설계도 전체 결과입니다.", required=True)]),
            ApiSpec(method="POST", path="/api/v1/blueprints/{blueprint_id}/revise", description="기존 설계도와 수정 요청을 바탕으로 개선된 설계도를 생성합니다.", request=[ApiField(name="blueprint_id", type="string", description="수정할 설계도 ID입니다.", required=True), ApiField(name="instruction", type="string", description="사용자가 원하는 수정 방향입니다.", required=True)], response=[ApiField(name="result", type="object", description="수정된 설계도 전체 결과입니다.", required=True)]),
        ],
        database_schema=[
            DatabaseTable(name="blueprints", description="사용자가 생성한 설계도 결과를 저장하는 중심 테이블입니다.", columns=[DatabaseColumn(name="id", type="uuid", description="설계도 고유 식별자입니다.", constraints=["primary_key"]), DatabaseColumn(name="idea", type="text", description="사용자가 입력한 원본 서비스 아이디어입니다.", constraints=["not_null"]), DatabaseColumn(name="result", type="jsonb", description="생성된 설계도 JSON 결과입니다.", constraints=["not_null"]), DatabaseColumn(name="created_at", type="timestamp", description="설계도 생성 시각입니다.", constraints=["not_null"])]),
            DatabaseTable(name="blueprint_features", description="설계도에 포함된 핵심 기능을 검색하거나 비교하기 위해 분리 저장하는 테이블입니다.", columns=[DatabaseColumn(name="id", type="uuid", description="기능 항목 고유 식별자입니다.", constraints=["primary_key"]), DatabaseColumn(name="blueprint_id", type="uuid", description="blueprints 테이블 참조 ID입니다.", constraints=["not_null", "foreign_key"]), DatabaseColumn(name="name", type="varchar", description="기능 이름입니다.", constraints=["not_null"]), DatabaseColumn(name="priority", type="varchar", description="기능 우선순위입니다.", constraints=["not_null"])]),
            DatabaseTable(name="blueprint_api_specs", description="생성된 API 설계 항목을 endpoint 단위로 저장하는 테이블입니다.", columns=[DatabaseColumn(name="id", type="uuid", description="API 설계 항목 고유 식별자입니다.", constraints=["primary_key"]), DatabaseColumn(name="blueprint_id", type="uuid", description="blueprints 테이블 참조 ID입니다.", constraints=["not_null", "foreign_key"]), DatabaseColumn(name="method", type="varchar", description="HTTP method입니다.", constraints=["not_null"]), DatabaseColumn(name="path", type="varchar", description="API endpoint path입니다.", constraints=["not_null"])]),
        ],
        database_erd="""erDiagram
  blueprints ||--o{ blueprint_features : contains
  blueprints ||--o{ blueprint_api_specs : contains
  blueprints {
    uuid id PK
    text idea
    jsonb result
    timestamp created_at
  }
  blueprint_features {
    uuid id PK
    uuid blueprint_id FK
    varchar name
    varchar priority
  }
  blueprint_api_specs {
    uuid id PK
    uuid blueprint_id FK
    varchar method
    varchar path
  }
""",
        sequence_diagram="""sequenceDiagram
  participant User as 사용자
  participant UI as React 화면
  participant API as FastAPI 서버
  participant Store as Blueprint Repository
  participant LLM as OpenAI API
  User->>UI: 서비스 아이디어 입력
  UI->>API: POST /api/v1/blueprint/generate
  API->>Store: 같은 idea 결과 확인
  alt cached result exists
    Store-->>API: 저장된 설계도 반환
  else cache miss
    API->>LLM: 구조화된 설계도 요청
    LLM-->>API: JSON 설계도 반환
    API->>Store: 결과 저장
  end
  API-->>UI: 설계도 응답 반환
  UI-->>User: 결과 화면 표시
""",
        non_functional_requirements=[
            DesignConsideration(
                category="reliability",
                title="생성 결과 재사용",
                description="같은 아이디어 요청은 cache_key로 재사용해 불필요한 LLM 호출과 응답 변동을 줄입니다.",
                priority="high",
            ),
            DesignConsideration(
                category="observability",
                title="생성 실패 추적",
                description="OpenAI 호출 실패, 품질 검증 실패, 재시도 횟수를 로그로 남겨 운영 중 원인을 빠르게 확인합니다.",
                priority="medium",
            ),
            DesignConsideration(
                category="performance",
                title="초기 화면 응답성",
                description="무거운 다이어그램 렌더링은 결과 탭 진입 이후로 미뤄 초기 입력 화면을 빠르게 보여줍니다.",
                priority="medium",
            ),
        ],
        security_considerations=[
            DesignConsideration(
                category="input_validation",
                title="아이디어 입력 검증",
                description="너무 짧거나 비어 있는 입력은 API 단계에서 차단하고, LLM에는 정리된 문자열만 전달합니다.",
                priority="high",
            ),
            DesignConsideration(
                category="secret_management",
                title="API key와 개인정보 보호",
                description="OpenAI API key와 데이터베이스 접속 정보는 서버 환경변수로만 관리하고, 개인정보는 암호화와 최소 보관 원칙을 적용합니다.",
                priority="high",
            ),
            DesignConsideration(
                category="abuse_prevention",
                title="생성 요청 제한",
                description="공개 서비스로 전환할 때는 IP 또는 사용자 단위 rate limit을 적용해 비용 폭증과 자동화 남용을 막습니다.",
                priority="medium",
            ),
        ],
        implementation_plan=[
            ImplementationStep(
                phase="1",
                title="핵심 생성 API 구현",
                description="blueprint 아이디어 입력, structured output 생성, Pydantic 검증, placeholder 개발 모드를 먼저 완성합니다.",
            ),
            ImplementationStep(
                phase="2",
                title="저장소와 조회 흐름 연결",
                description="in-memory와 PostgreSQL repository를 분리하고 생성, 목록, 상세, 삭제 API를 같은 계약으로 제공합니다.",
            ),
            ImplementationStep(
                phase="3",
                title="결과 화면과 수정 요청 UX 완성",
                description="React 탭 화면, Mermaid 다이어그램, Markdown 다운로드, 챗봇 수정 요청 흐름을 통합합니다.",
            ),
            ImplementationStep(
                phase="4",
                title="운영 준비 점검",
                description="CORS, 환경변수, 오류 안내, 요청 제한, 빌드 크기, 테스트 자동화를 확인한 뒤 배포 후보를 정리합니다.",
            ),
        ],
    )


def normalize_section_name(section: str) -> str:
    """URL path에서 받은 섹션 이름을 내부 처리 이름으로 정규화합니다."""
    aliases = {
        "api_spec": "api",
        "apis": "api",
        "database_schema": "database",
        "db": "database",
        "diagram": "diagrams",
        "plan": "planning",
        "implementation_plan": "planning",
    }
    normalized = section.strip().lower().replace("_section", "")
    return aliases.get(normalized, normalized)
