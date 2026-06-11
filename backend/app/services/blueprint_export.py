from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.schemas.blueprint import BlueprintResponse
from app.services.blueprint_normalizer import normalize_mermaid_erd_source, strip_mermaid_code_fence


def build_blueprint_export_zip(idea: str, blueprint: BlueprintResponse) -> bytes:
    """설계도 결과를 개발 산출물 ZIP 패키지로 변환합니다."""
    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("README.md", build_readme(idea, blueprint))
        archive.writestr("features.md", build_features_markdown(blueprint))
        archive.writestr("api-spec.md", build_api_markdown(blueprint))
        archive.writestr("database-schema.md", build_database_markdown(blueprint))
        archive.writestr("implementation-plan.md", build_plan_markdown(blueprint))
        archive.writestr("quality-report.md", build_quality_report_markdown(blueprint))
        archive.writestr("erd.mmd", normalize_mermaid_erd_source(blueprint.database_erd))
        archive.writestr("sequence.mmd", strip_mermaid_code_fence(blueprint.sequence_diagram))

    return buffer.getvalue()


def build_readme(idea: str, blueprint: BlueprintResponse) -> str:
    """프로젝트 시작 문서로 사용할 README 내용을 생성합니다."""
    return "\n".join(
        [
            "# DevBlueprint Export",
            "",
            "## 서비스 아이디어",
            idea,
            "",
            "## 개요",
            blueprint.overview,
            "",
            "## 기술 스택",
            f"- Backend: {format_inline_items(blueprint.tech_stack.backend)}",
            f"- Frontend: {format_inline_items(blueprint.tech_stack.frontend)}",
            f"- Database: {format_inline_items(blueprint.tech_stack.database)}",
            f"- AI: {format_inline_items(blueprint.tech_stack.ai)}",
            f"- 선정 이유: {blueprint.tech_stack.rationale}",
            "",
            "## 포함 파일",
            "- features.md: 핵심 기능과 우선순위",
            "- api-spec.md: REST API 초안",
            "- database-schema.md: 데이터베이스 테이블과 컬럼",
            "- implementation-plan.md: 비기능 요구사항, 보안 고려사항, 구현 계획",
            "- quality-report.md: 설계 결과 품질 체크",
            "- erd.mmd: Mermaid ERD",
            "- sequence.mmd: Mermaid 시퀀스 다이어그램",
            "",
        ]
    )


def build_features_markdown(blueprint: BlueprintResponse) -> str:
    """핵심 기능 목록을 Markdown 문서로 생성합니다."""
    lines = ["# 핵심 기능", ""]
    for feature in blueprint.features:
        lines.append(f"- **{feature.name}** `{feature.priority}`: {feature.description}")
    return "\n".join(lines) + "\n"


def build_api_markdown(blueprint: BlueprintResponse) -> str:
    """API 설계를 개발자가 읽기 쉬운 Markdown 문서로 생성합니다."""
    lines = ["# API 설계", ""]
    for endpoint in blueprint.api_spec:
        lines.extend(
            [
                f"## {endpoint.method} {endpoint.path}",
                endpoint.description,
                "",
                "### Request",
                format_fields(endpoint.request),
                "",
                "### Response",
                format_fields(endpoint.response),
                "",
            ]
        )
    return "\n".join(lines)


def build_database_markdown(blueprint: BlueprintResponse) -> str:
    """DB 테이블과 컬럼 설계를 Markdown 문서로 생성합니다."""
    lines = ["# 데이터베이스 설계", ""]
    for table in blueprint.database_schema:
        lines.extend([f"## {table.name}", table.description, "", format_columns(table.columns), ""])
    return "\n".join(lines)


def build_plan_markdown(blueprint: BlueprintResponse) -> str:
    """비기능 요구사항, 보안, 구현 계획을 하나의 실행 계획 문서로 생성합니다."""
    return "\n".join(
        [
            "# 구현 계획",
            "",
            "## 비기능 요구사항",
            format_considerations(blueprint.non_functional_requirements),
            "",
            "## 보안 고려사항",
            format_considerations(blueprint.security_considerations),
            "",
            "## 단계별 구현 계획",
            format_steps(blueprint.implementation_plan),
            "",
        ]
    )


def build_quality_report_markdown(blueprint: BlueprintResponse) -> str:
    """설계도 구현 준비도를 간단한 품질 리포트로 생성합니다."""
    checks = [
        ("기능 범위", 5 <= len(blueprint.features) <= 8, f"{len(blueprint.features)}개 기능"),
        ("API 범위", 4 <= len(blueprint.api_spec) <= 12, f"{len(blueprint.api_spec)}개 API"),
        ("DB 범위", 3 <= len(blueprint.database_schema) <= 8, f"{len(blueprint.database_schema)}개 테이블"),
        ("ERD 형식", blueprint.database_erd.strip().startswith("erDiagram"), "Mermaid erDiagram"),
        (
            "시퀀스 형식",
            blueprint.sequence_diagram.strip().startswith("sequenceDiagram"),
            "Mermaid sequenceDiagram",
        ),
        ("구현 계획", len(blueprint.implementation_plan) >= 3, f"{len(blueprint.implementation_plan)}개 단계"),
    ]
    passed = sum(1 for _, is_passed, _ in checks if is_passed)
    score = round((passed / len(checks)) * 100)
    lines = ["# 품질 리포트", "", f"- 점수: {score}점", f"- 통과: {passed}/{len(checks)}", ""]

    for label, is_passed, value in checks:
        status = "통과" if is_passed else "보강 필요"
        lines.append(f"- **{label}**: {status} ({value})")

    return "\n".join(lines) + "\n"


def format_inline_items(items: list[str]) -> str:
    """짧은 문자열 목록을 한 줄 표시용 텍스트로 변환합니다."""
    return ", ".join(items) if items else "없음"


def format_fields(fields: list) -> str:
    """API 필드 목록을 Markdown bullet로 변환합니다."""
    if not fields:
        return "- 없음"
    return "\n".join(
        f"- `{field.name}` ({field.type}, {'required' if field.required else 'optional'}): {field.description}"
        for field in fields
    )


def format_columns(columns: list) -> str:
    """DB 컬럼 목록을 Markdown bullet로 변환합니다."""
    if not columns:
        return "- 없음"
    return "\n".join(
        f"- `{column.name}` ({column.type}, {', '.join(column.constraints) or 'none'}): {column.description}"
        for column in columns
    )


def format_considerations(items: list) -> str:
    """고려사항 목록을 Markdown bullet로 변환합니다."""
    if not items:
        return "- 없음"
    return "\n".join(
        f"- **{item.title}** `{item.priority}` ({item.category}): {item.description}"
        for item in items
    )


def format_steps(steps: list) -> str:
    """구현 단계 목록을 Markdown bullet로 변환합니다."""
    if not steps:
        return "- 없음"
    return "\n".join(f"- **{step.phase}. {step.title}**: {step.description}" for step in steps)
