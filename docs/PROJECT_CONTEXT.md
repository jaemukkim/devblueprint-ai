# DevBlueprint AI Project Context

## Project Overview

DevBlueprint AI는 자연어 서비스 아이디어를 개발자가 참고할 수 있는 시스템 설계도로 변환하는 AI 기반 설계 도구입니다.

입력 예시:

```text
실시간 채팅 앱을 만들고 싶어요. 사용자 인증, 채팅방 생성, 파일 공유 기능이 필요해요.
```

생성 결과:

- 서비스 개요
- 핵심 기능
- 추천 기술 스택
- REST API 설계
- 데이터베이스 schema
- Mermaid ERD
- Mermaid sequence diagram

## Current Scope

현재 프로젝트는 MVP 기능 구현과 React 기반 화면 개선 단계입니다.

구현된 범위:

- 자연어 idea 입력
- FastAPI API 호출
- OpenAI Structured Outputs 또는 placeholder 응답 생성
- Pydantic schema 검증
- 품질 검증 및 retry
- Repository cache 확인
- PostgreSQL 저장
- 저장된 설계도 목록/상세/삭제
- React 화면 표시
- Markdown 다운로드

아직 MVP 범위에서 제외한 것:

- 로그인
- 결제
- 팀 협업 권한
- 복잡한 배포 인프라
- 사용자별 workspace
- 설계도 수정 기능

## Tech Stack

Backend:

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy
- Alembic
- PostgreSQL
- Uvicorn

Frontend:

- React
- Vite
- Mermaid
- lucide-react

AI:

- OpenAI API
- Structured Outputs

Dev / Test:

- pytest
- Docker Compose

## Main User Flow

```text
User Idea
  -> React UI
  -> POST /api/v1/blueprint/generate
  -> Repository Cache Check
  -> OpenAI Structured Output or Placeholder
  -> Schema Validation
  -> Quality Validation
  -> Retry if Needed
  -> Repository Save
  -> React Result Tabs
```

## API Endpoints

```text
GET    /health
POST   /api/v1/blueprint/generate
GET    /api/v1/blueprints
GET    /api/v1/blueprints/{blueprint_id}
DELETE /api/v1/blueprints/{blueprint_id}
```

## Frontend Structure

React 화면은 현재 메인 화면입니다.

주요 UI:

- 상단 navigation
- 다크 랜딩 히어로
- 아이디어 입력 카드
- 생성 산출물 카드
- 추천 아이디어 버튼
- 최근 설계도 카드 목록
- 결과 탭

결과 탭:

```text
요약
기능
API
DB
다이어그램
```

## Backend Structure

```text
backend/app/
  api/              FastAPI router
  core/             환경 설정
  db/               SQLAlchemy session
  models/           ORM model
  repositories/     저장소 계층
  schemas/          API 및 LLM output schema
  services/         생성, 검증, OpenAI 연동 로직
```

## Data Persistence

Repository backend는 환경 변수로 선택합니다.

```env
REPOSITORY_BACKEND=memory
REPOSITORY_BACKEND=postgres
```

PostgreSQL `blueprints` table:

```text
id
cache_key
idea
result
created_at
```

같은 idea 요청은 `cache_key`를 통해 기존 결과를 재사용합니다.

## Prompt / Output Policy

사용자-facing 설명은 한국어로 생성합니다.

기술 식별자는 영어를 유지합니다.

예:

- API path
- HTTP method
- JSON type
- DB table
- DB column
- DB constraint
- framework/library 이름

## Current Verification

최근 확인:

```text
pytest: 20 passed
React build: npm run build 통과
```

## Next Direction

가까운 다음 작업 후보:

- 강의실 노트북에서 실행 환경 재현
- React 화면 브라우저 검증
- PostgreSQL 저장 흐름 재확인
- 모바일 반응형 세부 조정
- README 스크린샷 추가
