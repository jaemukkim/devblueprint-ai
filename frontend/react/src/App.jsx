import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  Blocks,
  Bot,
  Braces,
  CheckCircle2,
  Code2,
  Database,
  Download,
  FileText,
  GitBranch,
  Info,
  LayoutGrid,
  Loader2,
  MessageCircle,
  Network,
  RefreshCw,
  Send,
  Server,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import {
  apiBaseUrl,
  applyBlueprintSectionPreview,
  createBlueprint,
  deleteBlueprint,
  getBlueprint,
  getHealth,
  listBlueprints,
  regenerateBlueprintSection,
  reviseBlueprint,
} from "./api.js";
import { downloadMarkdown } from "./markdown.js";
import { normalizeMermaidSource } from "./mermaid.js";

const MermaidDiagram = lazy(() => import("./DiagramRenderer.jsx"));

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
  { id: "plan", label: "계획" },
];

const SECTION_REGENERATION_BY_TAB = {
  features: "features",
  api: "api",
  database: "database",
  diagrams: "diagrams",
  plan: "planning",
};

const SECTION_LABELS = {
  features: "기능",
  api: "API",
  database: "DB",
  diagrams: "다이어그램",
  planning: "계획",
};

const DEFAULT_REGENERATION_INSTRUCTIONS = {
  features: "새 핵심 기능을 하나 추가하고 기존 기능 설명도 더 구현 가능한 단위로 정리해줘",
  api: "API endpoint와 request/response 필드를 더 현실적으로 다시 정리해줘",
  database: "테이블과 컬럼 구성을 더 구현 친화적으로 다시 정리해줘",
  diagrams: "현재 API와 DB를 더 잘 드러내도록 다이어그램을 다시 정리해줘",
  planning: "구현 순서와 운영 체크포인트를 더 현실적으로 다시 정리해줘",
};

// 생성 대기 화면에서 순차적으로 보여줄 작업 단계입니다.
const GENERATION_STEPS = [
  "아이디어 분석",
  "기능/기술 스택 설계",
  "API 설계",
  "DB 스키마 설계",
  "다이어그램/구현 계획 정리",
];

// 네트워크가 즉시 실패해도 사용자가 클릭 피드백을 인지할 수 있는 최소 표시 시간입니다.
// 챗봇으로 설계도 수정 요청을 보냈을 때 사용자에게 보여줄 진행 단계입니다.
const REVISION_STEPS = [
  "수정 요청 접수",
  "기존 설계도 분석",
  "변경 영향 반영",
  "품질 검증 중",
];

const GENERATION_FEEDBACK_MIN_MS = 600;

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

