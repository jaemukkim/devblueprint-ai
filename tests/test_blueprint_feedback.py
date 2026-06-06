from app.services.blueprint_feedback import (
    build_quality_feedback,
    choose_quality_retry_section,
    classify_quality_error_section,
)


def test_build_quality_feedback_translates_feature_count_error() -> None:
    feedback = build_quality_feedback(["features must contain at least 5 items"], "features")

    assert feedback == [
        "기능 섹션: 기능은 5~8개의 구체적인 MVP 기능으로 작성하고, 각 기능은 사용자 행동이나 백엔드 책임을 설명해야 합니다."
    ]


def test_build_quality_feedback_translates_api_path_error() -> None:
    feedback = build_quality_feedback(["api path must start with '/': api/v1/items"], "api")

    assert "API 섹션" in feedback[0]
    assert "모든 API path는 '/'로 시작" in feedback[0]
    assert "api/v1/items" not in feedback[0]


def test_build_quality_feedback_keeps_unknown_error_as_context() -> None:
    feedback = build_quality_feedback(["unexpected quality issue"], "database")

    assert feedback == ["DB 섹션: 다음 품질 오류를 수정해 주세요. 원본 오류: unexpected quality issue"]


def test_classify_quality_error_section_maps_validator_errors() -> None:
    assert classify_quality_error_section("feature description is too short: 요약") == "features"
    assert classify_quality_error_section("api path must start with '/': api/v1/items") == "api"
    assert classify_quality_error_section("table must include a primary_key column: books") == "database"
    assert classify_quality_error_section("database_erd must start with 'erDiagram'") == "diagrams"
    assert classify_quality_error_section("implementation_plan must contain at least 3 items") == "planning"


def test_choose_quality_retry_section_uses_dependency_order() -> None:
    assert choose_quality_retry_section([
        "database_erd must start with 'erDiagram'",
        "api path must start with '/': api/v1/items",
    ]) == "api"
