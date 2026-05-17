# DevBlueprint AI

DevBlueprint AI는 자연어 서비스 아이디어를 개발자가 참고할 수 있는 시스템 설계도로 변환하는 AI 기반 설계 도구입니다.

사용자가 아이디어를 입력하면 핵심 기능, 기술 스택, REST API 설계, 데이터베이스 설계, ERD, 시퀀스 다이어그램을 구조화된 결과로 생성합니다.

## 주요 기능

- FastAPI 기반 blueprint 생성 API
- OpenAI Structured Outputs 기반 응답 schema 고정
- Pydantic schema 기반 API 응답 검증
- 설계도 품질 검증 및 실패 시 feedback 기반 재시도
- `USE_OPENAI=false` 개발 모드 지원
- repository 계층을 통한 같은 idea 요청 재사용
- Streamlit MVP 화면
- Markdown 다운로드
- Mermaid ERD 및 sequence diagram 렌더링
- React/Vite 전환을 고려한 CORS 설정
- PostgreSQL 연동을 위한 SQLAlchemy 기본 구조 준비

## 프로젝트 구조

```text
backend/
  app/
    api/              FastAPI router
    core/             환경 설정
    db/               SQLAlchemy session 준비
    models/           ORM model
    repositories/     저장소 계층
    schemas/          API 및 LLM output schema
    services/         생성, 검증, OpenAI 연동 로직
frontend/
  streamlit_app.py    MVP 화면
docs/
  PROJECT_CONTEXT.md
  DEV_NOTES.md
  examples/
tests/
```

## 환경 변수

`.env.sample`을 참고해 `.env`를 생성합니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:5173
DATABASE_URL=postgresql+psycopg://devblueprint:devblueprint@localhost:5432/devblueprint
```

`USE_OPENAI=false`이면 API key가 있어도 실제 OpenAI API를 호출하지 않고 placeholder 응답을 사용합니다. 실제 LLM 결과를 확인할 때만 `USE_OPENAI=true`로 변경합니다.

## 실행 방법

의존성 설치:

```bash
pip install -r requirements.txt
```

백엔드 실행:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Streamlit 실행:

```bash
streamlit run frontend/streamlit_app.py
```

## 테스트

```bash
python -m pytest
```

현재 테스트는 API 응답, CORS, repository cache, 품질 검증, retry 로직을 검증합니다.

## 설계 흐름

```text
User Idea
  -> FastAPI Endpoint
  -> Repository Cache Check
  -> OpenAI Structured Output or Placeholder
  -> Pydantic Schema Validation
  -> Blueprint Quality Validation
  -> Retry on Validation Failure
  -> Streamlit Result View
```

## 예시 결과

- [야구 분석 및 승부 예측 서비스](docs/examples/baseball_prediction_blueprint.md)
- [호텔 예약 서비스](docs/examples/hotel_reservation_blueprint.md)

## 장기 계획

- React/Vite 프론트엔드 전환
- Alembic 초기 설정 추가
- PostgreSQL migration 추가
- `PostgresBlueprintRepository` 구현
- 생성 결과 저장/조회 API 추가
- Streamlit MVP 화면을 React 화면으로 대체
