"""
AI Agent Backend — Flask API
工具：即時天氣 / 新聞搜尋 / 網路搜尋
智慧判斷使用者意圖，自動呼叫對應工具

Geocoding：Nominatim (OpenStreetMap) — 原生支援中/英/日文，免費無需 API Key
天氣資料：Open-Meteo — 免費無需 API Key
"""

import re
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from ddgs import DDGS

app = Flask(__name__)
CORS(app)

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
]
NEWS_KW = [
    "新聞", "頭條", "熱門", "最新", "消息", "報導", "即時",
    "news", "headline", "latest", "breaking",
    "ニュース", "速報",
]


# ══════════════════════════════════════════════════════════════
#  意圖辨識 & 城市提取
# ══════════════════════════════════════════════════════════════

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
    """智慧搜尋：自動判斷意圖，路由至對應工具"""
    data  = request.get_json(force=True)
    query = data.get("query", "").strip()
    lang  = data.get("lang", "zh")

    if not query:
        return jsonify({"error": "請輸入搜尋內容"}), 400

    intent = detect_intent(query)

    if intent == "weather":
        return _weather(extract_city(query))
    elif intent == "news":
        return _news(query, lang)
    else:
        return _web(query)


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


def _weather(city: str):
    """即時天氣：Nominatim geocoding → Open-Meteo 天氣"""
    try:
        # Step 1：地理編碼（Nominatim 支援中英日文，自動解析）
        loc = _geo_lookup(city)

        if not loc:
            return jsonify({
                "error": f"找不到地點「{city}」，請嘗試更完整的城市名稱"
            }), 404

        lat     = loc["latitude"]
        lon     = loc["longitude"]
        name    = loc["name"]
        country = loc["country"]

        # Step 2：Open-Meteo 取得即時天氣
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "current":   (
                    "temperature_2m,apparent_temperature,"
                    "relative_humidity_2m,wind_speed_10m,"
                    "weather_code,precipitation"
                ),
                "timezone": "auto",   # 自動根據座標選擇時區
            },
            timeout=10,
        ).json()["current"]

        code               = w.get("weather_code", 0)
        condition, emoji   = WMO_CODE.get(code, ("未知", "🌡️"))

        return jsonify({
            "type":          "weather",
            "city":          name,
            "country":       country,
            "temperature":   w["temperature_2m"],
            "feels_like":    w["apparent_temperature"],
            "humidity":      w["relative_humidity_2m"],
            "wind_speed":    w["wind_speed_10m"],
            "precipitation": w["precipitation"],
            "condition":     condition,
            "emoji":         emoji,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"type": "news", "results": items, "query": query})
    except Exception as e:
        if _is_ratelimit(e):
            return jsonify({"error": "DuckDuckGo 請求過於頻繁，請稍等幾秒再試 🙏"}), 429
        return jsonify({"error": str(e)}), 500


def _web(query: str):
    """網路搜尋：DuckDuckGo Text（含 rate limit 自動重試）"""
    if not query:
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
        return jsonify({"type": "web", "results": items, "query": query})
    except Exception as e:
        if _is_ratelimit(e):
            return jsonify({"error": "DuckDuckGo 請求過於頻繁，請稍等幾秒再試 🙏"}), 429
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
