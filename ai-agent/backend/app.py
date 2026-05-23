"""
AI Agent Backend — Flask API
工具：即時天氣 / 新聞搜尋 / 網路搜尋

模式 A  快速模式 /api/search  — 關鍵字規則引擎，毫秒級
模式 B  AI 模式  /api/agent   — Ollama LLM (gemma4:e4b) 真正推理決策

Geocoding：Nominatim (OpenStreetMap) — 原生支援中/英/日文，免費無需 API Key
天氣資料：Open-Meteo — 免費無需 API Key
搜尋：ddgs (DuckDuckGo) — 免費無需 API Key
"""

import json
import re
import time
import uuid
import requests
import logging
import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from ddgs import DDGS

# ── 載入 .env（GEMINI_API_KEY 等） ────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # python-dotenv 未安裝時跳過，直接用系統環境變數

# ── Gemini SDK（可選，未安裝時 Gemini 功能自動停用） ──────────
# 使用新版 google-genai SDK（舊版 google.generativeai 已棄用）
try:
    from google import genai as _genai_module
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _genai_module = None
    genai_types    = None
    _GENAI_AVAILABLE = False

# ── 日誌設定 ───────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"ai-agent-{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ── Session 對話記憶（in-memory）──────────────────────────────
# sessions: { session_id: [ {role, content}, ... ] }
sessions: dict[str, list] = {}
MAX_HISTORY_MSGS = 20   # 最多保留 20 條（約 6-7 輪對話）

# ── Ollama 設定 ────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma4:e4b"

# ── Gemini 設定（使用新版 google-genai SDK）─────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"   # 免費層可用模型

GEMINI_SYSTEM_PROMPT = (
    "你是一個智慧搜尋助手，具備 Chain-of-Thought 多步驟推理能力。\n"
    "根據問題與歷史對話選擇工具：\n"
    "  - 天氣預報 → get_weather\n"
    "  - 明確要求新聞頭條 → search_news\n"
    "  - 其他查詢（含分析、比較、解釋）→ search_web\n\n"
    "【代名詞解析】從歷史找出代名詞對應的具體實體名稱，組成完整查詢詞。\n"
    "【複雜查詢】先思考需要哪些資訊再選工具；query 參數用精準關鍵詞，不加語氣詞。"
)

# Gemini 工具定義（新版 SDK 用 types.FunctionDeclaration）
_gemini_client = None
_gemini_tool   = None

if _GENAI_AVAILABLE and GEMINI_API_KEY:
    try:
        _gemini_client = _genai_module.Client(api_key=GEMINI_API_KEY)

        _gemini_tool = genai_types.Tool(function_declarations=[
            genai_types.FunctionDeclaration(
                name="get_weather",
                description="查詢指定城市天氣，支援今天/明天/7天/10天預報",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "city": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="城市名稱，支援中/英/日文"),
                        "date": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="today（今天）/ tomorrow（明天）/ week（7天）/ 10days（10天）"),
                    },
                    required=["city"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="search_news",
                description="搜尋最新新聞、頭條報導",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "query": genai_types.Schema(type=genai_types.Type.STRING, description="新聞搜尋關鍵字"),
                        "lang":  genai_types.Schema(type=genai_types.Type.STRING, description="zh/en/ja"),
                    },
                    required=["query"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="search_web",
                description="搜尋網路任意主題，適合分析、比較、解釋等複雜查詢",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "query": genai_types.Schema(type=genai_types.Type.STRING, description="搜尋關鍵字"),
                    },
                    required=["query"],
                ),
            ),
        ])

        # 驗證連線（列出模型不耗費 quota）
        logger.info(f"✅ Gemini 初始化成功 | model={GEMINI_MODEL}")
    except Exception as _ge:
        _gemini_client = None
        logger.warning(f"⚠️ Gemini 初始化失敗: {_ge}")
elif not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY 未設定，Gemini 功能停用（請確認 backend/.env 檔案）")

