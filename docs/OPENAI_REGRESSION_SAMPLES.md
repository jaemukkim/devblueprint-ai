# OpenAI 회귀 테스트 샘플

실제 OpenAI 호출 품질을 확인할 때 사용하는 대표 아이디어 목록입니다. 자동 테스트에서는 프롬프트 보존과 도메인 용어 기준만 확인하고, 수동 점검에서는 실제 생성 결과의 API, DB, Mermaid, 품질 리포트를 함께 확인합니다.

## 평가 기준

- 생성 성공 여부
- 기능 5~8개, API 4~8개, DB 테이블 3~6개 범위 유지
- API resource와 DB table의 도메인 일관성
- Mermaid ERD와 sequence diagram 렌더링 성공
- 품질 리포트 90점 이상 권장
- 실행 이력에서 실패 단계와 소요 시간 확인 가능
- Export ZIP에 모든 산출물 파일 포함

## 대표 샘플

1. 냉장고 재료 기반 요리 추천 서비스
2. 독서 기록과 문장 수집 앱
3. 풋살장 예약과 팀/개인 매칭 서비스
4. 소셜 로그인이 있는 개발자 커뮤니티
5. 고객 문의와 주문 상태 관리자 대시보드

## 수동 실행 절차

1. `.env`에서 `USE_OPENAI=true`를 설정합니다.
2. FastAPI와 React를 실행합니다.
3. 위 샘플을 하나씩 생성합니다.
4. 결과 탭에서 요약, API, DB, 다이어그램, 실행 이력을 확인합니다.
5. Export ZIP을 내려받아 `README.md`, `api-spec.md`, `database-schema.md`, `quality-report.md`, `erd.mmd`, `sequence.mmd` 포함 여부를 확인합니다.
