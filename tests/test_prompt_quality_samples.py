import json
from pathlib import Path

import pytest

from app.schemas.blueprint import BlueprintRequest
from app.services.prompts import (
    PIPELINE_STAGE_RULES,
    build_api_design_prompt,
    build_database_design_prompt,
    build_diagram_design_prompt,
    build_feature_design_prompt,
    build_idea_analysis_prompt,
    build_planning_design_prompt,
)


SAMPLE_PATH = Path(__file__).parent / "fixtures" / "prompt_quality_samples.json"


def load_prompt_quality_samples() -> list[dict]:
    with SAMPLE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


@pytest.mark.parametrize("sample", load_prompt_quality_samples(), ids=lambda sample: sample["id"])
def test_quality_sample_ideas_are_preserved_in_pipeline_prompts(sample: dict) -> None:
    idea = sample["idea"]
    prompts = build_sample_pipeline_prompts(idea)

    for prompt in prompts:
        assert idea in prompt
        assert "Service idea:" in prompt


@pytest.mark.parametrize("sample", load_prompt_quality_samples(), ids=lambda sample: sample["id"])
def test_quality_samples_define_domain_expectations(sample: dict) -> None:
    assert len(sample["expected_domain_terms"]) >= 3
    assert len(sample["expected_korean_terms"]) >= 3

    feature_prompt = build_feature_design_prompt(sample["idea"], analysis={"domain_terms": sample["expected_domain_terms"]})

    for term in sample["expected_korean_terms"]:
        assert term in feature_prompt


def test_pipeline_quality_rules_cover_generation_stages() -> None:
    assert "Return 5 to 8 concrete MVP features" in PIPELINE_STAGE_RULES["features"]
    assert "Return 4 to 8 domain-specific REST API endpoints" in PIPELINE_STAGE_RULES["api"]
    assert "Return 3 to 6 PostgreSQL-friendly tables" in PIPELINE_STAGE_RULES["database"]
    assert "Return a valid Mermaid erDiagram" in PIPELINE_STAGE_RULES["diagrams"]
    assert "Return 3 to 6 non-functional requirements" in PIPELINE_STAGE_RULES["planning"]


def test_prompt_quality_samples_are_unique() -> None:
    samples = load_prompt_quality_samples()
    sample_ids = [sample["id"] for sample in samples]
    sample_ideas = [sample["idea"] for sample in samples]

    assert len(samples) >= 5
    assert len(sample_ids) == len(set(sample_ids))
    assert len(sample_ideas) == len(set(sample_ideas))


def build_sample_pipeline_prompts(idea: str) -> list[str]:
    analysis = {"domain": "sample_domain", "entities": ["sample_entities"]}
    feature_design = {"features": ["sample_feature"], "tech_stack": {"backend": ["FastAPI"]}}
    api_design = {"api_spec": [{"method": "GET", "path": "/api/v1/sample-resources"}]}
    database_design = {"database_schema": [{"name": "sample_resources"}]}

    return [
        build_idea_analysis_prompt(BlueprintRequest(idea=idea)),
        build_feature_design_prompt(idea, analysis=analysis),
        build_api_design_prompt(idea, analysis=analysis, feature_design=feature_design),
        build_database_design_prompt(
            idea,
            analysis=analysis,
            feature_design=feature_design,
            api_design=api_design,
        ),
        build_diagram_design_prompt(
            idea,
            analysis=analysis,
            api_design=api_design,
            database_design=database_design,
        ),
        build_planning_design_prompt(
            idea,
            analysis=analysis,
            feature_design=feature_design,
            api_design=api_design,
            database_design=database_design,
        ),
    ]
