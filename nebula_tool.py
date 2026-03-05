from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
import json
import traceback

class NebulaGraphTool:
    def __init__(self, space_name="military_space_v6", host="127.0.0.1", port=9669):
        print(f"🔌 初始化 NebulaGraph 探针连接 [{host}:{port}]...")
        self.config = Config()
        self.config.max_connection_pool_size = 5
        self.pool = ConnectionPool()
        self.pool.init([(host, port)], self.config)
        self.space_name = space_name

    def execute_query(self, query: str) -> str:
        """
        核心探针：接收 nGQL 语句，返回 JSON 格式的查询结果
        """
        session = self.pool.get_session('root', 'nebula')
        try:
            # 1. 强制检查空间切换是否成功
            use_resp = session.execute(f"USE {self.space_name}")
            if not use_resp.is_succeeded():
                return json.dumps({"status": "error", "error_msg": f"切入图谱空间失败: {use_resp.error_msg()}"})
            
            # 2. 执行核心战术查询
            resp = session.execute(query)
            
            # 3. 拦截数据库层面的拒绝
            if not resp.is_succeeded():
                return json.dumps({"status": "error", "error_msg": resp.error_msg()})
            
            if resp.is_empty():
                return json.dumps({"status": "success", "data": [], "msg": "查询成功，但未找到匹配数据。"})

            # 4. 正确的 Nebula3 客户端数据解析引擎
            results = []
            keys = resp.keys()
            
            # 遍历所有结果行
            for i in range(resp.row_size()):
                record = {}
                row_vals = resp.row_values(i) # 获取该行的所有封装值
                
                for j, key in enumerate(keys):
                    val = row_vals[j]
                    
                    # 安全解析各类数据格式
                    if val.is_empty() or val.is_null():
                        record[key] = None
                    elif val.is_string():
                        record[key] = val.as_string()
                    elif val.is_int():
                        record[key] = val.as_int()
                    elif val.is_double():
                        record[key] = val.as_double()
                    elif val.is_bool():
                        record[key] = val.as_bool()
                    else:
                        # 对于极其复杂的图谱原生结构（如 Node, Edge, Path），直接转为文本字符串
                        record[key] = str(val)
                        
                results.append(record)
                
            # ensure_ascii=False 保证中文字符不被转义
            return json.dumps({"status": "success", "data": results}, ensure_ascii=False)
            
        except Exception as e:
            # 开启上帝视角：打印完整的堆栈信息，绝不瞒报
            err_detail = traceback.format_exc()
            print(f"\n❌ [探针内部异常崩溃]\n{err_detail}")
            return json.dumps({"status": "error", "error_msg": f"{type(e).__name__}: {str(e)}"})
        finally:
            session.release()

# --- 简单测试代码 ---
if __name__ == "__main__":
    tool = NebulaGraphTool()
    # 战术测试：随机调取 3 架飞机的名字和最大起飞重量
    test_query = "MATCH (a:Aircraft) RETURN a.Aircraft.Name AS Name, a.Aircraft.WeightMax AS MaxWeight LIMIT 3;"
    print("📡 发送探测指令...")
    result = tool.execute_query(test_query)
    print("📦 返回结果:", result)