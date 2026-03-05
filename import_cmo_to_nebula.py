import sqlite3
import time
import re
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

# =====================================================================
# 🛠️ 核心防御与清洗模块
# =====================================================================
def clean_name(name):
    return name[4:] if name.startswith("Data") else name

def sanitize(value):
    """终极防化清洗：免疫一切语法崩溃"""
    if value is None: return '""'
    if isinstance(value, str): 
        safe_str = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
        return f'"{safe_str}"'
    return str(value)

def map_plantuml_type_to_nebula(p_type):
    p_type = p_type.lower()
    if p_type in ['integer', 'int']: return 'int'
    elif p_type in ['double', 'float']: return 'float'
    elif p_type == 'boolean': return 'bool'
    elif p_type == 'datetime': return 'datetime'
    else: return 'string'

def run_ngql(session, query, ignore_error=False):
    """带有雷达探针的执行函数"""
    resp = session.execute(query)
    if not resp.is_succeeded() and not ignore_error:
        print(f"\n❌ [致命错误] 图数据库拒绝了指令！")
        print(f"📄 错误详情: {resp.error_msg()}")
        print(f"🛑 拦截的 nGQL: {query[:250]}...")
        exit(1)
    return resp

# =====================================================================
# 🗺️ 全域绝对路由表 (剔除了 LoadoutWeapons 和 MagazineWeapons 留给特种行动)
# =====================================================================
EDGE_ROUTING_MAP = {
    "DataAircraftSensors": "aircraft_has_sensor", "DataShipSensors": "ship_has_sensor", "DataSubmarineSensors": "submarine_has_sensor", "DataGroundUnitSensors": "groundunit_has_sensor", "DataFacilitySensors": "facility_has_sensor", "DataSatelliteSensors": "satellite_has_sensor", "DataMountSensors": "mount_has_sensor", "DataWeaponSensors": "weapon_has_sensor", 
    "DataAircraftMounts": "aircraft_has_mount", "DataShipMounts": "ship_has_mount", "DataSubmarineMounts": "submarine_has_mount", "DataGroundUnitMounts": "groundunit_has_mount", "DataFacilityMounts": "facility_has_mount", "DataSatelliteMounts": "satellite_has_mount",
    "DataMountWeapons": "mount_can_fire", "DataWeaponWarheads": "weapon_has_warhead",
    "DataShipMagazines": "ship_has_magazine", "DataSubmarineMagazines": "submarine_has_magazine", "DataFacilityMagazines": "facility_has_magazine", "DataGroundUnitMagazines": "groundunit_has_magazine",
    "DataAircraftComms": "aircraft_has_comm", "DataShipComms": "ship_has_comm", "DataSubmarineComms": "submarine_has_comm", "DataGroundUnitComms": "groundunit_has_comm", "DataFacilityComms": "facility_has_comm", "DataSatelliteComms": "satellite_has_comm", "DataWeaponComms": "weapon_has_comm", "DataMountComms": "mount_has_comm",
    "DataShipAircraftFacilities": "ship_has_aircraft_facility", "DataFacilityAircraftFacilities": "facility_has_aircraft_facility", "DataSubmarineAircraftFacilities": "submarine_has_aircraft_facility", "DataGroundUnitAircraftFacilities": "groundunit_has_aircraft_facility",
    "DataShipDockingFacilities": "ship_has_docking_facility", "DataFacilityDockingFacilities": "facility_has_docking_facility", "DataSubmarineDockingFacilities": "submarine_has_docking_facility", "DataGroundUnitDockingFacilities": "groundunit_has_docking_facility",
    "DataAircraftPropulsion": "aircraft_has_propulsion", "DataShipPropulsion": "ship_has_propulsion", "DataSubmarinePropulsion": "submarine_has_propulsion", "DataGroundUnitPropulsion": "groundunit_has_propulsion", "DataWeaponPropulsion": "weapon_has_propulsion", "DataAircraftFuel": "aircraft_has_fuel", "DataShipFuel": "ship_has_fuel", "DataSubmarineFuel": "submarine_has_fuel", "DataGroundUnitFuel": "groundunit_has_fuel", "DataFacilityFuel": "facility_has_fuel", "DataWeaponFuel": "weapon_has_fuel",
    
    # 微观消耗品关联
    "DataAircraftSignatures": "aircraft_has_signature", "DataShipSignatures": "ship_has_signature", "DataSubmarineSignatures": "submarine_has_signature"
}

