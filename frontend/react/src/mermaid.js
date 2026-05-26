// 저장된 설계도에 남아 있을 수 있는 Mermaid 비호환 ERD 문법을 렌더링/다운로드 전에 보정합니다.
// Mermaid 원본이 ERD가 아니면 그대로 반환해 다른 다이어그램 문법에 영향을 주지 않습니다.
export function normalizeMermaidSource(source) {
  const unfencedSource = stripMermaidCodeFence(source);

  if (!unfencedSource.trim().startsWith("erDiagram")) {
    return unfencedSource;
  }

  let inEntityBlock = false;

  return unfencedSource
    .split("\n")
    .map((line) => {
      const strippedLine = line.trim();

      if (strippedLine.endsWith("{")) {
        inEntityBlock = true;
        return line;
      }
      if (strippedLine === "}") {
        inEntityBlock = false;
        return line;
      }

      return inEntityBlock ? normalizeMermaidAttributeLine(line) : line;
    })
    .join("\n");
}

// LLM 응답이나 저장된 예전 결과에 남은 Markdown code fence를 제거합니다.
function stripMermaidCodeFence(source) {
  const trimmedSource = source.trim();
  if (!trimmedSource.startsWith("```")) {
    return source;
  }

  const lines = trimmedSource.split("\n");
  if (lines[0]?.trim().startsWith("```")) {
    lines.shift();
  }
  if (lines[lines.length - 1]?.trim().startsWith("```")) {
    lines.pop();
  }

  return lines.join("\n").trim();
}

// Mermaid ERD 속성 라인의 key token 표기를 현재 Mermaid 파서가 받는 형식으로 정리합니다.
function normalizeMermaidAttributeLine(line) {
  // Mermaid ERD는 복수 key token을 `PK, FK`처럼 쉼표로 구분해야 합니다.
  const normalizedKeyLine = line
    .replace(/\bUNIQUE\b/g, "UK")
    .replace(/\bUQ\b/gi, "UK")
    .replace(/\bPRIMARY\s+KEY\b/gi, "PK")
    .replace(/\bFOREIGN\s+KEY\b/gi, "FK")
    .replace(/\bNOT\s+NULL\b/gi, "")
    .replace(/\bNULL\b/gi, "")
    .replace(/\b(PK|FK|UK)(?:\s+(PK|FK|UK))+\b/g, (keyGroup) => keyGroup.split(/\s+/).join(", "));
  return normalizeMermaidAttributeType(normalizedKeyLine);
}

// Mermaid ERD attribute type은 공백 없는 한 단어여야 하므로 SQL 복합 타입을 underscore로 합칩니다.
function normalizeMermaidAttributeType(line) {
  const indentation = line.match(/^\s*/)?.[0] || "";
  const trimmedLine = line.trim();
  const tokens = trimmedLine.split(/\s+/);
  const keyStartIndex = tokens.findIndex((token) => ["PK", "FK", "UK"].includes(token.replace(",", "")));

  if (keyStartIndex > 2) {
    const type = normalizeMermaidTypeToken(tokens.slice(0, keyStartIndex - 1).join("_"));
    const name = tokens[keyStartIndex - 1];
    return `${indentation}${[type, name, ...tokens.slice(keyStartIndex)].join(" ")}`;
  }

  if (keyStartIndex === -1 && tokens.length > 2 && !trimmedLine.includes("\"")) {
    const type = normalizeMermaidTypeToken(tokens.slice(0, -1).join("_"));
    const name = tokens[tokens.length - 1];
    return `${indentation}${type} ${name}`;
  }

  if (tokens.length > 0) {
    const normalizedType = normalizeMermaidTypeToken(tokens[0]);
    if (normalizedType !== tokens[0]) {
      return `${indentation}${[normalizedType, ...tokens.slice(1)].join(" ")}`;
    }
  }

  return line;
}

// Mermaid attribute type에 괄호, 쉼표, 배열 기호가 섞이면 안전한 단일 토큰으로 바꿉니다.
function normalizeMermaidTypeToken(value) {
  const normalized = value
    .replaceAll("[]", "_array")
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  return normalized || "text";
}
