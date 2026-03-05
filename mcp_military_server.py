from mcp.server.fastmcp import FastMCP
from nebula_tool import NebulaGraphTool  # 引入我们写好的探针

# 1. 初始化 MCP 服务
mcp = FastMCP("Military_Graph_Center")

# 2. 实例化 Nebula 探针 (连接到 V6 满编宇宙)
graph_tool = NebulaGraphTool(space_name="military_space_v6")

# 3. 注册“图谱查询”超级工具
@mcp.tool()
def execute_ngql(query: str) -> str:
    """
    执行 nGQL 语句查询军工图谱数据库。
    你必须传入标准的 nGQL MATCH 语句。
    例如: MATCH (a:Aircraft) WHERE a.Aircraft.Name == "F-22A Raptor" RETURN a;
    """
    print(f"📡 [MCP探针] 正在执行 nGQL: {query}")
    return graph_tool.execute_query(query)

if __name__ == "__main__":
    mcp.run()