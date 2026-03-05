🦅 Military Knowledge Graph Agent (军工图谱智能决策中枢)
本项目是一个基于 LangGraph 和 MCP (Model Context Protocol) 架构构建的本地化军工战术推演智能体。系统底层依托 NebulaGraph 分布式图数据库，深度重构了现代海空战（基于 CMO / DB3K）的底层数据逻辑，使大语言模型（LLM）能够通过自然语言执行复杂的兵棋推演与微观战术查询。

✨ 核心特性
🔒 极致安全与本地化：大脑由本地 Ollama (如 Qwen3.5) 驱动，数据存放在本地 NebulaGraph 中，彻底阻断敏感军工数据外泄。

🕸️ 全域微观图谱引擎 (V6 满编版)：

将传统关系型军工数据（SQLite）进行“降维打击”，转化为高效的图结构。

涵盖实体：战机、军舰、潜艇、武器、雷达、消耗品（诱饵/声呐）、航空设施等。

深度穿透逻辑：运用 SQL JOIN 将“战术挂载方案 (Loadout)”与“弹药库 (Magazine)”的真实携弹量/备弹数提取为连线属性，支持微观算力推演。

🧠 LangGraph 智能路由与反思：

构建了包含 military、sap、pcb 多业务线的前台总调度 (Supervisor) 路由节点。

具备 自我纠错能力 (Self-Correction)：当生成的图查询语句 (nGQL) 报错时，智能体会读取报错日志并自动重试。

🔌 MCP 标准化探针接入：通过 Model Context Protocol 将图数据库查询能力 (NebulaGraphTool) 封装为标准服务，实现 LLM 与图谱的“神经接驳”。

🏗️ 系统架构与核心文件
import_cmo_to_nebula.py：图谱创世引擎（数据注射泵）。负责自动解析 PlantUML 法则、建立 NebulaGraph Schema、执行数据清洗（防 f-string/换行符崩溃）并泵入千万级微观数据。

nebula_tool.py：图数据库数据探针。安全解析图谱原生数据结构并转化为 JSON，内置全景报错雷达。

mcp_military_server.py：MCP 服务端。将图数据库探针包装为大模型可调用的标准 Tool。

nodes.py & graph.py & state.py：LangGraph 智能体核心逻辑。包含前台意图识别路由、图谱法则 (Schema) 的系统提示词注入、以及 Text2nGQL 的转换与提取。

schema.py：基于 Pydantic 的大模型动态输出结构化约束。

🚀 快速启动
1. 基础设施准备
确保已安装并启动 NebulaGraph (默认 127.0.0.1:9669)。

确保已安装并启动本地大模型服务 (如 Ollama + Qwen3.5)。

2. 构建军工图谱宇宙
确保 DB3K_512.db3 和 Capabilities.plantuml 在项目根目录，然后执行数据注射：

Bash
python import_cmo_to_nebula.py
(系统将自动创建 military_space_v6 空间并建立全部节点、边与倒排索引)

3. 启动 MCP 服务与 Agent
MCP 服务端与 LangGraph 客户端已配置为联合指挥中心，直接运行入口程序即可发起自然语言问询：

Bash
# 示例提问："帮我查一下 F-22A Raptor 战斗机能挂载什么武器？请列出它的挂载方案、武器名称及对应的最大携弹量。"
🎯 战术查询示例 (Text2nGQL)
得益于图谱的深度建模，AI Agent 目前可以直接推理并生成如下高阶 nGQL：

Cypher
# 查询 F-22A 的挂载网络及具体携弹量 (MaxLoad)
MATCH (a:Aircraft)-[:aircraft_can_equip]->(l:Loadout)-[e:loadout_contains]->(w:Weapon) 
WHERE a.Aircraft.Name CONTAINS "F-22" 
RETURN l.Loadout.Name, w.Weapon.Name, e.MaxLoad LIMIT 20;
📈 未来战略路线
[ ] 接入动态运动学数据 (Kinetics) 以支持飞行包线计算。

[ ] 开发战术可视化 UI 面板 (Streamlit / Gradio)。

[ ] 激活多轮战术推演的短期与长期记忆 (Memory Context)。