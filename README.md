# DevBlueprint AI

DevBlueprint AI는 자연어로 작성한 서비스 아이디어를 개발자가 참고할 수 있는 시스템 설계도로 바꿔 주는 AI 기반 설계 도구입니다.

사용자가 아이디어를 입력하면 핵심 기능, 기술 스택, REST API 설계, 데이터베이스 설계, ERD, 시퀀스 다이어그램, 비기능 요구사항, 보안 고려사항, 구현 계획을 구조화된 결과로 생성합니다. 생성된 설계도는 PostgreSQL에 저장할 수 있고, React 화면에서 다시 조회하거나 삭제할 수 있습니다.

## 현재 상태

- FastAPI 기반 설계도 생성 API
- OpenAI Structured Outputs 기반 응답 schema 고정
- `USE_OPENAI=false` 개발 모드 placeholder 응답 지원
- 설계도 schema 검증 및 실패 시 feedback 기반 재시도
- Repository 계층을 통한 in-memory / PostgreSQL 저장소 분리
- 같은 idea 요청에 대한 cache 재사용
- PostgreSQL 기반 설계도 저장, 목록 조회, 상세 조회, 삭제
- React/Vite 기반 메인 화면
- 스크롤 랜딩 영역과 실제 설계도 생성 화면
- 최근 설계도 카드 목록, 상세 열기, 삭제
- 결과 탭: 요약 / 기능 / API / DB / 다이어그램
- Markdown 다운로드
- Mermaid ERD 및 sequence diagram 렌더링
- Mermaid 동적 로딩으로 초기 React bundle 크기 절감
- Mermaid 문법 정규화: code fence, ERD key token, SQL 타입, 제약 조건 보정
- 저장된 예전 설계도도 조회 시 Mermaid 정규화 적용
- Mermaid 렌더링 오류 시 다이어그램별 오류 메시지와 line 정보 표시
- 설계도 수정 요청 챗봇 UI
- 챗봇 수정 요청 기반 새 설계도 생성
- 섹션별 재생성 미리보기 및 미리보기 적용
- 중복 수정 요청 방지 및 사용자 안내
- 최근 설계도 목록에서 초안/개선안 구분
- 수정 요청 요약 표시
- 구조화된 API 오류 응답과 프론트 사용자 메시지 처리
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
  BLUEPRINT_QUALITY_CHECKLIST.md
  examples/
tests/
```

## 환경 변수

`.env.sample`을 참고해 프로젝트 루트에 `.env`를 생성합니다. `.env`는 실제 로컬 실행값을 담는 파일이므로 Git에 올리지 않습니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false

API_BASE_URL=http://localhost:8010
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:8502,http://localhost:5173,http://127.0.0.1:5173

REPOSITORY_BACKEND=memory

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
- `FRONTEND_ORIGINS`: FastAPI CORS 허용 origin입니다. React 개발 서버 기본값은 `http://localhost:5173`입니다.

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

로컬 개발에서는 Docker로 PostgreSQL만 실행하고, FastAPI는 호스트에서 `8010` 포트로 실행하는 방식을 권장합니다.

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
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010
```

권장 로컬 주소:

```text
http://localhost:8010
```

코드를 수정한 뒤에는 실행 중인 FastAPI 터미널에서 `Ctrl + C`로 종료하고 다시 실행합니다. Docker Desktop이나 PostgreSQL 컨테이너는 종료할 필요가 없습니다.

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

React 개발 서버는 `frontend/react/.env` 또는 `frontend/react/.env.local`의 API 주소를 사용합니다.

```env
VITE_API_BASE_URL=http://localhost:8010
```

FastAPI 포트를 바꾸면 이 값도 같은 포트로 바꾼 뒤 React 개발 서버를 재시작합니다.

## 포트 정리

```text
React:      http://localhost:5173
FastAPI:    http://localhost:8010
PostgreSQL: localhost:5432
Streamlit:  http://localhost:8501 또는 8502
```

현재 메인 화면은 React입니다. Streamlit은 MVP 기록용으로 남겨 둔 상태입니다.

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
POST   /api/v1/blueprints/{blueprint_id}/revise
POST   /api/v1/blueprints/{blueprint_id}/sections/{section}/regenerate
POST   /api/v1/blueprints/{blueprint_id}/sections/{section}/apply
DELETE /api/v1/blueprints/{blueprint_id}
```

## 테스트

```powershell
python -m pytest
```

현재 테스트는 health check, CORS, 설계도 생성, cache 재사용, 목록 조회, 상세 조회, 삭제, 수정 요청, 섹션별 재생성, 미리보기 적용, 중복 수정 방지, schema 검증, Mermaid 정규화, OpenAI retry 로직을 검증합니다.

최근 확인 결과:

```text
60 passed
```

React 빌드 확인:

```powershell
cd frontend/react
npm run build
```

PowerShell 실행 정책 때문에 `npm.ps1`이 막힌 환경에서는 아래처럼 `npm.cmd`를 사용합니다.

```powershell
npm.cmd run build
```

현재 React 빌드는 통과합니다. Mermaid는 다이어그램 탭에서만 동적 로딩되지만 Mermaid lazy chunk가 500 kB를 넘기 때문에 Vite chunk size 경고가 남을 수 있습니다. 이 경고는 빌드 실패가 아닙니다.

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
  -> Mermaid Normalization
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
  -> Mermaid Normalization
  -> New Saved Blueprint
  -> Recent List as 개선안
```

섹션별 재생성 흐름:

```text
Saved Blueprint Detail
  -> Section Regeneration Request
  -> Preview Result
  -> Diagram / Text Preview
  -> Apply Preview
  -> New Saved Blueprint
```

섹션 재생성 미리보기는 원본 설계도를 바로 덮어쓰지 않습니다. 사용자가 “미리보기 적용”을 누르면 미리보기 결과를 새 개선안으로 저장합니다.

## Mermaid 다이어그램 안정화

백엔드와 프론트엔드에서 Mermaid 코드를 함께 정규화합니다.

- Markdown code fence 제거
- ERD key token 보정: `PK FK` -> `PK, FK`, `UNIQUE`/`UQ` -> `UK`
- SQL 타입 보정: `timestamp with time zone`, `varchar(255)`, `decimal(10,2)`, `text[]`
- ERD 제약 조건 보정: `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `NULL`
- 저장된 예전 설계도도 조회 시 정규화된 결과로 반환

프론트엔드는 다이어그램별로 독립 렌더링합니다. 특정 다이어그램에 문법 오류가 있어도 다른 다이어그램까지 함께 실패하지 않도록 처리하고, 오류가 난 경우 가능한 line 번호와 원본 line을 표시합니다.

## 예시 결과

- [호텔 예약 서비스](docs/examples/hotel_reservation_blueprint.md)
- [풋살장 예약 서비스](docs/examples/futsal_reservation_blueprint.md)

## 다음 작업 후보

- 실제 OpenAI 호출 기준 회귀 테스트와 샘플 설계도 점검
- 저장된 설계도 관리 UX 개선: 검색, 필터, 정렬, 삭제 확인 흐름
- 섹션별 재생성 결과 diff 표시 고도화
- 모바일 화면에서 생성, 상세, 재생성, 삭제 흐름 확인
- Vite `manualChunks` 또는 Mermaid 로딩 최적화 추가 검토
