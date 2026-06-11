import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.blueprint import BlueprintRequest  # noqa: E402
from app.services.blueprint_generator import generate_blueprint  # noqa: E402
from app.services.blueprint_quality_evaluator import (  # noqa: E402
    evaluate_blueprint_generation_samples,
    load_prompt_quality_samples,
    summarize_quality_evaluations,
)


def main() -> int:
    """고정 샘플 아이디어로 실제 설계도 생성 품질을 평가합니다."""
    parser = argparse.ArgumentParser(description="DevBlueprint AI prompt quality evaluation runner")
    parser.add_argument(
        "--samples",
        default=str(ROOT_DIR / "tests" / "fixtures" / "prompt_quality_samples.json"),
        help="품질 평가 샘플 JSON 경로",
    )
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 실행할 샘플 수")
    args = parser.parse_args()

    samples = load_prompt_quality_samples(args.samples)
    if args.limit is not None:
        samples = samples[: args.limit]

    evaluations = evaluate_blueprint_generation_samples(
        samples,
        lambda idea: generate_blueprint(BlueprintRequest(idea=idea)),
    )
    payload = {
        "summary": summarize_quality_evaluations(evaluations),
        "items": [
            {
                "sample_id": evaluation.sample_id,
                "score": evaluation.score,
                "passed": evaluation.passed,
                "matched_terms": evaluation.matched_terms,
                "missing_terms": evaluation.missing_terms,
            }
            for evaluation in evaluations
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["summary"]["passed_count"] == payload["summary"]["sample_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
