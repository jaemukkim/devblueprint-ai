# Dev Notes

## Current Status

DevBlueprint AI는 자연어 서비스 아이디어를 입력받아 개발자가 참고할 수 있는 시스템 설계도를 생성하고, 생성 결과를 저장/조회/삭제할 수 있는 MVP입니다.

현재 메인 화면은 React/Vite입니다. Streamlit은 초기 MVP 기록용으로 `frontend/streamlit/`에 보관되어 있습니다.

현재 구현된 주요 흐름:

- FastAPI 백엔드에서 설계도 생성 API 제공
- OpenAI Structured Outputs로 `BlueprintResponse` schema에 맞는 결과 생성
- `USE_OPENAI=false` 개발 모드에서 OpenAI 호출 없이 placeholder 응답 사용
- 설계도 schema 검증 및 실패 시 feedback 기반 최대 3회 재시도
- Repository 계층을 통해 저장 방식 분리
- `REPOSITORY_BACKEND=memory` / `postgres` 선택 지원
- PostgreSQL `blueprints` 테이블에 설계도 결과 저장
- 같은 idea 요청은 `cache_key`로 DB 결과 재사용
- 저장된 설계도 목록 조회, 상세 조회, 삭제 API 제공
- React 화면에서 설계도 생성, 최근 설계도 조회, 상세 열기, 삭제 지원
- 결과 화면은 `요약 / 기능 / API / DB / 다이어그램` 탭으로 분리
- Markdown 다운로드 지원
- Mermaid ERD와 sequence diagram 렌더링
- Mermaid 코드는 백엔드 저장 전과 프론트 렌더링 전에 정규화
- 저장된 예전 설계도는 조회 시 정규화된 Mermaid 결과로 반환
- Mermaid 오류는 다이어그램별로 분리 표시하고 가능한 line 정보를 함께 제공
- 챗봇 기반 수정 요청 API와 UI 연결
- 섹션별 설계도 재생성 미리보기 및 미리보기 적용 지원
- 중복 수정 요청 방지 및 사용자 안내
- 구조화된 API 오류 응답을 프론트에서 사용자 메시지로 변환

## Local Setup

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
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010
```

FastAPI 주소:

```text
http://localhost:8010
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

로컬 개발에서는 Docker로 PostgreSQL만 실행하고, FastAPI와 React는 호스트에서 실행하는 구성을 권장합니다.

## Environment

루트의 `.env.sample`을 기준으로 `.env`를 구성합니다.

실제 API key, DB user, DB password는 `.env`에만 둡니다. `.env.sample`, README, docs에는 실제 비밀번호를 적지 않습니다.

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

PostgreSQL 저장을 확인하려면:

```env
REPOSITORY_BACKEND=postgres
```

React API 주소:

```env
VITE_API_BASE_URL=http://localhost:8010
```

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

## Frontend Notes

React 화면 구조:

- 상단 고정 navigation
- 스크롤 히어로 영역
- 아이디어 입력 카드
- 생성 출력물 카드
- 추천 아이디어 버튼
- 최근 설계도 카드 목록
- 결과 탭: 요약 / 기능 / API / DB / 다이어그램
- 상세 화면의 수정 요청 챗봇
- 섹션별 재생성 미리보기와 적용 버튼

주요 파일:

```text
frontend/react/src/App.jsx
frontend/react/src/styles.css
frontend/react/src/api.js
frontend/react/src/markdown.js
frontend/react/src/mermaid.js
```

## Architecture Notes

백엔드는 다음 책임으로 나뉩니다.

- `api/`: FastAPI router와 endpoint 정의
- `schemas/`: API request/response 및 LLM structured output 계약
- `services/`: 설계도 생성, OpenAI 호출, prompt 구성, 품질 검증, Mermaid 정규화
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
- 사용자 facing 설명은 한국어로 생성하고, API path, HTTP method, JSON type, DB type, constraint 같은 기술 명세는 영어를 유지합니다.
- React/Vite 개발 서버 기본 origin인 `http://localhost:5173`을 CORS에 포함합니다.
- 수정 요청은 기존 설계도를 직접 덮어쓰지 않고 새 설계도로 저장합니다.
- 섹션 재생성 미리보기는 사용자가 적용할 때만 새 개선안으로 저장합니다.
- 같은 원본 idea와 같은 수정 요청은 중복 생성하지 않고 `409`로 안내합니다.
- Mermaid 정규화는 백엔드와 프론트엔드 양쪽에 둡니다. 백엔드는 저장/조회 안정성을, 프론트는 렌더링 직전 안전망을 담당합니다.
- OpenAI 클라이언트는 로컬 프록시 환경 변수 영향을 피하도록 `trust_env=False`로 생성합니다.

## Current Test Coverage

현재 테스트는 다음 영역을 검증합니다.

- `/health` 정상 응답
- React 개발 서버 origin CORS 허용
- blueprint 생성 API 기본 응답 형태
- 빈 idea 입력 시 `422`
- 같은 idea 요청 시 repository cache 재사용
- 저장된 설계도 목록 조회
- 저장된 설계도 상세 조회
- 저장된 설계도 삭제
- 저장된 설계도 수정 요청
- 섹션별 설계도 재생성
- 섹션 재생성 미리보기 적용
- 같은 수정 요청 중복 방지
- 없는 설계도 조회/삭제 시 `404`
- 설계도 품질 검증 규칙
- 설계도 품질 검증 실패 시 retry
- Mermaid 정규화
- 저장소 조회 시 예전 Mermaid 결과 정규화
- in-memory repository 저장/조회/clear

최근 확인 결과:

```powershell
python -m pytest tests/test_blueprint_normalizer.py tests/test_blueprint_repository.py tests/test_blueprint_api.py tests/test_blueprint_validator.py tests/test_blueprint_retry.py
# 60 passed
```

React 빌드:

```powershell
cd frontend/react
npm run build
```

## Known Notes

- pytest cache provider는 Windows 권한 경고를 피하기 위해 `pytest.ini`에서 비활성화했습니다.
- Mermaid lazy chunk가 커서 Vite chunk size warning이 보일 수 있습니다. 현재 빌드는 통과합니다.
- FastAPI를 재시작할 때는 uvicorn 프로세스만 종료합니다. Docker Desktop이나 DB 컨테이너를 같이 종료할 필요는 없습니다.

## Next Work Candidates

추천 순서:

1. 실제 OpenAI 호출 기준으로 대표 아이디어 2~3개 회귀 테스트
2. 저장된 설계도 관리 UX 개선: 검색, 필터, 정렬, 삭제 확인
3. 섹션별 재생성 결과 diff 표시 고도화
4. 모바일 화면에서 생성, 상세, 재생성, 삭제 흐름 확인
5. 배포 준비: 환경 변수 점검, CORS origin 정리, 운영용 실행 방식 문서화
6. Mermaid lazy chunk 최적화 또는 Vite `manualChunks` 설정 검토
