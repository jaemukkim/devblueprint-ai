import { useEffect, useMemo, useState } from "react";
import {
  Blocks,
  Bot,
  Braces,
  Code2,
  Database,
  Download,
  FileText,
  GitBranch,
  Info,
  LayoutGrid,
  Loader2,
  Network,
  RefreshCw,
  Send,
  Server,
  Sparkles,
  Trash2,
} from "lucide-react";
import mermaid from "mermaid";

import { createBlueprint, deleteBlueprint, getBlueprint, listBlueprints } from "./api.js";
import { downloadMarkdown } from "./markdown.js";

const SAMPLE_IDEAS = [
  "챗봇을 이용한 쇼핑몰 고객상담 자동화 서비스",
  "개발자를 위한 AI 기반 API 설계 자동화 도구",
  "다이어터를 위한 AI 기반 식단 관리 서비스"
];

const IDEA_SUGGESTIONS = [
  "실시간 협업형 시스템 설계 화이트보드",
  "소셜 로그인이 있는 커뮤니티 플랫폼",
  "AI 추천 기반 독서 기록 앱"
];

// 기술 스택 카테고리별로 화면에 표시할 대표 아이콘을 연결합니다.
const TECH_STACK_CATEGORY_ICONS = {
  Backend: Server,
  Frontend: Code2,
  Database,
  AI: Bot,
};

// 결과 화면 탭 정의를 상단 메뉴와 결과 탭이 함께 사용합니다.
const RESULT_TABS = [
  { id: "summary", label: "요약" },
  { id: "features", label: "기능" },
  { id: "api", label: "API" },
  { id: "database", label: "DB" },
  { id: "diagrams", label: "다이어그램" },
];

// 생성 대기 화면에서 순차적으로 보여줄 작업 단계입니다.
const GENERATION_STEPS = [
  "아이디어 분석",
  "기능 요구사항 정리",
  "API 초안 구성",
  "DB/ERD 설계",
  "시퀀스 정리",
];

// 네트워크가 즉시 실패해도 사용자가 클릭 피드백을 인지할 수 있는 최소 표시 시간입니다.
const GENERATION_FEEDBACK_MIN_MS = 600;

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

function MermaidDiagram({ source }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  const [view, setView] = useState("diagram");

  useEffect(() => {
    let mounted = true;
    const id = `diagram-${crypto.randomUUID()}`;

    mermaid
      .render(id, source)
      .then((result) => {
        if (mounted) {
          setSvg(result.svg);
          setError("");
        }
      })
      .catch((err) => {
        if (mounted) {
          setSvg("");
          setError(String(err));
        }
      });

    return () => {
      mounted = false;
    };
  }, [source]);

  return (
    <div className="diagram-panel">
      <div className="view-tabs">
        <button className={view === "diagram" ? "active" : ""} onClick={() => setView("diagram")}>
          Diagram
        </button>
        <button className={view === "code" ? "active" : ""} onClick={() => setView("code")}>
          Code
        </button>
      </div>
      {view === "code" ? (
        <pre className="code-block">{source}</pre>
      ) : error ? (
        <pre className="diagram-error">{error}</pre>
      ) : (
        <div className="diagram" dangerouslySetInnerHTML={{ __html: svg }} />
      )}
    </div>
  );
}

