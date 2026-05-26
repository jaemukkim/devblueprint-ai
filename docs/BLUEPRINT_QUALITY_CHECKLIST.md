# Blueprint Quality Checklist

DevBlueprint AI의 생성 결과가 MVP 구현에 실제로 참고 가능한지 확인하기 위한 기준입니다.

## 생성 결과 기준

- 기능은 사용자의 서비스 도메인에 맞아야 하며, placeholder성 기능명은 피합니다.
- 기능 설명은 사용자의 구체적인 행동이나 백엔드 책임을 설명해야 합니다.
- API path는 `/items`, `/records`, `/data`, `/results` 같은 generic resource를 피합니다.
- 같은 HTTP method와 path 조합이 중복되면 안 됩니다.
- API request/response field는 프론트엔드가 바로 연결할 수 있을 만큼 이름, 타입, 설명이 구체적이어야 합니다.
- DB table은 최소 3개 이상의 column과 `primary_key` column을 포함해야 합니다.
- DB table과 column 이름은 snake_case를 사용해야 합니다.
- ERD에는 `database_schema`에 있는 모든 table이 포함되어야 합니다.
- ERD 관계는 실제 table 이름과 column 이름을 기준으로 작성되어야 합니다.
- Sequence diagram은 주요 사용자 흐름 하나를 화면, API, 저장소 단계까지 보여줘야 합니다.
- 비기능 요구사항은 성능, 안정성, 관측성, 확장성 중 실제 서비스에 필요한 항목을 다뤄야 합니다.
- 보안 고려사항은 인증, 권한, 입력 검증, 민감정보 저장 여부를 포함해야 합니다.
- 구현 계획은 MVP에서 바로 시작 가능한 순서여야 합니다.

## Mermaid 기준

- Mermaid 코드는 Markdown code fence 없이 렌더링 가능한 본문만 저장되는 것이 가장 좋습니다.
- ERD key token은 `PK`, `FK`, `UK`를 사용합니다.
- 여러 key token이 함께 붙는 경우 `PK, FK`처럼 comma로 구분합니다.
- `UNIQUE`, `UQ`처럼 Mermaid ERD에서 불안정한 token은 `UK`로 정규화합니다.
- `timestamp with time zone`, `varchar(255)`, `decimal(10,2)`, `text[]`처럼 공백이나 괄호가 있는 SQL 타입은 Mermaid가 읽을 수 있는 형태로 정규화합니다.
- `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `NULL` 같은 SQL 제약 문장은 Mermaid ERD attribute line에 그대로 남기지 않습니다.
- 하나의 다이어그램 오류가 다른 다이어그램 렌더링까지 막지 않아야 합니다.

## 개선 루프

1. 샘플 아이디어로 설계도를 생성합니다.
2. 위 기준에서 실패한 항목을 기록합니다.
3. 단순 표현 문제는 prompt에 반영합니다.
4. 반복적으로 발생하는 구조 문제는 validator에 반영합니다.
5. Mermaid 문법 문제는 normalizer와 frontend 렌더링 안전망에 반영합니다.
6. prompt를 바꿀 경우 `BLUEPRINT_PROMPT_VERSION`을 올려 기존 cache와 분리합니다.

## 회귀 테스트 후보

- 호텔 예약 서비스
- 풋살장 예약 서비스
- 배드민턴 복식 팀 매칭 서비스
- 인증과 결제가 포함된 커머스 서비스
- 실시간 알림이 포함된 커뮤니티 서비스
