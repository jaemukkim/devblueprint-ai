# Blueprint Quality Checklist

DevBlueprint AI의 생성 결과가 MVP 구현에 실제로 도움이 되는지 확인하기 위한 기준입니다.

## 생성 결과 기준

- 기능은 사용자의 서비스 도메인에 맞아야 하며, placeholder성 기능명은 피합니다.
- 기능 설명은 사용자의 구체적 행동이나 백엔드 책임을 설명해야 합니다.
- API path는 `/items`, `/records`, `/data`, `/results` 같은 generic resource를 피합니다.
- 같은 HTTP method와 path 조합이 중복되면 안 됩니다.
- API request/response field는 프론트엔드가 바로 연결할 수 있을 만큼 이름, 타입, 설명이 구체적이어야 합니다.
- DB table은 최소 3개 이상의 column과 `primary_key` column을 포함해야 합니다.
- DB table과 column 이름은 snake_case를 사용해야 합니다.
- ERD에는 `database_schema`에 있는 모든 table이 포함되어야 합니다.
- sequence diagram은 주요 사용자 흐름 하나를 화면, API, 저장소 단계까지 보여줘야 합니다.

## 개선 루프

1. 샘플 아이디어로 설계도를 생성합니다.
2. 위 기준에서 실패한 항목을 기록합니다.
3. 단순 표현 문제는 prompt에 반영합니다.
4. 반복적으로 발생하는 구조 문제는 validator에 반영합니다.
5. prompt를 바꾼 경우 `BLUEPRINT_PROMPT_VERSION`을 올려 기존 cache와 분리합니다.
