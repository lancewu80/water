import { useState, useEffect, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SearchBox from "./components/SearchBox";
import WeatherCard from "./components/WeatherCard";
import NewsCard from "./components/NewsCard";
import WebResultCard from "./components/WebResultCard";

// ── 前端意圖偵測（快速模式用）────────────────────────────────
const WEATHER_KW = [
  "天氣","氣溫","溫度","下雨","晴天","颱風","濕度","風速",
  "weather","temperature","rain","sunny","humidity","wind","forecast",
  "天気","気温","湿度","風速","雨","晴れ",
];
const NEWS_KW = [
  "新聞","頭條","熱門","最新","消息","報導","即時",
  "news","headline","latest","breaking","ニュース","速報",
];

function detectIntent(query) {
  if (!query.trim()) return null;
  const q = query.toLowerCase();
  if (WEATHER_KW.some((kw) => q.includes(kw))) return "weather";
  if (NEWS_KW.some((kw) => q.includes(kw)))    return "news";
  return "web";
}

const INTENT_META = {
  weather: { label: "即時天氣", icon: "🌤️", color: "#3b82f6" },
  news:    { label: "新聞搜尋", icon: "📰", color: "#8b5cf6" },
  web:     { label: "網路搜尋", icon: "🔍", color: "#10b981" },
};
const TOOL_META = {
  get_weather: { label: "即時天氣", icon: "🌤️" },
  search_news: { label: "新聞搜尋", icon: "📰" },
  search_web:  { label: "網路搜尋", icon: "🔍" },
};
const NEWS_TAGS = {
  zh: ["台灣","科技","財經","政治","娛樂","體育","國際","健康"],
  en: ["Technology","Politics","Finance","Sports","Entertainment","Health","Science","World"],
  ja: ["テクノロジー","政治","経済","スポーツ","エンタメ","健康","科学","国際"],
};

// ── Agent 模式設定 ────────────────────────────────────────────
const AGENT_MODES = [
  {
    key:      "fast",
    label:    "快速",
    icon:     "⚡",
    sub:      "規則引擎",
    color:    "#10b981",
    endpoint: "/api/search",
    hint:     "快速模式：關鍵字規則引擎，自動判斷天氣 / 新聞 / 網路搜尋",
    synthesis: false,
  },
  {
    key:      "ollama",
    label:    "Ollama",
    icon:     "🧠",
    sub:      "本地 LLM",
    color:    "#8b5cf6",
    endpoint: "/api/agent",
    hint:     "Ollama 模式：本地 LLM 推理 · 多輪對話記憶 · 隱私優先",
    synthesis: false,
  },
  {
    key:      "gemini",
    label:    "Gemini",
    icon:     "🔷",
    sub:      "Google AI",
    color:    "#3b82f6",
    endpoint: "/api/agent/gemini",
    hint:     "Gemini 模式：Google AI 深度分析 · 生成結構化報告",
    synthesis: true,
  },
  {
    key:      "multi",
    label:    "Multi-AI",
    icon:     "🔀",
    sub:      "智慧協作",
    color:    "#f59e0b",
    endpoint: "/api/agent/multi",
    hint:     "Multi-AI 模式：自動選擇最佳 AI · 複雜問題用 Gemini · 簡單問題用 Ollama",
    synthesis: true,
  },
];

// ── agent_used 顯示設定 ──────────────────────────────────────
const AGENT_USED_META = {
  Gemini:    { icon: "🔷", color: "#3b82f6", label: "Gemini" },
  Ollama:    { icon: "🧠", color: "#8b5cf6", label: "Ollama" },
  Rule:      { icon: "⚡", color: "#10b981", label: "規則引擎" },
  gemini:    { icon: "🔷", color: "#3b82f6", label: "Gemini" },
  ollama:    { icon: "🧠", color: "#8b5cf6", label: "Ollama" },
};

function genSessionId() {
  return crypto.randomUUID?.() ??
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

// ── 共用 Markdown 元件對應（react-markdown + remark-gfm）────
const MD_TABLE = {
  table: ({ children }) => (
    <div className="md-table-wrapper">
      <table className="md-table">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="md-thead">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr:    ({ children }) => <tr className="md-tr">{children}</tr>,
  th:    ({ children }) => <th className="md-th">{children}</th>,
  td:    ({ children }) => <td className="md-td">{children}</td>,
};

const MD_COMPONENTS_DIRECT = {
  h1:     ({ children }) => <div className="analysis-main-title">{children}</div>,
  h2:     ({ children }) => <div className="analysis-section-title">{children}</div>,
  h3:     ({ children }) => <div className="direct-h3">{children}</div>,
  h4:     ({ children }) => <div className="direct-h3">{children}</div>,
  p:      ({ children }) => <div className="analysis-para">{children}</div>,
  ul:     ({ children }) => <div className="md-list">{children}</div>,
  ol:     ({ children }) => <div className="md-list md-list-ol">{children}</div>,
  li:     ({ children }) => (
    <div className="analysis-bullet">
      <span className="analysis-bullet-dot">•</span>
      <span>{children}</span>
    </div>
  ),
  hr:     () => <hr className="md-hr" />,
  strong: ({ children }) => <strong>{children}</strong>,
  em:     ({ children }) => <em>{children}</em>,
  code:   ({ children }) => <code className="md-inline-code">{children}</code>,
  pre:    ({ children }) => <pre className="md-pre">{children}</pre>,
  blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
  ...MD_TABLE,
};

// AnalysisCard 使用藍色系版本（h2 顏色不同，其餘共用）
const MD_COMPONENTS_ANALYSIS = {
  ...MD_COMPONENTS_DIRECT,
  h2: ({ children }) => <div className="analysis-section-title analysis-h2">{children}</div>,
};

const GFM_PLUGINS = [remarkGfm];

// ── 直接回答卡片（使用 react-markdown + remark-gfm 渲染）─────
function DirectAnswerCard({ answer, agentUsed }) {
  if (!answer || !answer.trim()) return null;
  const agentMeta = AGENT_USED_META[agentUsed] ?? { icon: "🤖", color: "#6b7280", label: agentUsed ?? "AI" };

  return (
    <div className="direct-answer-card">
      <div className="direct-answer-header" style={{ "--agent-color": agentMeta.color }}>
        <span className="direct-answer-icon">💬</span>
        <span className="direct-answer-title">AI 直接回答</span>
        <span className="direct-answer-badge">
          {agentMeta.icon} {agentMeta.label}
        </span>
      </div>
      <div className="direct-answer-body">
        <ReactMarkdown remarkPlugins={GFM_PLUGINS} components={MD_COMPONENTS_DIRECT}>
          {answer}
        </ReactMarkdown>
      </div>
    </div>
  );
}

// ── 分析報告卡片（使用 react-markdown + remark-gfm 渲染）─────
function AnalysisCard({ synthesis }) {
  if (!synthesis || !synthesis.trim()) return null;
  return (
    <div className="analysis-card">
      <div className="analysis-card-header">
        <span className="analysis-card-icon">🤖</span>
        <span className="analysis-card-title">AI 深度分析報告</span>
      </div>
      <div className="analysis-card-body">
        <ReactMarkdown remarkPlugins={GFM_PLUGINS} components={MD_COMPONENTS_ANALYSIS}>
          {synthesis}
        </ReactMarkdown>
      </div>
    </div>
  );
}

// ── 結果渲染（抽出共用）──────────────────────────────────────
function ResultView({ data, showHeader = true, isAiMode = false }) {
  if (!data) return null;
  return (
    <>
      {/* 直接回答（direct_answer 型別）*/}
      {data.type === "direct_answer" && (
        <DirectAnswerCard answer={data.answer} agentUsed={data.agent_used} />
      )}

      {/* AI 分析報告（Gemini / Multi 搜尋模式合成）*/}
      {isAiMode && data.synthesis && (
        <AnalysisCard synthesis={data.synthesis} />
      )}

      {data.type === "weather" && <WeatherCard data={data} />}
      {data.type === "news" && (
        <>
          {showHeader && <div className="results-header">📰 「{data.query}」的新聞結果</div>}
          <div className="news-grid">
            {data.results.map((item, i) => <NewsCard key={i} item={item} />)}
          </div>
        </>
      )}
      {data.type === "web" && (
        <>
          {showHeader && <div className="results-header">🔍 「{data.query}」的搜尋結果</div>}
          <div className="web-list">
            {data.results.map((item, i) => <WebResultCard key={i} item={item} />)}
          </div>
        </>
      )}
    </>
  );
}

export default function App() {
  const [query,         setQuery]         = useState("");
  const [intent,        setIntent]        = useState(null);
  const [lang,          setLang]          = useState("zh");
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState(null);
  const [agentMode,     setAgentMode]     = useState("fast");  // "fast"|"ollama"|"gemini"|"multi"
  const [directMode,    setDirectMode]    = useState(false);   // false=搜尋 true=直接回答

  // ── 結果 & 對話記憶 ──────────────────────────────────────────
  const [currentResult, setCurrentResult] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [sessionId,     setSessionId]     = useState(() => genSessionId());
  const [activeTab,     setActiveTab]     = useState("result");

  const modeConfig  = AGENT_MODES.find(m => m.key === agentMode) ?? AGENT_MODES[0];
  const isAiMode    = agentMode !== "fast";

  useEffect(() => { setIntent(detectIntent(query)); }, [query]);

  const search = useCallback(async (searchQuery = query, searchLang = lang) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    setActiveTab("result");

    const body = { query: searchQuery, lang: searchLang };
    if (isAiMode) {
      body.session_id = sessionId;
      if (directMode) {
        body.direct = true;
      } else if (modeConfig.synthesis) {
        body.synthesis = true;
      }
    }

    try {
      const res = await fetch(modeConfig.endpoint, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });

      const text = await res.text();
      if (!text.trim()) {
        throw new Error(`伺服器回應為空（HTTP ${res.status}），請重試或重啟後端`);
      }
      let data;
      try { data = JSON.parse(text); }
      catch { throw new Error(`回應格式錯誤（非 JSON）：${text.slice(0, 100)}`); }
      if (data.error) throw new Error(data.error);

      setCurrentResult(data);

      if (isAiMode) {
        setConversations(prev => [...prev, {
          id:    Date.now(),
          query: searchQuery,
          data,
          ts:    new Date().toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" }),
        }]);
        setQuery("");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [query, lang, agentMode, sessionId, modeConfig, isAiMode, directMode]);

  const clearConversation = useCallback(async () => {
    if (isAiMode) {
      await fetch("/api/session/clear", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
    setConversations([]);
    setCurrentResult(null);
    setError(null);
    setSessionId(genSessionId());
    setActiveTab("result");
  }, [isAiMode, sessionId]);

  const handleModeChange = (newMode) => {
    if (newMode === agentMode) return;
    setAgentMode(newMode);
    setCurrentResult(null);
    setConversations([]);
    setError(null);
    setSessionId(genSessionId());
    setActiveTab("result");
    // fast 模式不支援直接回答
    if (newMode === "fast") setDirectMode(false);
  };

  const handleTag = (tag) => { const q = `${tag} 新聞`; setQuery(q); search(q, lang); };
  const handleLangChange = (nl) => { setLang(nl); if (currentResult?.type === "news") search(query, nl); };

  const curIntent    = intent || currentResult?.type || null;
  const meta         = (!isAiMode && curIntent) ? INTENT_META[curIntent] : null;
  const historyCount = conversations.length;

  // agent_used 顯示
  const agentUsed    = currentResult?.agent_used;
  const agentUsedMeta = agentUsed ? (AGENT_USED_META[agentUsed] ?? { icon: "🤖", color: "#6b7280", label: agentUsed }) : null;

  return (
    <div className={`app ${isAiMode ? "ai-mode" : ""} mode-${agentMode}`}>
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <span className="logo">{modeConfig.icon}</span>
          <h1 className="title">AI 智慧搜尋</h1>
          <p className="subtitle">{modeConfig.hint}</p>
        </div>
      </header>

      <main className="main">
        {/* ── 搜尋區 ── */}
        <div className="search-section">

          {/* ── 4 模式選擇器 ── */}
          <div className="mode-selector-row">
            {AGENT_MODES.map(m => (
              <button
                key={m.key}
                className={`mode-btn ${agentMode === m.key ? "mode-btn-active" : ""}`}
                style={{ "--mode-color": m.color }}
                onClick={() => handleModeChange(m.key)}
                title={m.hint}
              >
                <span className="mode-btn-icon">{m.icon}</span>
                <span className="mode-btn-label">{m.label}</span>
                <span className="mode-btn-sub">{m.sub}</span>
              </button>
            ))}
          </div>

          {/* Session bar（AI 模式才顯示）*/}
          {isAiMode && (
            <div className="session-bar">
              {historyCount > 0
                ? <>
                    <span className="session-count">💬 {historyCount} 輪對話</span>
                    <button className="clear-btn" onClick={clearConversation}>🗑️ 清除對話</button>
                  </>
                : <span className="mode-hint">LLM 自動選擇工具 · 記得上下文</span>
              }
            </div>
          )}

          {/* ── 回答方式切換（AI 模式才顯示）── */}
          {isAiMode && (
            <div className="source-toggle-row">
              <span className="source-toggle-label">回答方式</span>
              <div className="source-toggle-group">
                <button
                  className={`source-btn ${!directMode ? "source-btn-active" : ""}`}
                  onClick={() => setDirectMode(false)}
                  title="透過 DuckDuckGo 搜尋後由 AI 分析"
                >
                  🔍 搜尋
                </button>
                <button
                  className={`source-btn ${directMode ? "source-btn-active" : ""}`}
                  onClick={() => setDirectMode(true)}
                  title="直接向 AI 提問，不搜尋網路"
                >
                  💬 直接回答
                </button>
              </div>
              {directMode && (
                <span className="source-hint">
                  AI 憑自身知識回答，不查網路・適合知識問答、程式、翻譯
                </span>
              )}
            </div>
          )}

          <SearchBox
            value={query}
            onChange={setQuery}
            onSearch={() => search()}
            loading={loading}
            placeholder={
              agentMode === "fast"
                ? "台北天氣？最新科技新聞？Claude AI 是什麼？"
                : directMode
                  ? "直接問 AI：解釋量子糾纏、寫個 Python 函式、翻譯這句話…"
                  : agentMode === "gemini"
                    ? "問複雜問題，例如：iPhone 16 vs Samsung S25 哪個好？"
                    : agentMode === "multi"
                      ? "任何問題，AI 自動選擇最佳分析方式…"
                      : historyCount > 0
                        ? "繼續追問，例如：明天呢？那東京呢？"
                        : "問任何問題，LLM 自動決定用哪個工具..."
            }
          />

          {meta && (
            <div className="intent-badge" style={{ "--badge-color": meta.color }}>
              <span>{meta.icon}</span><span>{meta.label}</span>
            </div>
          )}

          {(curIntent === "news" || currentResult?.type === "news") && (
            <div className="lang-switch">
              {["zh","en","ja"].map(l => (
                <button key={l} className={`lang-btn ${lang===l?"active":""}`}
                  onClick={() => handleLangChange(l)}>
                  {{zh:"🇹🇼 中文",en:"🇺🇸 English",ja:"🇯🇵 日本語"}[l]}
                </button>
              ))}
            </div>
          )}

          {(curIntent === "news" || currentResult?.type === "news") && !isAiMode && (
            <div className="news-tags">
              {NEWS_TAGS[lang].map(tag => (
                <button key={tag} className="tag-btn" onClick={() => handleTag(tag)}>{tag}</button>
              ))}
            </div>
          )}
        </div>

        {/* ── 錯誤 ── */}
        {error && <div className="error-box"><span>⚠️</span> {error}</div>}

        {/* ── Loading ── */}
        {loading && (
          <div className="loading">
            <div className={`spinner ${isAiMode ? "spinner-ai" : ""}`} />
            <span>
              {directMode
                ? (agentMode === "gemini" ? "🔷 Gemini 思考中…"
                   : agentMode === "multi"  ? "🔀 Multi-AI 思考中…"
                   : "🧠 Ollama 思考中…")
                : (agentMode === "gemini" ? "🔷 Gemini 搜尋分析中…"
                   : agentMode === "multi" ? "🔀 Multi-AI 推理中…"
                   : isAiMode ? "🧠 LLM 推理中…"
                   : "搜尋中…")}
            </span>
          </div>
        )}

        {/* ── 頁簽（有結果才顯示）── */}
        {(currentResult || historyCount > 0) && !loading && (
          <div className="tabs-wrapper">

            {/* 頁簽標題列 */}
            <div className="tabs-header">
              <button
                className={`tab-btn ${activeTab === "result" ? "tab-active" : ""}`}
                onClick={() => setActiveTab("result")}
              >
                🔎 目前結果
              </button>
              {isAiMode && (
                <button
                  className={`tab-btn ${activeTab === "history" ? "tab-active" : ""}`}
                  onClick={() => setActiveTab("history")}
                >
                  💬 對話記錄
                  {historyCount > 0 && (
                    <span className="tab-badge">{historyCount}</span>
                  )}
                </button>
              )}
            </div>

            {/* ── 頁簽內容：目前結果 ── */}
            {activeTab === "result" && (
              <div className="tab-panel results-section">

                {/* AI 模式：顯示 LLM 決策 + agent_used */}
                {isAiMode && currentResult?.llm_decision && (
                  <div className="llm-decision">
                    {/* 使用哪個 AI */}
                    {agentUsedMeta && (
                      <span
                        className="agent-used-badge"
                        style={{ "--agent-color": agentUsedMeta.color }}
                        title={`由 ${agentUsedMeta.label} 處理`}
                      >
                        {agentUsedMeta.icon} {agentUsedMeta.label}
                      </span>
                    )}
                    <span className="llm-decision-icon">🧠</span>
                    <span>決策：呼叫</span>
                    <code className="llm-tool">
                      {TOOL_META[currentResult.llm_decision.tool]?.icon ?? "🔧"}{" "}
                      {currentResult.llm_decision.tool}
                    </code>
                    <span>參數：</span>
                    <code className="llm-args">{JSON.stringify(currentResult.llm_decision.args)}</code>
                    {currentResult.history_count > 0 && (
                      <span className="history-badge">💬 第 {currentResult.history_count} 輪</span>
                    )}
                  </div>
                )}

                <ResultView data={currentResult} showHeader={!isAiMode} isAiMode={isAiMode} />
              </div>
            )}

            {/* ── 頁簽內容：對話記錄 ── */}
            {activeTab === "history" && isAiMode && (
              <div className="tab-panel chat-history">
                {conversations.length === 0 && (
                  <div className="history-empty">還沒有對話記錄</div>
                )}
                {conversations.map((conv, idx) => (
                  <div key={conv.id} className="history-item">
                    {/* 輪次 + 時間 */}
                    <div className="history-meta">
                      <span className="history-turn">第 {idx + 1} 輪</span>
                      <span className="history-time">{conv.ts}</span>
                      {conv.data?.agent_used && (
                        <span className="history-tool-tag">
                          {AGENT_USED_META[conv.data.agent_used]?.icon ?? "🤖"}{" "}
                          {AGENT_USED_META[conv.data.agent_used]?.label ?? conv.data.agent_used}
                        </span>
                      )}
                      {conv.data?.llm_decision && (
                        <span className="history-tool-tag">
                          {TOOL_META[conv.data.llm_decision.tool]?.icon}{" "}
                          {conv.data.llm_decision.tool}
                        </span>
                      )}
                    </div>

                    {/* 使用者問句 */}
                    <div className="history-query">
                      <span className="history-q-icon">👤</span>
                      <span className="history-q-text">{conv.query}</span>
                    </div>

                    {/* 直接回答（若有）*/}
                    {conv.data?.type === "direct_answer" && conv.data?.answer && (
                      <div className="history-synthesis">
                        <DirectAnswerCard answer={conv.data.answer} agentUsed={conv.data.agent_used} />
                      </div>
                    )}

                    {/* AI 分析報告（若有）*/}
                    {conv.data?.synthesis && (
                      <div className="history-synthesis">
                        <AnalysisCard synthesis={conv.data.synthesis} />
                      </div>
                    )}

                    {/* 結果摘要 */}
                    <div className="history-summary">
                      <HistorySummary data={conv.data} />
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        )}

      </main>

      <footer className="footer">
        天氣：Open-Meteo・搜尋：DuckDuckGo・
        {agentMode === "fast"   && "快速模式（規則引擎）"}
        {agentMode === "ollama" && `Ollama（${OLLAMA_MODEL_NAME}）· Session: ${sessionId.slice(0,8)}…`}
        {agentMode === "gemini" && `Gemini（${GEMINI_MODEL_NAME}）· Session: ${sessionId.slice(0,8)}…`}
        {agentMode === "multi"  && `Multi-AI（Gemini + Ollama）· Session: ${sessionId.slice(0,8)}…`}
      </footer>
    </div>
  );
}

// ── 對話記錄摘要 ─────────────────────────────────────────────
function HistorySummary({ data }) {
  if (!data) return null;
  if (data.synthesis) return null;     // 有分析報告時不顯示摘要
  if (data.type === "direct_answer") return null;  // 直接回答已由 DirectAnswerCard 顯示
  if (data.type === "weather") {
    return (
      <span className="summary-text">
        🌡️ {data.city}：{data.condition} {data.emoji} {data.temperature}°C，濕度 {data.humidity}%
      </span>
    );
  }
  if (data.type === "news") {
    const titles = data.results?.slice(0, 2).map(r => r.title) ?? [];
    return <span className="summary-text">📰 {titles.join("；") || "（無結果）"}</span>;
  }
  if (data.type === "web") {
    const titles = data.results?.slice(0, 2).map(r => r.title) ?? [];
    return <span className="summary-text">🔍 {titles.join("；") || "（無結果）"}</span>;
  }
  return null;
}

const OLLAMA_MODEL_NAME = "gemma4:e4b";
const GEMINI_MODEL_NAME = "gemini-2.5-flash";
