# Dev Notes

## Current Status

DevBlueprint AI는 자연어 서비스 아이디어를 입력받아 개발자가 참고할 수 있는 시스템 설계도를 생성하고, 생성 결과를 저장/조회/삭제할 수 있는 MVP입니다.

현재 메인 화면은 React/Vite입니다. Streamlit은 초기 MVP 기록으로 `frontend/streamlit/`에 남겨두었습니다.

현재 구현된 주요 흐름:

- FastAPI 백엔드에서 설계도 생성 API 제공
- OpenAI Structured Outputs로 `BlueprintResponse` schema에 맞는 결과 생성
- `USE_OPENAI=false` 개발 모드에서는 OpenAI 호출 없이 placeholder 응답 사용
- 설계도 품질 검증 및 실패 시 feedback 기반 최대 3회 재시도
- Repository 계층을 통해 저장 방식 분리
- `REPOSITORY_BACKEND=memory` / `postgres` 선택 지원
- PostgreSQL `blueprints` 테이블에 설계도 결과 저장
- 같은 idea 요청은 `cache_key`로 DB 결과 재사용
- 저장된 설계도 목록 조회, 상세 조회, 삭제 API 제공
- React 화면에서 설계도 생성, 최근 설계도 조회, 상세 열기, 삭제 지원
- 결과 화면은 `요약 / 기능 / API / DB / 다이어그램` 탭으로 분리
- Markdown 다운로드 지원
- 다운로드 파일명은 사용자 idea 기반으로 생성
- Mermaid ERD와 sequence diagram 렌더링
- 다크 랜딩 히어로 + 실제 앱 대시보드 형태로 UI 개선 진행 중

## Tomorrow Setup

내일 노트북에서 이어서 작업할 때는 아래 순서로 확인합니다.

1. 저장소 최신 상태 받기
2. Python 가상환경 활성화
3. Python 의존성 설치 확인
4. Docker DB 실행
5. Alembic migration 적용
6. FastAPI 실행
7. React 실행
8. 브라우저에서 생성/저장/조회/삭제 확인

## Run Locally

프로젝트 루트에서 실행합니다.

```powershell
.\.venv\Scripts\activate
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

FastAPI 주소:

```text
http://localhost:8000
```

React 실행:

```powershell
cd frontend/react
npm install
npm run dev
```

React 주소:

```text
http://localhost:5173
```

FastAPI를 `8001`로 실행해야 하는 경우:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

이 경우 `frontend/react/.env.local`에 아래 값을 둡니다.

```env
VITE_API_BASE_URL=http://localhost:8001
```

## Environment

루트의 `.env.sample`을 기준으로 `.env`를 구성합니다.

실제 API key, DB user, DB password는 `.env`에만 둡니다. `.env.sample`, README, docs에는 실제 비밀번호를 적지 않습니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false

API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:8502,http://localhost:5173

REPOSITORY_BACKEND=memory

POSTGRES_DB=devblueprint
POSTGRES_USER=change_me_user
POSTGRES_PASSWORD=change_me_password
DATABASE_URL=postgresql+psycopg://change_me_user:change_me_password@localhost:5432/devblueprint
```

PostgreSQL 저장을 확인하려면:

```env
REPOSITORY_BACKEND=postgres
```

## API

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
DELETE /api/v1/blueprints/{blueprint_id}
```

## Frontend Notes

React 화면 구조:

- 상단 고정 navigation
- 다크 히어로 영역
- 아이디어 입력 카드
- 생성 산출물 카드
- 추천 아이디어 버튼
- 최근 설계도 카드 목록
- 결과 탭: 요약 / 기능 / API / DB / 다이어그램

주요 파일:

```text
frontend/react/src/App.jsx
frontend/react/src/styles.css
frontend/react/src/api.js
frontend/react/src/markdown.js
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
id                    설계도 고유 ID
cache_key             같은 idea 또는 같은 수정 요청 재사용을 위한 key
idea                  사용자가 입력한 원본 아이디어
revision_instruction  수정 요청으로 생성된 설계도의 원문 요청
result                생성된 설계도 전체 JSON
created_at            생성 시각
```

## Key Decisions

- LLM 결과는 자유 텍스트가 아니라 Pydantic schema 기반 structured output으로 받습니다.
- API 응답 계약은 `BlueprintResponse`를 기준으로 고정합니다.
- 사용자-facing 설명은 한국어로 생성하고, API path, HTTP method, JSON type, DB type, constraint 같은 기술 식별자는 영어를 유지합니다.
- Streamlit MVP로 빠르게 검증한 뒤 React/Vite를 메인 화면으로 전환했습니다.
- React/Vite 개발 서버 기본 origin인 `http://localhost:5173`을 CORS에 포함했습니다.
- 생성형 결과 특성상 Update는 MVP 범위에서 제외하고 Create/Read/Delete 중심으로 구성했습니다.
- 챗봇 수정 요청은 기존 설계도를 직접 덮어쓰지 않고 새 설계도로 저장합니다.
- 같은 원본 idea와 같은 수정 요청은 중복 생성하지 않고 `409`로 안내합니다.
- UI에서는 같은 idea 묶음을 `초안`, `개선안 1`, `개선안 2`로 표시합니다.
- 수정 요청 요약은 카드 제목과 경쟁하지 않도록 제목 아래 별도 한 줄로 표시합니다.

## 2026-05-21 작업 메모

오늘 정리된 주요 작업:

- 홈 화면 및 결과 영역 UI 간격/가독성 개선
- 기술 스택 영역 아이콘 기반 표시
- 생성 중 로딩/진행 메시지 개선
- 설계도 생성 품질 검증 및 retry 개선
- API field description, ERD table 누락 검증 보완
- 품질 게이트 UI 추가
- 파란색 로봇 느낌의 챗봇 진입 UI 추가
- 챗봇 기반 수정 요청 API 연결
- 중복 수정 요청 방지 및 챗봇 말풍선 안내
- 최근 설계도 카드에서 초안/개선안 구분
- 수정 요청 원문 저장 및 카드 요약 표시
- `revision_instruction` DB 컬럼 migration 추가

실행 환경 반영:

```powershell
docker compose up --build -d api
docker compose exec api python -m alembic upgrade head
```

현재 Docker API 상태 확인:

```text
GET /health
status: ok
use_openai: True
repository_backend: postgres
```

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
- 저장된 설계도 수정 요청
- 같은 수정 요청 중복 방지
- 없는 설계도 조회/삭제 시 `404`
- 품질 검증 규칙
- 품질 검증 실패 시 retry
- in-memory repository 저장/조회/clear

최근 확인 결과:

```powershell
python -m pytest
# 32 passed
```

React 빌드:

```powershell
cd frontend/react
npm run build
```

## Next Work Candidates

추천 순서:

1. 집 PC에서 FastAPI + React + Docker DB 실행 확인
2. React 화면에서 설계도 생성, 목록 조회, 상세 열기, 챗봇 수정, 삭제 흐름 확인
3. 긴 제목/긴 수정 요청이 최근 설계도 카드에서 깨지지 않는지 확인
4. 챗봇 수정 요청 성공 후 사용자가 새 설계도를 더 쉽게 인지할 수 있는 강조 UX 검토
5. 삭제를 실제 DB 삭제로 유지할지, `deleted_at` 기반 소프트 삭제로 바꿀지 결정
6. 모바일 화면 반응형 확인
7. Mermaid ERD 및 sequence diagram 렌더링 확인
8. README에 화면 스크린샷 추가 여부 검토
