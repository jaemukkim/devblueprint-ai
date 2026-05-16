from pydantic import BaseModel, Field


# 사용자가 입력하는 서비스 아이디어 요청 모델입니다.
# 최소 길이를 둬서 너무 짧은 입력이 바로 LLM 처리 단계로 넘어가지 않게 합니다.
class BlueprintRequest(BaseModel):
    idea: str = Field(..., min_length=5, description="소프트웨어 또는 서비스 아이디어입니다.")


# 생성된 설계도에 포함될 핵심 기능 단위입니다.
# priority는 화면에서 정렬이나 강조 표시 기준으로 활용할 수 있습니다.
class Feature(BaseModel):
    name: str
    description: str
    priority: str = "medium"


# 추천 기술 스택을 영역별로 나누어 담는 모델입니다.
# MVP에서는 database가 비어 있을 수 있으며, rationale에는 추천 이유를 설명합니다.
class TechStack(BaseModel):
    backend: list[str] = []
    frontend: list[str] = []
    database: list[str] = []
    ai: list[str] = []
    rationale: str = ""


# REST API 설계 초안을 표현하는 모델입니다.
# request와 response는 아직 형태가 고정되지 않았기 때문에 dict로 열어둡니다.
class ApiSpec(BaseModel):
    method: str
    path: str
    description: str
    request: dict = {}
    response: dict = {}


# 데이터베이스 테이블 설계 제안 모델입니다.
# 현재 MVP는 DB 저장을 하지 않지만, 결과물에는 테이블 설계 초안을 포함할 수 있습니다.
class DatabaseTable(BaseModel):
    name: str
    description: str
    columns: list[dict] = []


# API가 최종적으로 반환하는 전체 시스템 설계도 응답 모델입니다.
# 이 구조가 LLM의 structured output 계약이 되므로, 이후 OpenAI 연동도 이 형태에 맞춥니다.
class BlueprintResponse(BaseModel):
    overview: str
    features: list[Feature]
    tech_stack: TechStack
    api_spec: list[ApiSpec]
    database_schema: list[DatabaseTable]
    sequence_diagram: str