# 工具定義（Ollama tool format）
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查詢指定城市的天氣，支援即時（今天）或明天預報",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱，支援中文/英文/日文，例如：台北、東京、Paris"
                    },
                    "date": {
                        "type": "string",
                        "description": "查詢日期：today（今天即時，預設）、tomorrow（明天）、week（未來7天）、10days（未來10天）",
                        "enum": ["today", "tomorrow", "week", "10days"]
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "搜尋最新新聞，適用於新聞、頭條、時事等查詢",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "新聞搜尋關鍵字"
                    },
                    "lang": {
                        "type": "string",
                        "description": "語言：zh（繁體中文）、en（英文）、ja（日文），預設 zh",
                        "enum": ["zh", "en", "ja"]
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜尋網路上任何主題的資訊，適用於一般知識、產品、技術等查詢",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── 天氣代碼（WMO code → 中文描述 + emoji）────────────────────
WMO_CODE = {
    0:  ("晴天",         "☀️"),
    1:  ("大致晴朗",     "🌤️"),
    2:  ("部分多雲",     "⛅"),
    3:  ("陰天",         "☁️"),
    45: ("霧",           "🌫️"),
    48: ("霧淞",         "🌫️"),
    51: ("毛毛雨",       "🌦️"),
    53: ("毛毛雨",       "🌦️"),
    55: ("毛毛雨",       "🌦️"),
    61: ("小雨",         "🌧️"),
    63: ("中雨",         "🌧️"),
    65: ("大雨",         "🌧️"),
    71: ("小雪",         "🌨️"),
    73: ("中雪",         "❄️"),
    75: ("大雪",         "❄️"),
    80: ("陣雨",         "🌦️"),
    81: ("陣雨",         "🌦️"),
    82: ("強陣雨",       "⛈️"),
    95: ("雷陣雨",       "⛈️"),
    96: ("雷陣雨夾冰雹", "⛈️"),
    99: ("強雷陣雨",     "⛈️"),
}

# ── 意圖關鍵字 ───────────────────────────────────────────────
WEATHER_KW = [
    "天氣", "氣溫", "溫度", "下雨", "晴天", "颱風", "濕度", "風速",
    "weather", "temperature", "rain", "sunny", "humidity", "wind", "forecast",
    "天気", "気温", "湿度", "風速", "雨", "晴れ",
    # ── 時間相關（快速模式的天氣追問）
    "明天", "後天", "一週", "7天", "七天", "10天", "十天", "週預報", "週間", "未來",
    "tomorrow", "week", "days",
]
NEWS_KW = [
    "新聞", "頭條", "熱門", "最新", "消息", "報導", "即時",
    "news", "headline", "latest", "breaking",
    "ニュース", "速報",
]

# ── 停用詞（查詞清理用） ──────────────────────────────────────
STOPWORDS = [
    "最近", "最新", "有哪些", "有什麼", "怎樣", "如何", "呢", "嗎", "啊",
    "告訴我", "幫我", "請", "能否", "可以", "是什麼", "是啥",
    "recent", "latest", "what", "which", "any", "can", "please",
]


# ══════════════════════════════════════════════════════════════
#  意圖辨識 & 城市提取
# ══════════════════════════════════════════════════════════════

def clean_query(query: str) -> str:
    """
    清理查詢詞：移除停用詞，提升搜尋準確度
    例如：「最近有哪些人工智慧新聞」→ 「人工智慧新聞」
    """
    result = query
    for sw in STOPWORDS:
        result = re.sub(re.escape(sw), "", result, flags=re.IGNORECASE).strip()
    return result if result else query  # 如果清理後為空，返回原始查詢


def detect_intent(query: str) -> str:
    q = query.lower()
    if any(kw in q for kw in WEATHER_KW):
        return "weather"
    if any(kw in q for kw in NEWS_KW):
        return "news"
    return "web"


def extract_city(query: str) -> str:
    """
    智慧提取城市名稱（不依賴對照表）：
      「台北天氣如何」   → 「台北」
      「東京今天天氣怎樣」→ 「東京」
      「weather in Tokyo」→ 「Tokyo」
      「台中氣溫」       → 「台中」
    """
    q_lower = query.lower()

    # 找第一個天氣關鍵字的位置
    first_pos = len(query)
    matched_kw = None
    for kw in WEATHER_KW:
        idx = q_lower.find(kw.lower())
        if idx != -1 and idx < first_pos:
            first_pos = idx
            matched_kw = kw

    if matched_kw is None:
        return query.strip()

    before = query[:first_pos].strip()
    after  = query[first_pos + len(matched_kw):].strip()

    NOISE = ["如何", "怎樣", "怎麼樣", "呢", "啊", "嗎", "今天", "今日",
             "現在", "now", "today", "how", "is", "like", "？", "?"]

    def clean(text: str) -> str:
        for w in NOISE:
            text = re.sub(re.escape(w), "", text, flags=re.IGNORECASE).strip()
        return text

    if before:
        city = clean(before)
        return city if city else query.strip()
    elif after:
        city = re.sub(r"^(in|for|at|of|the)\s+", "", after, flags=re.IGNORECASE).strip()
        city = clean(city)
        return city if city else query.strip()
    return query.strip()


# ══════════════════════════════════════════════════════════════
#  路由
# ══════════════════════════════════════════════════════════════

@app.route("/api/search", methods=["POST"])
def smart_search():
    """⚡ 快速模式：關鍵字規則引擎，毫秒級回應"""
    data  = request.get_json(force=True)
    query = data.get("query", "").strip()
    lang  = data.get("lang", "zh")

    if not query:
        return jsonify({"error": "請輸入搜尋內容"}), 400

    intent = detect_intent(query)
    cleaned_query = clean_query(query)  # 清理查詞

    if intent == "weather":
        return _weather(extract_city(query))
    elif intent == "news":
        return _news(cleaned_query, lang)  # 用清理後的查詞
    else:
        return _web(cleaned_query)  # 用清理後的查詞


@app.route("/api/agent", methods=["POST"])
def agent_search():
    """🧠 AI 模式：Ollama LLM 推理決策，自動選工具與提取參數（支援多輪對話記憶）"""
    data       = request.get_json(force=True)
    query      = data.get("query", "").strip()
    session_id = data.get("session_id", "") or str(uuid.uuid4())
    direct     = data.get("direct", False)   # True = 直接回答，不呼叫工具
    logger.info(f"\n{'='*80}")
    logger.info(f"🧠 AI 模式搜尋 | session_id={session_id[:8]}... | query='{query}' | direct={direct}")

    if not query:
        return jsonify({"error": "請輸入搜尋內容"}), 400

    # ── 取出該 session 的對話歷史 ────────────────────────────────
    history = sessions.get(session_id, [])

    # ── 直接回答模式（跳過工具，直接問 Ollama）────────────────────
    if direct:
        text = _run_ollama_direct(query, history)
        if not text:
            return jsonify({"error": "⚠️ Ollama 無回應，請確認 ollama serve 已啟動"}), 503
        new_hist = history + [
            {"role": "user",      "content": query},
            {"role": "assistant", "content": text},
        ]
        sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]
        return jsonify({
            "type":          "direct_answer",
            "answer":        text,
            "agent_used":    "ollama",
            "session_id":    session_id,
            "history_count": len(new_hist) // 2,
        })

    # ── 規則式追問解析（在 LLM 之前攔截，小模型保底）────────────
    logger.info(f"📋 執行規則解析器...")
    rule_result = _try_rule_followup(query, history)
    if rule_result:
        name, args = rule_result
        logger.info(f"⚡ 執行規則結果 | tool={name} | args={json.dumps(args, ensure_ascii=False)}")
        if name == "get_weather":
            raw = _weather(args.get("city", query), args.get("date", "today"))
        elif name == "search_news":
            raw = _news(args.get("query", query), args.get("lang", "zh"))
        elif name == "search_web":
            raw = _web(args.get("query", query))
        else:
            raw = None

        if raw is not None:
            # Flask 工具函數有時回傳 (Response, status_code) tuple，需拆開
            response_obj = raw[0] if isinstance(raw, tuple) else raw
            status_code  = raw[1] if isinstance(raw, tuple) else 200

            # 安全地提取 JSON 資料（處理 Response 物件與 dict）
            if isinstance(response_obj, dict):
                result_data = response_obj
            elif hasattr(response_obj, 'get_json'):
                result_data = response_obj.get_json()
            else:
                logger.error(f"❌ 未預期的回應型態: {type(response_obj)}")
                return jsonify({"error": f"規則執行失敗：未預期的回應型態"}), 500

            logger.debug(f"   ✅ 規則工具執行完成 | status={status_code} | result_type={result_data.get('type', 'unknown')}")
            # 若工具本身回錯誤（如找不到城市），直接透傳給前端
            if status_code >= 400 or result_data.get("error"):
                logger.warning(f"   ⚠️ 規則工具返回錯誤: {result_data.get('error', 'unknown error')}")
                return response_obj, status_code

            tool_summary = _summarize_result(result_data)
            args_hint    = json.dumps(args, ensure_ascii=False)
            new_history  = history + [
                {"role": "user",      "content": query},
                {"role": "assistant", "content": f"[工具={name} 參數={args_hint}] {tool_summary}"},
            ]
            if len(new_history) > MAX_HISTORY_MSGS:
                new_history = new_history[-MAX_HISTORY_MSGS:]
            sessions[session_id] = new_history
            result_data.update({
                "llm_decision":  {"tool": name, "args": args},
                "session_id":    session_id,
                "history_count": len(new_history) // 2,
                "rule_matched":  True,
            })
            return jsonify(result_data)

    try:
        # ── Step 1：組合 messages（system + 歷史 + 本輪用戶輸入） ──
        messages = [
            {
                "role":    "system",
                "content": (
                    "你是一個智慧搜尋助手，可以記住對話歷史。\n"
                    "根據使用者問題（結合前文上下文）選擇工具：\n"
                    "- 天氣預報 → get_weather\n"
                    "- 明確要求新聞頭條 → search_news\n"
                    "- 其他查詢 → search_web\n\n"
                    "【代名詞解析規則】\n"
                    "若用戶用「他」「她」「它」「這個人」「這部片」「這件事」等代名詞，"
                    "必須從歷史對話找出對應的具體名稱，組合成完整查詢詞。\n"
                    "例如：上一輪查「介紹賴清德」，用戶問「他的政策有哪些」"
                    "→ query 應為「賴清德 政策」，呼叫 search_web。\n\n"
                    "【追問規則（依上一輪工具）】\n"
                    "上一輪是 get_weather：\n"
                    "  - 「明天呢」→ 同城市 date=tomorrow\n"
                    "  - 「一週/7天/這週」→ 同城市 date=week\n"
                    "  - 「10天/十天/未來10天」→ 同城市 date=10days\n"
                    "  - 「那XX呢/換XX城市」→ 新城市 date=today\n"
                    "上一輪是 search_web 或 search_news：\n"
                    "  - 用戶追問細節、用代名詞 → 解析出原始主題 + 新關鍵詞，呼叫 search_web\n"
                    "  - 用戶明確說「新聞」→ 呼叫 search_news\n\n"
                    "重要：query 參數直接用搜尋關鍵詞，不加語氣詞和問句。\n\n"
                    "【語言規則】\n"
                    "歷史對話中若出現日文城市（如福岡、東京、大阪）或日文內容，"
                    "不代表後續查詢要使用日文。\n"
                    "lang 參數應根據當前問題的語言決定：\n"
                    "  - 用繁體中文問 → lang='zh'（預設）\n"
                    "  - 明確要求英文新聞 → lang='en'\n"
                    "  - 明確要求日文新聞 → lang='ja'\n"
                    "沒有明確指定語言時，一律用 lang='zh'。"
                )
            },
            *history,                                   # 注入歷史對話
            {"role": "user", "content": query},
        ]

        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": messages,
                  "tools": AGENT_TOOLS, "stream": False,
                  "options": {"num_predict": 8192}},
            timeout=180,   # 3 分鐘（大型 prompt / 慢速機器需要較長推理時間）
        )
        resp.raise_for_status()
        msg = resp.json()["message"]
        tool_calls = msg.get("tool_calls")

        # ── Step 2：LLM 沒呼叫工具 → fallback 到規則引擎 ──────────
        if not tool_calls:
            result = smart_search()
            # 安全地提取 JSON（處理 (Response, status) tuple）
            if isinstance(result, tuple):
                response_obj, status_code = result[0], result[1]
                if isinstance(response_obj, dict):
                    result_data = response_obj
                elif hasattr(response_obj, 'get_json'):
                    result_data = response_obj.get_json()
                else:
                    logger.error(f"❌ Fallback 失敗：未預期的回應型態 {type(response_obj)}")
                    return jsonify({"error": "Fallback 處理失敗"}), 500
                if status_code >= 400:
                    return result
            else:
                result_data = result.get_json() if hasattr(result, 'get_json') else result

            # 重要：fallback 也要寫入 session 歷史，否則追問（如「10天呢」）會遺失上下文
            result_type = result_data.get("type")
            if result_type == "weather":
                fallback_tool = "get_weather"
                fallback_args = {
                    "city": result_data.get("city") or extract_city(query),
                    "date": "today",
                }
            elif result_type == "news":
                fallback_tool = "search_news"
                fallback_args = {
                    "query": result_data.get("query", query),
                    "lang": "zh",
                }
            else:
                fallback_tool = "search_web"
                fallback_args = {
                    "query": result_data.get("query", query),
                }

            tool_summary = _summarize_result(result_data)
            args_hint = json.dumps(fallback_args, ensure_ascii=False)
            new_history = history + [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"[工具={fallback_tool} 參數={args_hint}] {tool_summary}"},
            ]
            if len(new_history) > MAX_HISTORY_MSGS:
                new_history = new_history[-MAX_HISTORY_MSGS:]
            sessions[session_id] = new_history

            result_data.update({"llm_fallback": True, "session_id": session_id,
                                 "history_count": len(new_history) // 2})
            return jsonify(result_data)

        # ── Step 3：執行 LLM 選定的工具 ────────────────────────────
        tc   = tool_calls[0]
        fn   = tc["function"]
        name = fn["name"]
        args = fn["arguments"]
        if isinstance(args, str):
            args = json.loads(args)

        logger.info(f"🤖 LLM 決策 | tool={name} | args={json.dumps(args, ensure_ascii=False)}")
        llm_decision = {"tool": name, "args": args}

        if name == "get_weather":
            raw = _weather(args.get("city", query), args.get("date", "today"))
        elif name == "search_news":
            raw = _news(args.get("query", query), args.get("lang", "zh"))
        elif name == "search_web":
            raw = _web(args.get("query", query))
        else:
            return jsonify({"error": f"未知工具：{name}"}), 500

        # 拆 Flask tuple return
        response_obj = raw[0] if isinstance(raw, tuple) else raw
        status_code  = raw[1] if isinstance(raw, tuple) else 200

        # 安全地提取 JSON 資料（處理 Response 物件與 dict）
        if isinstance(response_obj, dict):
            result_data = response_obj
        elif hasattr(response_obj, 'get_json'):
            result_data = response_obj.get_json()
        else:
            logger.error(f"❌ 未預期的回應型態: {type(response_obj)}")
            return jsonify({"error": f"LLM 工具執行失敗：未預期的回應型態"}), 500

        if status_code >= 400 or result_data.get("error"):
            return response_obj, status_code

        # ── Step 4：把本輪對話寫入 session 歷史 ────────────────────
        # 使用純文字 user/assistant 格式（避免 Ollama 不支援 tool_calls replay）
        tool_summary = _summarize_result(result_data)

        # 歷史摘要明確記錄工具名稱與關鍵參數，方便 LLM 追問時參考
        args_hint = json.dumps(args, ensure_ascii=False)
        history = history + [
            {"role": "user",      "content": query},
            {"role": "assistant", "content": f"[工具={name} 參數={args_hint}] {tool_summary}"},
        ]

        # 超過上限時，保留最新的 N 條（每輪 2 條）
        if len(history) > MAX_HISTORY_MSGS:
            history = history[-MAX_HISTORY_MSGS:]

        sessions[session_id] = history

        # ── Step 5：回傳結果（附帶 session 資訊）────────────────────
        result_data.update({
            "llm_decision":  llm_decision,
            "session_id":    session_id,
            "history_count": len(history) // 2,   # 幾輪對話
        })
        return jsonify(result_data)

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "⏱️ Ollama 推理逾時（超過 3 分鐘），模型可能負載過高",
            "hint":  "請稍後再試，或切換至「⚡ 快速模式」"
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "⚠️ 無法連線 Ollama，請確認已執行 ollama serve",
            "hint":  "可切換至「⚡ 快速模式」繼續使用"
        }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    """清除指定 session 的對話歷史"""
    data       = request.get_json(force=True)
    session_id = data.get("session_id", "")
    sessions.pop(session_id, None)
    return jsonify({"ok": True, "session_id": session_id})


def _last_mentioned_city(history: list) -> str:
    """
    從歷史中尋找最近一次提到過的城市名稱
    用途：即使上次天氣查詢失敗，仍可在追問（如「10天呢」）時復用該城市
    """
    logger.debug(f"   搜尋歷史中的城市... 共 {len(history)} 條記錄")
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            logger.debug(f"   檢查 history[{i}]: {content[:80]}...")
            # 查找 get_weather 工具的參數
            m = re.match(r'\[工具=get_weather\s+參數=(\{.*?\})', content)
            if m:
                try:
                    args = json.loads(m.group(1))
                    if args.get("city"):
                        city = args["city"]
                        logger.debug(f"   ✅ 找到城市: '{city}' (from history[{i}])")
                        return city
                except Exception as e:
                    logger.debug(f"   ❌ JSON 解析失敗: {e}")
    logger.debug(f"   ❌ 歷史中未找到城市")
    return ""


def _last_turn(history: list) -> tuple[str, dict, str]:
    """
    從歷史中取出最近一次工具呼叫：(tool_name, tool_args, user_query)
    同時回傳對應的使用者原始問句，供實體名稱提取使用。
    """
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        if msg.get("role") == "assistant":
            m = re.match(r'\[工具=(\w+)\s+參數=(\{.*?\})', msg.get("content", ""))
            if m:
                try:
                    tool = m.group(1)
                    args = json.loads(m.group(2))
                    # 取前一條（對應的使用者問句）
                    user_q = ""
                    if i > 0 and history[i - 1].get("role") == "user":
                        user_q = history[i - 1].get("content", "")
                    return tool, args, user_q
                except Exception:
                    pass
    return "", {}, ""


# 追問模式：(正則, date 值)
_WEATHER_FOLLOWUP = [
    (re.compile(r"10天|十天|未來10天|未來十天"), "10days"),
    (re.compile(r"一週|7天|七天|這週|本週|週預報"), "week"),
    (re.compile(r"明天|tomorrow"),                "tomorrow"),
    (re.compile(r"後天"),                          "tomorrow"),  # 近似
    (re.compile(r"今天|today|現在"),               "today"),
]

# 代名詞模式
_PRONOUN_RE = re.compile(r"^(他|她|它|這個人|這人|此人|這件事|這個|這部|那個)")

# 查詢前綴動詞（提取實體名稱用）
_QUERY_PREFIX_RE = re.compile(
    r"^(介紹|告訴我|幫我查|搜尋|關於|查詢|說明|解釋|什麼是|誰是|怎麼|如何|是什麼|"
    r"帶我了解|給我|找|查|看看)\s*"
)
# 查詢後綴功能詞（清理實體名稱尾部）
_QUERY_SUFFIX_RE = re.compile(
    r"\s*(介紹|說明|是誰|是什麼|相關|資訊|資料|的新聞|詳細|怎樣|怎麼樣)$"
)


def _try_rule_followup(query: str, history: list):
    """
    規則式追問解析器（LLM 之前攔截）
    - 若上一輪是天氣查詢，且當前 query 包含時間追問模式 → 直接返回 (get_weather, args)
    - 若 query 以代名詞開頭，且上一輪是網路/新聞查詢 → 用上一輪 query 補全搜尋詞
    返回 (tool_name, args_dict) 或 None（交給 LLM 處理）
    """
    logger.debug(f"🔍 規則追問解析器開始 | query='{query}'")
    if not history:
        logger.debug("❌ 無歷史記錄，跳過規則")
        return None

    last_tool, last_args, last_user_query = _last_turn(history)
    logger.debug(f"📋 歷史上下文 | last_tool={last_tool} | last_user_query='{last_user_query}')")

    # ── 天氣追問（只攔截明確的「時間」追問，不攔截城市切換）────
    # 檢查 query 是否包含時間追問模式（10天/明天/一週等）
    weather_time_match = None
    for pattern, date_val in _WEATHER_FOLLOWUP:
        if pattern.search(query):
            weather_time_match = date_val
            break

    if weather_time_match:
        logger.info(f"✅ 天氣時間追問規則觸發 | weather_time_match={weather_time_match}")
        # 額外保護：如果 query 含有非天氣意圖的詞，放行給 LLM
        non_weather = re.search(r"介紹|新聞|搜尋|政策|資訊|是誰|什麼人|查詢|告訴", query)
        if not non_weather:
            # 優先用上一輪的城市（last_tool == "get_weather"）
            # 如果上一輪不是天氣查詢，試著從歷史中尋找最近提過的城市
            city = ""
            logger.debug(f"   檢查上一輪工具: last_tool={last_tool}")
            if last_tool == "get_weather":
                city = last_args.get("city", "")
                logger.debug(f"   上一輪是天氣查詢，取城市: '{city}'")
            if not city:
                logger.debug(f"   上一輪不是天氣查詢或無城市，查詢歷史...")
                city = _last_mentioned_city(history)
                logger.debug(f"   從歷史找到城市: '{city}'")
            # 只有找到城市才觸發規則
            if city:
                logger.info(f"✅ 天氣追問規則返回 | city={city} | date={weather_time_match}")
                return ("get_weather", {"city": city, "date": weather_time_match})
            else:
                logger.debug(f"   ❌ 找不到城市，放行給 LLM")

    # ── 代名詞追問（網路 / 新聞搜尋）────────────────────────────
    if last_tool in ("search_web", "search_news") and _PRONOUN_RE.match(query.strip()):
        logger.info(f"✅ 代名詞追問規則觸發 | last_tool={last_tool}")
        # ★ 關鍵：優先用使用者的原始問句來提取實體名稱，
        #         而非 LLM 的搜尋詞（LLM 可能把「蔡英文」擴展成「蔡英文 賴清德 比較」）
        entity_source = last_user_query or last_args.get("query", "")
        logger.debug(f"📝 entity_source='{entity_source}' (from {'user_query' if last_user_query else 'search_args'})")

        # Step 1：去前綴（「介紹蔡英文」→「蔡英文」）
        entity = _QUERY_PREFIX_RE.sub("", entity_source).strip()
        logger.debug(f"   去前綴: '{entity_source}' → '{entity}'")
        # Step 2：去後綴（「蔡英文 介紹」→「蔡英文」）
        entity = _QUERY_SUFFIX_RE.sub("", entity).strip()
        logger.debug(f"   去後綴: '{entity}'")
        # Step 3：fallback — 清空時保留原始來源
        entity = entity or entity_source
        logger.debug(f"   最終實體: '{entity}'")

        if entity:
            # 從當前 query 提取追問的主題詞
            remainder = _PRONOUN_RE.sub("", query.strip()).strip()           # 去代名詞
            topic     = re.sub(r"^的\s*", "", remainder).strip()             # 去開頭助詞「的」
            topic     = re.sub(r"[呢嗎啊吧哦哈]+$", "", topic).strip()      # 去結尾語氣詞
            logger.debug(f"   主題詞提取: '{query.strip()}' → '{topic}'")
            # 組合：空格分隔 → DuckDuckGo 精準關鍵字（「蔡英文 政見」比「蔡英文的政見」更精確）
            new_query = f"{entity} {topic}".strip() if topic else entity
            logger.debug(f"   最終搜尋詞: '{new_query}'")
            if new_query and new_query != query:
                # ★ 不繼承 last_tool：上一輪可能是 search_news，但追問不一定需要新聞
                #   → 依追問主題決定工具，避免工具類型不一致造成結果跟新 session 差很多
                #   → lang 也固定 zh，避免繼承到歷史中的 ja/en
                follow_tool = (
                    "search_news"
                    if re.search(r"新聞|頭條|報導|最新消息|時事", topic)
                    else "search_web"
                )
                logger.info(f"✅ 代名詞規則返回 | tool={follow_tool} | query='{new_query}' | lang=zh")
                logger.debug(f"   工具決策依據: topic='{topic}' → {'news' if follow_tool=='search_news' else 'web'}")
                return (follow_tool, {"query": new_query, "lang": "zh"})

    logger.debug("❌ 無規則匹配，交由 LLM 決策")
    return None   # 不符合規則 → 交給 LLM


def _summarize_result(data: dict) -> str:
    """將工具結果轉為簡短文字，供 LLM 上下文使用"""
    t = data.get("type")
    if t == "weather":
        return (f"{data.get('city')} 天氣：{data.get('condition')} {data.get('emoji')}，"
                f"氣溫 {data.get('temperature')}°C，體感 {data.get('feels_like')}°C，"
                f"濕度 {data.get('humidity')}%，風速 {data.get('wind_speed')} km/h")
    elif t == "news":
        titles = [r.get("title", "") for r in data.get("results", [])[:3]]
        return f"新聞搜尋結果（前3筆）：" + "；".join(titles)
    elif t == "web":
        titles = [r.get("title", "") for r in data.get("results", [])[:3]]
        return f"網路搜尋結果（前3筆）：" + "；".join(titles)
    return json.dumps(data, ensure_ascii=False)[:300]


@app.route("/api/weather")
def weather():
    city = request.args.get("city", "台北")
    return _weather(city)


@app.route("/api/news")
def news():
    query = request.args.get("q", "今日新聞")
    lang  = request.args.get("lang", "zh")
    return _news(query, lang)


@app.route("/api/web")
def web():
    query = request.args.get("q", "")
    return _web(query)


# ══════════════════════════════════════════════════════════════
#  工具實作
# ══════════════════════════════════════════════════════════════

def _geo_lookup(city: str) -> dict | None:
    """
    Nominatim (OpenStreetMap) geocoding
    ─ 原生支援繁體中文、簡體中文、英文、日文等任意語言
    ─ 完全免費，不需 API Key
    ─ 使用規範：需加 User-Agent，請勿高頻呼叫
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q":               city,
                "format":          "json",
                "limit":           1,
                "accept-language": "zh-TW",  # 回傳繁體中文地名
            },
            headers={"User-Agent": "ai-agent-weather/1.0 (local-dev)"},
            timeout=10,
        ).json()

        if not resp:
            return None

        r = resp[0]
        # display_name 最後一段通常是國家名稱，例如 "臺灣" 或 "日本"
        display_parts = r.get("display_name", "").split(", ")
        country = display_parts[-1] if display_parts else ""

        return {
            "latitude":  float(r["lat"]),
            "longitude": float(r["lon"]),
            "name":      city,      # 保留使用者輸入的城市名（較直觀）
            "country":   country,
        }
    except Exception:
        return None


def _weather(city: str, date: str = "today"):
    """
    天氣查詢：
      date="today"    → 即時天氣（current）
      date="tomorrow" → 明日預報（daily forecast index 1）
    """
    try:
        loc = _geo_lookup(city)
        if not loc:
            return jsonify({"error": f"找不到地點「{city}」，請嘗試更完整的城市名稱"}), 404

        lat, lon, name, country = loc["latitude"], loc["longitude"], loc["name"], loc["country"]

        if date in ("week", "10days"):
            # ── 多天預報：7 天或 10 天 ────────────────────────────────
            days = 7 if date == "week" else 10
            meteo_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":  lat, "longitude": lon,
                    "daily": ("temperature_2m_max,temperature_2m_min,"
                              "apparent_temperature_max,"
                              "precipitation_sum,precipitation_probability_max,"
                              "wind_speed_10m_max,weather_code"),
                    "timezone":      "auto",
                    "forecast_days": days,
                },
                timeout=10,
            )
            if not meteo_resp.ok:
                return jsonify({"error": f"Open-Meteo 錯誤（HTTP {meteo_resp.status_code}）"}), 502
            raw = meteo_resp.text.strip()
            if not raw:
                return jsonify({"error": "Open-Meteo 回傳空內容"}), 502

            daily = meteo_resp.json().get("daily", {})
            dates       = daily.get("time", [])
            codes       = daily.get("weather_code", [])
            temp_max    = daily.get("temperature_2m_max", [])
            temp_min    = daily.get("temperature_2m_min", [])
            feels_max   = daily.get("apparent_temperature_max", [])
            precip      = daily.get("precipitation_sum", [])
            precip_prob = daily.get("precipitation_probability_max", [])
            wind        = daily.get("wind_speed_10m_max", [])

            forecast = []
            for i in range(len(dates)):
                cond, emoji = WMO_CODE.get(codes[i] if i < len(codes) else 0, ("未知", "🌡️"))
                forecast.append({
                    "date":       dates[i],
                    "condition":  cond,
                    "emoji":      emoji,
                    "temp_max":   temp_max[i]    if i < len(temp_max)    else None,
                    "temp_min":   temp_min[i]    if i < len(temp_min)    else None,
                    "feels_max":  feels_max[i]   if i < len(feels_max)   else None,
                    "precip":     precip[i]      if i < len(precip)      else None,
                    "precip_prob":precip_prob[i] if i < len(precip_prob) else None,
                    "wind":       wind[i]        if i < len(wind)        else None,
                })

            return jsonify({
                "type":       "weather",
                "date_label": f"未來 {days} 天預報",
                "city":       name,
                "country":    country,
                "forecast":   forecast,   # 前端判斷有此欄位時改用預報表格
            })

        elif date == "tomorrow":
            # ── 明天預報：用 daily 參數，取 index=1 ──────────────────
            meteo_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":  lat, "longitude": lon,
                    "daily":     ("temperature_2m_max,temperature_2m_min,"
                                  "apparent_temperature_max,apparent_temperature_min,"
                                  "precipitation_sum,wind_speed_10m_max,weather_code"),
                    "timezone":      "auto",
                    "forecast_days": 2,
                },
                timeout=10,
            )
            if not meteo_resp.ok:
                return jsonify({"error": f"Open-Meteo 錯誤（HTTP {meteo_resp.status_code}）"}), 502
            raw = meteo_resp.text.strip()
            if not raw:
                return jsonify({"error": "Open-Meteo 回傳空內容"}), 502
            daily = meteo_resp.json().get("daily", {})
            code             = daily.get("weather_code", [0, 0])[1]
            condition, emoji = WMO_CODE.get(code, ("未知", "🌡️"))
            forecast_date    = daily.get("time", ["", ""])[1]
            temp_max         = daily.get("temperature_2m_max",         [None, None])[1]
            temp_min         = daily.get("temperature_2m_min",         [None, None])[1]
            feels_max        = daily.get("apparent_temperature_max",   [None, None])[1]
            precip           = daily.get("precipitation_sum",          [None, None])[1]
            wind             = daily.get("wind_speed_10m_max",         [None, None])[1]

            return jsonify({
                "type":          "weather",
                "date_label":    f"明天（{forecast_date}）",
                "city":          name,
                "country":       country,
                "temperature":   temp_max,
                "temp_min":      temp_min,
                "feels_like":    feels_max,
                "humidity":      None,           # daily API 沒有濕度
                "wind_speed":    wind,
                "precipitation": precip,
                "condition":     condition,
                "emoji":         emoji,
            })

        else:
            # ── 今天即時天氣 ──────────────────────────────────────────
            meteo_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":  lat, "longitude": lon,
                    "current":   ("temperature_2m,apparent_temperature,"
                                  "relative_humidity_2m,wind_speed_10m,"
                                  "weather_code,precipitation"),
                    "timezone": "auto",
                },
                timeout=10,
            )
            if not meteo_resp.ok:
                return jsonify({"error": f"Open-Meteo 錯誤（HTTP {meteo_resp.status_code}）"}), 502
            raw = meteo_resp.text.strip()
            if not raw:
                return jsonify({"error": "Open-Meteo 回傳空內容"}), 502
            meteo_data = meteo_resp.json()
            if "current" not in meteo_data:
                return jsonify({"error": f"Open-Meteo 格式異常：{raw[:120]}"}), 502
            w                = meteo_data["current"]
            code             = w.get("weather_code", 0)
            condition, emoji = WMO_CODE.get(code, ("未知", "🌡️"))
            query_time       = w.get("time", "")[:16]   # "2026-05-22T14:03"

            return jsonify({
                "type":          "weather",
                "date_label":    f"今天（{query_time}）",
                "city":          name,
                "country":       country,
                "temperature":   w["temperature_2m"],
                "temp_min":      None,
                "feels_like":    w["apparent_temperature"],
                "humidity":      w["relative_humidity_2m"],
                "wind_speed":    w["wind_speed_10m"],
                "precipitation": w["precipitation"],
                "condition":     condition,
                "emoji":         emoji,
            })

    except requests.exceptions.Timeout:
        return jsonify({"error": "⏱️ 天氣 API 請求逾時，請稍後再試"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "🌐 無法連線天氣 API，請確認網路連線"}), 503
    except Exception as e:
        return jsonify({"error": f"天氣查詢失敗：{e}"}), 500


def _is_ratelimit(err: Exception) -> bool:
    """判斷是否為 DuckDuckGo rate limit 錯誤"""
    msg = str(err).lower()
    return "ratelimit" in msg or "202" in msg or "rate limit" in msg


def _ddgs_call(fn, max_retries: int = 3):
    """
    執行 DuckDuckGo 查詢，自動重試（指數退避）
    ─ 第 1 次失敗：等 2 秒
    ─ 第 2 次失敗：等 4 秒
    ─ 第 3 次失敗：拋出例外
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if _is_ratelimit(e) and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)      # 2s → 4s
                time.sleep(wait)
                continue
            raise                               # 非 rate limit 錯誤直接拋出
    raise last_err


