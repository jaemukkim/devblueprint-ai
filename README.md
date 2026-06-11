# DevBlueprint AI

DevBlueprint AI는 자연어로 작성한 서비스 아이디어를 개발자가 바로 검토할 수 있는 구조화된 소프트웨어 설계도로 변환하는 AI 기반 설계 도구입니다.

아이디어 한 줄을 입력하면 핵심 기능, 기술 스택, REST API 명세, 데이터베이스 스키마, Mermaid ERD, 시퀀스 다이어그램, 비기능 요구사항, 보안 고려사항, 구현 계획까지 하나의 설계 패키지로 생성합니다. 생성된 설계도는 저장, 재조회, 섹션별 재생성, 개선안 적용, ZIP export까지 이어지는 흐름으로 관리할 수 있습니다.

## 주요 기능

- 자연어 서비스 아이디어 기반 설계도 생성
- OpenAI Structured Outputs 기반 응답 스키마 고정
- LangGraph 기반 단계형 생성 파이프라인
- Specialist 구조 분리: 아이디어 분석, 기능 설계, API 설계, DB 설계, 다이어그램 설계, 구현 계획
- 품질 검증 실패 시 피드백 기반 재시도
- 기능/API/DB/다이어그램/계획 섹션별 재생성 preview
- preview 결과를 원본과 비교한 뒤 새 개선안으로 저장
- 중복 수정 요청 방지
- PostgreSQL 저장소와 in-memory 개발 저장소 지원
- 최근 설계도 목록, 상세 조회, 삭제
- 실행 이력 탭: LangGraph 노드, specialist, route, 오류 상세, 소요 시간 표시
- 설계 품질 리포트 표시
- Mermaid ERD와 sequence diagram 렌더링
- Mermaid 문법 정규화 및 렌더링 오류 격리
- Markdown/ZIP export 패키지 다운로드
- `USE_OPENAI=false` placeholder 모드로 로컬 개발 가능

## 생성 결과

DevBlueprint AI가 생성하는 설계도는 다음 영역으로 구성됩니다.

- 요약: 서비스 개요와 설계 방향
- 기능: MVP 기준 핵심 기능과 우선순위
- 기술 스택: backend, frontend, database, AI 구성과 선정 이유
- API: HTTP method, path, request/response field
- DB: 테이블, 컬럼, 제약조건
- 다이어그램: Mermaid ERD, Mermaid sequence diagram
- 계획: 비기능 요구사항, 보안 고려사항, 단계별 구현 계획
- 품질 리포트: 기능/API/DB/다이어그램/계획 완성도 체크
- 실행 이력: LangGraph 노드별 실행, 재시도, 오류, 소요 시간

## 프로젝트 구조

```text
backend/
  app/
    api/              FastAPI router
    core/             환경 설정
    db/               SQLAlchemy session
    models/           SQLAlchemy ORM model
    repositories/     저장소 인터페이스와 구현체
    schemas/          API 응답과 LLM structured output schema
    services/         생성, 검증, 정규화, export, OpenAI 연동 로직
frontend/
  react/              현재 메인 웹 UI
  streamlit/          이전 MVP UI
migrations/           Alembic migration
docs/                 개발 노트, 품질 체크리스트, 배포 준비 문서
tests/                backend test suite
```

## 아키텍처

```text
React UI
  -> FastAPI
  -> Repository cache check
  -> LangGraph pipeline
       -> idea_analyst
       -> feature_designer
       -> api_designer
       -> database_designer
       -> diagram_designer
       -> implementation_planner
       -> validation / retry route
  -> Mermaid normalization
  -> Repository save
  -> React result tabs
```

섹션 재생성은 원본 설계도를 바로 덮어쓰지 않습니다. 먼저 preview를 만들고, 사용자가 적용을 선택하면 새 개선안으로 저장합니다.

```text
Saved Blueprint
  -> Section regeneration request
  -> Preview result
  -> Quality validation
  -> Apply preview
  -> New saved blueprint
```

## 환경 변수

루트에 `.env` 파일을 만들고 `.env.sample` 또는 아래 예시를 기준으로 설정합니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false

API_BASE_URL=http://localhost:8010
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

REPOSITORY_BACKEND=memory

POSTGRES_DB=devblueprint
POSTGRES_USER=change_me_user
POSTGRES_PASSWORD=change_me_password
DATABASE_URL=postgresql+psycopg://change_me_user:change_me_password@localhost:5432/devblueprint
```

주요 설정:

- `USE_OPENAI=false`: OpenAI API를 호출하지 않고 placeholder 설계도를 생성합니다.
- `USE_OPENAI=true`: 실제 OpenAI API로 설계도를 생성합니다.
- `REPOSITORY_BACKEND=memory`: 서버 메모리에 저장합니다. 서버를 끄면 데이터가 사라집니다.
- `REPOSITORY_BACKEND=postgres`: PostgreSQL에 설계도와 실행 이력을 저장합니다.
- `FRONTEND_ORIGINS`: React 개발 서버 또는 배포 프론트엔드 origin을 CORS에 허용합니다.
- `VITE_API_BASE_URL`: React에서 호출할 FastAPI 주소입니다. `frontend/react/.env.local`에 둘 수 있습니다.

## 로컬 실행

### 1. Python 환경 준비

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. PostgreSQL 실행

in-memory 모드만 사용할 경우 이 단계는 생략할 수 있습니다.

```powershell
docker compose up -d db
python -m alembic upgrade head
```

PostgreSQL을 사용할 때는 `.env`를 다음처럼 맞춥니다.

```env
REPOSITORY_BACKEND=postgres
DATABASE_URL=postgresql+psycopg://사용자명:비밀번호@localhost:5432/devblueprint
```

### 3. FastAPI 실행

로컬 개발 권장 포트는 `8010`입니다.

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010 --reload
```

