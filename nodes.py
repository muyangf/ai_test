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


async def action(state):
    """工具执行节点"""
    mcp_tools = await mcp_client.get_tools()
    all_tools = mcp_tools  # 👈 只使用 MCP 提供的真实探针

    tool_executor = ToolNode(all_tools)
    return await tool_executor.ainvoke(state)


from langgraph.prebuilt import ToolNode


async def weapon_expert_node(state):
    """提取军事信息的专家节点 (搭载图谱法则)"""
    print(f"🤖 军工图谱专家正在推演 (重试次数: {state.get('retry_count', 0)})")

    mcp_tools = await mcp_client.get_tools()
    all_tools = mcp_tools

    bound_model = ChatOpenAI(
        model=Config.MODEL_NAME,
        api_key=Config.API_KEY,
        base_url=Config.BASE_URL,
        temperature=0.1, # 降低温度以保证 nGQL 语法严谨
    ).bind_tools(all_tools)

    instructions = parser.get_format_instructions()

    system_prompt = f"""你是一个顶级的军事装备情报官和图数据库专家。
你现在连接着一个极度详尽的 NebulaGraph 军工图谱数据库。

【军工图谱物理法则 (Schema)】
1. 核心实体节点 (TAG):
   - Aircraft (飞机): Name, WeightMax, Length...
   - Weapon (武器): Name, Type, AirRangeMax...
   - Sensor (雷达/传感器): Name, RangeMax...
   - Loadout (战术挂载方案): Name...
   - Magazine (弹药库): Name, Capacity...

2. 核心战术连线 (EDGE):
   - aircraft_has_sensor: Aircraft -> Sensor (战机自带雷达)
   - aircraft_can_equip: Aircraft -> Loadout (战机可用的挂载方案)
   - loadout_contains: Loadout -> Weapon (挂载方案包含的武器，连线上有 DefaultLoad 和 MaxLoad 属性，代表携弹量！)
   - magazine_contains_weapon: Magazine -> Weapon (弹药库里的武器，连线上有 Quantity 属性，代表备弹数！)

【你的核心任务】
第一阶段 - 情报侦察：只要用户询问武器参数、飞机雷达、战机携弹量等，你必须调用 `execute_ngql` 工具，编写 nGQL (MATCH) 语句去查询数据库。不需要输出 JSON，直接调用工具！

💡 nGQL 编写指南 (极度重要)：
- 查飞机：`MATCH (a:Aircraft) WHERE a.Aircraft.Name CONTAINS "F-22" RETURN a.Aircraft.Name LIMIT 5;`
- 查飞机的挂载武器和携弹量 (联表穿透)：`MATCH (a:Aircraft)-[:aircraft_can_equip]->(l:Loadout)-[e:loadout_contains]->(w:Weapon) WHERE a.Aircraft.Name CONTAINS "F-22" RETURN l.Loadout.Name, w.Weapon.Name, e.MaxLoad LIMIT 10;`

第二阶段 - 结构化汇报：工具返回结果后，你必须从中提取真实数据，组装成 JSON 格式输出给用户。
⚠️ 严厉警告：绝对不允许输出 JSON Schema 定义规则，直接输出真实的 JSON 实例！

【最终输出格式要求】
{instructions}"""

    if state.get("error_log"):
        system_prompt += f"\n\n⚠️ 纠错指令：上轮执行失败，原因是：{state['error_log']}。如果是 nGQL 语法错误，请检查你的 MATCH 语句并重试！"

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await bound_model.ainvoke(messages)
    
    return {"messages": [response], "retry_count": state.get("retry_count", 0) + 1}
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

    # 🌟 终极图谱注入版 SOP 提示词 (Text2nGQL)
    system_prompt = f"""你是一个顶级的军事装备情报官和图数据库专家。
你现在连接着一个极度详尽的 NebulaGraph 军工图谱数据库。

【图谱物理法则 (Schema)】
1. 核心实体节点 (TAG):
   - Aircraft (飞机): 属性有 Name, WeightMax, Length, Crew 等。
   - Weapon (武器): 属性有 Name, Type, AirRangeMax, SurfaceRangeMax 等。
   - Sensor (雷达/传感器): 属性有 Name, RangeMax 等。
   - Loadout (战术挂载方案): 属性有 Name, DefaultCombatRadius 等。
   - Magazine (弹药库): 属性有 Name, Capacity。

2. 核心关系连线 (EDGE):
   - aircraft_has_sensor: Aircraft -> Sensor (飞机自带雷达)
   - aircraft_can_equip: Aircraft -> Loadout (飞机可用的挂载方案)
   - loadout_contains: Loadout -> Weapon (挂载方案包含的武器，连线上有 DefaultLoad 和 MaxLoad 属性代表携弹量！)
   - magazine_contains_weapon: Magazine -> Weapon (弹药库里的武器，连线上有 Quantity 属性代表数量！)

【你的核心任务】
第一阶段 - 情报侦察：如果用户询问某款武器的参数、飞机的雷达、或者战机的携弹量，你必须调用 `execute_ngql` 工具，并编写 nGQL (MATCH) 语句去查询数据库。

💡 nGQL 编写指南 (极度重要)：
- 查询节点：`MATCH (a:Aircraft) WHERE a.Aircraft.Name CONTAINS "F-22" RETURN a.Aircraft.Name, a.Aircraft.WeightMax LIMIT 5;`
- 查询飞机挂载的武器及数量 (联表穿透)：`MATCH (a:Aircraft)-[:aircraft_can_equip]->(l:Loadout)-[e:loadout_contains]->(w:Weapon) WHERE a.Aircraft.Name CONTAINS "F-22" RETURN l.Loadout.Name, w.Weapon.Name, e.MaxLoad LIMIT 10;`

第二阶段 - 结构化汇报：获取到资料后，请将其提取并组装成 JSON 格式输出给用户。
⚠️ 严厉警告：绝对不允许输出 JSON Schema 的定义规则，直接输出真实的 JSON 实例！

【格式要求】
{instructions}"""

    # 如果有上轮报错信息，将其加入提示词进行修正
    if state.get("error_log"):
        system_prompt += f"\n\n⚠️ 纠错指令：上轮执行失败，原因是：{state['error_log']}。如果是 nGQL 语法错误，请检查你的 MATCH 语句并重试！"
    # ... 后面的代码保持不变 ...

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