def _news(query: str, lang: str = "zh"):
    """新聞搜尋：DuckDuckGo News（含 rate limit 自動重試）"""
    logger.info(f"🔎 新聞搜尋 | query='{query}' | lang={lang}")
    region_map = {"zh": "tw-tzh", "en": "us-en", "ja": "jp-jpn"}
    region = region_map.get(lang, "tw-tzh")

    def fetch():
        items = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, region=region, max_results=9):
                items.append({
                    "title":   r.get("title", ""),
                    "summary": r.get("body", ""),
                    "url":     r.get("url", ""),
                    "source":  r.get("source", ""),
                    "date":    r.get("date", ""),
                    "image":   r.get("image", ""),
                })
        return items

    try:
        items = _ddgs_call(fetch)
        logger.info(f"✅ 新聞搜尋完成 | 找到 {len(items)} 筆結果")
        if items:
            logger.debug(f"   標題: {items[0].get('title', 'N/A')[:60]}...")
        return jsonify({"type": "news", "results": items, "query": query})
    except Exception as e:
        if _is_ratelimit(e):
            logger.warning(f"⚠️ DuckDuckGo 速率限制: {str(e)}")
            return jsonify({"error": "DuckDuckGo 請求過於頻繁，請稍等幾秒再試 🙏"}), 429
        logger.error(f"❌ 新聞搜尋失敗: {str(e)}")
        return jsonify({"error": str(e)}), 500


