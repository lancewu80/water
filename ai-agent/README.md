# 🤖 AI 智慧搜尋系統

一套結合自然語言意圖辨識的 Agent 應用，單一搜尋框自動判斷並執行：

| 功能 | 觸發範例 | 資料來源 |
|------|---------|---------|
| 🌤️ 即時天氣 | `台北天氣`、`東京氣溫` | Open-Meteo（免費，無需 Key） |
| 📰 新聞搜尋 | `最新新聞`、`科技頭條` | DuckDuckGo News |
| 🔍 網路搜尋 | 其他任何查詢（預設）| DuckDuckGo Text |

---

## 環境需求

| 工具 | 版本 | 說明 |
|------|------|------|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端建構工具 |
| npm | 9+ | 套件管理 |

---

## 快速開始

### Step 1：後端設定

```bash
# 進入後端資料夾
cd ai-agent/backend

# 安裝 Python 套件
pip install -r requirements.txt
```

`requirements.txt` 包含：
- `flask` — HTTP API 框架
- `flask-cors` — 允許前端跨來源請求
- `duckduckgo-search` — 新聞 / 網路搜尋
- `requests` — 呼叫 Open-Meteo API

### Step 2：前端設定

```bash
# 進入前端資料夾
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

### 開啟瀏覽器

打開 **http://localhost:3000**，即可使用 AI 智慧搜尋介面。

---

## 使用方式

### 天氣查詢
在搜尋框輸入包含天氣相關關鍵字的查詢：
```
台北天氣
東京氣溫
London weather
```
系統會自動偵測並顯示 🌤️ 即時天氣卡片，包含：
- 🌡️ 氣溫 / 體感溫度
- 💧 相對濕度
- 💨 風速
- 🌂 降水量

### 新聞搜尋
輸入包含新聞相關關鍵字的查詢：
```
最新科技新聞
台灣今日頭條
AI news
```
出現語言切換按鈕（🇹🇼 中文 / 🇺🇸 English / 🇯🇵 日本語）以及快捷標籤（科技、財經、政治⋯⋯）。

### 網路搜尋
輸入任何一般查詢（預設行為）：
```
Claude AI 是什麼
Python Flask 教學
如何學習 React
```
顯示搜尋結果卡片，含標題、摘要、來源連結。

---

## 專案結構

```
ai-agent/
├── backend/
│   ├── app.py              ← Flask API 主程式（意圖辨識 + 3 個工具）
│   └── requirements.txt    ← Python 依賴
├── frontend/
│   ├── package.json
│   ├── vite.config.js      ← /api Proxy 設定（開發用）
│   ├── index.html
│   └── src/
│       ├── App.jsx          ← 主邏輯：搜尋、意圖偵測、結果渲染
│       ├── App.css
│       └── components/
│           ├── SearchBox.jsx       ← 搜尋框元件
│           ├── SearchBox.css
│           ├── WeatherCard.jsx     ← 天氣卡片
│           ├── WeatherCard.css
│           ├── NewsCard.jsx        ← 新聞卡片
│           ├── NewsCard.css
│           ├── WebResultCard.jsx   ← 網路搜尋結果
│           └── WebResultCard.css
├── ai-agent-simple.py      ← 原始 Agent 範例（Ollama）
├── ai-agent-weather.py     ← 天氣 Agent 範例（Ollama）
├── 系統設計文件.docx        ← 系統設計文件
└── README.md               ← 本檔案
```

---

## API 端點

後端提供以下 REST API（base URL: `http://localhost:5000`）：

| 方法 | 路徑 | 說明 | 參數 |
|------|------|------|------|
| POST | `/api/search` | 智慧搜尋（自動判斷意圖） | `{ query, lang }` |
| GET | `/api/weather` | 直接查天氣 | `?city=台北` |
| GET | `/api/news` | 直接搜尋新聞 | `?q=關鍵字&lang=zh` |
| GET | `/api/web` | 直接網路搜尋 | `?q=關鍵字` |

---

## 常見問題

### Q: `ModuleNotFoundError: No module named 'flask'`
```bash
pip install -r requirements.txt
```

### Q: `npm install` 失敗
確認 Node.js 版本 >= 18：
```bash
node -v
```

### Q: 前端出現 `Network Error` 或 API 無回應
- 確認後端已在終端機 1 正常執行
- 確認後端執行在 port 5000
- `vite.config.js` 的 proxy 設定將 `/api` 轉發至 `http://localhost:5000`

### Q: 天氣搜尋找不到城市
- 輸入較通用的城市名稱（例如「台北」而非「內湖區」）
- 支援中文、英文、日文城市名稱

### Q: DuckDuckGo 搜尋結果為空
- DuckDuckGo 有每分鐘請求頻率限制，稍候再試
- 確認網路連線正常

---

## 生產環境部署（選用）

```bash
# 前端打包
cd frontend
npm run build
# 輸出靜態檔案至 dist/

# 後端使用 Gunicorn（需先安裝）
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

- 📄 [系統設計文件.docx](./系統設計文件.docx) — 完整架構設計、API 規格、元件說明
- 🌐 [Open-Meteo 文件](https://open-meteo.com/en/docs)
- 🔍 [duckduckgo-search PyPI](https://pypi.org/project/duckduckgo-search/)
