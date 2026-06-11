# 배포/운영 준비

DevBlueprint AI를 로컬 데모에서 운영 가능한 서비스로 올리기 위한 체크리스트입니다.

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

## 배포 전 체크리스트

- `python -m alembic upgrade head` 실행
- `python -m pytest` 또는 핵심 테스트 세트 통과
- `cd frontend/react && npm run build` 통과
- `FRONTEND_ORIGINS`에는 실제 프론트 주소만 등록
- `.env`에는 실제 비밀값을 넣고 Git에는 커밋하지 않기
- `/health`에서 `use_openai=true`, `repository_backend=postgres` 확인
- OpenAI 실제 샘플 3개 이상 생성 확인
- Export ZIP 다운로드 확인

## Docker Compose 메모

현재 `docker-compose.yml`은 API를 `8000` 포트로 노출합니다. 로컬 권장 개발 포트는 `8010`이므로, 운영 또는 Docker 환경에서는 프론트의 `VITE_API_BASE_URL`을 실제 API 주소에 맞춰야 합니다.

## 운영 리스크

- OpenAI rate limit 또는 결제 상태에 따라 생성이 실패할 수 있습니다.
- 설계도 생성은 40~90초까지 걸릴 수 있습니다.
- Mermaid 출력은 정규화가 있지만 모델 출력에 따라 추가 보정이 필요할 수 있습니다.
- 현재 인증/워크스페이스가 없으므로 공개 운영 전 사용자 격리 설계가 필요합니다.

## 권장 다음 단계

1. 운영용 Dockerfile과 정적 프론트 서빙 방식 확정
2. 사용자/워크스페이스 테이블 추가
3. 설계도 soft delete 도입
4. 생성 요청 rate limit 추가
5. 구조화 로그와 요청 ID 추가