def _web(query: str):
    """網路搜尋：DuckDuckGo Text（含 rate limit 自動重試）"""
    logger.info(f"🔎 網路搜尋 | query='{query}'")
    if not query:
        logger.warning("⚠️ 網路搜尋：查詢詞為空")
        return jsonify({"error": "請輸入搜尋關鍵字"}), 400

    def fetch():
        items = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=9):
                href = r.get("href", "")
                items.append({
                    "title":   r.get("title", ""),
                    "summary": r.get("body", ""),
                    "url":     href,
                    "source":  re.sub(r"https?://(www\.)?", "", href).split("/")[0],
                })
        return items

    try:
        items = _ddgs_call(fetch)
        logger.info(f"✅ 網路搜尋完成 | 找到 {len(items)} 筆結果")
        if items:
            logger.debug(f"   標題: {items[0].get('title', 'N/A')[:60]}...")
        return jsonify({"type": "web", "results": items, "query": query})
    except Exception as e:
        if _is_ratelimit(e):
            logger.warning(f"⚠️ DuckDuckGo 速率限制: {str(e)}")
            return jsonify({"error": "DuckDuckGo 請求過於頻繁，請稍等幾秒再試 🙏"}), 429
        logger.error(f"❌ 網路搜尋失敗: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════
#  Gemini 多 Agent 協作
#  架構：
#    /api/agent/gemini → Gemini 專屬（複雜推理 + 工具）
#    /api/agent/multi  → Orchestrator 自動路由（複雜→Gemini / 簡單→Ollama）
# ══════════════════════════════════════════════════════════════

# ── 共用輔助函數 ──────────────────────────────────────────────

def _to_gemini_history(history: list) -> list:
    """
    Ollama 格式歷史 → Gemini Content 物件列表（新版 SDK）
    Ollama: {role: user|assistant, content: "..."}
    Gemini: Content(role=user|model, parts=[Part(text="...")])
    同時清理 assistant 訊息中的 [工具=X 參數=Y] 結構標記
    """
    result = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        content = msg["content"]
        if msg["role"] == "assistant":
            content = re.sub(r"^\[工具=\w+\s+參數=\{.*?\}\]\s*", "", content).strip()
            if not content:
                continue
        result.append(
            genai_types.Content(role=role, parts=[genai_types.Part(text=content)])
        )
    return result


def _assess_complexity(query: str) -> str:
    """
    Orchestrator：評估查詢複雜度，決定路由
    Returns: "gemini"（複雜推理）| "ollama"（標準工具查詢）
    """
    COMPLEX_KW = [
        # 中文
        "分析", "比較", "為什麼", "為何", "原因", "影響", "趨勢", "預測",
        "建議", "優缺點", "差異", "解釋", "評估", "洞察", "深入", "綜合",
        "背後", "機制", "策略", "評比", "如何才能", "有什麼關係",
        # 英文
        "analyze", "compare", "why", "reason", "impact", "trend",
        "predict", "recommend", "pros and cons", "difference", "explain",
    ]
    matched = [kw for kw in COMPLEX_KW if kw in query.lower()]
    if matched:
        logger.debug(f"   🧭 複雜度評估：匹配={matched} → gemini")
        return "gemini"
    logger.debug(f"   🧭 複雜度評估：無複雜關鍵字 → ollama")
    return "ollama"


def _execute_tool(name: str, args: dict, query: str):
    """共用工具執行器，避免各 endpoint 重複相同程式碼"""
    if name == "get_weather":
        return _weather(args.get("city", query), args.get("date", "today"))
    elif name == "search_news":
        return _news(args.get("query", query), args.get("lang", "zh"))
    elif name == "search_web":
        return _web(args.get("query", query))
    return None


def _safe_extract(raw) -> tuple:
    """
    安全地從工具回傳值提取 (result_data, status_code)
    處理 Flask Response 物件 / tuple / dict 三種情況
    """
    response_obj = raw[0] if isinstance(raw, tuple) else raw
    status_code  = raw[1] if isinstance(raw, tuple) else 200
    if isinstance(response_obj, dict):
        return response_obj, status_code
    elif hasattr(response_obj, "get_json"):
        return response_obj.get_json(), status_code
    return None, 500


def _update_session(session_id: str, history: list, query: str,
                    tool_name: str, tool_args: dict, result_data: dict):
    """統一更新 session 歷史，避免各 endpoint 重複邏輯"""
    summary   = _summarize_result(result_data)
    args_hint = json.dumps(tool_args, ensure_ascii=False)
    new_hist  = history + [
        {"role": "user",      "content": query},
        {"role": "assistant", "content": f"[工具={tool_name} 參數={args_hint}] {summary}"},
    ]
    sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]