function Section({ title, description, children }) {
  return (
    <section className="section">
      <div className="section-heading">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

// 생성 상태 UI가 너무 빨리 사라지지 않도록 남은 대기 시간을 계산합니다.
function getRemainingFeedbackMs(startedAt) {
  return Math.max(0, GENERATION_FEEDBACK_MIN_MS - (Date.now() - startedAt));
}

// 짧은 대기 시간을 Promise로 감싸 생성 흐름의 finally에서도 사용할 수 있게 합니다.
function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

// 상단 메뉴 클릭 시 같은 화면 안의 대상 영역으로 부드럽게 이동합니다.
function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

// 기술 스택 이름을 아이콘 칩과 함께 렌더링해 목록을 빠르게 훑어볼 수 있게 합니다.
function TechStackColumn({ title, items }) {
  const CategoryIcon = TECH_STACK_CATEGORY_ICONS[title] || Blocks;

  return (
    <div className="stack-column">
      <div className="stack-column-header">
        <span className="stack-category-icon">
          <CategoryIcon size={18} />
        </span>
        <strong>{title}</strong>
      </div>
      <div className="stack-chip-list">
        {items.length > 0 ? (
          items.map((item) => (
            <span className="stack-chip" key={item}>
              <Braces size={14} />
              {item}
            </span>
          ))
        ) : (
          <span className="stack-chip stack-chip-empty">추천 없음</span>
        )}
      </div>
    </div>
  );
}

function App() {
  const [idea, setIdea] = useState("");
  const [blueprint, setBlueprint] = useState(null);
  const [recentBlueprints, setRecentBlueprints] = useState([]);
  const [selectedBlueprintId, setSelectedBlueprintId] = useState(null);
  const [loading, setLoading] = useState(false);
  // 설계도 생성 요청 중인지 구분해 홈 입력 패널에 전용 피드백을 표시합니다.
  const [isGenerating, setIsGenerating] = useState(false);
  // 긴 생성 시간 동안 현재 어느 단계처럼 보일지 관리합니다.
  const [generationStepIndex, setGenerationStepIndex] = useState(0);
  // 상단 메뉴와 결과 탭이 같은 선택 상태를 공유하도록 관리합니다.
  const [activeResultTab, setActiveResultTab] = useState("summary");
  const [error, setError] = useState("");

  const canGenerate = idea.trim().length >= 5 && !loading;

  const selectedIdea = useMemo(() => {
    const selected = recentBlueprints.find((item) => item.id === selectedBlueprintId);
    return selected?.idea || idea;
  }, [idea, recentBlueprints, selectedBlueprintId]);

  async function refreshRecent() {
    const response = await listBlueprints();
    setRecentBlueprints(response.items || []);
  }

  useEffect(() => {
    refreshRecent().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!isGenerating) {
      setGenerationStepIndex(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setGenerationStepIndex((currentIndex) => Math.min(currentIndex + 1, GENERATION_STEPS.length - 1));
    }, 4500);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isGenerating]);

  async function handleGenerate() {
    if (!canGenerate) {
      return;
    }

    setLoading(true);
    setIsGenerating(true);
    setGenerationStepIndex(0);
    setError("");
    const startedAt = Date.now();

    try {
      const result = await createBlueprint(idea);
      setBlueprint(result);
      setSelectedBlueprintId(null);
      setActiveResultTab("summary");
      await refreshRecent();
    } catch (err) {
      setError(err.message);
    } finally {
      await wait(getRemainingFeedbackMs(startedAt));
      setLoading(false);
      setIsGenerating(false);
    }
  }

  async function handleOpen(id) {
    setLoading(true);
    setError("");

    try {
      const stored = await getBlueprint(id);
      setBlueprint(stored.result);
      setIdea(stored.idea);
      setSelectedBlueprintId(stored.id);
      setActiveResultTab("summary");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("저장된 설계도를 삭제할까요?")) {
      return;
    }

    setError("");

    try {
      await deleteBlueprint(id);
      if (selectedBlueprintId === id) {
        setBlueprint(null);
        setSelectedBlueprintId(null);
      }
      await refreshRecent();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleResultNav(tabId) {
    setActiveResultTab(tabId);
    scrollToSection("result");
  }

  return (
    <div className="app-shell">
      <header className="app-nav">
        <div className="brand">
          <span className="brand-mark">
            <LayoutGrid size={18} />
          </span>
          <strong>Dev<span>Blueprint</span> AI</strong>
        </div>
        <nav className="nav-links" aria-label="주요 메뉴">
          <button type="button" onClick={() => scrollToSection("workspace")}>대시보드</button>
          <button type="button" onClick={() => scrollToSection("recent")}>내 설계도</button>
          <button type="button" onClick={() => handleResultNav("api")}>API 설계</button>
          <button type="button" onClick={() => handleResultNav("database")}>ERD / DB</button>
          <button type="button" onClick={() => handleResultNav("diagrams")}>시퀀스</button>
        </nav>
        {blueprint ? (
          <button className="nav-action" onClick={() => downloadMarkdown(selectedIdea, blueprint)}>
            <Download size={18} />
            Markdown
          </button>
        ) : (
          <a className="nav-action" href="#workspace">
            설계 시작
          </a>
        )}
      </header>

      <main className="workspace">
        <section className="hero-section">
          <div className="hero-copy">
            <span className="hero-pill">AI 기반 시스템 설계</span>
            <h1>
              아이디어를
              <span>설계도로 만드는</span>
              가장 빠른 방법
            </h1>
            <p>서비스를 자연어로 설명하면 핵심 기능, API, DB, ERD, 시퀀스 다이어그램까지 한 번에 정리합니다.</p>

            <div className="hero-actions">
              <a className="primary-link" href="#workspace">지금 바로 시작</a>
              <button className="ghost-button" onClick={() => setIdea(SAMPLE_IDEAS[1])}>예시 보기</button>
            </div>

            <div className="hero-stats">
              <div>
                <strong>2.4s</strong>
                <span>평균 생성 시간</span>
              </div>
              <div>
                <strong>5가지</strong>
                <span>설계 산출물</span>
              </div>
              <div>
                <strong>무료</strong>
                <span>로컬 개발 플랜</span>
              </div>
            </div>

            <div className="artifact-section">
              <span className="section-kicker">생성 산출물</span>
              <div className="artifact-grid">
                <article className="artifact-card">
                  <span className="artifact-icon blue"><Server size={18} /></span>
                  <strong>REST API 설계</strong>
                  <p>endpoint, HTTP method, 요청/응답 구조를 자동 정의</p>
                </article>
                <article className="artifact-card">
                  <span className="artifact-icon violet"><Database size={18} /></span>
                  <strong>ERD & DB 설계</strong>
                  <p>테이블 구조, 관계, 인덱스까지 시각화된 다이어그램 생성</p>
                </article>
                <article className="artifact-card">
                  <span className="artifact-icon green"><GitBranch size={18} /></span>
                  <strong>시퀀스 다이어그램</strong>
                  <p>주요 플로우의 컴포넌트 간 상호작용을 시각적으로 표현</p>
                </article>
              </div>
            </div>
          </div>

          <section className="input-panel hero-input" id="workspace">
            <div className="suggestion-panel">
              <p>이런 아이디어 어때요?</p>
              <div>
                {IDEA_SUGGESTIONS.map((suggestion) => (
                  <button key={suggestion} onClick={() => setIdea(suggestion)} type="button">
                    <Sparkles size={14} />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <label htmlFor="idea">서비스 아이디어</label>
            <textarea
              id="idea"
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder="예: 실시간 채팅 앱을 만들고 싶어요. 사용자 인증, 채팅방 생성, 파일 공유 기능이 필요해요."
            />

            <div className="action-row">
              <button className="primary-button" onClick={handleGenerate} disabled={!canGenerate}>
                {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                {isGenerating ? "설계도 생성 중..." : "설계도 생성"}
              </button>
              <p className="action-hint">
                <Info size={15} />
                {isGenerating ? GENERATION_STEPS[generationStepIndex] : "구체적일수록 더 정확한 설계도가 생성돼요"}
              </p>
              {error && <p className="error-text">{error}</p>}
            </div>

            {isGenerating ? <GenerationStatus activeStepIndex={generationStepIndex} /> : (
              <div className="generation-preview">
                <span>핵심 기능 5개 도출</span>
                <span>REST API endpoint 설계</span>
                <span>ERD 및 DB 구조 생성</span>
                <span>시퀀스 다이어그램 정리</span>
              </div>
            )}
          </section>
        </section>

        <section className="app-board" id="result">
          <aside className="recent-panel" id="recent">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Saved Blueprints</p>
                <h2>최근 설계도</h2>
              </div>
              <button className="icon-button" onClick={() => refreshRecent()} aria-label="최근 설계도 새로고침">
                <RefreshCw size={18} />
              </button>
            </div>

            <div className="recent-list">
              {recentBlueprints.length === 0 ? (
                <p className="empty-text">저장된 설계도가 아직 없습니다.</p>
              ) : (
                recentBlueprints.map((item) => (
                  <div className="recent-row" key={item.id}>
                    <button
                      className={item.id === selectedBlueprintId ? "recent-item active" : "recent-item"}
                      onClick={() => handleOpen(item.id)}
                    >
                      <span className="recent-icon"><Network size={18} /></span>
                      <span className="recent-content">
                        <strong>{item.idea}</strong>
                        <small>{new Date(item.created_at).toLocaleString()}</small>
                      </span>
                      <span className="recent-status">완료</span>
                    </button>
                    <button className="danger-button" onClick={() => handleDelete(item.id)} aria-label="설계도 삭제">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </aside>

          <div className="result-area">
            {isGenerating ? (
              <section className="empty-state generating-state" aria-live="polite">
                <Loader2 className="spin" size={34} />
                <p>{GENERATION_STEPS[generationStepIndex]} 중입니다. 잠시만 기다려 주세요.</p>
              </section>
            ) : !blueprint ? (
              <section className="empty-state">
                <FileText size={34} />
                <p>아이디어를 입력하면 기능, API, DB, 다이어그램 설계도가 여기에 표시됩니다.</p>
              </section>
            ) : (
              <BlueprintView activeTab={activeResultTab} blueprint={blueprint} setActiveTab={setActiveResultTab} />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

// 생성 대기 시간 동안 사용자가 진행 상황을 체감할 수 있도록 단계별 안내를 보여줍니다.
function GenerationStatus({ activeStepIndex }) {
  return (
    <div className="generation-status" aria-live="polite">
      <div className="generation-status-header">
        <Loader2 className="spin" size={18} />
        <strong>{GENERATION_STEPS[activeStepIndex]}</strong>
      </div>
      <p>구현에 필요한 산출물을 순서대로 만들고 있어요.</p>
      <div className="generation-steps">
        {GENERATION_STEPS.map((step, index) => (
          <span
            className={[
              "generation-step",
              index === activeStepIndex ? "active" : "",
              index < activeStepIndex ? "done" : "",
            ].filter(Boolean).join(" ")}
            key={step}
          >
            {step}
          </span>
        ))}
      </div>
    </div>
  );
}

function BlueprintView({ activeTab, blueprint, setActiveTab }) {
  return (
    <div className="result-layout">
      <nav className="result-tabs" aria-label="설계도 결과 탭">
        {RESULT_TABS.map((tab) => (
          <button
            className={activeTab === tab.id ? "active" : ""}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="tab-panel">
        {activeTab === "summary" && (
          <div className="summary-tab">
            <section className="result-summary">
              <div>
                <p className="eyebrow">Generated Blueprint</p>
                <h2>설계도 결과</h2>
                <p>{blueprint.overview}</p>
              </div>
              <div className="summary-metrics">
                <Metric label="features" value={blueprint.features.length} />
                <Metric label="apis" value={blueprint.api_spec.length} />
                <Metric label="tables" value={blueprint.database_schema.length} />
              </div>
            </section>

            <Section title="기술 스택" description="서비스 성격에 맞춘 구현 기술 후보입니다.">
              <div className="stack-grid stack-grid-wide">
                {Object.entries({
                  Backend: blueprint.tech_stack.backend,
                  Frontend: blueprint.tech_stack.frontend,
                  Database: blueprint.tech_stack.database,
                  AI: blueprint.tech_stack.ai,
                }).map(([title, items]) => (
                  <TechStackColumn items={items} key={title} title={title} />
                ))}
              </div>
              <p className="note">{blueprint.tech_stack.rationale}</p>
            </Section>
          </div>
        )}

        {activeTab === "features" && (
          <Section title="핵심 기능" description="MVP 구현 우선순위를 기준으로 기능을 정리합니다.">
            <div className="feature-list">
              {blueprint.features.map((feature) => (
                <article className="feature-item" key={feature.name}>
                  <div className="feature-title">
                    <span className={`priority ${feature.priority}`}>{feature.priority}</span>
                    <h3>{feature.name}</h3>
                  </div>
                  <p>{feature.description}</p>
                </article>
              ))}
            </div>
          </Section>
        )}

        {activeTab === "api" && (
          <Section title="API 설계" description="프론트엔드와 백엔드가 주고받을 endpoint 초안입니다.">
            <div className="endpoint-grid">
              {blueprint.api_spec.map((endpoint) => (
                <article className="endpoint-card" key={`${endpoint.method}-${endpoint.path}`}>
                  <div className="endpoint-card-header">
                    <MethodBadge method={endpoint.method} />
                    <span>{endpoint.path}</span>
                  </div>
                  <p className="endpoint-description">{endpoint.description}</p>
                  <FieldTable title="Request" rows={endpoint.request} />
                  <FieldTable title="Response" rows={endpoint.response} />
                </article>
              ))}
            </div>
          </Section>
        )}

        {activeTab === "database" && (
          <Section title="데이터베이스 설계" description="초기 구현에 필요한 주요 table과 column 구조입니다.">
            <div className="schema-grid">
              {blueprint.database_schema.map((table) => (
                <article className="schema-card" key={table.name}>
                  <div className="schema-card-header">
                    <Database size={16} />
                    <span>{table.name}</span>
                  </div>
                  <p className="schema-description">{table.description}</p>
                  <ColumnList rows={table.columns} />
                </article>
              ))}
            </div>
          </Section>
        )}

        {activeTab === "diagrams" && (
          <div className="diagram-grid">
            <Section title="데이터베이스 ERD" description="테이블 간 관계를 Mermaid ERD로 표현합니다.">
              <MermaidDiagram source={blueprint.database_erd} />
            </Section>

            <Section title="시퀀스 다이어그램" description="사용자 요청이 처리되는 주요 흐름입니다.">
              <MermaidDiagram source={blueprint.sequence_diagram} />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <Blocks size={16} />
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function MethodBadge({ method }) {
  return (
    <code className={`method-badge method-${method.toLowerCase()}`}>
      <Braces size={13} />
      {method}
    </code>
  );
}

function FieldTable({ title, rows }) {
  return (
    <div className="data-block">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>name</th>
            <th>type</th>
            <th>required</th>
            <th>description</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${title}-${row.name}`}>
              <td>{row.name}</td>
              <td>{row.type}</td>
              <td>{row.required ? "true" : "false"}</td>
              <td>{row.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const CONSTRAINT_LABELS = {
  primary_key: "PRIMARY KEY",
  not_null: "NOT NULL",
  foreign_key: "FOREIGN KEY",
  unique: "UNIQUE",
};

function formatConstraint(constraint) {
  const normalized = constraint.toLowerCase();
  const normalizedKey = normalized.replaceAll(" ", "_");

  if (normalized.startsWith("foreign key")) {
    return "FOREIGN KEY";
  }

  return CONSTRAINT_LABELS[normalizedKey] || CONSTRAINT_LABELS[normalized] || constraint;
}

function ColumnList({ rows }) {
  return (
    <div className="column-list">
      {rows.map((row) => (
        <div className="column-row" key={row.name}>
          <div className="column-main">
            <strong>{row.name}</strong>
          </div>
          <span className="column-type">{row.type}</span>
          <div className="constraint-list">
            {row.constraints.map((constraint) => (
              <span className="constraint-badge" key={`${row.name}-${constraint}`} title={constraint}>
                {formatConstraint(constraint)}
              </span>
            ))}
          </div>
          <p>{row.description}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
