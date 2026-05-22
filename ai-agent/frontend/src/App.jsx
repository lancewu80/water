import { useState, useEffect, useCallback } from "react";
import SearchBox from "./components/SearchBox";
import WeatherCard from "./components/WeatherCard";
import NewsCard from "./components/NewsCard";
import WebResultCard from "./components/WebResultCard";

// ── 前端意圖偵測（快速模式用，即時更新 badge）────────────────
const WEATHER_KW = [
  "天氣","氣溫","溫度","下雨","晴天","颱風","濕度","風速",
  "weather","temperature","rain","sunny","humidity","wind","forecast",
  "天気","気温","湿度","風速","雨","晴れ",
];
const NEWS_KW = [
  "新聞","頭條","熱門","最新","消息","報導","即時",
  "news","headline","latest","breaking",
  "ニュース","速報",
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
  get_weather:  { label: "即時天氣", icon: "🌤️" },
  search_news:  { label: "新聞搜尋", icon: "📰" },
  search_web:   { label: "網路搜尋", icon: "🔍" },
};

const NEWS_TAGS = {
  zh: ["台灣", "科技", "財經", "政治", "娛樂", "體育", "國際", "健康"],
  en: ["Technology", "Politics", "Finance", "Sports", "Entertainment", "Health", "Science", "World"],
  ja: ["テクノロジー", "政治", "経済", "スポーツ", "エンタメ", "健康", "科学", "国際"],
};

export default function App() {
  const [query,       setQuery]       = useState("");
  const [intent,      setIntent]      = useState(null);
  const [lang,        setLang]        = useState("zh");
  const [results,     setResults]     = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [aiMode,      setAiMode]      = useState(false);   // ⚡ / 🧠
  const [llmDecision, setLlmDecision] = useState(null);   // LLM 選了哪個工具

  useEffect(() => {
    setIntent(detectIntent(query));
  }, [query]);

  const search = useCallback(async (searchQuery = query, searchLang = lang) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setLlmDecision(null);

    const endpoint = aiMode ? "/api/agent" : "/api/search";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, lang: searchLang }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // 儲存 LLM 決策資訊（AI 模式才有）
      if (data.llm_decision) setLlmDecision(data.llm_decision);

      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [query, lang, aiMode]);

  const handleTag = (tag) => {
    const q = `${tag} 新聞`;
    setQuery(q);
    search(q, lang);
  };

  const handleLangChange = (newLang) => {
    setLang(newLang);
    if (results?.type === "news") search(query, newLang);
  };

  const handleModeToggle = () => {
    setAiMode((prev) => !prev);
    setResults(null);
    setError(null);
    setLlmDecision(null);
  };

  // AI 模式下不顯示前端推斷的 intent badge（由 LLM 決定）
  const currentIntent = intent || (results?.type ?? null);
  const meta = (!aiMode && currentIntent) ? INTENT_META[currentIntent] : null;

  return (
    <div className={`app ${aiMode ? "ai-mode" : ""}`}>
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <span className="logo">{aiMode ? "🧠" : "🤖"}</span>
          <h1 className="title">AI 智慧搜尋</h1>
          <p className="subtitle">
            {aiMode
              ? "AI 模式：Ollama LLM 推理決策，自動選工具與提取參數"
              : "快速模式：關鍵字規則引擎，自動判斷天氣 / 新聞 / 網路搜尋"}
          </p>
        </div>
      </header>

      {/* ── 搜尋區 ── */}
      <main className="main">
        <div className="search-section">

          {/* 模式切換 Toggle */}
          <div className="mode-toggle-row">
            <button
              className={`mode-toggle ${aiMode ? "mode-ai" : "mode-fast"}`}
              onClick={handleModeToggle}
              title={aiMode ? "切換到快速模式（關鍵字引擎）" : "切換到 AI 模式（Ollama LLM）"}
            >
              <span className="mode-icon">{aiMode ? "🧠" : "⚡"}</span>
              <span className="mode-label">{aiMode ? "AI 模式" : "快速模式"}</span>
              <span className="mode-sub">{aiMode ? "gemma4:e4b" : "規則引擎"}</span>
            </button>
            {aiMode && (
              <span className="mode-hint">LLM 自動選擇工具與參數</span>
            )}
          </div>

          <SearchBox
            value={query}
            onChange={setQuery}
            onSearch={() => search()}
            loading={loading}
            placeholder={
              aiMode
                ? "問任何問題，LLM 自動決定用哪個工具..."
                : "台北天氣？最新科技新聞？Claude AI 是什麼？"
            }
          />

          {/* 快速模式：前端意圖 Badge */}
          {meta && (
            <div className="intent-badge" style={{ "--badge-color": meta.color }}>
              <span>{meta.icon}</span>
              <span>{meta.label}</span>
            </div>
          )}

          {/* 語言切換（新聞模式）*/}
          {(intent === "news" || results?.type === "news") && (
            <div className="lang-switch">
              {["zh", "en", "ja"].map((l) => (
                <button
                  key={l}
                  className={`lang-btn ${lang === l ? "active" : ""}`}
                  onClick={() => handleLangChange(l)}
                >
                  {{ zh: "🇹🇼 中文", en: "🇺🇸 English", ja: "🇯🇵 日本語" }[l]}
                </button>
              ))}
            </div>
          )}

          {/* 新聞快捷標籤 */}
          {(intent === "news" || results?.type === "news") && (
            <div className="news-tags">
              {NEWS_TAGS[lang].map((tag) => (
                <button key={tag} className="tag-btn" onClick={() => handleTag(tag)}>
                  {tag}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── 錯誤訊息 ── */}
        {error && (
          <div className="error-box">
            <span>⚠️</span> {error}
          </div>
        )}

        {/* ── Loading ── */}
        {loading && (
          <div className="loading">
            <div className={`spinner ${aiMode ? "spinner-ai" : ""}`} />
            <span>{aiMode ? "🧠 LLM 推理中…" : "搜尋中…"}</span>
          </div>
        )}

        {/* ── LLM 決策資訊（AI 模式） ── */}
        {llmDecision && !loading && (
          <div className="llm-decision">
            <span className="llm-decision-icon">🧠</span>
            <span>LLM 決策：呼叫</span>
            <code className="llm-tool">{TOOL_META[llmDecision.tool]?.icon} {llmDecision.tool}</code>
            <span>參數：</span>
            <code className="llm-args">{JSON.stringify(llmDecision.args)}</code>
          </div>
        )}

        {/* ── 結果區 ── */}
        {results && !loading && (
          <div className="results-section">
            {results.type === "weather" && <WeatherCard data={results} />}

            {results.type === "news" && (
              <>
                <div className="results-header">📰 「{results.query}」的新聞結果</div>
                <div className="news-grid">
                  {results.results.map((item, i) => <NewsCard key={i} item={item} />)}
                </div>
              </>
            )}

            {results.type === "web" && (
              <>
                <div className="results-header">🔍 「{results.query}」的搜尋結果</div>
                <div className="web-list">
                  {results.results.map((item, i) => <WebResultCard key={i} item={item} />)}
                </div>
              </>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        天氣：Open-Meteo・搜尋：DuckDuckGo・AI：Ollama {aiMode ? `(${OLLAMA_MODEL_NAME})` : "（快速模式）"}
      </footer>
    </div>
  );
}

const OLLAMA_MODEL_NAME = "gemma4:e4b";
