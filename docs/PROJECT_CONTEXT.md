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
- 비기능 요구사항
- 보안 고려사항
- 구현 계획

## Current Scope

현재 프로젝트는 MVP 기능 구현과 React 기반 화면 안정화 단계입니다.

구현된 범위:

- 자연어 idea 입력
- FastAPI API 호출
- OpenAI Structured Outputs 또는 placeholder 응답 생성
- Pydantic schema 검증
- 설계도 품질 검증 및 retry
- Repository cache 확인
- PostgreSQL 저장
- 저장된 설계도 목록/상세/삭제
- 수정 요청 기반 새 설계도 생성
- 섹션별 재생성 미리보기
- 섹션별 재생성 미리보기 적용
- React 화면 표시
- Mermaid 다이어그램 렌더링 및 오류 표시
- Markdown 다운로드

아직 MVP 범위에서 제외한 것:

- 로그인
- 결제
- 팀 작업 권한
- 복잡한 배포 인프라
- 사용자별 workspace
- 설계도 직접 편집 기능

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
  -> Mermaid Normalization
  -> Repository Save
  -> React Result Tabs
```

## Revision Flow

```text
Saved Blueprint
  -> User Revision Instruction
  -> Duplicate Revision Check
  -> OpenAI Revision Prompt or Placeholder
  -> Quality Validation
  -> Mermaid Normalization
  -> Save as New Blueprint
  -> Recent List Badge as 개선안
```

## Section Regeneration Flow

```text
Saved Blueprint
  -> Select Section
  -> Regenerate Preview
  -> Review Changed Result
  -> Apply Preview
  -> Save as New Blueprint
```

섹션 재생성은 미리보기 단계와 저장 단계를 분리합니다. 미리보기만 생성한 상태에서는 원본 설계도가 바뀌지 않습니다.

## API Endpoints

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

## Frontend Structure

React 화면은 현재 메인 화면입니다.

주요 UI:

- 상단 navigation
- 스크롤 히어로
- 아이디어 입력 카드
- 생성 출력물 카드
- 추천 아이디어 버튼
- 최근 설계도 카드 목록
- 결과 탭
- 상세 화면
- 수정 요청 챗봇
- 섹션별 재생성 미리보기
- Mermaid 다이어그램 오류 표시

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
  services/         생성, 검증, OpenAI 연동, Mermaid 정규화 로직
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
revision_instruction
result
created_at
```

같은 idea 요청은 `cache_key`를 통해 기존 결과를 재사용합니다. 같은 원본 설계도와 같은 수정 요청도 중복 생성하지 않습니다.

## Mermaid Policy

LLM이 생성한 Mermaid 코드는 저장 전과 렌더링 전에 정규화합니다.

정규화 대상:

- Markdown code fence
- ERD key token: `PK FK`, `UNIQUE`, `UQ`
- SQL 타입: `timestamp with time zone`, `varchar(255)`, `decimal(10,2)`, `text[]`
- ERD 제약 조건: `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `NULL`

저장된 예전 설계도도 repository 조회 시 정규화된 결과로 반환합니다. 원본 저장 JSON을 강제로 수정하지는 않습니다.

## Prompt / Output Policy

사용자 facing 설명은 한국어로 생성합니다.

기술 명세에는 영어를 유지합니다.

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
pytest: 60 passed
React build: npm run build 통과
```

검증된 주요 영역:

- API 기본 동작
- 저장소 cache
- 수정 요청
- 섹션별 재생성
- 미리보기 적용
- Mermaid 정규화
- 저장된 예전 Mermaid 결과 조회 안정화
- OpenAI retry

## Next Direction

가까운 다음 작업 후보:

- 실제 OpenAI 호출 기준 대표 아이디어 회귀 테스트
- 저장된 설계도 검색/필터/정렬 UX
- 삭제 확인과 복구 가능성 검토
- 섹션별 재생성 diff 표시 고도화
- 모바일 화면 반응형 점검
- 배포 환경 변수와 운영 실행 문서 정리