def _run_gemini_decision(query: str, history: list) -> tuple | None:
    """
    使用 Gemini 進行工具決策（新版 google-genai SDK）
    Returns:
      (tool_name, args_dict)           → 需要呼叫工具
      ("direct_answer", {"text": ...}) → Gemini 直接回答
      None                             → 呼叫失敗
    """
    if _gemini_client is None:
        logger.warning("⚠️ Gemini Client 未初始化")
        return None
    try:
        gemini_hist = _to_gemini_history(history)
        chat = _gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=genai_types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_PROMPT,
                tools=[_gemini_tool],
                temperature=0.1,
            ),
            history=gemini_hist,
        )
        resp = chat.send_message(query)

        # 解析 function call（新 SDK 從 candidates[0].content.parts 取）
        for part in resp.candidates[0].content.parts:
            if part.function_call and part.function_call.name:
                fc   = part.function_call
                args = {k: v for k, v in fc.args.items()}
                logger.info(f"🤖 Gemini 工具決策 | tool={fc.name} | args={json.dumps(args, ensure_ascii=False)}")
                return (fc.name, args)

        # 沒有 function call → 純文字回答
        text = resp.text or ""
        logger.info(f"💬 Gemini 直接回答 | len={len(text)}")
        return ("direct_answer", {"text": text})

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            logger.warning(f"⚠️ Gemini quota 超限，請稍後再試: {err_str[:120]}")
        else:
            logger.error(f"❌ Gemini 呼叫失敗: {err_str[:200]}")
        return None


