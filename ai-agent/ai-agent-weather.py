import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:e4b"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查詢指定城市的即時天氣，回傳溫度與天氣狀況",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱，例如：台北、高雄、台中、東京、紐約"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "執行數學計算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }
]

# ── 城市對應經緯度（Open-Meteo 用經緯度查詢）──
CITY_COORDS = {
    "台北": (25.04, 121.51),
    "高雄": (22.63, 120.27),
    "台中": (24.15, 120.67),
    "台南": (22.99, 120.21),
    "東京": (35.68, 139.69),
    "大阪": (34.69, 135.50),
    "紐約": (40.71, -74.01),
    "倫敦": (51.51, -0.13),
    "首爾": (37.57, 126.98),
}

# 天氣代碼對應文字
WMO_CODE = {
    0: "晴天", 1: "大致晴朗", 2: "部分多雲", 3: "陰天",
    45: "霧", 48: "霧淞",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "陣雨", 81: "陣雨", 82: "強陣雨",
    95: "雷陣雨", 96: "雷陣雨夾冰雹", 99: "強雷陣雨",
}

def get_weather(city):
    coords = CITY_COORDS.get(city)
    if not coords:
        return f"找不到 {city} 的座標，目前支援：{', '.join(CITY_COORDS.keys())}"

    lat, lon = coords
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,"
        f"wind_speed_10m,weathercode"
        f"&timezone=Asia/Taipei"
    )
    resp = requests.get(url, timeout=10)
    data = resp.json()["current"]

    temp     = data["temperature_2m"]
    humidity = data["relative_humidity_2m"]
    wind     = data["wind_speed_10m"]
    code     = data["weathercode"]
    condition = WMO_CODE.get(code, f"天氣代碼 {code}")

    return f"{city}：{condition}，氣溫 {temp}°C，濕度 {humidity}%，風速 {wind} km/h"


def execute_tool(name, args):
    if name == "get_weather":
        return get_weather(args["city"])
    elif name == "calculator":
        try:
            return f"計算結果：{eval(args['expression'])}"
        except Exception as e:
            return f"計算錯誤：{e}"
    return f"未知工具：{name}"


def call_ollama(messages):
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False
    })
    resp.raise_for_status()
    return resp.json()["message"]


def run_agent(user_input):
    messages = [
        {"role": "system", "content": "你是一個有工具使用能力的 AI 助手，需要時請呼叫工具完成任務。"},
        {"role": "user",   "content": user_input}
    ]
    print(f"\n使用者：{user_input}")

    for _ in range(5):
        reply = call_ollama(messages)
        messages.append(reply)

        if not reply.get("tool_calls"):
            print(f"\nAgent：{reply['content']}")
            return

        for tc in reply["tool_calls"]:
            fn   = tc["function"]
            name = fn["name"]
            args = fn["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            print(f"\n[呼叫工具] {name}({args})")
            result = execute_tool(name, args)
            print(f"[工具結果] {result}")

            messages.append({"role": "tool", "content": result})


if __name__ == "__main__":
    run_agent("台北和東京現在天氣怎樣？哪個城市比較熱？")