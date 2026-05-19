# Dev Notes

## Current Status

DevBlueprint AI는 자연어 서비스 아이디어를 입력받아 개발자가 참고할 수 있는 시스템 설계도를 생성하고, 생성 결과를 저장/조회/삭제할 수 있는 MVP입니다.

현재 구현된 주요 흐름은 다음과 같습니다.

- FastAPI 백엔드에서 설계도 생성 API 제공
- OpenAI Structured Outputs로 `BlueprintResponse` schema에 맞는 결과 생성
- `USE_OPENAI=false` 개발 모드에서는 OpenAI 호출 없이 placeholder 응답 사용
- 설계도 품질 검증 및 실패 시 feedback 기반 최대 3회 재시도
- Repository 계층을 통해 저장 방식 분리
- `REPOSITORY_BACKEND=memory` / `postgres` 선택 지원
- PostgreSQL `blueprints` 테이블에 설계도 결과 저장
- 같은 idea 요청은 `cache_key`로 DB 결과 재사용
- 저장된 설계도 목록 조회, 상세 조회, 삭제 API 제공
- Streamlit MVP 화면에서 생성/목록/상세/삭제 지원
- Markdown 다운로드 지원
- 다운로드 파일명은 사용자 idea 기반으로 생성
- Mermaid ERD와 sequence diagram 렌더링
- Streamlit에서 `.env`의 `API_BASE_URL` 자동 로딩
- React/Vite 전환을 고려한 CORS 설정 포함

## Run Locally

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

만약 `8000` 포트에서 `WinError 10013`이 발생하면 `8001`로 실행합니다.

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

Streamlit 실행:

```powershell
python -m streamlit run frontend/streamlit/streamlit_app.py
```

Streamlit을 `8502`로 실행할 경우:

```powershell
python -m streamlit run frontend/streamlit/streamlit_app.py --server.port 8502
```

React 실행:

```powershell
cd frontend/react
npm install
npm run dev
```

FastAPI를 `8001`로 실행할 경우 `frontend/react/.env.local`에 아래 값을 둡니다.

```env
VITE_API_BASE_URL=http://localhost:8001
```

## Environment

`.env.sample`을 기준으로 `.env`를 구성합니다. 실제 API key, DB user, DB password는 `.env`에만 둡니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false

API_BASE_URL=http://localhost:8001
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:8502,http://localhost:5173

REPOSITORY_BACKEND=postgres

POSTGRES_DB=devblueprint
POSTGRES_USER=user
POSTGRES_PASSWORD=password
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/devblueprint
```

포트 관계:

```text
브라우저 -> Streamlit: http://localhost:8501 또는 http://localhost:8502
Streamlit -> FastAPI:  API_BASE_URL
FastAPI -> PostgreSQL: DATABASE_URL
```

`API_BASE_URL`은 Streamlit이 호출할 FastAPI 주소입니다. FastAPI를 `8001`로 실행하면 `.env`의 `API_BASE_URL`도 `http://localhost:8001`이어야 합니다.

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
DELETE /api/v1/blueprints/{blueprint_id}
```

## Architecture Notes

백엔드는 다음 책임으로 나뉩니다.

- `api/`: FastAPI router와 endpoint 정의
- `schemas/`: API request/response 및 LLM structured output 계약
- `services/`: 설계도 생성, OpenAI 호출, prompt 구성, 품질 검증
- `repositories/`: 설계도 결과 저장/조회/삭제 책임
- `db/`: SQLAlchemy engine/session
- `models/`: PostgreSQL ORM model
- `core/`: 환경 설정

Repository 구현체:

- `InMemoryBlueprintRepository`: 서버 메모리 저장소
- `PostgresBlueprintRepository`: PostgreSQL 저장소

PostgreSQL 저장 컬럼:

```text
id          설계도 고유 ID
cache_key   같은 idea 재사용을 위한 key
idea        사용자가 입력한 원본 아이디어
result      생성된 설계도 전체 JSON
created_at  생성 시각
```

## Key Decisions

- LLM 결과는 자유 텍스트가 아니라 Pydantic schema 기반 structured output으로 받습니다.
- API 응답 계약은 `BlueprintResponse`를 기준으로 고정합니다.
- 사용자-facing 설명은 한국어로 생성하고, API path, HTTP method, JSON type, DB type, constraint 같은 기술 식별자는 영어를 유지합니다.
- MVP 화면은 Streamlit으로 빠르게 검증하고, 다음 단계에서 React/Vite로 전환합니다.
- React/Vite 개발 서버 기본 origin인 `http://localhost:5173`을 CORS에 포함했습니다.
- 생성형 결과 특성상 Update는 MVP 범위에서 제외하고 Create/Read/Delete 중심으로 구성했습니다.

## Current Test Coverage

현재 테스트는 다음 영역을 검증합니다.

- `/health` 정상 응답
- React 개발 서버 origin CORS 허용
- blueprint 생성 API 기본 응답 형태
- 짧은 idea 입력 시 `422`
- 같은 idea 요청의 repository cache 재사용
- 저장된 설계도 목록 조회
- 저장된 설계도 상세 조회
- 저장된 설계도 삭제
- 없는 설계도 조회/삭제 시 `404`
- 품질 검증 규칙
- 품질 검증 실패 시 retry
- in-memory repository 저장/조회/clear

최근 확인 결과:

```powershell
python -m pytest
# 20 passed
```

## Next Work Candidates

다음 큰 방향은 React/Vite 프론트엔드의 UI 품질과 기능 안정성을 높이는 것입니다.

추천 순서:

1. React 개발 서버 실행 확인
2. 설계도 생성, 목록, 상세, 삭제 흐름 브라우저 검증
3. Mermaid ERD 및 sequence diagram 렌더링 확인
4. 화면 레이아웃과 모바일 대응 개선
5. Streamlit은 MVP 기록으로 유지하고 React를 메인 화면으로 전환
