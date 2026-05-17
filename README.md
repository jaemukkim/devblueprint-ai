# DevBlueprint AI

AI-powered system architecture generator.

사용자가 자연어로 서비스 아이디어를 입력하면 기능 목록, 기술 스택, REST API 설계, DB 설계, 시퀀스 다이어그램을 구조화된 결과로 생성합니다.

## Features

- FastAPI 기반 blueprint 생성 API
- OpenAI Structured Outputs 기반 응답 schema 고정
- `USE_OPENAI=false` 개발 모드 지원
- 같은 idea 요청에 대한 in-memory cache
- Streamlit 결과 화면
- Markdown 다운로드
- 기본 API 테스트

## Project Structure

```text
backend/
  app/
    api/
    core/
    schemas/
    services/
frontend/
  streamlit_app.py
docs/
  PROJECT_CONTEXT.md
  examples/
tests/
```

## Environment

`.env.sample`을 참고해 `.env`를 만듭니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
USE_OPENAI=false
API_BASE_URL=http://localhost:8000
```

`USE_OPENAI=false`이면 API key가 있어도 OpenAI를 호출하지 않고 placeholder 응답을 사용합니다. 실제 LLM 결과를 확인할 때만 `USE_OPENAI=true`로 바꾸면 됩니다.

## Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

다른 터미널에서 Streamlit을 실행합니다.

```bash
streamlit run frontend/streamlit_app.py
```

## Tests

```bash
python -m pytest
```

## Example

예시 결과 문서는 [docs/examples/baseball_prediction_blueprint.md](docs/examples/baseball_prediction_blueprint.md)에서 확인할 수 있습니다.

## Notes

- 테스트는 외부 네트워크와 OpenAI 비용에 의존하지 않도록 `USE_OPENAI=false` 경로를 사용합니다.
- 현재 cache는 서버 메모리 기반이라 서버를 재시작하면 초기화됩니다.
- 장기 저장이 필요해지면 PostgreSQL이나 파일 기반 저장소로 확장할 수 있습니다.
