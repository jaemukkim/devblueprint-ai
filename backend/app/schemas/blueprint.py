from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# 사용자가 입력하는 서비스 아이디어 요청 모델입니다.
# min_length를 두어 너무 짧은 입력이 LLM 처리 단계로 바로 넘어가지 않게 합니다.
class BlueprintRequest(BaseModel):
    idea: str = Field(..., min_length=5, description="소프트웨어 또는 서비스 아이디어입니다.")


# 생성된 설계도에 포함될 핵심 기능 단위입니다.
# priority는 UI 정렬이나 강조 표시 기준으로 사용할 수 있도록 허용 값을 제한합니다.
# 저장된 설계도를 사용자의 추가 요청에 맞게 다시 다듬을 때 사용하는 요청 모델입니다.
class BlueprintRevisionRequest(BaseModel):
    instruction: str = Field(..., min_length=5, description="설계도를 어떻게 수정할지 설명한 요청입니다.")


class BlueprintSectionRegenerationRequest(BaseModel):
    instruction: str | None = Field(
        default=None,
        min_length=5,
        description="특정 섹션을 다시 생성할 때 반영할 추가 지시사항입니다.",
    )


class Feature(BaseModel):
    name: str
    description: str
    priority: Literal["high", "medium", "low"]


# 추천 기술 스택을 영역별로 나누어 담는 모델입니다.
# MVP에서는 database가 빈 배열일 수 있으며, rationale에는 추천 이유를 설명합니다.
class TechStack(BaseModel):
    backend: list[str]
    frontend: list[str]
    database: list[str]
    ai: list[str]
    rationale: str


# API request/response에 포함되는 필드 단위입니다.
# JSON 예시를 자유 dict로 두는 대신 name/type/description으로 고정해 LLM 출력 안정성을 높입니다.
class ApiField(BaseModel):
    name: str
    type: str
    description: str
    required: bool


# REST API 설계 초안을 표현하는 모델입니다.
# method는 실제 HTTP method만 들어오도록 Literal로 제한합니다.
class ApiSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str
    request: list[ApiField]
    response: list[ApiField]


# 데이터베이스 컬럼 설계 단위입니다.
# constraints는 primary_key, not_null, unique 같은 개발자 친화적인 영문 값을 유지합니다.
class DatabaseColumn(BaseModel):
    name: str
    type: str
    description: str
    constraints: list[str]


# 데이터베이스 테이블 설계 제안 모델입니다.
# 현재 MVP는 DB 저장을 하지 않지만, 결과물에는 테이블 설계 초안을 포함할 수 있습니다.
class DatabaseTable(BaseModel):
    name: str
    description: str
    columns: list[DatabaseColumn]

# 설계 시 고려사항을 담는 모델입니다.
class DesignConsideration(BaseModel):
    category: str
    title: str
    description: str
    priority: Literal["high", "medium", "low"]


class ImplementationStep(BaseModel):
    phase: str
    title: str
    description: str


class IdeaAnalysis(BaseModel):
    service_summary: str
    target_users: list[str]
    core_entities: list[str]
    mvp_scope: list[str]
    out_of_scope: list[str]


class FeatureDesign(BaseModel):
    overview: str
    features: list[Feature]
    tech_stack: TechStack


class ApiDesign(BaseModel):
    api_spec: list[ApiSpec]


class DatabaseDesign(BaseModel):
    database_schema: list[DatabaseTable]


class DiagramDesign(BaseModel):
    database_erd: str
    sequence_diagram: str

class PlanningDesign(BaseModel):
    non_functional_requirements: list[DesignConsideration]
    security_considerations: list[DesignConsideration]
    implementation_plan: list[ImplementationStep]


# API가 최종적으로 반환하는 전체 시스템 설계도 응답 모델입니다.
# 이 구조가 LLM의 structured output 계약이 되므로 OpenAI 응답도 이 형태에 맞춥니다.
class BlueprintResponse(BaseModel):
    overview: str
    features: list[Feature]
    tech_stack: TechStack
    api_spec: list[ApiSpec]
    database_schema: list[DatabaseTable]
    database_erd: str
    sequence_diagram: str
    non_functional_requirements: list[DesignConsideration] = Field(default_factory=list)
    security_considerations: list[DesignConsideration] = Field(default_factory=list)
    implementation_plan: list[ImplementationStep] = Field(default_factory=list)


# 저장된 설계도 목록에서 보여줄 최소 정보입니다.
# 전체 result를 목록에 모두 싣지 않아 응답 크기를 작게 유지합니다.
class BlueprintSummary(BaseModel):
    id: str
    idea: str
    revision_instruction: str | None = None
    created_at: datetime


# 저장된 설계도 상세 조회 응답입니다.
# 목록 정보와 함께 실제 생성 결과 전체를 result에 담습니다.
class StoredBlueprintResponse(BlueprintSummary):
    result: BlueprintResponse


class BlueprintSectionRegenerationResponse(BaseModel):
    section: str
    result: BlueprintResponse


# 저장된 설계도 목록 조회 응답입니다.
# 이후 pagination 정보를 추가하기 쉽도록 배열을 바로 반환하지 않고 items로 감쌉니다.
class BlueprintListResponse(BaseModel):
    items: list[BlueprintSummary]


# API 에러 응답을 문서화하기 위한 모델입니다.
# FastAPI 기본 에러 형식과 별개로, 우리가 직접 처리하는 오류에는 이 구조를 사용합니다.
class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    extra: dict[str, Any] | None = None
