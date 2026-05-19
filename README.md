# DevBlueprint AI

DevBlueprint AI는 자연어 서비스 아이디어를 개발자가 참고할 수 있는 시스템 설계도로 변환하는 AI 기반 설계 도구입니다.

사용자가 아이디어를 입력하면 핵심 기능, 기술 스택, REST API 설계, 데이터베이스 설계, ERD, 시퀀스 다이어그램을 구조화된 결과로 생성하고, 생성된 설계도는 PostgreSQL에 저장해 다시 조회하거나 삭제할 수 있습니다.

## 주요 기능

- FastAPI 기반 설계도 생성 API
- OpenAI Structured Outputs 기반 응답 schema 고정
- `USE_OPENAI=false` 개발 모드 지원
- 설계도 품질 검증 및 실패 시 feedback 기반 재시도
- Repository 계층을 통한 저장 방식 분리
- In-memory / PostgreSQL repository 선택 지원
- 같은 idea 요청에 대한 cache 재사용
- PostgreSQL 기반 설계도 저장, 목록 조회, 상세 조회, 삭제
- Streamlit MVP 화면
- 최근 설계도 목록, 상세 열기, 삭제
- Markdown 다운로드
- Mermaid ERD 및 sequence diagram 렌더링
- React/Vite 전환을 고려한 CORS 설정

## 프로젝트 구조

```text
backend/
  app/
    api/              FastAPI router
    core/             환경 설정
    db/               SQLAlchemy session
    models/           ORM model
    repositories/     저장소 계층
    schemas/          API 및 LLM output schema
    services/         생성, 검증, OpenAI 연동 로직
frontend/
  streamlit/
    streamlit_app.py  MVP 화면
  react/              React/Vite 프론트엔드
migrations/           Alembic migration
docs/
  PROJECT_CONTEXT.md
  DEV_NOTES.md
  examples/
tests/
```

## 환경 변수

`.env.sample`을 참고해 프로젝트 루트에 `.env`를 생성합니다. `.env`는 실제 로컬 실행값을 담는 파일이므로 Git에 올리지 않습니다.

```env
# OpenAI 설정
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false

# API / 프론트엔드 설정
API_BASE_URL=http://localhost:8001
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:8502,http://localhost:5173

# 저장소 설정
REPOSITORY_BACKEND=postgres

# PostgreSQL 설정
POSTGRES_DB=devblueprint
POSTGRES_USER=change_me_user
POSTGRES_PASSWORD=change_me_password
DATABASE_URL=postgresql+psycopg://change_me_user:change_me_password@localhost:5432/devblueprint
```

주요 설정 의미:

- `USE_OPENAI=false`: OpenAI API를 호출하지 않고 placeholder 설계도를 생성합니다.
- `USE_OPENAI=true`: 실제 OpenAI API로 설계도를 생성합니다.
- `API_BASE_URL`: Streamlit이 호출할 FastAPI 주소입니다.
- `REPOSITORY_BACKEND=memory`: 서버 메모리에만 저장합니다. 서버를 끄면 데이터가 사라집니다.
- `REPOSITORY_BACKEND=postgres`: PostgreSQL `blueprints` 테이블에 저장합니다.
- `FRONTEND_ORIGINS`: FastAPI CORS 허용 origin입니다. React 전환 시 `http://localhost:5173`을 사용합니다.

실제 로컬 `.env`에는 본인이 Docker DB에 맞춘 계정과 비밀번호를 넣습니다. 예시 문서와 `.env.sample`에는 실제 비밀번호를 적지 않습니다.

## 포트 정리

기본적으로는 아래 조합을 사용할 수 있습니다.

```text
FastAPI:   http://localhost:8000
Streamlit: http://localhost:8501
PostgreSQL: localhost:5432
```

Windows에서 `8000` 포트 실행 시 `WinError 10013`이 발생하면 FastAPI를 `8001`로 실행하고 `.env`의 `API_BASE_URL`도 같이 바꿉니다.

```env
API_BASE_URL=http://localhost:8001
```

Streamlit을 `8502`로 실행해도 괜찮습니다. 이때 중요한 것은 Streamlit 포트가 아니라 `API_BASE_URL`이 실제 FastAPI 포트를 바라보는지입니다.

```text
브라우저 -> Streamlit: http://localhost:8502
Streamlit -> FastAPI:  http://localhost:8001
FastAPI -> PostgreSQL: DATABASE_URL
```

## 실행 방법

가상환경 활성화:

```powershell
.\.venv\Scripts\activate
```

의존성 설치:

```powershell
python -m pip install -r requirements.txt
```

PostgreSQL 실행:

```powershell
docker compose up -d db
```

Migration 적용:

```powershell
python -m alembic upgrade head
```

FastAPI 실행:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

`8000` 포트가 막혀 있으면:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

Streamlit 실행:

```powershell
python -m streamlit run frontend/streamlit/streamlit_app.py
```

Streamlit을 `8502`로 실행하려면:

```powershell
python -m streamlit run frontend/streamlit/streamlit_app.py --server.port 8502
```

React 실행:

```powershell
cd frontend/react
npm install
npm run dev
```

FastAPI를 `8001`로 실행하는 경우 `frontend/react/.env.local`을 만들고 아래 값을 넣습니다.

```env
VITE_API_BASE_URL=http://localhost:8001
```

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
DELETE /api/v1/blueprints/{blueprint_id}
```

## 테스트

```powershell
python -m pytest
```

현재 테스트는 health check, CORS, 설계도 생성, cache 재사용, 목록 조회, 상세 조회, 삭제, 품질 검증, OpenAI retry 로직을 검증합니다.

## 설계 흐름

```text
User Idea
  -> Streamlit
  -> FastAPI Endpoint
  -> Repository Cache Check
  -> OpenAI Structured Output or Placeholder
  -> Pydantic Schema Validation
  -> Blueprint Quality Validation
  -> Retry on Validation Failure
  -> Repository Save
  -> Streamlit Result View
```

PostgreSQL 사용 시 같은 idea 요청은 `cache_key`로 먼저 조회하고, 이미 저장된 결과가 있으면 새로 생성하지 않고 DB 결과를 재사용합니다.

## 예시 결과

- [호텔 예약 서비스](docs/examples/hotel_reservation_blueprint.md)
- [풋살장 예약 서비스](docs/examples/futsal_reservation_blueprint.md)

## 다음 계획

- React 화면 UI 품질 개선
- React 화면 기능 검증 및 Streamlit MVP 대체
- 배포 환경 설정 정리
