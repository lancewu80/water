比較Acer Nitro AN515及Acer Predator Helios Neo 16在玩3A遊戲跟AI LLM運算時的適合度分析

用 Claude Code 快速跑起來
你有 Claude Code，可以這樣做：
步驟一： 在終端機輸入
bashpip install anthropic
export ANTHROPIC_API_KEY="你的金鑰"
步驟二： 把上面的程式碼存成 agent.py，然後請 Claude Code 幫你：
幫我執行 agent.py，然後加一個「搜尋網路」的工具

接下來可以加的功能
功能怎麼做記憶把 messages 存到 JSON 檔，下次讀進來更多工具加函式定義 + 在 execute_tool 裡實作多 Agent一個 Agent 呼叫另一個 Agent 當作工具RAG工具裡加向量搜尋（用 ChromaDB 或 Pinecone）
這份 Job Description 主要在找熟悉這個完整架構的人。上面這個範例就是最核心的骨架，Job 裡提到的 LangChain、LlamaIndex 其實都是在幫你把這些東西包裝好。先搞懂手刻版，框架就很容易理解了！

Gemini API Key:
https://aistudio.google.com/api-keys


Step 1：安裝套件
# 後端
pip install chromadb python-docx PyMuPDF

# 拉取 Embedding 模型（只需一次，約 274 MB）
ollama pull nomic-embed-text

# 前端
cd frontend
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-link