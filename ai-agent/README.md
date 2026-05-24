# 🤖 AI 智慧搜尋 + 知識庫系統

一套結合自然語言意圖辨識、多輪對話記憶、**Multi-Agent 協作**與 **RAG 知識庫**的 Agent 應用。
單一搜尋框搭配四種模式，從毫秒級規則引擎到 Gemini AI 深度分析；搭配知識庫管理頁面，讓 AI 回答時自動引用企業內部文件。

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

### 🗄️ RAG 知識庫

| 功能 | 說明 |
|------|------|
| **上傳文件** | 拖曳 `.pdf` / `.docx`，自動切塊、向量化索引 |
| **HTML 頁面** | 富文字編輯器（TipTap）直接撰寫，即時索引 |
| **語意搜尋** | 輸入自然語言，找最相關的知識片段 |
| **進階搜尋** | 語意搜尋旁的 🤖 AI Tab，直接讓 LLM 參考 KB 回答；可選 Ollama / Gemini / Multi-Agent |
| **原始格式預覽** | PDF → 瀏覽器原生閱讀器；DOCX → HTML 渲染 |
| **下載** | 一鍵下載原始 PDF / DOCX 檔案 |
| **AI 整合** | 勾選「🗄️ 使用知識庫」，AI 回答時自動注入相關內容（RAG） |
| **RAG 閾值過濾** | cosine distance > 0.75 的不相關 chunks 不注入 LLM，避免知識庫誤導 AI |

---

## 環境需求

| 工具 | 版本 | 說明 |
|------|------|------|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端建構工具 |
| npm | 9+ | 套件管理 |
| Ollama | 最新版 | 本地 LLM 及 Embedding（Ollama / Multi-AI / 知識庫模式需要） |
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
ddgs
google-genai
python-dotenv
# RAG 知識庫（可選，不安裝則知識庫功能停用）
chromadb
python-docx
PyMuPDF
mammoth
```

建立 `.env` 檔（Gemini 模式需要）：
```bash
# ai-agent/backend/.env
GEMINI_API_KEY=你的Gemini_API_Key
```

> 取得 Gemini API Key：前往 https://aistudio.google.com/ → Get API Key → 免費 Free Tier 即可

### Step 2：安裝並啟動 Ollama

```bash
# 下載安裝 Ollama：https://ollama.com/

# AI 對話模型（約 9GB）
ollama pull gemma4:e4b

# RAG Embedding 模型（知識庫功能需要，約 274MB）
ollama pull nomic-embed-text

# 確認 Ollama 服務已在 http://localhost:11434 執行
ollama serve
```

### Step 3：前端設定

```bash
cd ai-agent/frontend

# 安裝 Node 套件
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
也可以問不需要工具的問題，Ollama 直接回答：
```
寫一個 Java binary search
用繁體中文解釋 Python 的 GIL
```