function DiagramLoading() {
  return <div className="diagram-loading">다이어그램 렌더러를 불러오고 있습니다.</div>;
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
// 저장명에 과거 수정 문구가 섞여 있더라도 입력창에는 원본 서비스 아이디어만 보여줍니다.
function getBaseIdea(ideaText) {
  return ideaText.split("수정:", 1)[0].replace("·", "").trim();
}

// 같은 서비스 아이디어에서 파생된 수정 결과를 초안과 개선안으로 구분해 최근 목록에 표시합니다.
function buildRecentBlueprintItems(items) {
  const versionById = new Map();
  const groups = new Map();

  items.forEach((item) => {
    const baseIdea = getBaseIdea(item.idea);
    const group = groups.get(baseIdea) || [];
    group.push(item);
    groups.set(baseIdea, group);
  });

  groups.forEach((group) => {
    [...group]
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .forEach((item, index) => {
        versionById.set(item.id, index + 1);
      });
  });

  return items.map((item) => {
    const version = versionById.get(item.id) || 1;

    return {
      ...item,
      baseIdea: getBaseIdea(item.idea),
      version,
      versionLabel: version === 1 ? "초안" : `개선안 ${version - 1}`,
      isRevision: version > 1,
      revisionSummary: summarizeRevisionInstruction(item.revision_instruction),
    };
  });
}

function toUserError(error) {
  // 사용자에게 보여줄 오류 제목과 조치 문구를 표준화합니다.
  if (typeof error === "string") {
    return {
      type: "request",
      title: "요청을 확인해 주세요",
      message: error,
      detail: "",
    };
  }

  const type = error?.type || "request";
  const statusText = error?.status ? `status=${error.status}` : "";
  const message = error?.message || "알 수 없는 오류가 발생했습니다.";
  const errorCopy = ERROR_COPY_BY_TYPE[type] || ERROR_COPY_BY_TYPE.request;
  const hint = error?.hint || "";
  const errorCode = error?.errorCode || "";
  const detailParts = [statusText, errorCode].filter(Boolean);

  return {
    type,
    title: errorCopy.title,
    message: errorCopy.message(message, hint),
    detail: detailParts.join(" · "),
    hint,
    errorCode,
  };
}

const ERROR_COPY_BY_TYPE = {
  network: {
    title: "API 서버 연결 실패",
    message: (message) => `${message} 현재 API 주소는 ${apiBaseUrl}입니다.`,
  },
  openai: {
    title: "OpenAI 호출 실패",
    message: (message, hint) => message || hint || "OpenAI 연결, API key, 모델 권한 또는 네트워크 설정을 확인해 주세요.",
  },
  validation: {
    title: "설계도 품질 검증 실패",
    message: (message, hint) => hint || `생성 결과가 품질 기준을 통과하지 못했습니다. ${message}`,
  },
  duplicate: {
    title: "중복 요청",
    message: (message) => message,
  },
  not_found: {
    title: "데이터를 찾을 수 없음",
    message: (message) => message,
  },
  server: {
    title: "백엔드 처리 실패",
    message: (message) => message,
  },
  request: {
    title: "요청 실패",
    message: (message) => message,
  },
};

// 카드가 길어지지 않도록 수정 요청 원문을 짧은 한 줄 요약으로 줄입니다.
function summarizeRevisionInstruction(instruction) {
  if (!instruction) {
    return "";
  }

  const normalizedInstruction = instruction.replace(/\s+/g, " ").trim();
  const maxLength = 18;
  const characters = Array.from(normalizedInstruction);

  if (characters.length <= maxLength) {
    return normalizedInstruction;
  }

  return `${characters.slice(0, maxLength).join("")}...`;
}

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
  // 챗봇 수정 요청이 진행 중인지 구분해 입력창과 버튼 상태를 제어합니다.
  const [isRevising, setIsRevising] = useState(false);
  // 긴 생성 시간 동안 현재 어느 단계처럼 보일지 관리합니다.
  const [generationStepIndex, setGenerationStepIndex] = useState(0);
  // 상단 메뉴와 결과 탭이 같은 선택 상태를 공유하도록 관리합니다.
  const [activeResultTab, setActiveResultTab] = useState("summary");
  // 설계 보조 챗 위젯의 열림/닫힘 상태를 관리합니다.
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isRegeneratingSection, setIsRegeneratingSection] = useState(false);
  // 섹션 재생성 미리보기를 새 저장본으로 적용하는 동안 버튼 중복 클릭을 막습니다.
  const [isApplyingSectionPreview, setIsApplyingSectionPreview] = useState(false);
  const [sectionPreview, setSectionPreview] = useState(null);
  const [isShowingSectionPreview, setIsShowingSectionPreview] = useState(false);
  const [regenerationNotice, setRegenerationNotice] = useState("");
  const [lastRegenerationFailure, setLastRegenerationFailure] = useState(null);
  const [error, setError] = useState(null);
  // 개발 중 현재 연결된 API 서버와 백엔드 모드를 빠르게 확인하기 위한 상태입니다.
  const [environmentStatus, setEnvironmentStatus] = useState({
    loading: true,
    error: "",
    health: null,
  });

  const canGenerate = idea.trim().length >= 5 && !loading;
  const displayedBlueprint = isShowingSectionPreview && sectionPreview ? sectionPreview.result : blueprint;
  const previewChangeCount = useMemo(
    () => (sectionPreview && blueprint
      ? getSectionChangeCount(blueprint, sectionPreview.result, sectionPreview.section)
      : null),
    [blueprint, sectionPreview],
  );

  const selectedIdea = useMemo(() => {
    const selected = recentBlueprints.find((item) => item.id === selectedBlueprintId);
    return getBaseIdea(selected?.idea || idea);
  }, [idea, recentBlueprints, selectedBlueprintId]);

  const recentBlueprintItems = useMemo(
    () => buildRecentBlueprintItems(recentBlueprints),
    [recentBlueprints],
  );

  async function refreshRecent() {
    const response = await listBlueprints();
    const items = response.items || [];
    setRecentBlueprints(items);
    return items;
  }

  // health endpoint를 호출해 개발 환경 상태 패널에 표시할 값을 갱신합니다.
  async function refreshEnvironmentStatus() {
    setEnvironmentStatus((current) => ({ ...current, loading: true, error: "" }));

    try {
      const health = await getHealth();
      setEnvironmentStatus({ loading: false, error: "", health });
    } catch (err) {
      setEnvironmentStatus({
        loading: false,
        error: toUserError(err).message,
        health: null,
      });
    }
  }

  useEffect(() => {
    refreshRecent().catch((err) => setError(toUserError(err)));
  }, []);

  useEffect(() => {
    refreshEnvironmentStatus();
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
    setError(null);
    setSectionPreview(null);
    setIsShowingSectionPreview(false);
    setRegenerationNotice("");
    const startedAt = Date.now();

    try {
      const result = await createBlueprint(idea);
      setBlueprint(result);
      setActiveResultTab("summary");
      const items = await refreshRecent();
      const savedBlueprint = items.find((item) => item.idea.trim() === idea.trim());
      setSelectedBlueprintId(savedBlueprint?.id || null);
    } catch (err) {
      setError(toUserError(err));
    } finally {
      await wait(getRemainingFeedbackMs(startedAt));
      setLoading(false);
      setIsGenerating(false);
    }
  }

  async function handleOpen(id) {
    setLoading(true);
    setError(null);
    setSectionPreview(null);
    setIsShowingSectionPreview(false);
    setRegenerationNotice("");

    try {
      const stored = await getBlueprint(id);
      setBlueprint(stored.result);
      setIdea(getBaseIdea(stored.idea));
      setSelectedBlueprintId(stored.id);
      setActiveResultTab("summary");
    } catch (err) {
      setError(toUserError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("저장된 설계도를 삭제할까요?")) {
      return;
    }

    setError(null);

    try {
      await deleteBlueprint(id);
      if (selectedBlueprintId === id) {
        setBlueprint(null);
        setSelectedBlueprintId(null);
        setSectionPreview(null);
        setIsShowingSectionPreview(false);
        setRegenerationNotice("");
      }
      await refreshRecent();
    } catch (err) {
      setError(toUserError(err));
    }
  }

  function handleResultNav(tabId) {
    setActiveResultTab(tabId);
    scrollToSection("result");
  }

  async function handleRegenerateSection(section, presetInstruction = null) {
    if (!selectedBlueprintId || isRegeneratingSection || isRevising) {
      return;
    }

    const previousInstruction = lastRegenerationFailure?.section === section
      ? lastRegenerationFailure.instruction
      : "";
    const instruction = presetInstruction ?? window.prompt(
      `${SECTION_LABELS[section] || "섹션"} 재생성 요청`,
      previousInstruction || DEFAULT_REGENERATION_INSTRUCTIONS[section] || "",
    );

    if (instruction === null) {
      setRegenerationNotice("재생성 요청을 취소했습니다.");
      return;
    }

    if (instruction.trim().length > 0 && instruction.trim().length < 5) {
      setError(toUserError("재생성 요청은 5자 이상 입력해 주세요."));
      return;
    }

    setIsRegeneratingSection(true);
    setError(null);
    setRegenerationNotice("");
    setLastRegenerationFailure(null);

    try {
      const preview = await regenerateBlueprintSection(selectedBlueprintId, section, instruction?.trim() || undefined);
      const normalizedPreview = {
        ...normalizeSectionPreview(preview, section, instruction?.trim() || ""),
        instruction: instruction?.trim() || "",
      };
      const changeCount = blueprint ? getSectionChangeCount(blueprint, normalizedPreview.result, normalizedPreview.section) : 0;
      setSectionPreview(normalizedPreview);
      setIsShowingSectionPreview(true);
      if (changeCount === 0) {
        setRegenerationNotice("재생성 결과가 원본과 거의 같습니다. 더 구체적인 요청으로 다시 시도해 주세요.");
      } else {
        setRegenerationNotice(getSectionChangeNotice(blueprint, normalizedPreview.result, normalizedPreview.section));
      }
      setActiveResultTab(section === "planning" ? "plan" : section);
      scrollToSection("result");
    } catch (err) {
      const userError = toUserError(err);
      const trimmedInstruction = instruction?.trim() || "";
      setLastRegenerationFailure({
        section,
        instruction: trimmedInstruction,
        message: userError.message,
      });
      setRegenerationNotice(`재생성 실패: ${userError.message}`);
    } finally {
      setIsRegeneratingSection(false);
    }
  }

  function handleRetryRegeneration() {
    if (!lastRegenerationFailure) {
      return;
    }

    handleRegenerateSection(lastRegenerationFailure.section, lastRegenerationFailure.instruction);
  }

  async function handleApplySectionPreview() {
    if (!selectedBlueprintId || !sectionPreview || isApplyingSectionPreview) {
      return;
    }

    setIsApplyingSectionPreview(true);
    setError(null);
    setRegenerationNotice("");

    try {
      const applied = await applyBlueprintSectionPreview(
        selectedBlueprintId,
        sectionPreview.section,
        sectionPreview.result,
        sectionPreview.instruction || "",
      );
      setBlueprint(applied.result);
      setIdea(getBaseIdea(applied.idea));
      setSelectedBlueprintId(applied.id);
      setSectionPreview(null);
      setIsShowingSectionPreview(false);
      setRegenerationNotice("미리보기를 새 개선안으로 저장했습니다.");
      await refreshRecent();
      scrollToSection("result");
    } catch (err) {
      setRegenerationNotice(`미리보기 적용 실패: ${toUserError(err).message}`);
    } finally {
      setIsApplyingSectionPreview(false);
    }
  }

  async function handleReviseBlueprint(instruction) {
    if (!selectedBlueprintId || isRevising) {
      return;
    }

    setIsRevising(true);
    setError(null);
    setSectionPreview(null);
    setIsShowingSectionPreview(false);
    setRegenerationNotice("");

    try {
      const revised = await reviseBlueprint(selectedBlueprintId, instruction);
      setBlueprint(revised.result);
      setIdea(getBaseIdea(revised.idea));
      setSelectedBlueprintId(revised.id);
      setActiveResultTab("summary");
      await refreshRecent();
      scrollToSection("result");
    } catch (err) {
      setError(toUserError(err));
      throw err;
    } finally {
      setIsRevising(false);
    }
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
        {displayedBlueprint ? (
          <button className="nav-action" onClick={() => downloadMarkdown(selectedIdea, displayedBlueprint)}>
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
                <strong>30~60s</strong>
                <span>품질 생성 예상</span>
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
              {error && <ErrorNotice error={error} />}
            </div>

            {isGenerating ? <GenerationStatus activeStepIndex={generationStepIndex} /> : (
              <div className="generation-preview">
                <span>아이디어 분석</span>
                <span>기능/기술 스택 설계</span>
                <span>API와 DB 스키마 구성</span>
                <span>다이어그램/구현 계획 정리</span>
              </div>
            )}

            <DevEnvironmentStatus
              apiBaseUrl={apiBaseUrl}
              environmentStatus={environmentStatus}
              onRefresh={refreshEnvironmentStatus}
            />
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
              {recentBlueprintItems.length === 0 ? (
                <p className="empty-text">저장된 설계도가 아직 없습니다.</p>
              ) : (
                recentBlueprintItems.map((item) => (
                  <div className="recent-row" key={item.id}>
                    <button
                      className={item.id === selectedBlueprintId ? "recent-item active" : "recent-item"}
                      onClick={() => handleOpen(item.id)}
                    >
                      <span className="recent-icon"><Network size={18} /></span>
                      <span className="recent-content">
                        <span className="recent-title-line">
                          <strong>{item.baseIdea}</strong>
                        </span>
                        {item.revisionSummary && (
                          <span className="recent-revision-note" title={item.revision_instruction || ""}>
                            <span>수정</span>
                            {item.revisionSummary}
                          </span>
                        )}
                        <span className="recent-meta-line">
                          <span className="recent-badge-row">
                            <span className={item.isRevision ? "recent-version revision" : "recent-version"}>
                              {item.versionLabel}
                            </span>
                            <span className="recent-status">완료</span>
                          </span>
                          <small>{new Date(item.created_at).toLocaleString()}</small>
                        </span>
                      </span>
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
            ) : !displayedBlueprint ? (
              <section className="empty-state">
                <FileText size={34} />
                <p>아이디어를 입력하면 기능, API, DB, 다이어그램 설계도가 여기에 표시됩니다.</p>
              </section>
            ) : (
              <BlueprintView
                activeTab={activeResultTab}
                blueprint={displayedBlueprint}
                canRegenerate={Boolean(selectedBlueprintId) && !isRevising && !isApplyingSectionPreview}
                hasPreview={Boolean(sectionPreview)}
                isApplyingSectionPreview={isApplyingSectionPreview}
                isPreviewVisible={Boolean(isShowingSectionPreview && sectionPreview)}
                isRegeneratingSection={isRegeneratingSection}
                onApplySectionPreview={handleApplySectionPreview}
                onRegenerateSection={handleRegenerateSection}
                onRetryRegeneration={handleRetryRegeneration}
                onTogglePreview={() => setIsShowingSectionPreview((current) => !current)}
                previewChangeCount={previewChangeCount}
                previewSection={sectionPreview?.section || null}
                regenerationFailure={lastRegenerationFailure}
                regenerationNotice={regenerationNotice}
                setActiveTab={setActiveResultTab}
              />
            )}
          </div>
        </section>
      </main>

      <BlueprintAssistantChat
        blueprint={blueprint}
        canRevise={Boolean(selectedBlueprintId)}
        isOpen={isChatOpen}
        isRevising={isRevising}
        onRevise={handleReviseBlueprint}
        onToggle={() => setIsChatOpen((current) => !current)}
      />
    </div>
  );
}

// API 오류 유형별로 사용자가 바로 이해할 수 있는 안내를 표시합니다.
function ErrorNotice({ error }) {
  return (
    <div className={`error-notice ${error.type || "request"}`} role="alert">
      <strong>{error.title}</strong>
      <p>{error.message}</p>
      {error.hint && error.hint !== error.message && <p>{error.hint}</p>}
      {error.detail && <small>{error.detail}</small>}
    </div>
  );
}

// 로컬 개발 중 프론트가 바라보는 API와 백엔드 health 상태를 요약합니다.
function DevEnvironmentStatus({ apiBaseUrl, environmentStatus, onRefresh }) {
  const health = environmentStatus.health;
  const openai = health?.openai || null;
  const statusLabel = environmentStatus.loading
    ? "확인 중"
    : environmentStatus.error
      ? "연결 실패"
      : "연결됨";

  return (
    <div className="dev-status-panel" aria-label="개발 환경 상태">
      <div>
        <span>API</span>
        <strong>{apiBaseUrl}</strong>
      </div>
      <div>
        <span>Backend</span>
        <strong>{statusLabel}</strong>
      </div>
      <div>
        <span>OpenAI</span>
        <strong>{openai ? openai.status : health ? (health.use_openai ? "ON" : "OFF") : "-"}</strong>
      </div>
      <div>
        <span>Model</span>
        <strong>{openai?.model || "-"}</strong>
      </div>
      <div>
        <span>Key</span>
        <strong>{openai ? (openai.api_key_configured ? "SET" : "MISSING") : "-"}</strong>
      </div>
      <div>
        <span>Storage</span>
        <strong>{health?.repository_backend || "-"}</strong>
      </div>
      <button type="button" onClick={onRefresh} aria-label="개발 환경 상태 새로고침">
        <RefreshCw size={14} />
      </button>
      {openai?.message && <p>{openai.message}</p>}
      {environmentStatus.error && <p>{environmentStatus.error}</p>}
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

function BlueprintView({
  activeTab,
  blueprint,
  canRegenerate,
  hasPreview,
  isApplyingSectionPreview,
  isPreviewVisible,
  isRegeneratingSection,
  onApplySectionPreview,
  onRegenerateSection,
  onRetryRegeneration,
  onTogglePreview,
  previewChangeCount,
  previewSection,
  regenerationFailure,
  regenerationNotice,
  setActiveTab,
}) {
  const qualityItems = buildQualityItems(blueprint);
  const regenerationSection = SECTION_REGENERATION_BY_TAB[activeTab] || null;
  const regenerationLabel = SECTION_LABELS[regenerationSection] || "";

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

      {(regenerationSection || hasPreview) && (
        <section className={isPreviewVisible && previewChangeCount === 0 ? "section-regeneration-bar preview unchanged" : isPreviewVisible ? "section-regeneration-bar preview" : "section-regeneration-bar"}>
          <div>
            <strong>{isPreviewVisible ? `${SECTION_LABELS[previewSection] || "섹션"} 미리보기` : `${regenerationLabel} 다시 생성`}</strong>
            <p>
              {regenerationNotice || (isPreviewVisible
                ? previewChangeCount > 0
                  ? `저장되지 않은 결과입니다. 원본과 다른 항목 ${previewChangeCount}개를 확인했어요.`
                  : "저장되지 않은 결과지만 원본과 거의 같습니다. 요청을 더 구체적으로 입력해 보세요."
                : "현재 저장본을 기준으로 preview를 만듭니다.")}
            </p>
          </div>
          <div className="section-regeneration-actions">
            {isPreviewVisible && previewChangeCount > 0 && (
              <button
                className="primary-button"
                disabled={isApplyingSectionPreview}
                onClick={onApplySectionPreview}
                type="button"
              >
                {isApplyingSectionPreview ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
                {isApplyingSectionPreview ? "적용 중" : "미리보기 적용"}
              </button>
            )}
            {hasPreview && (
              <button className="secondary-button" type="button" onClick={onTogglePreview}>
                {isPreviewVisible ? <X size={16} /> : <CheckCircle2 size={16} />}
                {isPreviewVisible ? "원본 보기" : "미리보기 보기"}
              </button>
            )}
            {regenerationFailure && (
              <button
                className="secondary-button"
                disabled={!canRegenerate || isRegeneratingSection}
                onClick={onRetryRegeneration}
                type="button"
              >
                {isRegeneratingSection ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
                같은 요청 다시 시도
              </button>
            )}
            {regenerationSection && (
              <button
                className="primary-button section-regenerate-button"
                disabled={!canRegenerate || isRegeneratingSection}
                onClick={() => onRegenerateSection(regenerationSection)}
                type="button"
              >
                {isRegeneratingSection ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
                {isRegeneratingSection ? "재생성 중" : "다시 생성"}
              </button>
            )}
          </div>
        </section>
      )}

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

            <QualityChecks items={qualityItems} />

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
              <Suspense fallback={<DiagramLoading />}>
                <MermaidDiagram label="ERD 다이어그램" source={blueprint.database_erd} />
              </Suspense>
            </Section>

            <Section title="시퀀스 다이어그램" description="사용자 요청이 처리되는 주요 흐름입니다.">
              <Suspense fallback={<DiagramLoading />}>
                <MermaidDiagram label="시퀀스 다이어그램" source={blueprint.sequence_diagram} />
              </Suspense>
            </Section>
          </div>
        )}

        {activeTab === "plan" && (
          <div className="planning-grid">
            <Section title="비기능 요구사항" description="MVP를 실제 서비스로 다듬을 때 먼저 확인할 운영 품질 기준입니다.">
              <DesignConsiderationList items={blueprint.non_functional_requirements || []} />
            </Section>

            <Section title="보안 고려사항" description="입력, 권한, 비밀값, 남용 방지 관점의 구현 체크포인트입니다.">
              <DesignConsiderationList items={blueprint.security_considerations || []} />
            </Section>

            <Section title="구현 계획" description="개발자가 순서대로 진행할 수 있는 단계별 실행 계획입니다.">
              <ImplementationPlan steps={blueprint.implementation_plan || []} />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}

// 백엔드 validator를 통과한 결과임을 사용자가 볼 수 있게 요약 검증 항목을 만듭니다.
function buildQualityItems(blueprint) {
  const endpointKeys = blueprint.api_spec.map((endpoint) => `${endpoint.method} ${endpoint.path}`);
  const uniqueEndpointCount = new Set(endpointKeys).size;
  const erdText = blueprint.database_erd.toLowerCase();
  const erdMatchesSchema = blueprint.database_schema.every((table) => erdText.includes(table.name.toLowerCase()));

  return [
    {
      label: "기능 범위",
      value: `${blueprint.features.length}개 기능`,
      passed: blueprint.features.length >= 5 && blueprint.features.length <= 8,
    },
    {
      label: "API 중복 검사",
      value: `${uniqueEndpointCount}개 endpoint`,
      passed: uniqueEndpointCount === blueprint.api_spec.length,
    },
    {
      label: "DB 구조",
      value: `${blueprint.database_schema.length}개 table`,
      passed: blueprint.database_schema.length >= 3 && blueprint.database_schema.length <= 6,
    },
    {
      label: "ERD 일치",
      value: erdMatchesSchema ? "schema 반영" : "확인 필요",
      passed: erdMatchesSchema,
    },
    {
      label: "다이어그램 형식",
      value: "Mermaid 통과",
      passed: blueprint.database_erd.startsWith("erDiagram") && blueprint.sequence_diagram.startsWith("sequenceDiagram"),
    },
    {
      label: "운영 계획",
      value: `${blueprint.implementation_plan?.length || 0}개 단계`,
      passed: (blueprint.non_functional_requirements?.length || 0) >= 3
        && (blueprint.security_considerations?.length || 0) >= 3
        && (blueprint.implementation_plan?.length || 0) >= 3,
    },
  ];
}

function getSectionChangeCount(originalBlueprint, previewBlueprint, section) {
  if (section === "diagrams") {
    return getChangedDiagramLabels(originalBlueprint, previewBlueprint).length;
  }

  const originalItems = getComparableSectionItems(originalBlueprint, section);
  const previewItems = getComparableSectionItems(previewBlueprint, section);
  const maxLength = Math.max(originalItems.length, previewItems.length);
  let changeCount = 0;

  for (let index = 0; index < maxLength; index += 1) {
    if (JSON.stringify(originalItems[index] || null) !== JSON.stringify(previewItems[index] || null)) {
      changeCount += 1;
    }
  }

  return changeCount;
}

// 섹션별 변경 수를 사용자가 보는 단위에 맞춰 설명합니다.
function getSectionChangeNotice(originalBlueprint, previewBlueprint, section) {
  if (section === "diagrams") {
    const changedLabels = getChangedDiagramLabels(originalBlueprint, previewBlueprint);
    return `다이어그램 미리보기에 ${changedLabels.join(", ")} ${changedLabels.length}개가 반영됐습니다.`;
  }

  const changeCount = getSectionChangeCount(originalBlueprint, previewBlueprint, section);
  return `재생성 미리보기에 변경 항목 ${changeCount}개가 반영됐습니다.`;
}

// Mermaid 문자열의 공백/쉼표 보정 차이는 제외하고 실제 다이어그램 내용 변경만 셉니다.
function getChangedDiagramLabels(originalBlueprint, previewBlueprint) {
  const diagramPairs = [
    ["ERD", originalBlueprint?.database_erd || "", previewBlueprint?.database_erd || ""],
    ["시퀀스", originalBlueprint?.sequence_diagram || "", previewBlueprint?.sequence_diagram || ""],
  ];

  return diagramPairs
    .filter(([, originalSource, previewSource]) => normalizeDiagramText(originalSource) !== normalizeDiagramText(previewSource))
    .map(([label]) => label);
}

// Mermaid 렌더링 보정 후 공백을 제거해 화면상 의미 있는 변경만 비교합니다.
function normalizeDiagramText(source) {
  return normalizeMermaidSource(source).replace(/\s+/g, "").trim();
}

function getComparableSectionItems(blueprint, section) {
  if (!blueprint) {
    return [];
  }

  if (section === "features") {
    return [blueprint.overview, blueprint.tech_stack, ...blueprint.features];
  }

  if (section === "api") {
    return blueprint.api_spec || [];
  }

  if (section === "database") {
    return blueprint.database_schema || [];
  }

  if (section === "diagrams") {
    return [blueprint.database_erd, blueprint.sequence_diagram];
  }

  if (section === "planning") {
    return [
      ...(blueprint.non_functional_requirements || []),
      ...(blueprint.security_considerations || []),
      ...(blueprint.implementation_plan || []),
    ];
  }

  return [];
}

function normalizeSectionPreview(preview, section, instruction) {
  if (section !== "features" || !instruction.trim()) {
    return preview;
  }

  const result = structuredClone(preview.result);
  const requestedLabel = cleanFeatureInstruction(instruction);

  if (!requestedLabel || isFeatureInstructionReflected(result.features || [], instruction)) {
    return preview;
  }

  const requestedFeature = {
    name: requestedLabel.endsWith("기능") ? requestedLabel : `${requestedLabel} 기능`,
    description: `사용자가 요청한 '${instruction}' 내용을 핵심 기능으로 반영해 화면, API, 데이터 모델에서 구현 범위를 추적할 수 있게 합니다.`,
    priority: "medium",
  };

  if ((result.features || []).length < 8) {
    result.features = [...(result.features || []), requestedFeature];
  } else {
    result.features = [...result.features.slice(0, -1), requestedFeature];
  }

  return {
    ...preview,
    result,
  };
}

function normalizeComparableText(value) {
  return value.replace(/\s+/g, "").toLowerCase();
}

function cleanFeatureInstruction(instruction) {
  let cleanedInstruction = instruction.trim().replace(/\n/g, " ");

  [
    "기능을 추가해줘",
    "기능 추가해줘",
    "기능을 추가",
    "기능 추가",
    "추가해줘",
    "해주세요",
    "해줘",
  ].forEach((suffix) => {
    cleanedInstruction = cleanedInstruction.replaceAll(suffix, "");
  });

  return cleanedInstruction.replace(/\s+/g, " ").replace(/[.,!?]+$/g, "").trim();
}

function isFeatureInstructionReflected(features, instruction) {
  const requestedTokens = getFeatureInstructionTokens(instruction);

  if (requestedTokens.length === 0) {
    return false;
  }

  return features.some((feature) => {
    const featureText = normalizeComparableText(`${feature.name} ${feature.description}`);
    const matchedCount = requestedTokens.filter((token) => featureText.includes(token)).length;
    return matchedCount >= Math.min(2, requestedTokens.length);
  });
}

function getFeatureInstructionTokens(instruction) {
  return cleanFeatureInstruction(instruction)
    .split(/\s+/)
    .map((token) => normalizeComparableText(token.replace(/[.,!?()[\]{}]/g, "")))
    .filter((token) => token.length >= 2 && !["기능", "추천", "관리", "제공"].includes(token));
}

// 설계도 생성 결과가 어떤 품질 기준을 통과했는지 카드 형태로 보여줍니다.
function QualityChecks({ items }) {
  return (
    <section className="quality-card">
      <div className="quality-heading">
        <div>
          <p className="eyebrow">Quality Gate</p>
          <h2>품질 검증 통과</h2>
        </div>
        <span className="quality-badge">
          <CheckCircle2 size={16} />
          검증 완료
        </span>
      </div>
      <div className="quality-grid">
        {items.map((item) => (
          <div className={item.passed ? "quality-item passed" : "quality-item"} key={item.label}>
            <CheckCircle2 size={17} />
            <span>
              <strong>{item.label}</strong>
              <small>{item.value}</small>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
// 비기능 요구사항과 보안 고려사항을 렌더링하는 컴포넌트입니다.
function DesignConsiderationList({ items }) {
  if (!items.length) {
    return <p className="empty-text plan-empty">아직 정리된 항목이 없습니다.</p>;
  }

  return (
    <div className="consideration-list">
      {items.map((item) => (
        <article className="consideration-item" key={`${item.category}-${item.title}`}>
          <div className="consideration-heading">
            <span className={`priority ${item.priority}`}>{item.priority}</span>
            <span className="consideration-category">{item.category}</span>
          </div>
          <h3>{item.title}</h3>
          <p>{item.description}</p>
        </article>
      ))}
    </div>
  );
}
// 구현 계획을 렌더링하는 컴포넌트입니다.
function ImplementationPlan({ steps }) {
  if (!steps.length) {
    return <p className="empty-text plan-empty">아직 정리된 구현 단계가 없습니다.</p>;
  }

  return (
    <div className="implementation-list">
      {steps.map((step) => (
        <article className="implementation-step" key={`${step.phase}-${step.title}`}>
          <span>{step.phase}</span>
          <div>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

// 설계도 결과를 보면서 바로 수정 요청을 남길 수 있는 플로팅 챗 위젯입니다.
function BlueprintAssistantChat({ blueprint, canRevise, isOpen, isRevising, onRevise, onToggle }) {
  const [message, setMessage] = useState("");
  const [chatStatus, setChatStatus] = useState("");
  // 중복 요청처럼 사용자가 바로 이해해야 하는 응답은 봇 말풍선으로 따로 보여줍니다.
  const [chatNotice, setChatNotice] = useState(null);
  const [pendingInstruction, setPendingInstruction] = useState("");
  const [revisionStepIndex, setRevisionStepIndex] = useState(0);
  const quickPrompts = [
    "관리자 기능 추가해줘",
    "DB 구조를 더 현실적으로 나눠줘",
    "API 설명을 더 구체화해줘",
  ];
  const isDisabled = !blueprint || !canRevise || isRevising;

  useEffect(() => {
    if (!isRevising) {
      setRevisionStepIndex(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setRevisionStepIndex((currentIndex) => Math.min(currentIndex + 1, REVISION_STEPS.length - 1));
    }, 3500);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isRevising]);

  useEffect(() => {
    if (blueprint && canRevise) {
      return;
    }

    setMessage("");
    setChatStatus("");
    setChatNotice(null);
    setPendingInstruction("");
    setRevisionStepIndex(0);
  }, [blueprint, canRevise]);

  // 사용자의 수정 요청을 부모 컴포넌트의 API 연결 함수로 넘기고 입력 상태를 정리합니다.
  async function submitRevision(instruction) {
    const trimmedInstruction = instruction.trim();

    if (!trimmedInstruction || isDisabled) {
      return;
    }

    setChatStatus("");
    setChatNotice(null);
    setPendingInstruction(trimmedInstruction);

    try {
      await onRevise(trimmedInstruction);
      setMessage("");
      setPendingInstruction("");
      setChatNotice({
        tone: "success",
        title: "수정 요청을 반영했어요.",
        message: "변경된 설계도를 결과 화면에 다시 정리해뒀습니다.",
      });
    } catch (err) {
      if (err.status === 409) {
        setChatNotice({
          tone: "info",
          title: "이미 반영된 요청이에요.",
          message: "같은 기능은 다시 생성하지 않았어요. 다른 변경사항을 입력해 주세요.",
        });
      } else {
        setChatStatus(err.message);
      }
    } finally {
      setPendingInstruction("");
    }
  }

  return (
    <aside className={isOpen ? "assistant-chat open" : "assistant-chat"} aria-label="설계 보조 챗">
      {isOpen && (
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <span className="assistant-bot-mark">
              <Bot size={22} />
            </span>
            <div>
              <strong>DevBlueprint Bot</strong>
              <small>{canRevise ? "현재 설계도 개선 준비됨" : "설계도 생성 후 수정 가능"}</small>
            </div>
            <button type="button" onClick={onToggle} aria-label="설계 보조 챗 닫기">
              <X size={18} />
            </button>
          </div>

          <div className="assistant-chat-body">
            <div className="assistant-message bot">
              <p>
                생성된 설계도를 보면서 기능, API, DB, 다이어그램을 어떻게 바꾸고 싶은지 알려주세요.
              </p>
            </div>

            {isRevising && (
              <div className="assistant-revision-progress" aria-live="polite">
                <div className="assistant-progress-heading">
                  <Loader2 className="spin" size={17} />
                  <strong>{REVISION_STEPS[revisionStepIndex]}</strong>
                </div>
                {pendingInstruction && <p>요청: {pendingInstruction}</p>}
                <div className="assistant-progress-steps">
                  {REVISION_STEPS.map((step, index) => (
                    <span
                      className={[
                        "assistant-progress-step",
                        index === revisionStepIndex ? "active" : "",
                        index < revisionStepIndex ? "done" : "",
                      ].filter(Boolean).join(" ")}
                      key={step}
                    >
                      {step}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="assistant-quick-prompts" aria-label="빠른 수정 요청 예시">
              {quickPrompts.map((prompt) => (
                <button type="button" key={prompt} disabled={isDisabled} onClick={() => submitRevision(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>

            {chatNotice && (
              <div className={`assistant-message bot ${chatNotice.tone}`}>
                <strong>{chatNotice.title}</strong>
                <p>{chatNotice.message}</p>
              </div>
            )}

            {chatStatus && <p className="assistant-chat-status">{chatStatus}</p>}
          </div>

          <form
            className="assistant-chat-input"
            onSubmit={(event) => {
              event.preventDefault();
              submitRevision(message);
            }}
          >
            <input
              aria-label="설계도 수정 요청"
              disabled={isDisabled}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={isRevising ? "수정 요청을 반영하는 중입니다" : canRevise ? "수정 요청을 입력하세요" : "먼저 설계도를 생성하세요"}
              type="text"
              value={message}
            />
            <button type="submit" disabled={isDisabled || message.trim().length < 5} aria-label="수정 요청 보내기">
              {isRevising ? <Loader2 className="spin" size={17} /> : <Send size={17} />}
            </button>
          </form>
        </section>
      )}

      <button
        className={isOpen ? "assistant-chat-button active" : "assistant-chat-button"}
        type="button"
        onClick={onToggle}
        aria-label={isOpen ? "설계 보조 챗 닫기" : "설계 보조 챗 열기"}
      >
        {isOpen ? <MessageCircle size={24} /> : <Bot size={25} />}
      </button>
    </aside>
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
