# mcp_military_server.py
from mcp.server.fastmcp import FastMCP
import os

# 1. 初始化 MCP 服务
mcp = FastMCP("Military_Data_Center")

# 定义一个存放军事说明书的路径
DOCS_PATH = "./military_docs"
os.makedirs(DOCS_PATH, exist_ok=True)

# 2. 注册一个“搜索文件”的工具
@mcp.tool()
def list_weapon_files() -> list[str]:
    """列出当前数据库中所有的武器说明书文件名称。"""
    return os.listdir(DOCS_PATH)

# 3. 注册一个“读取参数”的工具
@mcp.tool()
def read_weapon_spec(file_name: str) -> str:
    """读取特定武器说明书的详细文本内容。"""
    safe_path = os.path.join(DOCS_PATH, os.path.basename(file_name))
    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()