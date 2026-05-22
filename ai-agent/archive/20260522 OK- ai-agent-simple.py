import json
import requests

# ── 設定 ──────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:e4b"

# ── 定義工具 ──────────────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "執行數學計算，例如 2+3*4",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "數學算式"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查詢某城市的天氣",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱，例如 台北"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "讀取本地文字檔案內容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "檔案路徑"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# ── 工具實作 ──────────────────────────────────────
def execute_tool(name, args):
    if name == "calculator":
        try:
            result = eval(args["expression"])
            return f"計算結果：{args['expression']} = {result}"
        except Exception as e:
            return f"計算錯誤：{e}"

    elif name == "get_weather":
        # 這裡可以換成真實 API，例如 OpenWeatherMap
        mock = {"台北": "晴天 28°C", "高雄": "多雲 31°C", "台中": "陰天 25°C"}
        return mock.get(args["city"], f"{args['city']}：天氣資料不足")

    elif name == "read_file":
        try:
            with open(args["path"], "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"讀取失敗：{e}"

    return f"未知工具：{name}"

# ── 呼叫 Ollama ───────────────────────────────────
def call_ollama(messages):
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False
    })
    response.raise_for_status()
    return response.json()["message"]

# ── Agent 主迴圈 ──────────────────────────────────
def run_agent(user_input):
    messages = [
        {"role": "system", "content": "你是一個有工具使用能力的 AI 助手，需要時請呼叫工具來完成任務。"},
        {"role": "user", "content": user_input}
    ]

    print(f"\n使用者：{user_input}")

    for step in range(5):  # 最多 5 輪避免無限迴圈
        reply = call_ollama(messages)
        messages.append(reply)

        # 沒有 tool call → 任務完成
        if not reply.get("tool_calls"):
            print(f"\nAgent：{reply['content']}")
            return reply["content"]

        # 有 tool call → 執行工具
        for tc in reply["tool_calls"]:
            fn = tc["function"]
            tool_name = fn["name"]
            tool_args = fn["arguments"]

            # Ollama 有時回傳字串，需要 parse
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)

            print(f"\n[呼叫工具] {tool_name}({tool_args})")
            result = execute_tool(tool_name, tool_args)
            print(f"[工具結果] {result}")

            # 把工具結果塞回 messages
            messages.append({
                "role": "tool",
                "content": result
            })

    return "達到最大步驟數，任務未完成。"

# ── 執行 ──────────────────────────────────────────
if __name__ == "__main__":
    run_agent("台北天氣怎麼樣？然後幫我算 (88 + 12) * 5")