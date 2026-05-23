# 🤖 AI 智慧搜尋系統

一套結合自然語言意圖辨識、多輪對話記憶與 **Multi-Agent 協作**的 Agent 應用。
單一搜尋框搭配四種模式，從毫秒級規則引擎到 Gemini AI 深度分析，按需選用。

---

## ✨ 功能總覽

### 搜尋工具（三種，全模式共用）

| 工具 | 觸發範例 | 資料來源 |
|------|---------|---------|
| 🌤️ 即時天氣 | `台北天氣`、`東京氣溫`、`London weather` | Open-Meteo（免費，無需 Key） |
| 📰 新聞搜尋 | `最新新聞`、`科技頭條`、`AI news` | DuckDuckGo News |
| 🔍 網路搜尋 | 其他任何查詢（預設） | DuckDuckGo Text |

### 四種 Agent 模式

| 模式 | 圖示 | 說明 | 適用場景 |
|------|------|------|---------|
| **快速模式** | ⚡ | 關鍵字規則引擎，毫秒回應 | 天氣 / 新聞 / 快速查詢 |
| **Ollama 模式** | 🧠 | 本地 LLM 推理，隱私優先，多輪對話 | 一般問答 / 寫程式 / 翻譯 |
| **Gemini 模式** | 🔷 | Google Gemini 2.5 Flash，生成結構化分析報告 | 比較 / 深度分析 / 複雜推理 |
| **Multi-AI 模式** | 🔀 | Orchestrator 自動選擇最佳 AI | 混合查詢 / 任意問題 |

> **Multi-AI 路由邏輯**：含「分析/比較/為什麼/解釋/影響…」→ Gemini；其餘（寫程式/問答/天氣）→ Ollama

---

## 環境需求

| 工具 | 版本 | 說明 |
|------|------|------|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端建構工具 |
| npm | 9+ | 套件管理 |
| Ollama | 最新版 | 本地 LLM（Ollama / Multi-AI 模式需要） |
| Gemini API Key | — | Google AI Studio 免費申請（Gemini / Multi-AI 模式需要） |

---

## 快速開始

### Step 1：後端設定

```bash
cd ai-agent/backend

# 安裝 Python 套件
pip install -r requirements.txt
```

`requirements.txt` 內容：
```
flask
flask-cors
requests
duckduckgo-search
google-genai
python-dotenv
```

建立 `.env` 檔（Gemini 模式需要）：
```bash
# ai-agent/backend/.env
GEMINI_API_KEY=你的Gemini_API_Key
```

> 取得 Gemini API Key：前往 https://aistudio.google.com/ → Get API Key → 免費 Free Tier 即可

### Step 2：安裝並啟動 Ollama（Ollama / Multi-AI 模式）

```bash
# 下載安裝 Ollama：https://ollama.com/
# 拉取模型（約 9GB）
ollama pull gemma4:e4b

# 確認 Ollama 服務已在 http://localhost:11434 執行
```

### Step 3：前端設定

```bash
cd ai-agent/frontend

# 安裝 Node 套件（包含 react-markdown、remark-gfm）
npm install
```

---

## 啟動程式

> 需要**同時開兩個終端機視窗**分別執行後端與前端。

### 終端機 1 — 後端（Flask）

```bash
cd ai-agent/backend
python app.py
```

啟動後看到：
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### 終端機 2 — 前端（React + Vite）

```bash
cd ai-agent/frontend
npm run dev
```