# =====================================================================
# ⚡ 阶段零：自动建立物理法则 (Schema)
# =====================================================================
def establish_schema(session, plantuml_path, tags):
    print("\n⚡ [阶段零] 正在自动解析 PlantUML 并颁布微观物理法则...")
    with open(plantuml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    class_pattern = re.compile(r"class\s+(\w+)\s*\{([^}]+)\}")
    table_props = {}
    for class_name, props_str in class_pattern.findall(content):
        props = []
        for prop_name, prop_type in re.findall(r"(\w+):\s*(\w+)", props_str):
            if prop_name.upper() in ['ID', 'COMPONENTID', 'COMPONENTNUMBER', 'COMMENTS']: continue
            props.append(f"`{prop_name}` {map_plantuml_type_to_nebula(prop_type)}")
        table_props[class_name] = props

    for tag in tags:
        # 如果 PlantUML 里没找到（比如某些隐秘的微观表），提供基础兜底字段
        props_str = ", ".join(table_props.get(tag, ["`Name` string"]))
        run_ngql(session, f"CREATE TAG IF NOT EXISTS `{clean_name(tag)}`({props_str});")
    
    for table_name, edge_name in EDGE_ROUTING_MAP.items():
        props_str = ", ".join(table_props.get(table_name, []))
        if props_str:
            run_ngql(session, f"CREATE EDGE IF NOT EXISTS `{edge_name}`({props_str});")
        else:
            run_ngql(session, f"CREATE EDGE IF NOT EXISTS `{edge_name}`();")
                
    # 🎯 特别创建：带有载弹量属性的两大挂载/弹药边
    run_ngql(session, "CREATE EDGE IF NOT EXISTS `loadout_contains`(DefaultLoad int, MaxLoad int, Optional bool, Internal bool);")
    run_ngql(session, "CREATE EDGE IF NOT EXISTS `magazine_contains_weapon`(Quantity int);")
    
    print("⏳ 法则颁布完毕，等待 NebulaGraph 集群元数据同步 (10秒)...")
    time.sleep(10)

# =====================================================================
# 🚀 引擎主控程序
# =====================================================================
def pump_data(sqlite_path, plantuml_path, space_name):
    print("🔌 连接 NebulaGraph 物理引擎 (127.0.0.1:9669)...")
    config = Config()
    config.max_connection_pool_size = 10
    pool = ConnectionPool()
    pool.init([('127.0.0.1', 9669)], config)
    session = pool.get_session('root', 'nebula')
    
    print(f"\n🌌 正在开辟军工宇宙微观层面 [{space_name}]...")
    run_ngql(session, f"CREATE SPACE IF NOT EXISTS {space_name} (partition_num=10, replica_factor=1, vid_type=fixed_string(64));")
    time.sleep(15) 
    run_ngql(session, f'USE {space_name}')

    # 满编微观实体定义 (新增诱饵、声呐、雷达反射截面积)
    target_entities = {
        "DataAircraft": "ID, Name, Length, Span, Height, WeightEmpty, WeightMax, Crew, Agility, ClimbRate",
        "DataWeapon": "ID, Name, Type, Length, Span, Diameter, Weight, AirRangeMax, SurfaceRangeMax",
        "DataSensor": "ID, Name, Type, RangeMax, MaxContactsAir",
        "DataGroundUnit": "ID, Name, Category, Length, Width, Mass, Crew, DamagePoints",
        "DataSatellite": "ID, Name, Category, Type, Length, Span, Height, WeightEmpty, DamagePoints",
        "DataPropulsion": "ID, Name, Type, NumberOfEngines, ThrustPerEngineMilitary, SFCMilitary",
        "DataFuel": "ID, Type, Capacity",
        "DataShip": "ID, Name, Category, Type, Length, Beam, Draft, DisplacementFull, Crew, DamagePoints",
        "DataSubmarine": "ID, Name, Category, Type, Length, Beam, Draft, DisplacementFull, Crew, MaxDepth, DamagePoints",
        "DataFacility": "ID, Name, Category, Type, DamagePoints",
        "DataLoadout": "ID, Name, LoadoutRole, DefaultCombatRadius",
        "DataMount": "ID, Name, Capacity, DamagePoints",
        "DataMagazine": "ID, Name, Capacity",
        "DataWarhead": "ID, Name, Type, DamagePoints",
        "DataComm": "ID, Name, Type, Range",
        "DataAircraftFacility": "ID, Type, Capacity",
        "DataDockingFacility": "ID, Type, Capacity",
        
        # 🌊 V6 微观深潜新增
        "DataChaff": "ID, Name",
        "DataFlare": "ID, Name",
        "DataDecoy": "ID, Name",
        "DataSonobuoy": "ID, Name",
        "DataSignature": "ID, Name"
    }
    
    establish_schema(session, plantuml_path, list(target_entities.keys()))

    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # 4. 阶段一：全域+微观实体注入
    for table, columns in target_entities.items():
        tag_name = clean_name(table)
        print(f"🚀 提取 [{table}] -> 泵入图谱 [{tag_name}]...")
        
        # 🛡️ 动态探测机制：如果表不存在，静默跳过（兼容不同版本的 DB3K）
        try:
            cursor.execute(f"SELECT {columns} FROM {table}")
        except sqlite3.OperationalError:
            print(f"⚠️ 数据库中未找到表 {table}，自动跳过。")
            continue
            
        batch_size = 100
        count = 0
        col_names = [c.strip() for c in columns.split(",")]
        ngql_prefix = f"INSERT VERTEX `{tag_name}`({', '.join(col_names[1:])}) VALUES "
        values_list = []
        
        for row in cursor.fetchall():
            vid = f"{tag_name}_{row[0]}"
            props = ", ".join([sanitize(val) for val in row[1:]])
            values_list.append(f'"{vid}":({props})')
            count += 1
            if count % batch_size == 0:
                run_ngql(session, ngql_prefix + ", ".join(values_list) + ";")
                values_list = []
        if values_list: run_ngql(session, ngql_prefix + ", ".join(values_list) + ";")
        print(f"✅ [{tag_name}] 注入完成: {count} 条。")

    # 5. 阶段二：常规网络注入
    print("\n🕸️ 开始编织海陆空天电常规网络...")
    for rel_table, edge_name in EDGE_ROUTING_MAP.items():
        # 推断目标表
        tgt_table = "DataUnknown"
        for key in ["Sensors", "Mounts", "Warheads", "Magazines", "Comms", "AircraftFacilities", "DockingFacilities", "Propulsion", "Fuel", "Signatures"]:
            if key in rel_table: 
                tgt_table = f"Data{key[:-1]}" if key.endswith("s") and key not in ["Comms"] else f"Data{key}"
                if key == "Comms": tgt_table = "DataComm"
                break
        
        src_table = rel_table.replace(tgt_table[4:] + "s", "").replace(tgt_table[4:], "")
        
        src_tag, tgt_tag = clean_name(src_table), clean_name(tgt_table)
        print(f"🔗 打线: {src_tag} -[{edge_name}]-> {tgt_tag} (忽略部分极微观缺失表)")
        
        try:
            cursor.execute(f"SELECT ID, ComponentID FROM {rel_table}")
            count = 0
            batch_size = 200
            ngql_prefix = f"INSERT EDGE `{edge_name}`() VALUES "
            values_list = []
            
            for row in cursor.fetchall():
                src_vid, tgt_vid = f"{src_tag}_{row[0]}", f"{tgt_tag}_{row[1]}"
                values_list.append(f'"{src_vid}"->"{tgt_vid}":()')
                count += 1
                if count % batch_size == 0:
                    run_ngql(session, ngql_prefix + ", ".join(values_list) + ";")
                    values_list = []
            if values_list: run_ngql(session, ngql_prefix + ", ".join(values_list) + ";")
        except sqlite3.OperationalError:
            pass

    # 6. 阶段三：🎯 特种行动 1 & 2 (极致穿透)
    print("\n🎯 [特种行动 1] 穿透 WeaponRecord 解析战机真实挂载方案...")
    try:
        cursor.execute("SELECT lw.ID, wr.ComponentID, wr.DefaultLoad, wr.MaxLoad, lw.Optional, lw.Internal FROM DataLoadoutWeapons lw JOIN DataWeaponRecord wr ON lw.ComponentID = wr.ID")
        count, values_list = 0, []
        for row in cursor.fetchall():
            values_list.append(f'"Loadout_{row[0]}"->"Weapon_{row[1]}":({row[2] or 0}, {row[3] or 0}, {"true" if row[4] else "false"}, {"true" if row[5] else "false"})')
            count += 1
            if count % 200 == 0:
                run_ngql(session, f"INSERT EDGE `loadout_contains`(DefaultLoad, MaxLoad, Optional, Internal) VALUES {', '.join(values_list)};")
                values_list = []
        if values_list: run_ngql(session, f"INSERT EDGE `loadout_contains`(DefaultLoad, MaxLoad, Optional, Internal) VALUES {', '.join(values_list)};")
        print(f"✅ [特种行动 1] 战机挂载网络打通: 共 {count} 条。")
    except Exception as e: print(f"⚠️ 特种行动 1 失败: {e}")

    print("\n🎯 [特种行动 2] 穿透弹药库 (MagazineWeapons) 提取真实备弹数量...")
    try:
        # 动态探测数量列名 (可能是 MaxLoad 也可能是 Quantity)
        cursor.execute("PRAGMA table_info(DataMagazineWeapons)")
        cols = [row[1] for row in cursor.fetchall()]
        qty_col = "MaxLoad" if "MaxLoad" in cols else ("Quantity" if "Quantity" in cols else "1")
        
        cursor.execute(f"SELECT ID, ComponentID, {qty_col} FROM DataMagazineWeapons")
        count, values_list = 0, []
        for row in cursor.fetchall():
            qty = row[2] if row[2] is not None else 1
            values_list.append(f'"Magazine_{row[0]}"->"Weapon_{row[1]}":({qty})')
            count += 1
            if count % 200 == 0:
                run_ngql(session, f"INSERT EDGE `magazine_contains_weapon`(Quantity) VALUES {', '.join(values_list)};")
                values_list = []
        if values_list: run_ngql(session, f"INSERT EDGE `magazine_contains_weapon`(Quantity) VALUES {', '.join(values_list)};")
        print(f"✅ [特种行动 2] 军舰弹药库容量打通: 共 {count} 条。")
    except Exception as e: print(f"⚠️ 特种行动 2 失败: {e}")

    # 7. 终极收尾：建立倒排索引
    print("\n🔍 正在为微观实体建立战术倒排索引...")
    for tag in ["Aircraft", "Weapon", "Sensor", "Ship", "Submarine", "Loadout", "Magazine", "Chaff", "Flare"]:
        run_ngql(session, f"CREATE TAG INDEX IF NOT EXISTS idx_{tag.lower()} ON {tag}();", ignore_error=True)
    time.sleep(5)
    for tag in ["Aircraft", "Weapon", "Sensor", "Ship", "Submarine", "Loadout", "Magazine", "Chaff", "Flare"]:
        run_ngql(session, f"REBUILD TAG INDEX idx_{tag.lower()};", ignore_error=True)

    conn.close()
    pool.close()
    print("\n🎉 V6 深潜微观宇宙构建完毕！AI 大脑现在掌握了从宏观编排到单枚诱饵弹抛射的绝对算力！")

if __name__ == "__main__":
    pump_data("DB3K_512.db3", "Capabilities.plantuml", "military_space_v6")