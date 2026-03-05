from pydantic import BaseModel, Field
from typing import List, Dict, Any

class WeaponInfo(BaseModel):
    """军事武器装备的动态战术数据模型"""
    summary: str = Field(description="对用户提问的精简自然语言回答与战术总结")
    tactical_data: List[Dict[str, Any]] = Field(description="从图数据库中提取出的具体结构化数据记录（如查到的武器列表、参数、最大携弹量等）")