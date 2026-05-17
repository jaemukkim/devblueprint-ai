import os

import requests
import streamlit as st


# Streamlit 앱이 호출할 백엔드 API 주소입니다.
# 배포 환경에서는 API_BASE_URL 환경변수만 바꾸면 같은 화면 코드를 그대로 사용할 수 있습니다.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


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


st.set_page_config(page_title="DevBlueprint AI", layout="wide")
st.title("DevBlueprint AI")

# 사용자가 자연어로 서비스 아이디어를 입력하는 영역입니다.
# MVP에서는 이 입력값 하나로 전체 설계도 생성을 시작합니다.
idea = st.text_area(
    "서비스 아이디어",
    placeholder="예: 스포츠 야구 분석 및 승부 예측 서비스",
    height=140,
)

if st.button("설계도 생성", type="primary"):
    if not idea.strip():
        st.warning("서비스 아이디어를 입력해 주세요.")
    else:
        # 버튼을 누르면 FastAPI 백엔드에 아이디어를 전달하고 구조화된 설계도 응답을 받습니다.
        with st.spinner("설계도를 생성하는 중입니다..."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/blueprint/generate",
                json={"idea": idea},
                timeout=120,
            )

        if response.ok:
            blueprint = response.json()

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

            st.subheader("시퀀스 다이어그램")
            st.code(blueprint["sequence_diagram"], language="mermaid")

            with st.expander("원본 JSON 보기"):
                st.json(blueprint)
        else:
            st.error(f"API 요청에 실패했습니다: {response.status_code}")
            st.code(response.text)
