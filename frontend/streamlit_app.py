import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


st.set_page_config(page_title="DevBlueprint AI", layout="wide")
st.title("DevBlueprint AI")

# 사용자가 자연어로 서비스 아이디어를 입력하는 영역입니다.
# MVP에서는 이 입력값 하나만으로 전체 설계도 생성을 시작합니다.
idea = st.text_area(
    "서비스 아이디어",
    placeholder="예) 스포츠 야구 분석 및 승부 예측 서비스",
    height=140,
)

if st.button("설계도 생성", type="primary"):
    if not idea.strip():
        st.warning("서비스 아이디어를 입력해 주세요.")
    else:
        # 버튼을 누르면 FastAPI 백엔드에 아이디어를 전달하고, 구조화된 설계도 응답을 받습니다.
        with st.spinner("설계도를 생성하는 중입니다..."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/blueprint/generate",
                json={"idea": idea},
                timeout=60,
            )

        if response.ok:
            blueprint = response.json()

            # 응답 영역은 백엔드의 BlueprintResponse 모델 순서와 맞춰 표시합니다.
            st.subheader("개요")
            st.write(blueprint["overview"])

            st.subheader("핵심 기능")
            st.dataframe(blueprint["features"], use_container_width=True)

            st.subheader("기술 스택")
            st.json(blueprint["tech_stack"])

            st.subheader("API 설계")
            st.json(blueprint["api_spec"])

            st.subheader("데이터베이스 설계")
            st.json(blueprint["database_schema"])

            st.subheader("시퀀스 다이어그램")
            st.code(blueprint["sequence_diagram"], language="mermaid")
        else:
            st.error(f"API 요청에 실패했습니다: {response.status_code}")
            st.code(response.text)
