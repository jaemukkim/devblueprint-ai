# Dev Notes

## Current Status

DevBlueprint AI는 자연어 서비스 아이디어를 입력받아 개발자가 참고할 수 있는 시스템 설계도를 생성하는 MVP입니다.

현재 구현된 주요 흐름은 다음과 같습니다.

- FastAPI 백엔드에서 `/api/v1/blueprint/generate` API 제공
- OpenAI Structured Outputs로 `BlueprintResponse` schema에 맞는 결과 생성
- `USE_OPENAI=false` 개발 모드에서는 OpenAI 호출 없이 placeholder 응답 사용
- 같은 idea 요청은 repository 계층을 통해 재사용
- Pydantic schema 검증 후 별도 품질 검증 레이어 실행
- 품질 검증 실패 시 OpenAI 결과를 feedback 기반으로 최대 3회 재시도
- Streamlit MVP 화면에서 결과 표시
- Markdown 다운로드 지원
- Mermaid ERD와 sequence diagram 렌더링
- React 전환을 고려한 CORS 설정 추가
- PostgreSQL 도입을 위한 DB/session/model 기본 구조 준비

## Run Locally

백엔드 실행:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Streamlit 실행:

```bash
streamlit run frontend/streamlit_app.py
```

테스트 실행:

```bash
python -m pytest
```

## Environment

`.env.sample`을 기준으로 `.env`를 구성합니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGINS=http://localhost:8501,http://localhost:5173
DATABASE_URL=postgresql+psycopg://devblueprint:devblueprint@localhost:5432/devblueprint
```

`USE_OPENAI=false`이면 API key가 있어도 실제 OpenAI 호출을 하지 않습니다. 실제 LLM 결과를 확인할 때만 `USE_OPENAI=true`로 바꿉니다.

## Architecture Notes

백엔드는 다음 책임으로 나뉩니다.

- `api/`: FastAPI router와 endpoint 정의
- `schemas/`: API request/response 및 LLM structured output 계약
- `services/`: 설계도 생성, OpenAI 호출, prompt 구성, 품질 검증
- `repositories/`: 설계도 결과 저장/조회 책임
- `db/`: SQLAlchemy engine/session 준비
- `models/`: 향후 PostgreSQL 저장을 위한 ORM model
- `core/`: 환경 설정

현재 repository 구현체는 `InMemoryBlueprintRepository`입니다. PostgreSQL을 붙일 때는 같은 repository 인터페이스를 유지하면서 DB 기반 구현체를 추가하는 방향이 좋습니다.

## Key Decisions

- LLM 결과는 자유 텍스트가 아니라 Pydantic schema 기반 structured output으로 받습니다.
- API 응답 계약은 `BlueprintResponse`를 기준으로 고정합니다.
- 사용자-facing 설명은 한국어로 생성하고, API path, HTTP method, JSON type, DB type, constraint 같은 기술 식별자는 영어를 유지합니다.
- MVP에서는 Streamlit을 사용하지만, 장기적으로 React 전환을 고려합니다.
- React/Vite 개발 서버 기본 origin인 `http://localhost:5173`을 CORS에 포함했습니다.
- PostgreSQL은 아직 API 흐름에 연결하지 않고, SQLAlchemy/Alembic 도입을 위한 기본 구조만 준비했습니다.

## Current Test Coverage

현재 테스트는 다음 영역을 검증합니다.

- `/health` 정상 응답
- blueprint 생성 API 기본 응답 형태
- 짧은 idea 입력 시 `422`
- 같은 idea 요청의 repository cache 재사용
- React 개발 서버 origin CORS 허용
- 품질 검증 규칙
- 품질 검증 실패 시 retry
- in-memory repository 저장/조회/clear

## Next Work Candidates

장기 방향 기준으로 다음 작업 후보는 아래 순서가 자연스럽습니다.

1. Alembic 초기 설정 추가
2. `blueprints` 테이블 migration 생성
3. `PostgresBlueprintRepository` 구현
4. `USE_DATABASE` 또는 repository 선택 설정 추가
5. React/Vite 프론트엔드 새로 구성
6. Streamlit 화면과 React 화면을 병행하다가 React로 전환
7. README를 포트폴리오 제출용으로 정리
