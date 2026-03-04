import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from schema import WeaponInfo
from config import Config
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.messages import AIMessage


# ⚠️ 注意：你可以把之前写的 class Route(BaseModel): 删掉了，我们不用它了


# ==========================================
# 2. 编写“前台总调度”条件边 (防弹版路由)
# ==========================================
async def router_edge(state):
    """根据用户输入，决定流程走向哪个节点"""
    print("🏢 [总指挥部] 正在分析用户意图，准备分发任务...")

    # 实例化一个最基础的纯文本模型
    model = ChatOpenAI(
        model=Config.MODEL_NAME,
        api_key=Config.API_KEY,
        base_url=Config.BASE_URL,
        temperature=0,  # 保证输出绝对稳定
    )

    system_prompt = """你是一个大型科技公司的前台总调度员（Supervisor）。
你的唯一工作是阅读用户最新发来的问题，并将其精确分配给最合适的专家部门。
- military：用户询问武器、战斗机、参数、机密文件等。
- sap：用户询问 SAP S/4HANA Public Cloud、业务蓝图(BBP)、采购类别等。
- pcb：用户询问 PCB 行业、电子元器件贸易、中小企业分包风险等。
- general：日常打招呼、或者以上都不符合的普通问题。

⚠️ 终极警告：你只能输出 "military", "sap", "pcb", "general" 这四个纯英文单词中的一个。绝对不允许输出任何其他多余的标点符号、解释或汉字！"""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # 直接调用模型，获取最原始的纯文本回复
    response = await model.ainvoke(messages)

    # 清理大模型可能不小心带上的空格或换行符
    decision = response.content.strip().lower()

    # 💡 终极防呆兜底：如果模型真的犯病输出了别的词，强制转接给前台
    valid_departments = ["military", "sap", "pcb", "general"]
    if decision not in valid_departments:
        print(f"⚠️ [警告] 模型输出了非法路由词: {decision}，已强制兜底到 general")
        decision = "general"

    print(f"🔀 [总指挥部] 判定完毕，将任务流转至: {decision} 部门")

    return decision


# 1. 建立 MCP 联合指挥中心
mcp_client = MultiServerMCPClient(
    {
        "military_skill_set": {
            "command": "uv",
            "args": ["run", "mcp_military_server.py"],
            "transport": "stdio",  # 👈 必须加上这一行通信协议声明
        }
    }
)


# --- 1. 先定义工具 (必须放在前面) ---
@tool
def query_weapon_database(weapon_name: str):
    """
    查询军事装备数据库，获取特定武器的详细技术参数。
    当用户询问武器的航程、发动机、生产商等具体数据时，请使用此工具。
    """
    # 这里我们先用模拟数据，下一阶段会替换为真正的 NebulaGraph 查询语句
    mock_db = {
        "歼-20": {
            "engine": "WS-15",
            "max_range": "5500km",
            "manufacturer": "成都飞机制造成员",
        },
        "F-22": {
            "engine": "F119-PW-100",
            "max_range": "2960km",
            "manufacturer": "洛克希德·马丁",
        },
    }

    # 模拟查询逻辑
    result = mock_db.get(weapon_name, "数据库中暂无该武器的详细记录。")
    return f"查询结果：{result}"


from langgraph.prebuilt import ToolNode


async def action(state):
    """工具执行节点"""
    # 同样需要获取包含 MCP 在内的所有工具
    mcp_tools = await mcp_client.get_tools()
    all_tools = [query_weapon_database] + mcp_tools

    # all_tools = [query_weapon_database]

    # 动态构建执行器并异步执行
    tool_executor = ToolNode(all_tools)
    return await tool_executor.ainvoke(state)