### 🔷 Gemini 模式
自動啟用深度合成（synthesis），適合比較分析：
```
Acer Predator Helios Neo 16 vs Acer Nitro AN515 遊戲效能比較
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

### 🗄️ 知識庫使用流程

**1. 建立知識庫內容**

點擊右上角「🗄️ 知識庫」按鈕進入管理頁面：
- **上傳文件**：拖曳 `.pdf` 或 `.docx` 到上傳區，系統自動切塊並向量化
- **新增頁面**：使用 TipTap 富文字編輯器撰寫 HTML 頁面（適合撰寫 SOP、FAQ 等）

**2. 搜尋知識庫**

切換到「🔍 語意搜尋」頁簽，輸入自然語言，找到相關知識片段，點擊「🔍 查看全文」可預覽完整文件。

若語意搜尋結果不滿意，切換到「🤖 進階搜尋」頁簽：

- 相同查詢字串自動帶入（兩個 Tab 共用輸入框）
- 選擇 AI 模型（🦙 Ollama / ✨ Gemini / 🔀 Multi-Agent）
- 按「🤖 詢問 AI」，LLM 會參考知識庫後以自然語言回答
- AI 回答支援 Markdown 格式渲染（標題、粗體、條列、程式碼）

**3. 讓 AI 使用知識庫**

在主搜尋頁面勾選「🗄️ 使用知識庫」，AI 回答時會自動：
1. 將問題向量化
2. 搜尋最相關的知識片段（Top-5）
3. 將片段注入 LLM System Prompt
4. 生成引用知識庫內容的回答

---

## 專案結構

```
ai-agent/
├── backend/
│   ├── app.py              ← Flask API 主程式
│   │                         ・/api/search            快速搜尋（規則引擎）
│   │                         ・/api/agent             Ollama LLM Agent
│   │                         ・/api/agent/gemini      Gemini Agent
│   │                         ・/api/agent/multi       Multi-Agent Orchestrator
│   │                         ・/api/agent/status      Agent 狀態查詢
│   │                         ・/api/session/clear     清除對話記憶
│   │                         ・/api/kb/*              知識庫 CRUD & 搜尋
│   ├── kb.py               ← 知識庫管理（ChromaDB + Ollama Embedding）
│   ├── extractors.py       ← 文字提取（PDF / DOCX / HTML → 純文字 + 分塊）
│   ├── kb_store/           ← ChromaDB 向量資料庫（自動建立）
│   ├── uploads/            ← 原始上傳檔案（PDF/DOCX，供預覽/下載）
│   ├── requirements.txt    ← Python 依賴
│   └── .env                ← GEMINI_API_KEY（不納入版控）
├── frontend/
│   ├── package.json
│   ├── vite.config.js      ← /api Proxy 設定
│   ├── index.html
│   └── src/
│       ├── App.jsx          ← 主邏輯：4 模式、知識庫切換、Markdown 渲染
│       ├── App.css
│       ├── kb.css           ← 知識庫頁面樣式
│       └── pages/
│           └── KnowledgeBase.jsx  ← 知識庫管理頁面
│                                     ・KbSearchPanel     語意搜尋
│                                     ・KbAiSearchPanel   進階搜尋（LLM + KB）
│                                     ・MarkdownText      Markdown 渲染元件
├── 系統設計文件.docx        ← 完整架構設計文件（v3.1）
└── README.md               ← 本檔案
```

---

## API 端點

### 搜尋 / Agent

| 方法 | 路徑 | 模式 | 說明 | 主要 Body 參數 |
|------|------|------|------|--------------|
| POST | `/api/search` | ⚡ 快速 | 關鍵字規則引擎 | `query`, `lang` |
| POST | `/api/agent` | 🧠 Ollama | Ollama LLM Agent | `query`, `session_id`, `direct`, `use_kb` |
| POST | `/api/agent/gemini` | 🔷 Gemini | Gemini Agent | `query`, `session_id`, `synthesis`, `direct`, `use_kb` |
| POST | `/api/agent/multi` | 🔀 Multi-AI | Orchestrator | `query`, `session_id`, `synthesis`, `direct`, `use_kb` |
| GET  | `/api/agent/status` | — | Agent 狀態 / 可用性 | — |
| POST | `/api/session/clear` | — | 清除對話記憶 | `session_id` |
| GET  | `/api/weather` | — | 直接查天氣 | `?city=台北` |
| GET  | `/api/news` | — | 直接搜尋新聞 | `?q=關鍵字&lang=zh` |
| GET  | `/api/web` | — | 直接網路搜尋 | `?q=關鍵字` |

### 知識庫（RAG）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET  | `/api/kb/stats` | 知識庫統計（文件數、chunk 數、模型） |
| POST | `/api/kb/upload` | 上傳 PDF / DOCX 並向量化索引 |
| GET  | `/api/kb/documents` | 列出所有文件 |
| GET  | `/api/kb/documents/<id>/chunks` | 取得文件文字片段 |
| GET  | `/api/kb/documents/<id>/preview` | 預覽原始文件（PDF串流 / DOCX轉HTML） |
| GET  | `/api/kb/documents/<id>/download` | 下載原始文件 |
| DELETE | `/api/kb/documents/<id>` | 刪除文件（含原始檔） |
| POST | `/api/kb/pages` | 新增 HTML 頁面 |
| GET  | `/api/kb/pages/<id>` | 取得頁面 HTML 內容 |
| PUT  | `/api/kb/pages/<id>` | 更新頁面（重新向量化） |
| DELETE | `/api/kb/pages/<id>` | 刪除頁面 |
| POST | `/api/kb/search` | 語意搜尋 | `query`, `top_k` |

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

### Q: 知識庫需要什麼額外環境？
需要 Ollama 執行 `nomic-embed-text` 模型（Embedding）：
```bash
ollama pull nomic-embed-text   # 約 274MB
```
Python 套件（已含於 requirements.txt）：
```bash
pip install chromadb python-docx PyMuPDF mammoth
```

### Q: DOCX 預覽顯示「mammoth 未安裝」？
```bash
pip install mammoth
```
安裝完成後**不需重啟** Flask，下次請求自動生效。

### Q: 進階搜尋和語意搜尋有什麼差異？

| | 語意搜尋 | 進階搜尋 |
|---|---|---|
| **技術** | ChromaDB cosine 向量搜尋 | LLM（Ollama / Gemini / Multi-Agent） |
| **結果** | 最相關的文件片段清單 | AI 自然語言綜合回答 |
| **適用場景** | 找特定段落、定位文件位置 | 需要推理、彙整或超出 KB 範圍的問題 |
| **KB 參考** | 直接顯示 KB 內容 | 注入 KB context 後 LLM 合成回答 |

兩個 Tab 的查詢字串同步，可在語意搜尋找到片段後無縫切換到進階搜尋取得 AI 解析。

### Q: 進階搜尋選 Gemini 卻說「知識庫無相關內容，無法回答」？

這是 RAG 距離閾值機制的正確行為：

- 知識庫的文件與問題 **cosine distance > 0.75**（相似度 < 25%），系統判定無相關內容
- 不注入無關的 KB context，讓 Gemini 改用自身訓練知識回答
- 調整 `kb.py` 中的 `RAG_THRESHOLD`（預設 `0.75`）可改變靈敏度

若需 AI 從 **企業知識庫**回答，請先在知識庫上傳相關文件，讓 KB 有對應內容可引用。

### Q: Gemini API Key 在哪申請？
前往 https://aistudio.google.com/ → 登入 Google 帳號 → Get API Key → 建立 Free Tier Key。
每天免費額度：Gemini 2.5 Flash 約 500 次請求。

### Q: Ollama 啟動後 AI 模式仍出現錯誤？
確認 `ollama serve` 已在背景執行，且模型已下載：
```bash
ollama list              # 列出已下載模型
ollama pull gemma4:e4b   # 重新拉取對話模型
ollama pull nomic-embed-text  # 重新拉取 Embedding 模型
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

- 📄 [系統設計文件.docx](./系統設計文件.docx) — 完整架構設計、API 規格、Multi-Agent 與 RAG 設計說明
- 🤖 [Ollama](https://ollama.com/) — 本地 LLM 執行環境
- 🔷 [Google AI Studio](https://aistudio.google.com/) — Gemini API Key 申請
- 🌐 [Open-Meteo 文件](https://open-meteo.com/en/docs) — 天氣 API
- 🔍 [duckduckgo-search PyPI](https://pypi.org/project/duckduckgo-search/) — 搜尋套件
- 🗄️ [ChromaDB 文件](https://docs.trychroma.com/) — 向量資料庫
- 📦 [nomic-embed-text](https://ollama.com/library/nomic-embed-text) — Embedding 模型
