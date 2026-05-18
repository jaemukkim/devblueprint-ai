import json
import os

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


# 로컬 개발에서는 .env의 API_BASE_URL 값을 먼저 읽어 FastAPI 주소를 맞춥니다.
load_dotenv()

# Streamlit 앱이 호출할 백엔드 API 주소입니다.
# 배포 환경에서는 API_BASE_URL 환경변수만 바꾸면 같은 화면 코드를 그대로 사용할 수 있습니다.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")

SAMPLE_IDEAS = [
    "챗봇을 이용한 쇼핑몰 고객상담 자동화 서비스",
    "개발자를 위한 AI 기반 API 설계 자동화 도구",
    "소상공인을 위한 예약 관리 및 고객 알림 서비스",
]


def render_list(title: str, items: list[str]) -> None:
    """기술 스택처럼 짧은 문자열 목록을 읽기 좋은 bullet 형태로 출력합니다."""
    st.markdown(f"**{title}**")
    if items:
        for item in items:
            st.markdown(f"- `{item}`")
    else:
        st.caption("MVP 단계에서는 사용하지 않습니다.")


def render_api_spec(api_spec: list[dict]) -> None:
    """API 설계 결과를 endpoint 단위로 접어서 보여줍니다."""
    for endpoint in api_spec:
        label = f"{endpoint['method']} {endpoint['path']}"
        with st.expander(label, expanded=True):
            st.write(endpoint["description"])

            left, right = st.columns(2)
            with left:
                st.markdown("**Request**")
                st.dataframe(endpoint["request"], use_container_width=True, hide_index=True)
            with right:
                st.markdown("**Response**")
                st.dataframe(endpoint["response"], use_container_width=True, hide_index=True)


def render_database_schema(database_schema: list[dict]) -> None:
    """테이블 설계 결과를 table 단위로 접어서 보여줍니다."""
    for table in database_schema:
        with st.expander(table["name"], expanded=True):
            st.write(table["description"])
            st.dataframe(table["columns"], use_container_width=True, hide_index=True)


def render_mermaid_diagram(source: str, height: int = 420) -> None:
    """Mermaid 코드를 HTML 컴포넌트 안에서 다이어그램으로 렌더링합니다."""
    mermaid_source = json.dumps(source)
    html = f"""
    <div class="mermaid" id="diagram"></div>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{ startOnLoad: false, theme: "default", securityLevel: "loose" }});
      const source = {mermaid_source};
      const target = document.getElementById("diagram");
      try {{
        const rendered = await mermaid.render("generated-diagram", source);
        target.innerHTML = rendered.svg;
      }} catch (error) {{
        target.innerHTML = `<pre style="white-space: pre-wrap; color: #b91c1c;">${{error}}</pre>`;
      }}
    </script>
    """
    components.html(html, height=height, scrolling=True)


def format_fields(fields: list[dict]) -> str:
    """API field 목록을 Markdown bullet로 변환합니다."""
    lines = []
    for field in fields:
        required = "required" if field.get("required") else "optional"
        lines.append(f"- `{field['name']}` ({field['type']}, {required}): {field['description']}")
    return "\n".join(lines) if lines else "- 없음"


def format_columns(columns: list[dict]) -> str:
    """DB column 목록을 Markdown bullet로 변환합니다."""
    lines = []
    for column in columns:
        constraints = ", ".join(column.get("constraints", [])) or "none"
        lines.append(f"- `{column['name']}` ({column['type']}, {constraints}): {column['description']}")
    return "\n".join(lines) if lines else "- 없음"


