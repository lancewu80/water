import { useState, useEffect, useCallback, useRef } from "react";
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

function genSessionId() {
  return crypto.randomUUID?.() ??
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

// ── 結果渲染（抽出共用）──────────────────────────────────────
function ResultView({ data, showHeader = true }) {
  if (!data) return null;
  return (
    <>
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
  const [aiMode,        setAiMode]        = useState(false);

  // ── 結果 & 對話記憶 ──────────────────────────────────────────
  const [currentResult, setCurrentResult] = useState(null);   // 最新一筆
  const [conversations, setConversations] = useState([]);     // 所有歷史
  const [sessionId,     setSessionId]     = useState(() => genSessionId());
  const [activeTab,     setActiveTab]     = useState("result"); // "result" | "history"

  useEffect(() => { setIntent(detectIntent(query)); }, [query]);

  const search = useCallback(async (searchQuery = query, searchLang = lang) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    setActiveTab("result");   // 搜尋時自動切到結果頁簽

    const endpoint = aiMode ? "/api/agent" : "/api/search";
    const body = { query: searchQuery, lang: searchLang };
    if (aiMode) body.session_id = sessionId;

    try {
      const res  = await fetch(endpoint, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });

      // 防護：回應可能為空（後端 crash 或網路中斷）
      const text = await res.text();
      if (!text.trim()) {
        throw new Error(`伺服器回應為空（HTTP ${res.status}），請重試或重啟後端`);
      }
      let data;
      try { data = JSON.parse(text); }
      catch { throw new Error(`回應格式錯誤（非 JSON）：${text.slice(0, 100)}`); }
      if (data.error) throw new Error(data.error);

      setCurrentResult(data);

      // 只有 AI 模式才累積歷史
      if (aiMode) {
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
  }, [query, lang, aiMode, sessionId]);

  const clearConversation = useCallback(async () => {
    if (aiMode) {
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
  }, [aiMode, sessionId]);

  const handleTag = (tag) => { const q = `${tag} 新聞`; setQuery(q); search(q, lang); };
  const handleLangChange = (nl) => { setLang(nl); if (currentResult?.type === "news") search(query, nl); };
  const handleModeToggle = () => {
    setAiMode(prev => !prev);
    setCurrentResult(null);
    setConversations([]);
    setError(null);
    setSessionId(genSessionId());
    setActiveTab("result");
  };

  const curIntent     = intent || currentResult?.type || null;
  const meta          = (!aiMode && curIntent) ? INTENT_META[curIntent] : null;
  const historyCount  = conversations.length;

  return (
    <div className={`app ${aiMode ? "ai-mode" : ""}`}>
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <span className="logo">{aiMode ? "🧠" : "🤖"}</span>
          <h1 className="title">AI 智慧搜尋</h1>
          <p className="subtitle">
            {aiMode
              ? "AI 模式：Ollama LLM 推理 · 多輪對話記憶"
              : "快速模式：關鍵字規則引擎，自動判斷天氣 / 新聞 / 網路搜尋"}
          </p>
        </div>
      </header>

      <main className="main">
        {/* ── 搜尋區 ── */}
        <div className="search-section">

          {/* 模式切換 */}
          <div className="mode-toggle-row">
            <button
              className={`mode-toggle ${aiMode ? "mode-ai" : "mode-fast"}`}
              onClick={handleModeToggle}
            >
              <span className="mode-icon">{aiMode ? "🧠" : "⚡"}</span>
              <span className="mode-label">{aiMode ? "AI 模式" : "快速模式"}</span>
              <span className="mode-sub">{aiMode ? "gemma4:e4b" : "規則引擎"}</span>
            </button>

            {aiMode && (
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
          </div>

          <SearchBox
            value={query}
            onChange={setQuery}
            onSearch={() => search()}
            loading={loading}
            placeholder={
              aiMode
                ? historyCount > 0 ? "繼續追問，例如：明天呢？那東京呢？"
                                   : "問任何問題，LLM 自動決定用哪個工具..."
                : "台北天氣？最新科技新聞？Claude AI 是什麼？"
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

          {(curIntent === "news" || currentResult?.type === "news") && !aiMode && (
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
            <div className={`spinner ${aiMode ? "spinner-ai" : ""}`} />
            <span>{aiMode ? "🧠 LLM 推理中…" : "搜尋中…"}</span>
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
              {aiMode && (
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
                {/* AI 模式：顯示 LLM 決策 */}
                {aiMode && currentResult?.llm_decision && (
                  <div className="llm-decision">
                    <span className="llm-decision-icon">🧠</span>
                    <span>LLM 決策：呼叫</span>
                    <code className="llm-tool">
                      {TOOL_META[currentResult.llm_decision.tool]?.icon} {currentResult.llm_decision.tool}
                    </code>
                    <span>參數：</span>
                    <code className="llm-args">{JSON.stringify(currentResult.llm_decision.args)}</code>
                    {currentResult.history_count > 0 && (
                      <span className="history-badge">💬 第 {currentResult.history_count} 輪</span>
                    )}
                  </div>
                )}
                <ResultView data={currentResult} showHeader={!aiMode} />
              </div>
            )}

            {/* ── 頁簽內容：對話記錄 ── */}
            {activeTab === "history" && aiMode && (
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
                      {conv.data?.llm_decision && (
                        <span className="history-tool-tag">
                          {TOOL_META[conv.data.llm_decision.tool]?.icon} {conv.data.llm_decision.tool}
                        </span>
                      )}
                    </div>

                    {/* 使用者問句 */}
                    <div className="history-query">
                      <span className="history-q-icon">👤</span>
                      <span className="history-q-text">{conv.query}</span>
                    </div>

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
        天氣：Open-Meteo・搜尋：DuckDuckGo・AI：Ollama{" "}
        {aiMode ? `(${OLLAMA_MODEL_NAME}) · Session: ${sessionId.slice(0,8)}…` : "（快速模式）"}
      </footer>
    </div>
  );
}

// ── 對話記錄摘要（簡短顯示結果概要）─────────────────────────
function HistorySummary({ data }) {
  if (!data) return null;
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
