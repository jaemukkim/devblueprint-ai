from app.schemas.blueprint import BlueprintRequest
from app.services.prompts import (
    PIPELINE_STAGE_RULES,
    SECTION_REGENERATION_RULES,
    SYSTEM_PROMPT,
    build_api_design_prompt,
    build_idea_analysis_prompt,
    build_section_regeneration_guidance,
)


def test_system_prompt_keeps_core_generation_contracts() -> None:
    assert "Recommend 5 to 8 core features" in SYSTEM_PROMPT
    assert "Recommend 4 to 8 REST API endpoints" in SYSTEM_PROMPT
    assert "Write user-facing descriptions in Korean" in SYSTEM_PROMPT
    assert "Mermaid erDiagram" in SYSTEM_PROMPT


def test_pipeline_stage_rules_are_split_by_generation_step() -> None:
    assert set(PIPELINE_STAGE_RULES) == {
        "analysis",
        "features",
        "api",
        "database",
        "diagrams",
        "planning",
    }
    assert "Do not design database tables" in PIPELINE_STAGE_RULES["api"]
    assert "Do not invent tables or endpoints" in PIPELINE_STAGE_RULES["diagrams"]


def test_stage_prompt_includes_context_blocks() -> None:
    prompt = build_api_design_prompt(
        "요리 추천 서비스",
        analysis={"domain": "recipes"},
        feature_design={"features": ["재료 기반 추천"]},
    )

    assert "Service idea:" in prompt
    assert "요리 추천 서비스" in prompt
    assert "Idea analysis JSON:" in prompt
    assert "Feature design JSON:" in prompt
    assert "Return 4 to 8 domain-specific REST API endpoints" in prompt


def test_analysis_prompt_keeps_service_idea() -> None:
    prompt = build_idea_analysis_prompt(BlueprintRequest(idea="독서 기록 앱"))

    assert "Analyze the following service idea" in prompt
    assert "독서 기록 앱" in prompt
    assert "explicit out-of-scope items" in prompt


def test_section_regeneration_guidance_uses_section_rule_map() -> None:
    assert build_section_regeneration_guidance("features") == SECTION_REGENERATION_RULES["features"]
    assert build_section_regeneration_guidance("unknown") == ""
