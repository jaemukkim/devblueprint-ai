import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.blueprint import BlueprintResponse


@dataclass(frozen=True)
class PromptQualitySample:
    """LLM 품질 평가에 사용할 고정 샘플과 기대 도메인 용어입니다."""

    id: str
    idea: str
    expected_domain_terms: list[str]
    expected_korean_terms: list[str]


@dataclass(frozen=True)
class BlueprintQualityEvaluation:
    """샘플 하나에 대한 설계도 평가 결과입니다."""

    sample_id: str
    score: int
    passed: bool
    matched_terms: list[str]
    missing_terms: list[str]


def load_prompt_quality_samples(path: str | Path) -> list[PromptQualitySample]:
    """JSON fixture에서 품질 평가 샘플을 읽어옵니다."""
    with Path(path).open(encoding="utf-8") as file:
        raw_samples = json.load(file)

    return [
        PromptQualitySample(
            id=sample["id"],
            idea=sample["idea"],
            expected_domain_terms=list(sample["expected_domain_terms"]),
            expected_korean_terms=list(sample["expected_korean_terms"]),
        )
        for sample in raw_samples
    ]


def evaluate_blueprint_against_sample(
    blueprint: BlueprintResponse,
    sample: PromptQualitySample,
) -> BlueprintQualityEvaluation:
    """생성된 설계도가 샘플의 기대 도메인 용어를 충분히 반영했는지 평가합니다."""
    searchable_text = normalize_searchable_text(blueprint.model_dump(mode="json"))
    expected_terms = [*sample.expected_domain_terms, *sample.expected_korean_terms]
    matched_terms = [term for term in expected_terms if normalize_term(term) in searchable_text]
    missing_terms = [term for term in expected_terms if term not in matched_terms]
    score = round((len(matched_terms) / len(expected_terms)) * 100) if expected_terms else 100

    return BlueprintQualityEvaluation(
        sample_id=sample.id,
        score=score,
        passed=not missing_terms,
        matched_terms=matched_terms,
        missing_terms=missing_terms,
    )


def evaluate_blueprint_generation_samples(
    samples: Iterable[PromptQualitySample],
    generate_blueprint_for_idea: Callable[[str], BlueprintResponse],
) -> list[BlueprintQualityEvaluation]:
    """샘플 아이디어별로 실제 설계도 생성을 실행하고 평가 결과를 반환합니다."""
    return [
        evaluate_blueprint_against_sample(generate_blueprint_for_idea(sample.idea), sample)
        for sample in samples
    ]


def summarize_quality_evaluations(evaluations: list[BlueprintQualityEvaluation]) -> dict[str, Any]:
    """여러 샘플 평가 결과를 CLI와 테스트에서 쓰기 쉬운 요약 값으로 변환합니다."""
    if not evaluations:
        return {
            "sample_count": 0,
            "passed_count": 0,
            "average_score": 0,
            "failed_samples": [],
        }

    passed_count = sum(1 for evaluation in evaluations if evaluation.passed)
    average_score = round(sum(evaluation.score for evaluation in evaluations) / len(evaluations))

    return {
        "sample_count": len(evaluations),
        "passed_count": passed_count,
        "average_score": average_score,
        "failed_samples": [
            {
                "sample_id": evaluation.sample_id,
                "score": evaluation.score,
                "missing_terms": evaluation.missing_terms,
            }
            for evaluation in evaluations
            if not evaluation.passed
        ],
    }


def normalize_searchable_text(value: Any) -> str:
    """중첩된 설계도 값을 용어 검색에 적합한 단일 문자열로 변환합니다."""
    return normalize_term(json.dumps(value, ensure_ascii=False, sort_keys=True))


def normalize_term(value: str) -> str:
    """공백과 대소문자 차이를 줄여 도메인 용어 매칭을 안정화합니다."""
    return value.replace("-", "_").replace(" ", "_").lower()