啟動後看到：
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:3000/
```

打開 **http://localhost:3000** 即可使用。

---

## 使用方式

### ⚡ 快速模式
輸入任何查詢，毫秒內完成意圖辨識並回傳結果。適合日常天氣、新聞、簡單搜尋。

### 🧠 Ollama 模式
LLM 自動決策使用哪個工具，並支援**多輪對話記憶**：
```
第1輪：台北天氣        → 查詢台北天氣
第2輪：明天呢？        → 仍查台北（記得上下文）
第3輪：那東京呢？      → 查詢東京天氣
```
也可以問不需要工具的問題，Ollama 直接回答（direct answer）：
```
寫一個 Java binary search
用繁體中文解釋 Python 的 GIL
```

### 🔷 Gemini 模式
自動啟用深度合成（synthesis），適合比較分析：
```
Acer Predator Helios Neo 16 vs Acer Nitro AN515 3A 遊戲效能比較
iPhone 16 和 Samsung S25 哪個更適合拍照？
```
回傳結果包含 **AI 深度分析報告**（含規格比較表格、效能分析、推薦結論）。

### 🔀 Multi-AI 模式
Orchestrator 依複雜度自動路由：
```
台北天氣              → Ollama 查詢（簡單）
寫個 Go REST API      → Ollama 直接回答（簡單程式）
分析特斯拉股價趨勢    → Gemini 分析（複雜）
為什麼量子計算很重要  → Gemini 回答（複雜推理）
```

---

## 專案結構

```
ai-agent/
├── backend/
│   ├── app.py              ← Flask API 主程式
│   │                         ・/api/search         快速搜尋（規則引擎）
│   │                         ・/api/agent          Ollama LLM Agent
│   │                         ・/api/agent/gemini   Gemini Agent
│   │                         ・/api/agent/multi    Multi-Agent Orchestrator
│   │                         ・/api/agent/status   Agent 狀態查詢
│   │                         ・/api/session/clear  清除對話記憶
│   ├── requirements.txt    ← Python 依賴
│   └── .env                ← GEMINI_API_KEY（不納入版控）
├── frontend/
│   ├── package.json
│   ├── vite.config.js      ← /api Proxy 設定
│   ├── index.html
│   └── src/
│       ├── App.jsx          ← 主邏輯：4 模式選擇、路由、Markdown 渲染
│       ├── App.css
│       └── components/
│           ├── SearchBox.jsx
│           ├── WeatherCard.jsx
│           ├── NewsCard.jsx
│           └── WebResultCard.jsx
├── ai-agent-simple.py      ← 原始 Ollama Agent 範例
├── ai-agent-weather.py     ← 天氣 Agent 範例
├── 系統設計文件.docx        ← 完整架構設計文件
└── README.md               ← 本檔案
```

---

## API 端點

| 方法 | 路徑 | 模式 | 說明 | 主要 Body 參數 |
|------|------|------|------|--------------|
| POST | `/api/search` | ⚡ 快速 | 關鍵字規則引擎 | `query`, `lang` |
| POST | `/api/agent` | 🧠 Ollama | Ollama LLM Agent | `query`, `session_id` |
| POST | `/api/agent/gemini` | 🔷 Gemini | Gemini Agent | `query`, `session_id`, `synthesis` |
| POST | `/api/agent/multi` | 🔀 Multi-AI | Orchestrator | `query`, `session_id`, `synthesis`, `direct` |
| GET  | `/api/agent/status` | — | Agent 狀態 / 可用性 | — |
| POST | `/api/session/clear` | — | 清除對話記憶 | `session_id` |
| GET  | `/api/weather` | — | 直接查天氣 | `?city=台北` |
| GET  | `/api/news` | — | 直接搜尋新聞 | `?q=關鍵字&lang=zh` |
| GET  | `/api/web` | — | 直接網路搜尋 | `?q=關鍵字` |

### 回應欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| `type` | 結果型別 | `weather` / `news` / `web` / `direct_answer` |
| `agent_used` | 實際使用的 AI | `gemini` / `ollama` / `rule` |
| `llm_decision` | LLM 工具決策 | `{"tool": "search_web", "args": {...}}` |
| `synthesis` | Gemini 深度分析報告（Markdown） | `## 📊 規格比較\n...` |
| `history_count` | 當前對話輪數 | `3` |
| `session_id` | 會話識別碼 | `uuid4` |

---

## 前端 Markdown 渲染

AI 回答支援完整 GFM（GitHub Flavored Markdown）渲染：

| 語法 | 渲染結果 |
|------|---------|
| `## 標題` | 章節標題（綠色 / 藍色依卡片類型） |
| `\| 表格 \|` | 有斑馬紋、滑鼠 hover 的互動表格 |
| `1. 項目` | 有序列表（顯示數字） |
| `- 項目` | 無序 bullet 列表 |
| `---` | 水平分隔線 |
| `` `code` `` | 等寬字體高亮 |
| ` ```block``` ` | 深色背景程式碼框 |

---

## 常見問題

### Q: Gemini API Key 在哪申請？
前往 https://aistudio.google.com/ → 登入 Google 帳號 → Get API Key → 建立 Free Tier Key。
每天免費額度：Gemini 2.5 Flash 約 500 次請求。

### Q: Ollama 啟動後 AI 模式仍出現錯誤？
確認 `ollama serve` 已在背景執行，且模型已下載：
```bash
ollama list          # 列出已下載模型
ollama pull gemma4:e4b   # 重新拉取（如果未顯示）
```

### Q: Multi-AI 模式每次都走 Gemini，Ollama 沒被使用？
查詢包含「比較/分析/為什麼/解釋」等複雜關鍵字時會路由到 Gemini。
純程式碼問題、翻譯、一般問答會路由到 Ollama。

### Q: `ModuleNotFoundError: No module named 'google.genai'`
```bash
pip install google-genai python-dotenv
```

### Q: 前端出現 `Network Error` 或 API 無回應
- 確認後端已在 port 5000 正常執行
- `vite.config.js` 的 proxy 設定將 `/api` 轉發至 `http://localhost:5000`

### Q: DuckDuckGo 搜尋結果為空
DuckDuckGo 有頻率限制，稍候再試，或確認網路連線正常。

### Q: AI 回答被截斷
確認後端 `app.py` 中 Ollama `num_predict` 設為 `8192`，Gemini `max_output_tokens` 設為 `8192`。

---

## 生產環境部署

```bash
# 前端打包
cd frontend
npm run build      # 輸出靜態檔案至 dist/

# 後端使用 Gunicorn
pip install gunicorn
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Nginx 反向代理設定（參考）：
```nginx
server {
    listen 80;
    root /path/to/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 相關文件

- 📄 [系統設計文件.docx](./系統設計文件.docx) — 完整架構設計、API 規格、Multi-Agent 設計說明
- 🤖 [Ollama](https://ollama.com/) — 本地 LLM 執行環境
- 🔷 [Google AI Studio](https://aistudio.google.com/) — Gemini API Key 申請
- 🌐 [Open-Meteo 文件](https://open-meteo.com/en/docs) — 天氣 API
- 🔍 [duckduckgo-search PyPI](https://pypi.org/project/duckduckgo-search/) — 搜尋套件
