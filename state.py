from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 核心：自动拼接历史消息
    messages: Annotated[list, add_messages]
    
    # 辅助机制：记录重试次数，防止无限死循环
    retry_count: int
    
    # 辅助机制：记录上一次解析的报错信息，喂给大模型自我纠错
    error_log: str