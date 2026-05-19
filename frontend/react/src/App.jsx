import { useEffect, useMemo, useState } from "react";
import {
  Database,
  Download,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  Trash2,
} from "lucide-react";
import mermaid from "mermaid";

import { createBlueprint, deleteBlueprint, getBlueprint, listBlueprints } from "./api.js";
import { downloadMarkdown } from "./markdown.js";

const SAMPLE_IDEAS = [
  "챗봇을 이용한 쇼핑몰 고객상담 자동화 서비스",
  "개발자를 위한 AI 기반 API 설계 자동화 도구",
  "소상공인을 위한 예약 관리 및 고객 알림 서비스",
];

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

function MermaidDiagram({ source }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

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

  if (error) {
    return <pre className="diagram-error">{error}</pre>;
  }

  return <div className="diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}

function Section({ title, children }) {
  return (
    <section className="section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function App() {
  const [idea, setIdea] = useState("");
  const [blueprint, setBlueprint] = useState(null);
  const [recentBlueprints, setRecentBlueprints] = useState([]);
  const [selectedBlueprintId, setSelectedBlueprintId] = useState(null);
  const [loading, setLoading] = useState(false);
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

  async function handleGenerate() {
    if (!canGenerate) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await createBlueprint(idea);
      setBlueprint(result);
      setSelectedBlueprintId(null);
      await refreshRecent();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow">Saved Blueprints</p>
            <h1>최근 설계도</h1>
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
                  <span>{item.idea}</span>
                  <small>{new Date(item.created_at).toLocaleString()}</small>
                </button>
                <button className="danger-button" onClick={() => handleDelete(item.id)} aria-label="설계도 삭제">
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">DevBlueprint AI</p>
            <h1>서비스 아이디어를 시스템 설계도로 변환</h1>
          </div>
          {blueprint && (
            <button className="secondary-button" onClick={() => downloadMarkdown(selectedIdea, blueprint)}>
              <Download size={18} />
              Markdown
            </button>
          )}
        </header>

        <section className="input-panel">
          <div className="sample-row">
            {SAMPLE_IDEAS.map((sample) => (
              <button key={sample} className="sample-button" onClick={() => setIdea(sample)}>
                {sample}
              </button>
            ))}
          </div>

          <label htmlFor="idea">서비스 아이디어</label>
          <textarea
            id="idea"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            placeholder="예: 스포츠 야구 분석 및 승부 예측 서비스"
          />

          <div className="action-row">
            <button className="primary-button" onClick={handleGenerate} disabled={!canGenerate}>
              {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              설계도 생성
            </button>
            {error && <p className="error-text">{error}</p>}
          </div>
        </section>

        {!blueprint ? (
          <section className="empty-state">
            <FileText size={34} />
            <p>아이디어를 입력하면 기능, API, DB, 다이어그램 설계도가 여기에 표시됩니다.</p>
          </section>
        ) : (
          <BlueprintView blueprint={blueprint} />
        )}
      </main>
    </div>
  );
}

function BlueprintView({ blueprint }) {
  return (
    <div className="result-layout">
      <Section title="개요">
        <p>{blueprint.overview}</p>
      </Section>

      <Section title="핵심 기능">
        <div className="feature-grid">
          {blueprint.features.map((feature) => (
            <article className="feature-item" key={feature.name}>
              <span className={`priority ${feature.priority}`}>{feature.priority}</span>
              <h3>{feature.name}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
      </Section>

      <Section title="기술 스택">
        <div className="stack-grid">
          {Object.entries({
            Backend: blueprint.tech_stack.backend,
            Frontend: blueprint.tech_stack.frontend,
            Database: blueprint.tech_stack.database,
            AI: blueprint.tech_stack.ai,
          }).map(([title, items]) => (
            <div className="stack-column" key={title}>
              <strong>{title}</strong>
              {items.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          ))}
        </div>
        <p className="note">{blueprint.tech_stack.rationale}</p>
      </Section>

      <Section title="API 설계">
        <div className="table-list">
          {blueprint.api_spec.map((endpoint) => (
            <details key={`${endpoint.method}-${endpoint.path}`} open>
              <summary>
                <code>{endpoint.method}</code>
                <span>{endpoint.path}</span>
              </summary>
              <p>{endpoint.description}</p>
              <FieldTable title="Request" rows={endpoint.request} />
              <FieldTable title="Response" rows={endpoint.response} />
            </details>
          ))}
        </div>
      </Section>

      <Section title="데이터베이스 설계">
        <div className="table-list">
          {blueprint.database_schema.map((table) => (
            <details key={table.name} open>
              <summary>
                <Database size={16} />
                <span>{table.name}</span>
              </summary>
              <p>{table.description}</p>
              <ColumnTable rows={table.columns} />
            </details>
          ))}
        </div>
      </Section>

      <Section title="데이터베이스 ERD">
        <MermaidDiagram source={blueprint.database_erd} />
      </Section>

      <Section title="시퀀스 다이어그램">
        <MermaidDiagram source={blueprint.sequence_diagram} />
      </Section>
    </div>
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

function ColumnTable({ rows }) {
  return (
    <div className="data-block">
      <table>
        <thead>
          <tr>
            <th>name</th>
            <th>type</th>
            <th>constraints</th>
            <th>description</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <td>{row.name}</td>
              <td>{row.type}</td>
              <td>{row.constraints.join(", ")}</td>
              <td>{row.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
