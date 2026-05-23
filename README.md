# DevBlueprint AI

DevBlueprint AI는 자연어로 작성한 서비스 아이디어를 개발자가 참고할 수 있는 시스템 설계도로 변환하는 AI 기반 설계 도구입니다.

사용자가 아이디어를 입력하면 핵심 기능, 기술 스택, REST API 설계, 데이터베이스 설계, ERD, 시퀀스 다이어그램을 구조화된 결과로 생성합니다. 생성된 설계도는 PostgreSQL에 저장할 수 있고, React 화면에서 다시 조회하거나 삭제할 수 있습니다.

## 현재 상태

- FastAPI 기반 설계도 생성 API
- OpenAI Structured Outputs 기반 응답 schema 고정
- OpenAI 모드에서 섹션별 생성 파이프라인 사용
- `USE_OPENAI=false` 개발 모드 지원
- 설계도 품질 검증 및 실패 시 feedback 기반 재시도
- Repository 계층을 통한 저장 방식 분리
- In-memory / PostgreSQL repository 선택 지원
- 같은 idea 요청에 대한 cache 재사용
- PostgreSQL 기반 설계도 저장, 목록 조회, 상세 조회, 삭제
- React/Vite 기반 메인 화면
- 다크 랜딩 히어로 + 실제 설계도 생성 앱 화면
- 최근 설계도 카드 목록, 상세 열기, 삭제
- 결과 탭: 요약 / 기능 / API / DB / 다이어그램
- 비기능 요구사항, 보안 고려사항, 구현 계획을 포함한 계획 탭
- Markdown 다운로드
- Mermaid ERD 및 sequence diagram 렌더링
- Mermaid 동적 로딩으로 초기 React bundle 크기 절감
- 설계도 수정 요청 챗봇 UI
- 챗봇 수정 요청 기반 새 설계도 생성
- 중복 수정 요청 방지 및 사용자 안내
- 최근 설계도 목록의 초안/개선안 구분
- 수정 요청 요약 표시
- 설계도 삭제는 현재 실제 삭제(hard delete) 정책 유지
- Streamlit MVP 화면은 `frontend/streamlit/`에 보관

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
  react/              현재 메인 프론트엔드
  streamlit/          이전 MVP 화면
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
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:8502,http://localhost:5173

# 저장소 설정
REPOSITORY_BACKEND=memory

# PostgreSQL 설정
POSTGRES_DB=devblueprint
POSTGRES_USER=change_me_user
POSTGRES_PASSWORD=change_me_password
DATABASE_URL=postgresql+psycopg://change_me_user:change_me_password@localhost:5432/devblueprint
```

주요 설정:

- `USE_OPENAI=false`: OpenAI API를 호출하지 않고 placeholder 설계도를 생성합니다.
- `USE_OPENAI=true`: 실제 OpenAI API로 설계도를 생성합니다.
- `REPOSITORY_BACKEND=memory`: 서버 메모리에만 저장합니다. 서버를 끄면 데이터가 사라집니다.
- `REPOSITORY_BACKEND=postgres`: PostgreSQL `blueprints` 테이블에 저장합니다.
- `FRONTEND_ORIGINS`: FastAPI CORS 허용 origin입니다. React 개발 서버는 기본적으로 `http://localhost:5173`입니다.

## 실행 방법

### 1. Python 가상환경