def _run_gemini_synthesis(query: str, tool_result: dict) -> str:
    """
    將搜尋結果送回 Gemini 生成分析報告。
    - 比較/vs 型查詢 → 結構化比較報告（規格 / 效能 / 推薦）
    - 分析/趨勢型查詢 → 重點摘要 + 洞察
    Returns: 報告文字（Markdown 格式），或 ""（失敗時）
    """
    if _gemini_client is None:
        return ""
    try:
        # 截取搜尋結果摘要（title + summary）避免 token 過長
        results = tool_result.get("results", [])
        result_lines = []
        for r in results[:6]:
            title   = r.get("title", "")
            summary = r.get("summary", "")[:200]
            result_lines.append(f"• {title}\n  {summary}")
        result_str = "\n".join(result_lines) or json.dumps(tool_result, ensure_ascii=False)[:1500]

        # 偵測查詢類型
        is_comparison = bool(re.search(
            r'\bvs\b|versus|比較|差異|哪個好|哪個更|推薦.*哪|選哪|還是.*好', query, re.IGNORECASE
        ))

        if is_comparison:
            system_inst = "你是專業產品評測分析師，根據網路資料提供客觀、有根據的比較報告，用繁體中文回答。"
            prompt = (
                f"用戶問題：{query}\n\n"
                f"搜尋到的相關資料：\n{result_str}\n\n"
                "請根據以上資料，撰寫一份結構化比較報告，格式如下：\n\n"
                "## 📊 規格比較\n"
                "（列出兩者關鍵規格差異，有數字更好）\n\n"
                "## ⚡ 效能分析\n"
                "（針對用戶問題的效能面向深入比較）\n\n"
                "## 💰 性價比評估\n"
                "（價格區間與物超所值程度）\n\n"
                "## 🎯 推薦結論\n"
                "（哪種需求適合哪個，給出明確建議）\n\n"
                "每段 2-3 句，有具體事實或數字支撐，不要模糊。"
            )
            max_tokens = 800
        else:
            system_inst = "你是專業分析師，根據搜尋結果提供結構化分析，用繁體中文回答，條理清晰。"
            prompt = (
                f"用戶問題：{query}\n\n"
                f"搜尋到的相關資料：\n{result_str}\n\n"
                "請根據以上資料，用繁體中文提供結構化分析，格式如下：\n\n"
                "## 🔍 重點摘要\n"
                "（3-4 個核心重點，每點一句）\n\n"
                "## 💡 深度洞察\n"
                "（超越表面資訊的分析與解讀）\n\n"
                "## 📌 結論\n"
                "（給用戶的具體建議或結論）\n\n"
                "有事實依據，不要模糊。"
            )
            max_tokens = 600

        resp = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_inst,
                temperature=0.3,
                max_output_tokens=max_tokens,
            ),
        )
        return resp.text or ""
    except Exception as e:
        logger.error(f"❌ Gemini 合成失敗: {e}")
        return ""


