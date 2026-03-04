from pydantic import BaseModel, Field

# 定义军事装备提取的标准化格式
class WeaponInfo(BaseModel):
    """军事武器装备的核心数据模型"""
    name: str = Field(description="武器装备的正式名称，例如：歼-20")
    engine: str = Field(description="配套的发动机型号，例如：WS-15")
    max_range: str = Field(description="装备的最大射程或作战航程，需包含单位")

# 这种拆分确保了如果你未来需要增加“雷达”或“载弹量”字段，只需在此处修改