# 사용자/워크스페이스 설계 초안

현재 DevBlueprint AI는 단일 로컬 사용자 또는 데모 환경을 기준으로 설계되어 있습니다. 여러 사용자가 지속적으로 쓰는 서비스가 되려면 사용자와 워크스페이스 개념이 필요합니다.

## 목표

- 사용자별 설계도 격리
- 팀 또는 프로젝트 단위 설계도 관리
- 초안, 개선본, 섹션 재생성 결과의 히스토리 추적
- Export 산출물과 실행 이력을 같은 워크스페이스 안에서 관리

## 1차 데이터 모델

```text
users
  id
  email
  display_name
  created_at

workspaces
  id
  owner_user_id
  name
  created_at

workspace_members
  id
  workspace_id
  user_id
  role
  created_at

blueprints
  id
  workspace_id
  cache_key
  idea
  revision_instruction
  result
  created_at

blueprint_run_events
  id
  blueprint_id
  run_type
  node_name
  specialist_id
  phase
  retry_count
  route
  error_count
  error_messages
  duration_ms
  created_at
```

## 권한 모델

- `owner`: 워크스페이스 설정, 멤버 관리, 삭제 가능
- `editor`: 설계도 생성, 재생성, Export 가능
- `viewer`: 설계도 조회와 Export만 가능

## API 변경 방향

- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}/blueprints`
- `POST /api/v1/workspaces/{workspace_id}/blueprint/generate`
- 기존 `/api/v1/blueprints/{blueprint_id}` 계열은 권한 확인 추가

## UI 변경 방향

- 상단에 현재 워크스페이스 선택기 추가
- 최근 설계도 목록을 워크스페이스 범위로 필터링
- 설계도 카드에 생성자, 개선본 번호, 마지막 실행 상태 표시
- 실행 이력 탭에 워크스페이스 멤버가 볼 수 있는 공유 디버그 정보 표시

## 도입 순서

1. DB schema에 `workspace_id` nullable 컬럼 추가
2. 기존 설계도는 기본 워크스페이스로 마이그레이션
3. API repository query에 workspace scope 추가
4. 프론트에 워크스페이스 선택기 추가
5. 로그인과 멤버 권한은 마지막 단계에서 연결