```powershell
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. PostgreSQL 실행

```powershell
docker compose up -d db
```

PostgreSQL 저장소를 사용할 경우 `.env`에서 아래 값을 실제 Docker DB 계정에 맞춥니다.

```env
REPOSITORY_BACKEND=postgres
DATABASE_URL=postgresql+psycopg://사용자명:비밀번호@localhost:5432/devblueprint
```

Migration 적용:

```powershell
python -m alembic upgrade head
```

### 3. FastAPI 실행

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

기본 주소:

```text
http://localhost:8000
```

`8000` 포트가 막혀 있으면 `8001`로 실행합니다.

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

이 경우 React의 API 주소도 같이 바꿔야 합니다.

### 4. React 실행

```powershell
cd frontend/react
npm install
npm run dev
```

기본 주소:

```text
http://localhost:5173
```

FastAPI를 `8001`로 실행하는 경우 `frontend/react/.env.local`을 만들고 아래 값을 넣습니다.

```env
VITE_API_BASE_URL=http://localhost:8001
```

FastAPI가 `8000`이면 보통 `.env.local` 없이 기본값으로 실행해도 됩니다.

## 포트 정리

```text
React:      http://localhost:5173
FastAPI:    http://localhost:8000
PostgreSQL: localhost:5432
Streamlit:  http://localhost:8501 또는 8502
```

현재 메인 화면은 React입니다. Streamlit은 MVP 기록용으로 남겨둔 상태입니다.

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
POST   /api/v1/blueprints/{blueprint_id}/revise
DELETE /api/v1/blueprints/{blueprint_id}
```

## 테스트

```powershell
python -m pytest
```

현재 테스트는 health check, CORS, 설계도 생성, cache 재사용, 목록 조회, 상세 조회, 삭제, 수정 요청, 중복 수정 방지, 품질 검증, OpenAI retry 로직을 검증합니다.

최근 확인 결과:

```text
37 passed
```

React 빌드 확인:

```powershell
cd frontend/react
npm run build
```

PowerShell 실행 정책 때문에 `npm.ps1`이 막히는 환경에서는 아래처럼 `npm.cmd`를 사용합니다.

```powershell
npm.cmd run build
```

현재 React 빌드는 통과합니다. Mermaid는 다이어그램 탭에서만 동적 로딩되도록 분리되어 초기 앱 chunk는 줄었지만, Mermaid 자체 lazy chunk가 500 kB를 넘기 때문에 Vite의 chunk size 경고는 남을 수 있습니다. 이 경고는 빌드 실패가 아닙니다.

## 설계 흐름

```text
User Idea
  -> React UI
  -> FastAPI Endpoint
  -> Repository Cache Check
  -> OpenAI Structured Output or Placeholder
  -> Pydantic Schema Validation
  -> Blueprint Quality Validation
  -> Retry on Validation Failure
  -> Repository Save
  -> React Result Tabs
```

PostgreSQL 사용 시 같은 idea 요청은 `cache_key`로 먼저 조회하고, 이미 저장된 결과가 있으면 새로 생성하지 않고 DB 결과를 재사용합니다.

수정 요청 흐름:

```text
Saved Blueprint
  -> Chatbot Revision Request
  -> Duplicate Revision Check
  -> OpenAI Revision Prompt or Placeholder
  -> Quality Validation
  -> New Saved Blueprint
  -> Recent List as 개선안
```

수정 요청으로 생성된 설계도는 원본 idea를 유지하고, `revision_instruction`에 사용자의 수정 요청 원문을 저장합니다. React 최근 설계도 카드에서는 `초안`, `개선안 1`, `개선안 2`처럼 구분하고, 수정 요청은 한 줄 요약으로 표시합니다.

현재 삭제 API는 저장된 설계도를 실제로 삭제합니다. `deleted_at` 기반 소프트 삭제는 보류하고 hard delete 정책을 유지합니다.

## 예시 결과

- [호텔 예약 서비스](docs/examples/hotel_reservation_blueprint.md)
- [풋살장 예약 서비스](docs/examples/futsal_reservation_blueprint.md)

## 다음 작업 후보

- README 스크린샷 추가
- 모바일 실제 기기에서 생성/조회/수정/삭제 흐름 확인
- 챗봇 수정 요청 성공 후 결과 영역 자동 이동/강조 UX 검토
- Mermaid lazy chunk 추가 최적화 또는 Vite manualChunks 설정 검토