# 2. 注意前面加了 async 关键字
async def weapon_expert_node(state):
    """提取军事信息的专家节点 (已升级为 MCP 异步并发架构)"""
    print(f"🤖 专家正在处理 (重试次数: {state.get('retry_count', 0)})")

    # ================= 1. 新增：MCP 技能动态加载区 =================
    # 动态获取 MCP 服务提供的最新工具
    mcp_tools = await mcp_client.get_tools()

    # 将你的本地工具 (如 query_weapon_database) 和 MCP 工具混合编队
    all_tools = [query_weapon_database] + mcp_tools

    # 绑定工具，注意这里必须调用异步的 .ainvoke() 方法
    bound_model = ChatOpenAI(
        model=Config.MODEL_NAME,
        api_key=Config.API_KEY,
        base_url=Config.BASE_URL,
        temperature=Config.TEMPERATURE,
    ).bind_tools(all_tools)

    # ================= 2. 保留并升级核心业务逻辑 =================
    instructions = parser.get_format_instructions()

    # 终极防呆版 SOP 提示词
    system_prompt = f"""你是一个专业的军事装备数据提取专家。

【标准工作流】
第一阶段 - 情报侦察：如果需要查询特定武器参数，请优先调用工具 (如 read_weapon_spec 等) 获取机密资料。在调用工具时，请直接触发工具，不需要输出 JSON。

第二阶段 - 结构化汇报：获取到资料后，你必须从中提取真实数据，并严格组装成最终的 JSON 格式输出。
⚠️ 严厉警告：请直接输出包含真实提取数据的 JSON 实例（例如 {{"name": "歼-20", "engine": "涡扇-15", "max_range": "未知"}}），**绝对不允许**输出 JSON Schema 的定义规则！

【格式要求】
{instructions}"""

    # 如果有上轮报错信息，将其加入提示词进行修正
    if state.get("error_log"):
        system_prompt += f"\n\n⚠️ 纠错指令：上轮解析失败，原因是：{state['error_log']}。请务必核对键名和格式！"

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # ================= 3. 修改：使用异步方式调用模型 =================
    # 注意这里必须换成 ainvoke (异步调用)
    response = await bound_model.ainvoke(messages)
    # ==============================================================

    # 返回更新后的消息列表和重试计数 (逻辑完全保留)
    return {"messages": [response], "retry_count": state.get("retry_count", 0) + 1}


# ==========================================
# 3. 虚拟部门占位符 (用于测试路由)
# ==========================================


async def sap_expert_node(state):
    """SAP 实施部门"""
    print("🟢 [SAP实施部] 接收到请求，准备梳理蓝图...")
    reply = "你好！我是 SAP S/4HANA Public Cloud 实施顾问。我已经准备好协助你撰写业务蓝图（BBP）文档了。请问我们今天是先梳理物料主数据，还是直接讨论采购类别的标准流程配置？"
    return {"messages": [AIMessage(content=reply)]}


async def pcb_expert_node(state):
    """PCB 供应链风控部门"""
    print("🔵 [PCB风控部] 接收到请求，准备评估风险...")
    reply = "收到！我是 PCB 贸易风控专家。无论是评估中小企业分包商的产能，还是核对供应商的底层报价单，都可以交给我。请提供你需要查询的供应商名称或批次号。"
    return {"messages": [AIMessage(content=reply)]}


async def general_node(state):
    """前台闲聊与兜底部门"""
    print("⚪ [前台] 接收到普通对话...")
    reply = "你好！这里是科技公司智能中枢。我可以帮你转接军事装备资料库、SAP 实施顾问，或是 PCB 供应链风控专家。请问有什么可以帮您？"
    return {"messages": [AIMessage(content=reply)]}


parser = JsonOutputParser(pydantic_object=WeaponInfo)


def format_validator_edge(state):
    last_msg = state["messages"][-1]

    # 【核心逻辑】如果模型想调用工具，直接放行去工具节点，不要用 JSON 解析
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        print("🛠️ 检测到工具调用指令，准备跳转...")
        return "action"  # 跳转到新定义的工具处理节点

    # 只有当没有工具调用时，才进行 JSON 格式校验
    try:
        parser.parse(last_msg.content)
        print("✅ 最终格式校验通过")
        return "end"
    except Exception as e:
        print(f"❌ 校验失败: {e}")
        # 如果重试超过指定次数（3 次）则强行终止，防止死循环
        if state.get("retry_count", 0) >= Config.MAX_RETRIES:
            return "end"
        return "retry"