확인:

```text
http://localhost:8010/health
```

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

React API 주소 설정:

```env
VITE_API_BASE_URL=http://localhost:8010
```

## Docker Compose

`docker-compose.yml`은 API를 `8000` 포트로 노출합니다. 로컬 직접 실행은 `8010`, Docker Compose 실행은 `8000`을 기준으로 맞추면 됩니다.

```powershell
docker compose up --build
```

Docker Compose로 실행할 때 React의 `VITE_API_BASE_URL`은 실제 API 주소에 맞춰 설정해야 합니다.

```text
http://localhost:8000
```

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
GET    /api/v1/blueprints/{blueprint_id}/runs
GET    /api/v1/blueprints/{blueprint_id}/export.zip
POST   /api/v1/blueprints/{blueprint_id}/revise
POST   /api/v1/blueprints/{blueprint_id}/sections/{section}/regenerate
POST   /api/v1/blueprints/{blueprint_id}/sections/{section}/apply
DELETE /api/v1/blueprints/{blueprint_id}
```

재생성 가능한 섹션:

```text
features
api
database
diagrams
planning
```

## Export 패키지

설계도 상세 화면에서 ZIP export를 내려받을 수 있습니다. ZIP에는 다음 파일이 포함됩니다.

```text
README.md
features.md
api-spec.md
database-schema.md
implementation-plan.md
quality-report.md
erd.mmd
sequence.mmd
```

## 품질 검증

생성 결과는 저장 전에 다음 기준으로 검증됩니다.

- 핵심 기능 개수와 설명 품질
- API path, method, request/response field 구조
- API와 DB schema 간 최소 연관성
- DB table, column, primary key, constraint 구조
- Mermaid ERD와 sequence diagram 형식
- 보안 고려사항과 구현 계획의 최소 완성도
- 섹션 재생성 시 사용자 요청 반영 여부

검증 실패 시 LangGraph route가 재시도 가능한 specialist로 돌아가고, 검증 피드백을 다음 생성 프롬프트에 반영합니다.

## 테스트

```powershell
python -m pytest
```

최근 확인 결과:

```text
97 passed
```

React production build:

```powershell
cd frontend/react
npm.cmd run build
```

PowerShell 실행 정책 때문에 `npm.ps1`이 막히는 환경에서는 `npm.cmd`를 사용합니다.

## 운영 준비 체크리스트

운영 모드에서는 최소한 아래 항목을 확인합니다.

- `USE_OPENAI=true`
- `REPOSITORY_BACKEND=postgres`
- `DATABASE_URL`이 운영 PostgreSQL을 가리킴
- `FRONTEND_ORIGINS`에 실제 프론트엔드 주소만 등록
- `python -m alembic upgrade head` 적용
- `/health`에서 OpenAI 사용 여부와 저장소 backend 확인
- 실제 OpenAI 생성 샘플 3개 이상 성공 확인
- Export ZIP 다운로드 확인
- 공개 서비스 전 인증, 사용자 격리, rate limit 추가 검토

자세한 배포 메모는 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)를 참고합니다.

## 문서

- [프로젝트 컨텍스트](docs/PROJECT_CONTEXT.md)
- [개발 노트](docs/DEV_NOTES.md)
- [품질 체크리스트](docs/BLUEPRINT_QUALITY_CHECKLIST.md)
- [OpenAI 회귀 샘플](docs/OPENAI_REGRESSION_SAMPLES.md)
- [작업 로드맵](docs/WORKSPACE_ROADMAP.md)
- [배포 준비 문서](docs/DEPLOYMENT.md)

## 예시 결과

- [호텔 예약 서비스](docs/examples/hotel_reservation_blueprint.md)
- [풋살장 예약 서비스](docs/examples/futsal_reservation_blueprint.md)

## 현재 상태

DevBlueprint AI는 로컬 개발 환경에서 설계도 생성, 저장, 재조회, 섹션 재생성, 개선안 적용, 실행 이력 확인, 품질 리포트, ZIP export까지 동작하는 상태입니다.

다음 큰 개선 방향은 LLM 품질 평가 세트 확장, 섹션별 diff 고도화, 운영용 인증/사용자 격리, 공개 배포 환경 정리입니다.
