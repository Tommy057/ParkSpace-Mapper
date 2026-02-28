import json
import math
import pandas as pd
import numpy as np
import re

# ================= 配置区域 =================
INPUT_JSON = '3dinfo.json'
INPUT_EXCEL = 'cad_b3.xlsx'
OUTPUT_JSON = 'scene_b3_final.json'
MATCH_THRESHOLD = 2500  # 稍微放宽阈值，因为我们会强制唯一匹配，不怕远处的乱绑

# 依然使用你提供的 6 组基准点（这组数据质量很高）
calibration_points = [
     # --- 基础点 (第一批) ---
    [6084153.455, -5342646.161,  13340.50353,   7464.22598], # B3-951
    [5854176.642, -5217641.498,  -9647.69673,  -5045.46429], # B3-156
    [6087865.955, -5322993.258,  13868.90533,   5196.91495], # B3-943
    [6012889.17,  -5277791.473,   6237.34532,    514.21583], # B3-742
    [5910717.651, -5246893.283,  -3837.73584,  -2404.88871], # B3-393
    [5848175.858, -5210141.482, -10236.43322,  -6256.55963], # B3-145
    
    # --- 修正点 (第二批) ---
    [6016190.144, -5342659.482,   6561.95759,   7464.22598], # B3-973
    [5960016.928, -5314939.798,    577.76146,   4394.59561], # B3-870

    # --- 关键修正点 (第三批 - 专门解决错位) ---
    # 修复 850/851 区域错位
    [5985253.799, -5326946.161,   3450.40661,   5889.87693], # 实际 B3-851
    # 修复 315/316 区域错位
    [5939922.121, -5320688.154,  -1087.19746,   4802.29062], # 实际 B3-316
    # 修复 108/107 区域错位
    [5853266.863, -5315177.103,  -9572.02764,   4394.48833], # 实际 B3-107
    # 修复 093/034 大偏差区域
    [5836201.599, -5327699.462, -11221.38297,   5778.17912]  # 实际 B3-034
]
# ===========================================

def format_tag(original_code):
    """ 格式化标签：B3-156 -> car-B3-0156 """
    try:
        parts = original_code.strip().split('-')
        if len(parts) >= 2:
            area = parts[0]
            number_str = parts[-1]
            number_val = int(re.search(r'\d+', number_str).group())
            return f"car-{area}-{number_val:04d}"
        else:
            return f"car-{original_code}"
    except:
        return f"car-{original_code}"

def calculate_affine_matrix(points):
    pts = np.array(points)
    A = np.c_[pts[:, 0], pts[:, 1], np.ones(len(pts))]
    B = pts[:, 2:4]
    M, _, _, _ = np.linalg.lstsq(A, B, rcond=None)
    return M

# --- 主程序 ---

print("1. 计算坐标转换矩阵...")
M = calculate_affine_matrix(calibration_points)

print("2. 读取 Excel 并进行坐标转换...")
df = pd.read_excel(INPUT_EXCEL)
cad_list = [] # 存放: {'tag': '...', 'pos': [x, y]}
cad_coords_arr = [] # 纯坐标数组，用于矩阵计算

for idx, row in df.iterrows():
    raw_code = str(row['车位号']).strip()
    # 坐标转换
    cx, cy = row['X'], row['Y']
    tx = cx * M[0][0] + cy * M[1][0] + M[2][0]
    ty = cx * M[0][1] + cy * M[1][1] + M[2][1]
    
    final_tag = format_tag(raw_code)
    cad_list.append({'tag': final_tag, 'original': raw_code})
    cad_coords_arr.append([tx, ty])

cad_coords_arr = np.array(cad_coords_arr) # 转为 numpy 数组
print(f"   已加载 {len(cad_list)} 个 CAD 车位点。")

print("3. 读取 3D 场景并提取车辆...")
with open(INPUT_JSON, 'r', encoding='utf-8') as f:
    scene_data = json.load(f)

nodes = scene_data.get('d', [])
car_nodes = [] # 存放: {'node': 引用, 'pos': [x, y]}
car_coords_arr = []

for node in nodes:
    style = node.get('s', {})
    props = node.get('p', {})
    # 判定是否为车
    if 'Car0-62.json' in str(style.get('shape3d', '')):
        pos = props.get('position')
        if pos:
            car_nodes.append(node)
            car_coords_arr.append([pos['x'], pos['y']])

car_coords_arr = np.array(car_coords_arr)
print(f"   已提取 {len(car_nodes)} 辆 3D 小车。")

# --- 核心算法：全局唯一最优匹配 ---
print("4. 开始全局最优匹配运算 (这可能需要几秒钟)...")

# 计算距离矩阵：行是车，列是车位
# dist_matrix[i][j] 代表 第i辆车 到 第j个车位 的距离
# 手动广播计算距离，避免依赖 scipy
diff = car_coords_arr[:, np.newaxis, :] - cad_coords_arr[np.newaxis, :, :]
dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))

# 将矩阵展平为 (距离, 车索引, 车位索引) 的列表
# 这一步是为了排序
matches = []
rows, cols = dist_matrix.shape
for r in range(rows):
    for c in range(cols):
        d = dist_matrix[r, c]
        if d < MATCH_THRESHOLD:
            matches.append((d, r, c))

# 按距离从小到大排序
print("   正在排序...")
matches.sort(key=lambda x: x[0])

# 开始分配
used_cars = set()
used_spaces = set()
success_count = 0
duplicate_prevention = 0

print("   正在分配唯一标签...")
for dist, car_idx, space_idx in matches:
    # 如果这辆车已经有主了，或者这个车位已经用掉了，就跳过
    if car_idx in used_cars or space_idx in used_spaces:
        continue
    
    # 执行绑定
    target_tag = cad_list[space_idx]['tag']
    car_node = car_nodes[car_idx]
    
    # 写入 JSON
    if 'p' not in car_node: car_node['p'] = {}
    car_node['p']['tag'] = target_tag
    
    # 标记为已占用
    used_cars.add(car_idx)
    used_spaces.add(space_idx)
    success_count += 1

print("-" * 30)
print(f"处理结果报告:")
print(f"CAD车位总数: {len(cad_list)}")
print(f"3D车辆总数:  {len(car_nodes)}")
print(f"成功唯一绑定: {success_count}")
print(f"未匹配车辆数: {len(car_nodes) - success_count}")
print(f"未匹配车位数: {len(cad_list) - success_count}")

# 5. 保存结果
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(scene_data, f, ensure_ascii=False, indent=2)

print(f"新文件已生成: {OUTPUT_JSON}")