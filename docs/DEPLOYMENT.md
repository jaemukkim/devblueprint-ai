# 배포/운영 준비

DevBlueprint AI를 로컬 데모가 아니라 운영 가능한 서비스로 올리기 전에 확인할 항목을 정리한 문서입니다.

## 운영 구성

- Frontend: React/Vite 정적 빌드
- Backend: FastAPI + Uvicorn
- Database: PostgreSQL
- Migration: Alembic
- AI: OpenAI API

## 필수 환경 변수

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=true

REPOSITORY_BACKEND=postgres
DATABASE_URL=postgresql+psycopg://user:password@host:5432/devblueprint

FRONTEND_ORIGINS=https://your-frontend.example.com
```

운영에서는 `USE_OPENAI=true`, `REPOSITORY_BACKEND=postgres` 조합을 기준으로 둡니다. `FRONTEND_ORIGINS`에는 실제 프론트엔드 주소만 등록합니다.

## 배포 전 체크리스트

- `python -m alembic upgrade head` 실행
- `python -m pytest` 통과
- `cd frontend/react && npm.cmd run build` 통과
- `/health`에서 `use_openai=true`, `repository_backend=postgres` 확인
- OpenAI 실제 생성 샘플 3개 이상 성공 확인
- 설계도 목록, 상세 조회, 삭제 확인
- 섹션별 재생성 preview와 적용 확인
- 실행 이력 탭에서 specialist, route, 오류 상세, 소요 시간 확인
- Export ZIP 다운로드와 포함 파일 확인
- `.env`에 실제 비밀 값을 넣고 Git에는 커밋하지 않기

## Docker Compose 메모

현재 `docker-compose.yml`은 API를 `8000` 포트로 노출합니다. 로컬 직접 실행 권장 포트는 `8010`이므로, 실행 방식에 따라 프론트엔드의 `VITE_API_BASE_URL`을 맞춰야 합니다.

```text
로컬 직접 실행: http://localhost:8010
Docker Compose: http://localhost:8000
```

Docker Compose 실행:

```powershell
docker compose up --build
```

## 운영 리스크

- OpenAI rate limit, 결제 상태, 모델 권한 문제로 생성이 실패할 수 있습니다.
- 전체 설계도 생성은 요청 복잡도에 따라 40~90초 이상 걸릴 수 있습니다.
- Mermaid 출력은 정규화가 있지만, 모델 출력에 따라 추가 보정이 필요할 수 있습니다.
- 현재 인증/워크스페이스 격리가 없으므로 공개 운영 전 사용자 격리 설계가 필요합니다.
- 생성 요청 비용을 제어하려면 rate limit과 사용량 로깅이 필요합니다.

## 권장 다음 단계

1. 운영용 Dockerfile과 정적 프론트엔드 서빙 방식 확정
2. 사용자와 워크스페이스 테이블 추가
3. 설계도 soft delete 도입
4. 생성 요청 rate limit 추가
5. 구조화 로그와 request id 추가
6. OpenAI 품질 회귀 샘플을 CI에서 선택 실행