def _run_ollama_direct(query: str, history: list) -> str:
    """
    Ollama 直接回答模式（不呼叫任何工具）
    讓 Ollama 憑自身知識直接回答，適合一般知識、閒聊、程式、翻譯等問題。
    Returns: 回答文字，失敗時回傳 ""
    """
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一個知識淵博的 AI 助手，請直接回答用戶的問題。\n"
                    "用繁體中文回答，條理清晰。\n"
                    "若問題涉及需要即時資料（如今天天氣、最新股價、最新新聞），"
                    "請誠實告知你的知識有截止日期，建議用戶切換至「搜尋模式」取得最新資訊。\n"
                    "適當時可使用 Markdown 格式（標題、條列、粗體）提升可讀性。"
                ),
            },
            *history,
            {"role": "user", "content": query},
        ]
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
                  "options": {"num_predict": 8192}},
            timeout=180,
        )
        resp.raise_for_status()
        text = resp.json()["message"].get("content", "")
        logger.info(f"🧠 Ollama 直接回答 | len={len(text)}")
        return text
    except requests.exceptions.Timeout:
        logger.warning("⚠️ Ollama 直接回答逾時")
        return ""
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Ollama 連線失敗")
        return ""
    except Exception as e:
        logger.error(f"❌ Ollama 直接回答失敗: {e}")
        return ""


def _run_gemini_direct(query: str, history: list) -> str:
    """
    Gemini 直接回答模式（不呼叫任何工具）
    讓 Gemini 憑自身知識直接回答，適合知識問答、分析推理等問題。
    Returns: 回答文字，失敗時回傳 ""
    """
    if _gemini_client is None:
        return ""
    try:
        gemini_hist = _to_gemini_history(history)
        chat = _gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=genai_types.GenerateContentConfig(
                system_instruction=(
                    "你是一個知識淵博的 AI 助手，請直接回答用戶的問題。\n"
                    "用繁體中文回答，條理清晰，有根據。\n"
                    "若問題涉及需要即時資料（如今天天氣、最新股價），"
                    "請誠實告知並建議用戶切換至「搜尋模式」。\n"
                    "使用 Markdown 格式（## 標題、- 條列、**粗體**）提升可讀性。"
                ),
                temperature=0.7,
                max_output_tokens=8192,   # 提高上限，避免截斷長篇回答
            ),
            history=gemini_hist,
        )
        resp = chat.send_message(query)
        text = resp.text or ""
        logger.info(f"🔷 Gemini 直接回答 | len={len(text)}")
        return text
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            logger.warning(f"⚠️ Gemini quota 超限（直接回答）: {err_str[:120]}")
        else:
            logger.error(f"❌ Gemini 直接回答失敗: {err_str[:200]}")
        return ""


# ── Gemini Agent 端點 ─────────────────────────────────────────

@app.route("/api/agent/gemini", methods=["POST"])
def gemini_agent_search():
    """
    🔷 Gemini Agent
    使用 Google Gemini 2.0 Flash 進行推理與工具選擇
    支援 synthesis=true 啟用深度分析合成
    """
    data       = request.get_json(force=True)
    query      = data.get("query", "").strip()
    session_id = data.get("session_id", "") or str(uuid.uuid4())
    synthesis  = data.get("synthesis", False)  # 是否啟用 Gemini 深度合成
    direct     = data.get("direct", False)     # True = 直接回答，不呼叫工具

    logger.info(f"\n{'='*80}")
    logger.info(f"🔷 Gemini Agent | session={session_id[:8]} | query='{query}' | synthesis={synthesis} | direct={direct}")

    if not query:
        return jsonify({"error": "請輸入搜尋內容"}), 400
    if _gemini_client is None:
        return jsonify({"error": "⚠️ Gemini 未初始化，請確認 GEMINI_API_KEY 與 pip install google-genai"}), 503

    history = sessions.get(session_id, [])

    # ── 直接回答模式（跳過工具，直接問 Gemini）────────────────────
    if direct:
        text = _run_gemini_direct(query, history)
        if not text:
            return jsonify({"error": "⚠️ Gemini 無回應，請稍後再試或確認 API Key"}), 503
        new_hist = history + [
            {"role": "user",      "content": query},
            {"role": "assistant", "content": text},
        ]
        sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]
        return jsonify({
            "type":          "direct_answer",
            "answer":        text,
            "agent_used":    "gemini",
            "session_id":    session_id,
            "history_count": len(new_hist) // 2,
        })

    # ── 規則層（與 Ollama Agent 共用，保持一致） ────────────────
    rule_result = _try_rule_followup(query, history)
    if rule_result:
        name, args = rule_result
        raw = _execute_tool(name, args, query)
        if raw is not None:
            result_data, status_code = _safe_extract(raw)
            if result_data is None:
                return jsonify({"error": "規則工具回傳格式異常"}), 500
            if status_code >= 400:
                return (raw[0] if isinstance(raw, tuple) else raw), status_code
            _update_session(session_id, history, query, name, args, result_data)
            result_data.update({
                "session_id": session_id, "agent_used": "rule→gemini",
                "rule_matched": True, "history_count": len(sessions[session_id]) // 2,
            })
            return jsonify(result_data)

    # ── Gemini 工具決策 ──────────────────────────────────────────
    decision = _run_gemini_decision(query, history)
    if decision is None:
        return jsonify({"error": "Gemini 決策失敗，請稍後再試或改用 /api/agent（Ollama 模式）"}), 503

    name, args = decision

    # Gemini 直接回答（無需工具）
    if name == "direct_answer":
        text = args.get("text", "")
        new_hist = history + [
            {"role": "user",      "content": query},
            {"role": "assistant", "content": text},
        ]
        sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]
        return jsonify({
            "type":          "direct_answer",
            "answer":        text,
            "agent_used":    "gemini",
            "session_id":    session_id,
            "history_count": len(new_hist) // 2,
        })

    # 執行工具
    raw = _execute_tool(name, args, query)
    if raw is None:
        return jsonify({"error": f"未知工具：{name}"}), 500

    result_data, status_code = _safe_extract(raw)
    if result_data is None:
        return jsonify({"error": "工具回傳格式異常"}), 500
    if status_code >= 400:
        return (raw[0] if isinstance(raw, tuple) else raw), status_code

    # 選擇性深度合成（synthesis=true 時啟用）
    if synthesis:
        synth_text = _run_gemini_synthesis(query, result_data)
        if synth_text:
            result_data["synthesis"] = synth_text
            logger.info(f"✨ Gemini 合成完成 | length={len(synth_text)}")

    _update_session(session_id, history, query, name, args, result_data)
    result_data.update({
        "llm_decision":  {"tool": name, "args": args},
        "session_id":    session_id,
        "agent_used":    "gemini",
        "history_count": len(sessions[session_id]) // 2,
    })
    return jsonify(result_data)


