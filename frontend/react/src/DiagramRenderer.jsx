import { useEffect, useMemo, useState } from "react";

import { normalizeMermaidSource } from "./mermaid.js";

let mermaidLoadPromise = null;
let mermaidRenderQueue = Promise.resolve();

// 다이어그램 탭이 실제로 열릴 때만 Mermaid를 불러와 초기 번들 크기를 줄입니다.
function loadMermaid() {
  if (!mermaidLoadPromise) {
    mermaidLoadPromise = import("mermaid").then((module) => {
      const mermaid = module.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "default",
        securityLevel: "loose",
      });
      return mermaid;
    });
  }

  return mermaidLoadPromise;
}

export default function MermaidDiagram({ label, source }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState(null);
  const [view, setView] = useState("diagram");
  const renderSource = useMemo(() => normalizeMermaidSource(source), [source]);

  useEffect(() => {
    let mounted = true;
    const id = `diagram-${crypto.randomUUID()}`;

    setError(null);
    setSvg("");

    enqueueMermaidRender(id, renderSource)
      .then((result) => {
        if (!mounted) {
          return;
        }

        if (isMermaidErrorSvg(result.svg)) {
          setSvg("");
          setError(buildMermaidErrorInfo(label, null, renderSource));
          return;
        }

        setSvg(result.svg);
        setError(null);
      })
      .catch((err) => {
        if (mounted) {
          setSvg("");
          setError(buildMermaidErrorInfo(label, err, renderSource));
        }
      });

    return () => {
      mounted = false;
    };
  }, [label, renderSource]);

  return (
    <div className="diagram-panel">
      <div className="view-tabs">
        <button className={view === "diagram" ? "active" : ""} onClick={() => setView("diagram")} type="button">
          Diagram
        </button>
        <button className={view === "code" ? "active" : ""} onClick={() => setView("code")} type="button">
          Code
        </button>
      </div>
      {view === "code" ? (
        <pre className="code-block">{renderSource}</pre>
      ) : error ? (
        <DiagramError error={error} />
      ) : svg ? (
        <div className="diagram" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <div className="diagram-loading">다이어그램을 렌더링하고 있습니다.</div>
      )}
    </div>
  );
}

// Mermaid 오류를 사용자가 바로 확인할 수 있는 구조로 보여줍니다.
function DiagramError({ error }) {
  return (
    <div className="diagram-error" role="alert">
      <strong>{error.title}</strong>
      <p>{error.message}</p>
      {error.lineNumber && (
        <code>
          line {error.lineNumber}: {error.lineText || "(빈 줄)"}
        </code>
      )}
      {error.detail && <small>{error.detail}</small>}
    </div>
  );
}

// Mermaid 싱글턴 렌더러가 동시 호출 중 실패 상태를 공유하지 않도록 요청을 순차 처리합니다.
function enqueueMermaidRender(id, source) {
  const renderTask = () => renderMermaidDiagram(id, source);
  const queuedRender = mermaidRenderQueue.then(renderTask, renderTask);
  mermaidRenderQueue = queuedRender.catch(() => undefined);
  return queuedRender;
}

// Mermaid 렌더링을 실행하고 결과 SVG가 명시적인 오류 화면인지 후처리에서 확인합니다.
async function renderMermaidDiagram(id, source) {
  const mermaid = await loadMermaid();
  return mermaid.render(id, source);
}

// Mermaid가 syntax error SVG를 정상 결과처럼 반환하는 경우를 화면 주입 전에 차단합니다.
function isMermaidErrorSvg(svg) {
  return svg.includes("Syntax error in text");
}

// Mermaid 오류 객체에서 줄 번호와 원본 줄을 추출해 안내 메시지를 만듭니다.
function buildMermaidErrorInfo(label, error, source) {
  const detail = formatMermaidError(error);
  const lineNumber = extractMermaidErrorLineNumber(detail);
  const lineText = lineNumber ? source.split("\n")[lineNumber - 1]?.trim() || "" : "";

  return {
    title: `${label} 문법 오류`,
    message: "렌더링하지 못했습니다. Code 탭에서 원본 Mermaid 코드를 확인해 주세요.",
    detail,
    lineNumber,
    lineText,
  };
}

// Mermaid 원본 오류가 너무 길게 나오지 않도록 핵심 문장만 안내에 붙입니다.
function formatMermaidError(error) {
  const rawMessage = String(error || "Mermaid parse error");
  const meaningfulLines = rawMessage
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const lineNumberMessage = meaningfulLines.find((line) => /line\s+\d+/i.test(line));
  const message = lineNumberMessage || meaningfulLines[0] || "Mermaid parse error";
  return message.length > 180 ? `${message.slice(0, 180)}...` : message;
}

// Mermaid 오류 문구의 `line N` 패턴을 찾아 원본 코드 위치를 계산합니다.
function extractMermaidErrorLineNumber(message) {
  const match = message.match(/line\s+(\d+)/i);
  return match ? Number(match[1]) : null;
}
