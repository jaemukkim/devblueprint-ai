from pathlib import Path

from app.schemas.blueprint import (
    ApiField,
    ApiSpec,
    BlueprintResponse,
    DatabaseColumn,
    DatabaseTable,
    DesignConsideration,
    Feature,
    ImplementationStep,
    TechStack,
)
from app.services.blueprint_quality_evaluator import (
    PromptQualitySample,
    evaluate_blueprint_against_sample,
    evaluate_blueprint_generation_samples,
    load_prompt_quality_samples,
    summarize_quality_evaluations,
)


SAMPLE_PATH = Path(__file__).parent / "fixtures" / "prompt_quality_samples.json"


def test_load_prompt_quality_samples_returns_typed_samples() -> None:
    samples = load_prompt_quality_samples(SAMPLE_PATH)

    assert len(samples) >= 10
    assert samples[0].id == "recipe_recommendation"
    assert samples[0].idea
    assert samples[0].expected_domain_terms


def test_evaluate_blueprint_against_sample_scores_expected_terms() -> None:
    sample = PromptQualitySample(
        id="warehouse_inventory",
        idea="재고 관리 서비스",
        expected_domain_terms=["inventory_items", "stock_movements", "reorder_alerts"],
        expected_korean_terms=["재고", "입출고", "재주문"],
    )
    blueprint = make_quality_test_blueprint()

    evaluation = evaluate_blueprint_against_sample(blueprint, sample)

    assert evaluation.sample_id == "warehouse_inventory"
    assert evaluation.score == 100
    assert evaluation.passed is True
    assert evaluation.missing_terms == []


def test_evaluate_blueprint_generation_samples_summarizes_failures() -> None:
    samples = [
        PromptQualitySample(
            id="matched",
            idea="재고 관리 서비스",
            expected_domain_terms=["inventory_items"],
            expected_korean_terms=["재고"],
        ),
        PromptQualitySample(
            id="missing",
            idea="계약 관리 서비스",
            expected_domain_terms=["contracts"],
            expected_korean_terms=["계약"],
        ),
    ]

    evaluations = evaluate_blueprint_generation_samples(samples, lambda idea: make_quality_test_blueprint())
    summary = summarize_quality_evaluations(evaluations)

    assert summary["sample_count"] == 2
    assert summary["passed_count"] == 1
    assert summary["average_score"] == 50
    assert summary["failed_samples"][0]["sample_id"] == "missing"


def make_quality_test_blueprint() -> BlueprintResponse:
    return BlueprintResponse(
        overview="재고, 입출고, 재주문 알림을 관리하는 창고 운영 설계도입니다.",
        features=[
            Feature(name="재고 현황 관리", description="inventory_items 기준으로 현재 재고를 관리합니다.", priority="high"),
            Feature(name="입출고 기록", description="stock_movements 이력을 등록하고 조회합니다.", priority="high"),
            Feature(name="재주문 알림", description="reorder_alerts 조건을 계산해 운영자에게 알립니다.", priority="medium"),
            Feature(name="상품 검색", description="상품명과 SKU로 재고 항목을 검색합니다.", priority="medium"),
            Feature(name="운영 리포트", description="기간별 입출고 추이를 요약합니다.", priority="low"),
        ],
        tech_stack=TechStack(
            backend=["FastAPI"],
            frontend=["React"],
            database=["PostgreSQL"],
            ai=["OpenAI API"],
            rationale="구조화된 운영 데이터를 관리하기 쉬운 조합입니다.",
        ),
        api_spec=[
            make_api_spec("GET", "/api/v1/inventory-items"),
            make_api_spec("POST", "/api/v1/stock-movements"),
            make_api_spec("GET", "/api/v1/reorder-alerts"),
            make_api_spec("PATCH", "/api/v1/inventory-items/{item_id}"),
        ],
        database_schema=[
            make_database_table("inventory_items"),
            make_database_table("stock_movements"),
            make_database_table("reorder_alerts"),
        ],
        database_erd="erDiagram\n  inventory_items ||--o{ stock_movements : has\n  inventory_items ||--o{ reorder_alerts : has",
        sequence_diagram="sequenceDiagram\n  participant User\n  User->>API: GET /api/v1/inventory-items\n  API-->>User: inventory_items",
        non_functional_requirements=make_considerations("performance"),
        security_considerations=make_considerations("security"),
        implementation_plan=[
            ImplementationStep(phase="1", title="DB 구성", description="inventory_items 테이블부터 구현합니다."),
            ImplementationStep(phase="2", title="입출고 API", description="stock_movements API를 구현합니다."),
            ImplementationStep(phase="3", title="알림", description="reorder_alerts 계산을 구현합니다."),
        ],
    )


def make_api_spec(method: str, path: str) -> ApiSpec:
    return ApiSpec(
        method=method,
        path=path,
        description=f"{path} endpoint",
        request=[ApiField(name="name", type="string", description="이름", required=True)],
        response=[ApiField(name="id", type="uuid", description="식별자", required=True)],
    )


def make_database_table(name: str) -> DatabaseTable:
    return DatabaseTable(
        name=name,
        description=f"{name} table",
        columns=[
            DatabaseColumn(name="id", type="uuid", description="식별자", constraints=["primary_key"]),
            DatabaseColumn(name="name", type="varchar", description="이름", constraints=["not_null"]),
            DatabaseColumn(name="created_at", type="timestamp", description="생성 시각", constraints=["not_null"]),
        ],
    )


def make_considerations(category: str) -> list[DesignConsideration]:
    return [
        DesignConsideration(
            category=category,
            title=f"{category} 항목 {index}",
            description="운영 환경에서 확인해야 하는 고려사항입니다.",
            priority="medium",
        )
        for index in range(1, 4)
    ]
