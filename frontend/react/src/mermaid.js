// 저장된 설계도에 남아 있을 수 있는 Mermaid 비호환 ERD 문법을 렌더링/다운로드 전에 보정합니다.
// Mermaid 원본이 ERD가 아니면 그대로 반환해 다른 다이어그램 문법에 영향을 주지 않습니다.
export function normalizeMermaidSource(source) {
  if (!source.trim().startsWith("erDiagram")) {
    return source;
  }

  return source
    .split("\n")
    .map((line) => normalizeMermaidAttributeLine(line))
    .join("\n");
}

// Mermaid ERD 속성 라인의 key token 표기를 현재 Mermaid 파서가 받는 형식으로 정리합니다.
function normalizeMermaidAttributeLine(line) {
  // Mermaid ERD는 복수 key token을 `PK, FK`처럼 쉼표로 구분해야 합니다.
  return line
    .replace(/\bUNIQUE\b/g, "UK")
    .replace(/\b(PK|FK|UK)(?:\s+(PK|FK|UK))+\b/g, (keyGroup) => keyGroup.split(/\s+/).join(", "));
}
