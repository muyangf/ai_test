import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 核心开关
    PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    # 动态获取基础配置
    if PROVIDER == "minimax":
        MODEL_NAME = "minimax-m2.5:cloud"
        BASE_URL = os.getenv("MINIMAX_BASE_URL")
        API_KEY = os.getenv("MINIMAX_API_KEY")
    else:
        # 默认使用本地 Ollama
        MODEL_NAME = "minimax-m2.5:cloud" # 或者你下载的其他模型
        BASE_URL = os.getenv("OLLAMA_BASE_URL")
        API_KEY = "ollama" # Ollama 通常不需要真实 Key，但 ChatOpenAI 必须传一个非空值

    TEMPERATURE = 0
    MAX_RETRIES = 3

    @classmethod
    def validate(cls):
        if cls.PROVIDER == "minimax" and not cls.API_KEY:
            raise ValueError("❌ 切换至 MiniMax 模式失败：未检测到 MINIMAX_API_KEY")
        print(f"模式确认：当前正在使用 {'🏠 本地 Ollama' if cls.PROVIDER == 'ollama' else '☁️ 云端 MiniMax'}")