@app.route("/api/agent/multi", methods=["POST"])
def multi_agent_search():
    """
    🔀 多 Agent 協作（Orchestrator）
    自動根據查詢複雜度路由：
      規則追問     → Rule Layer（最快，< 50ms）
      複雜推理分析 → Gemini（Chain-of-Thought + 深度合成）
      標準工具查詢 → Ollama（本地、隱私安全）
    回傳額外欄位：agent_used / route / synthesis
    """
    data       = request.get_json(force=True)
    query      = data.get("query", "").strip()
    session_id = data.get("session_id", "") or str(uuid.uuid4())
    synthesis  = data.get("synthesis", True)   # 複雜查詢預設啟用
    direct     = data.get("direct", False)     # True = 直接回答，不呼叫工具

    logger.info(f"\n{'='*80}")
    logger.info(f"🔀 Multi-Agent | session={session_id[:8]} | query='{query}' | direct={direct}")

    if not query:
        return jsonify({"error": "請輸入搜尋內容"}), 400

    history = sessions.get(session_id, [])

    # ── 直接回答模式（Orchestrator 評估複雜度選擇最佳 LLM）────────
    if direct:
        # 與搜尋模式相同：用 _assess_complexity 決定路由
        #   複雜（分析/比較/為什麼…）→ Gemini
        #   簡單（寫程式/翻譯/問答/寫 code）→ Ollama
        route = _assess_complexity(query)
        # 若 Gemini 不可用，直接改 ollama
        if route == "gemini" and _gemini_client is None:
            route = "ollama"
        logger.info(f"🧭 Direct 模式路由 | route={route}")

        text       = ""
        agent_used = ""

        if route == "gemini":
            text       = _run_gemini_direct(query, history)
            agent_used = "gemini" if text else ""

        if not text:
            # 簡單問題，或 Gemini 失敗 → Ollama
            text       = _run_ollama_direct(query, history)
            agent_used = "ollama" if text else ""

        if not text and _gemini_client is not None and route != "gemini":
            # Ollama 也失敗 → 最終 fallback 至 Gemini
            logger.warning("⚠️ Ollama 直接回答失敗，Fallback → Gemini")
            text       = _run_gemini_direct(query, history)
            agent_used = "gemini" if text else ""

        if not text:
            return jsonify({"error": "⚠️ Gemini 與 Ollama 均無法回答，請稍後再試"}), 503

        new_hist = history + [
            {"role": "user",      "content": query},
            {"role": "assistant", "content": text},
        ]
        sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]
        logger.info(f"💬 Multi 直接回答 | agent={agent_used} | route={route} | len={len(text)}")
        return jsonify({
            "type":          "direct_answer",
            "answer":        text,
            "agent_used":    agent_used,
            "route":         f"direct/{route}",
            "session_id":    session_id,
            "history_count": len(new_hist) // 2,
        })

    # ── Step 1：規則層（最優先） ─────────────────────────────────
    rule_result = _try_rule_followup(query, history)
    if rule_result:
        name, args = rule_result
        raw = _execute_tool(name, args, query)
        if raw is not None:
            result_data, status_code = _safe_extract(raw)
            if result_data is None:
                return jsonify({"error": "規則工具格式異常"}), 500
            if status_code >= 400:
                return (raw[0] if isinstance(raw, tuple) else raw), status_code
            _update_session(session_id, history, query, name, args, result_data)
            result_data.update({
                "session_id": session_id, "agent_used": "rule",
                "rule_matched": True, "route": "rule_layer",
                "history_count": len(sessions[session_id]) // 2,
            })
            logger.info(f"⚡ 規則層攔截成功 | tool={name}")
            return jsonify(result_data)

    # ── Step 2：Orchestrator 評估複雜度 ──────────────────────────
    route = _assess_complexity(query)
    if route == "gemini" and _gemini_client is None:
        logger.warning("⚠️ Gemini 不可用，Orchestrator 自動改路由至 Ollama")
        route = "ollama"
    logger.info(f"🧭 Orchestrator 決策 | route={route}")

    # ── Step 3a：Gemini 路徑（複雜推理）──────────────────────────
    if route == "gemini":
        decision = _run_gemini_decision(query, history)
        if decision is not None:
            name, args = decision

            # Gemini 直接回答
            if name == "direct_answer":
                text = args.get("text", "")
                new_hist = history + [
                    {"role": "user",      "content": query},
                    {"role": "assistant", "content": text},
                ]
                sessions[session_id] = new_hist[-MAX_HISTORY_MSGS:]
                return jsonify({
                    "type": "direct_answer", "answer": text,
                    "agent_used": "gemini", "route": "gemini",
                    "session_id": session_id,
                    "history_count": len(new_hist) // 2,
                })

            raw = _execute_tool(name, args, query)
            if raw is not None:
                result_data, status_code = _safe_extract(raw)
                if result_data and status_code < 400:
                    # 深度合成：Gemini 路徑的核心價值
                    if synthesis:
                        synth_text = _run_gemini_synthesis(query, result_data)
                        if synth_text:
                            result_data["synthesis"] = synth_text
                    _update_session(session_id, history, query, name, args, result_data)
                    result_data.update({
                        "llm_decision":  {"tool": name, "args": args},
                        "session_id":    session_id,
                        "agent_used":    "gemini",
                        "route":         "gemini",
                        "history_count": len(sessions[session_id]) // 2,
                    })
                    return jsonify(result_data)

        logger.warning("⚠️ Gemini 路徑失敗，Fallback → Ollama")

    # ── Step 3b：Ollama 路徑（標準查詢 / Gemini fallback）────────
    logger.info(f"🟢 Ollama 路徑執行 | route={route}")
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一個智慧搜尋助手。根據問題選擇工具：\n"
                    "天氣→get_weather、新聞→search_news、其他→search_web。\n"
                    "代名詞從歷史找出實體名稱；query 用精準關鍵詞。"
                ),
            },
            *history,
            {"role": "user", "content": query},
        ]
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": messages,
                  "tools": AGENT_TOOLS, "stream": False,
                  "options": {"num_predict": 8192}},
            timeout=180,
        )
        resp.raise_for_status()
        msg        = resp.json()["message"]
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            tc   = tool_calls[0]
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            logger.info(f"🟢 Ollama 工具決策 | tool={name} | args={json.dumps(args, ensure_ascii=False)}")
            raw = _execute_tool(name, args, query)
            if raw:
                result_data, status_code = _safe_extract(raw)
                if result_data and status_code < 400:
                    _update_session(session_id, history, query, name, args, result_data)
                    result_data.update({
                        "llm_decision":  {"tool": name, "args": args},
                        "session_id":    session_id,
                        "agent_used":    "ollama",
                        "route":         route,
                        "history_count": len(sessions[session_id]) // 2,
                    })
                    return jsonify(result_data)
        else:
            # Ollama 無工具呼叫 → fallback 規則引擎
            logger.info("🟢 Ollama 無工具決策，使用規則引擎 fallback")
            raw = smart_search()
            result_data, status_code = _safe_extract(raw)
            if result_data and status_code < 400:
                result_data.update({
                    "session_id":  session_id,
                    "agent_used":  "ollama_fallback",
                    "route":       route,
                })
                return jsonify(result_data)

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "⏱️ Ollama 推理逾時，可改用 /api/agent/gemini",
            "hint":  "Gemini 不依賴本地 Ollama，速度更快"
        }), 504
    except requests.exceptions.ConnectionError:
        # Ollama 不可用時，嘗試 Gemini 作為最後手段
        logger.warning("⚠️ Ollama 連線失敗，嘗試 Gemini 作為最終 Fallback")
        if _gemini_client is not None:
            decision = _run_gemini_decision(query, history)
            if decision and decision[0] != "direct_answer":
                name, args = decision
                raw = _execute_tool(name, args, query)
                if raw:
                    result_data, status_code = _safe_extract(raw)
                    if result_data and status_code < 400:
                        _update_session(session_id, history, query, name, args, result_data)
                        result_data.update({
                            "session_id": session_id,
                            "agent_used": "gemini_emergency_fallback",
                            "route": "gemini",
                        })
                        return jsonify(result_data)
        return jsonify({
            "error": "⚠️ Ollama 與 Gemini 均無法連線",
            "hint":  "請確認 ollama serve 已啟動，或檢查 GEMINI_API_KEY"
        }), 503
    except Exception as e:
        logger.error(f"❌ Multi-Agent 執行失敗: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Multi-Agent 執行失敗，無可用路由"}), 500


@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    """🔍 查詢各 Agent 狀態（Gemini / Ollama 是否可用）"""
    ollama_ok = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = r.ok
    except Exception:
        pass

    return jsonify({
        "gemini": {
            "available": _gemini_client is not None,
            "model":     GEMINI_MODEL if _gemini_client else None,
            "key_set":   bool(GEMINI_API_KEY),
        },
        "ollama": {
            "available": ollama_ok,
            "model":     OLLAMA_MODEL,
            "url":       OLLAMA_URL,
        },
        "endpoints": {
            "/api/agent":        "Ollama Agent（現有，不變）",
            "/api/agent/gemini": "Gemini Agent（新）",
            "/api/agent/multi":  "Multi-Agent Orchestrator（新）",
            "/api/agent/status": "Agent 狀態查詢（新）",
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
