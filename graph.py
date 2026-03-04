from langgraph.graph import StateGraph, START, END
from state import AgentState  # 假设你的状态定义文件叫 state.py，请按实际情况修改
from langgraph.checkpoint.memory import MemorySaver

# 导入你写好的所有部门和边
from nodes import (
    weapon_expert_node,
    action,
    format_validator_edge,
    router_edge,  # 👈 新引入的路由总机
    sap_expert_node,  # 👈 新增部门
    pcb_expert_node,  # 👈 新增部门
    general_node,  # 👈 新增部门
)

workflow = StateGraph(AgentState)

# ================= 1. 注册公司的所有"部门" =================
workflow.add_node("military_expert", weapon_expert_node)
workflow.add_node("action", action)  # 这是军事部专属的 MCP 工具房
workflow.add_node("sap_expert", sap_expert_node)
workflow.add_node("pcb_expert", pcb_expert_node)
workflow.add_node("general", general_node)

# ================= 2. 核心架构：大门一进来的星型路由分发 =================
# 用户的话刚进来(START)，立刻交给 router_edge 进行条件判断
workflow.add_conditional_edges(
    START,
    router_edge,
    {
        "military": "military_expert",  # 如果 router 返回 "military"，就去军工部
        "sap": "sap_expert",  # 去 SAP 部
        "pcb": "pcb_expert",  # 去 PCB 部
        "general": "general",  # 去前台兜底
    },
)

# ================= 3. 军事部门的内部流转 (保留你原来的神级防呆逻辑) =================
workflow.add_conditional_edges(
    "military_expert",
    format_validator_edge,
    {"action": "action", "retry": "military_expert", "end": END},
)
# 工具执行完，带着机密文件退回给军事专家
workflow.add_edge("action", "military_expert")

# ================= 4. 其他部门处理完直接下班 =================
workflow.add_edge("sap_expert", END)
workflow.add_edge("pcb_expert", END)
workflow.add_edge("general", END)

# =================================================================
# 5. 终极编译：利用 Studio 自带记忆，仅保留人工审批断点 (HITL)
# =================================================================

# ⚠️ 注意：删除了之前写的 memory = MemorySaver() 以及开头的 import

# 编译成最终的超级智能体 (去掉了 checkpointer 参数)
app = workflow.compile(
    interrupt_before=[
        "action",       # 军事部：在真正去读取机密文件/数据库前，必须审批
        "sap_expert",   # SAP部：在出具 BBP 蓝图前，必须审批
        "pcb_expert"    # PCB部：在执行风控评估前，必须审批
    ]
)