def blueprint_to_markdown(blueprint: dict) -> str:
    """생성된 설계도 JSON을 사람이 읽기 좋은 Markdown 문서로 변환합니다."""
    tech_stack = blueprint["tech_stack"]

    lines = [
        "# DevBlueprint AI Result",
        "",
        "## Overview",
        blueprint["overview"],
        "",
        "## Features",
    ]

    for feature in blueprint["features"]:
        lines.append(f"- **{feature['name']}** `{feature['priority']}`: {feature['description']}")

    lines.extend(
        [
            "",
            "## Tech Stack",
            f"- Backend: {', '.join(tech_stack['backend']) or 'none'}",
            f"- Frontend: {', '.join(tech_stack['frontend']) or 'none'}",
            f"- Database: {', '.join(tech_stack['database']) or 'none'}",
            f"- AI: {', '.join(tech_stack['ai']) or 'none'}",
            f"- Rationale: {tech_stack['rationale']}",
            "",
            "## API Spec",
        ]
    )

    for endpoint in blueprint["api_spec"]:
        lines.extend(
            [
                f"### {endpoint['method']} {endpoint['path']}",
                endpoint["description"],
                "",
                "#### Request",
                format_fields(endpoint["request"]),
                "",
                "#### Response",
                format_fields(endpoint["response"]),
                "",
            ]
        )

    lines.append("## Database Schema")
    for table in blueprint["database_schema"]:
        lines.extend([f"### {table['name']}", table["description"], "", format_columns(table["columns"]), ""])

    lines.extend(
        [
            "## Database ERD",
            "```mermaid",
            blueprint["database_erd"],
            "```",
            "",
            "## Sequence Diagram",
            "```mermaid",
            blueprint["sequence_diagram"],
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def show_request_error(exc: requests.RequestException) -> None:
    """백엔드 요청 실패 원인에 따라 사용자에게 다른 안내를 보여줍니다."""
    if isinstance(exc, requests.Timeout):
        st.error("요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.")
    elif isinstance(exc, requests.ConnectionError):
        st.error("백엔드 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해 주세요.")
        st.code("uvicorn app.main:app --app-dir backend --reload")
    else:
        st.error("API 요청 중 알 수 없는 오류가 발생했습니다.")
    st.caption(str(exc))


def show_api_error(response: requests.Response) -> None:
    """백엔드가 반환한 에러 응답을 가능한 한 읽기 좋게 표시합니다."""
    try:
        error_body = response.json()
    except ValueError:
        error_body = {"detail": response.text}

    if response.status_code == 503:
        st.error("설계도 생성 서비스가 일시적으로 응답하지 않습니다.")
    elif response.status_code == 422:
        st.error("입력값 형식이 올바르지 않습니다.")
    else:
        st.error(f"API 요청에 실패했습니다. status_code={response.status_code}")

    st.code(json.dumps(error_body, ensure_ascii=False, indent=2), language="json")


def request_blueprint(idea: str) -> dict | None:
    """설계도 생성 API를 호출하고 성공 시 결과 JSON을 반환합니다."""
    try:
        with st.spinner("설계도를 생성하고 있어요. 잠시만 기다려 주세요."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/blueprint/generate",
                json={"idea": idea},
                timeout=120,
            )
    except requests.RequestException as exc:
        show_request_error(exc)
        return None

    if not response.ok:
        show_api_error(response)
        return None

    return response.json()


def request_recent_blueprints() -> list[dict]:
    """최근 저장된 설계도 목록 API를 호출합니다."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/blueprints", timeout=10)
    except requests.RequestException as exc:
        st.sidebar.caption("최근 설계도 목록을 불러오지 못했습니다.")
        st.sidebar.caption(str(exc))
        return []

    if not response.ok:
        st.sidebar.caption(f"최근 설계도 목록 요청 실패: {response.status_code}")
        return []

    return response.json().get("items", [])


def request_stored_blueprint(blueprint_id: str) -> dict | None:
    """저장된 설계도 상세 API를 호출하고 result만 반환합니다."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/blueprints/{blueprint_id}", timeout=20)
    except requests.RequestException as exc:
        show_request_error(exc)
        return None

    if not response.ok:
        show_api_error(response)
        return None

    return response.json()["result"]


def delete_stored_blueprint(blueprint_id: str) -> bool:
    """저장된 설계도 삭제 API를 호출합니다."""
    try:
        response = requests.delete(f"{API_BASE_URL}/api/v1/blueprints/{blueprint_id}", timeout=20)
    except requests.RequestException as exc:
        show_request_error(exc)
        return False

    if response.status_code == 204:
        return True

    show_api_error(response)
    return False


def render_recent_blueprints() -> None:
    """사이드바에 최근 저장된 설계도 목록을 표시합니다."""
    st.sidebar.header("최근 설계도")

    if st.sidebar.button("새로고침", use_container_width=True):
        st.session_state.recent_blueprints = request_recent_blueprints()

    recent_blueprints = st.session_state.recent_blueprints
    if not recent_blueprints:
        st.sidebar.caption("저장된 설계도가 아직 없습니다.")
        return

    for item in recent_blueprints:
        idea = item["idea"]
        label = idea if len(idea) <= 24 else f"{idea[:24]}..."
        open_col, delete_col = st.sidebar.columns([4, 1])

        if open_col.button(label, key=f"recent-{item['id']}", use_container_width=True):
            blueprint = request_stored_blueprint(item["id"])
            if blueprint:
                st.session_state.blueprint = blueprint
                st.session_state.current_blueprint_id = item["id"]
                st.session_state.idea = idea

        if delete_col.button("삭제", key=f"delete-{item['id']}", use_container_width=True):
            if delete_stored_blueprint(item["id"]):
                st.session_state.recent_blueprints = request_recent_blueprints()

                if st.session_state.current_blueprint_id == item["id"]:
                    st.session_state.blueprint = None
                    st.session_state.current_blueprint_id = None

                st.rerun()


def render_blueprint(blueprint: dict) -> None:
    """생성된 설계도 결과를 화면에 렌더링합니다."""
    st.subheader("개요")
    st.write(blueprint["overview"])

    st.subheader("핵심 기능")
    st.dataframe(blueprint["features"], use_container_width=True, hide_index=True)

    st.subheader("기술 스택")
    stack_col_1, stack_col_2, stack_col_3, stack_col_4 = st.columns(4)
    with stack_col_1:
        render_list("Backend", blueprint["tech_stack"]["backend"])
    with stack_col_2:
        render_list("Frontend", blueprint["tech_stack"]["frontend"])
    with stack_col_3:
        render_list("Database", blueprint["tech_stack"]["database"])
    with stack_col_4:
        render_list("AI", blueprint["tech_stack"]["ai"])
    st.info(blueprint["tech_stack"]["rationale"])

    st.subheader("API 설계")
    render_api_spec(blueprint["api_spec"])

    st.subheader("데이터베이스 설계")
    render_database_schema(blueprint["database_schema"])

    st.subheader("데이터베이스 ERD")
    erd_tab, erd_code_tab = st.tabs(["Diagram", "Code"])
    with erd_tab:
        render_mermaid_diagram(blueprint["database_erd"], height=420)
    with erd_code_tab:
        st.code(blueprint["database_erd"], language="mermaid")

    st.subheader("시퀀스 다이어그램")
    sequence_tab, sequence_code_tab = st.tabs(["Diagram", "Code"])
    with sequence_tab:
        render_mermaid_diagram(blueprint["sequence_diagram"], height=460)
    with sequence_code_tab:
        st.code(blueprint["sequence_diagram"], language="mermaid")

    st.download_button(
        "Markdown 다운로드",
        data=blueprint_to_markdown(blueprint),
        file_name="devblueprint-result.md",
        mime="text/markdown",
    )

    with st.expander("원본 JSON 보기"):
        st.json(blueprint)


st.set_page_config(page_title="DevBlueprint AI", layout="wide")
st.title("DevBlueprint AI")

if "idea" not in st.session_state:
    st.session_state.idea = ""
if "blueprint" not in st.session_state:
    st.session_state.blueprint = None
if "current_blueprint_id" not in st.session_state:
    st.session_state.current_blueprint_id = None
if "recent_blueprints" not in st.session_state:
    st.session_state.recent_blueprints = request_recent_blueprints()

render_recent_blueprints()

sample_cols = st.columns(len(SAMPLE_IDEAS))
for index, sample_idea in enumerate(SAMPLE_IDEAS):
    with sample_cols[index]:
        if st.button(f"예시 {index + 1}", use_container_width=True):
            st.session_state.idea = sample_idea

# 사용자가 자연어로 서비스 아이디어를 입력하는 영역입니다.
# MVP에서는 이 입력값 하나로 전체 설계도 생성을 시작합니다.
idea = st.text_area(
    "서비스 아이디어",
    key="idea",
    placeholder="예: 스포츠 야구 분석 및 승부 예측 서비스",
    height=140,
)

if st.button("설계도 생성", type="primary"):
    if not idea.strip():
        st.warning("서비스 아이디어를 입력해 주세요.")
    else:
        blueprint = request_blueprint(idea)
        if blueprint:
            st.session_state.blueprint = blueprint
            st.session_state.current_blueprint_id = None
            st.session_state.recent_blueprints = request_recent_blueprints()
            st.rerun()

if st.session_state.blueprint:
    render_blueprint(st.session_state.blueprint)
