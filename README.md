🏢 Enterprise Multi-Agent Routing System (企业级多智能体调度中枢)
基于 LangGraph 和 MCP (Model Context Protocol) 构建的高可扩展、具备人工审批机制的企业级 AI 智能体系统。

本系统不仅是一个简单的对话机器人，而是一个**“AI 操作系统”**。它拥有一个绝对理智的前台路由大脑（Router），能够根据用户意图，将任务精准分发给不同的“虚拟专家部门”（军工数据、SAP 实施、PCB 供应链风控），并在执行关键物理操作前触发人工断点审批（HITL）。

✨ 核心特性 (Core Features)
🔀 纯文本防弹路由 (Bulletproof Routing)：通过 temperature=0 的大模型进行严格的意图分类（降级策略），彻底杜绝 JSON 解析崩溃，确保高并发下的分发稳定性。

🔌 MCP 技能物理解耦 (Skill Decoupling)：采用外部独立运行的 MCP Server（如 mcp_military_server.py），实现 Agent 代码与底层数据源的物理隔离。未来接入数据库、API 或 ERP 系统，主控代码无需修改任何一行。

🛡️ 人工断点审批 (Human-in-the-Loop, HITL)：在执行核心业务（如修改数据库、发送拒收邮件、出具最终蓝图）前，系统将自动挂起（Interrupt），等待人类主管点击审批或修改上下文后方可继续。

⚕️ 自愈与重试防线 (Self-Correction)：内置 format_validator_edge，当模型输出格式错误或产生幻觉时，系统将携带错误日志（error_log）强制模型反思重写，并受最大重试次数（retry_count）严格保护，防止死循环。

📂 组织架构设计 (Architecture)
系统采用经典的**“星型网络 + 局部流水线”**的拓扑结构：

Plaintext
[用户输入] 
   │
   ▼
[ 🧠 Router 总调度台 ] ──(意图识别)──┐
   │                               │
   ├─▶ [ 🟢 SAP 实施部 ] ──────────┼─▶ (撰写 BBP 蓝图 / 查询采购类别) ──▶ [⏸️ 需人工审批] ──▶ 🏁 结束
   │                               │
   ├─▶ [ 🔵 PCB 风控部 ] ──────────┼─▶ (评估供应商产能 / 抓取底层报价) ──▶ [⏸️ 需人工审批] ──▶ 🏁 结束
   │                               │
   ├─▶ [ ⚪ 前台客服部 ] ──────────┼─▶ (闲聊兜底) ──▶ 🏁 结束
   │                               │
   └─▶ [ 🔴 军工情报部 ] ──────────┘
             │  ▲
             │  │ (循环防呆与修正)
             ▼  │
       [ 🔧 Action (MCP工具库) ] ──▶ (跨界读取物理机密文件) ──▶ [⏸️ 需人工审批]
📁 核心文件说明 (Project Structure)
graph.py: 系统的骨架定义，负责组装所有节点、画出路由条件边，并配置 Checkpointer 记忆体和人工审批断点。

nodes.py: 系统的肌肉，包含所有虚拟部门的具体业务逻辑（weapon_expert_node, sap_expert_node, pcb_expert_node）以及纯文本路由引擎 router_edge。

state.py: 系统的血液，定义了全局共享的状态数据结构（AgentState），解决循环导入问题。

mcp_military_server.py: 独立的 MCP 微服务，封装了 list_weapon_files 和 read_weapon_spec 等与本地文件系统交互的危险操作。

config.py: 核心配置文件，用于统一管理大模型配置（Base URL, Model Name）和环境变量。

🚀 快速启动 (Getting Started)
1. 环境准备
确保你的机器上已安装 Python 3.10+，并推荐使用 uv 进行极速环境管理。

Bash
# 克隆仓库
git clone https://github.com/你的用户名/ai_test.git
cd ai_test

# 配置你的 API Key (请勿将真实 Key 提交至 Git！)
# 建议在本地新建 .env 文件并填入：
# OPENAI_API_KEY="sk-xxxxxxx"
2. 启动服务 (LangGraph Studio)
本项目已完美适配 LangGraph Studio。直接运行开发脚本，它会自动拉起所有依赖并开启本地可视化调试界面。

Bash
chmod +x dev.sh
./dev.sh
3. 测试用例 (Test Cases)
在 Studio 的界面中开启 New Thread，尝试输入以下指令，观察任务如何在不同部门间流转：

测试军工与 MCP："去机密档案库里看看，现在都有哪些武器的说明书文件？"

测试 SAP 与断点："我们今天来写一下关于采购类别的标准流程 BBP"

测试 PCB 业务："有一批中小企业分包的板子，帮我查查供应商资质"

测试闲聊兜底："你好，你是谁？"

🔮 未来演进路线 (Roadmap)
[ ] 第四阶段: 通过 Docker 部署 NebulaGraph，替换现有的本地 txt 文件读取。

[ ] 第五阶段: 编写 mcp_nebulagraph_server.py，赋予 Agent 图谱深度推理（GraphRAG）能力。

[ ] 第六阶段: 接入真实的 ERP 接口，让 SAP 与 PCB 节点拥有真正的物理执行能力。

Developed by 濮阳科技指挥官