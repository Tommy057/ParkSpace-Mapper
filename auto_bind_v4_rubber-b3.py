import json
import math
import pandas as pd
import numpy as np
import re

# ================= 配置区域 =================
INPUT_JSON = '3dinfo.json'
INPUT_EXCEL = 'cad_b3.xlsx'
OUTPUT_JSON = 'scene_b3_final.json'
MATCH_THRESHOLD = 6000  # 依然保持较大的阈值，依靠唯一性算法来保证准确

# 🔴 核心：所有校准点 (越多越好，越准越好)
# 格式: [CAD_X, CAD_Y, 3D_X, 3D_Y]
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
    """ 计算基础仿射矩阵 """
    pts = np.array(points)
    A = np.c_[pts[:, 0], pts[:, 1], np.ones(len(pts))]
    B = pts[:, 2:4]
    M, _, _, _ = np.linalg.lstsq(A, B, rcond=None)
    return M

def get_rubber_sheet_correction(cad_x, cad_y, matrix, calib_pts):
    """
    【核心黑科技】橡皮膜局部校正算法 (IDW)
    1. 先用全局矩阵算出一个“大概位置”。
    2. 看看离哪个校准点近。
    3. 根据距离权重，把坐标用力“拽”向正确的方向。
    """
    # 1. 基础预测
    base_x = cad_x * matrix[0][0] + cad_y * matrix[1][0] + matrix[2][0]
    base_y = cad_x * matrix[0][1] + cad_y * matrix[1][1] + matrix[2][1]
    
    # 2. 计算每个校准点的“残差” (也就是这个区域偏了多少)
    # 残差 = 真实3D - 矩阵算出来的3D
    calib_arr = np.array(calib_pts)
    cad_calib = calib_arr[:, 0:2]
    real_3d_calib = calib_arr[:, 2:4]
    
    pred_3d_calib_x = cad_calib[:, 0] * matrix[0][0] + cad_calib[:, 1] * matrix[1][0] + matrix[2][0]
    pred_3d_calib_y = cad_calib[:, 0] * matrix[0][1] + cad_calib[:, 1] * matrix[1][1] + matrix[2][1]
    
    residuals_x = real_3d_calib[:, 0] - pred_3d_calib_x
    residuals_y = real_3d_calib[:, 1] - pred_3d_calib_y
    
    # 3. 计算当前点到所有校准点的距离
    dists = np.sqrt((cad_x - cad_calib[:, 0])**2 + (cad_y - cad_calib[:, 1])**2)
    
    # 4. 反距离加权 (IDW): 距离越近，权重越大 (Power=2)
    # 防止除以零
    dists[dists == 0] = 0.001 
    weights = 1.0 / (dists ** 2)
    weight_sum = np.sum(weights)
    
    # 5. 计算加权后的修正量
    correction_x = np.sum(residuals_x * weights) / weight_sum
    correction_y = np.sum(residuals_y * weights) / weight_sum
    
    return base_x + correction_x, base_y + correction_y

# --- 主程序 ---

print("1. 计算全局基准矩阵...")
M = calculate_affine_matrix(calibration_points)

print("2. 读取 Excel 并进行【橡皮膜非线性转换】...")
df = pd.read_excel(INPUT_EXCEL)
cad_list = [] 
cad_coords_arr = [] 

for idx, row in df.iterrows():
    raw_code = str(row['车位号']).strip()
    
    # === 关键变化：使用橡皮膜算法计算坐标 ===
    tx, ty = get_rubber_sheet_correction(row['X'], row['Y'], M, calibration_points)
    # ====================================
    
    final_tag = format_tag(raw_code)
    cad_list.append({'tag': final_tag, 'original': raw_code})
    cad_coords_arr.append([tx, ty])

cad_coords_arr = np.array(cad_coords_arr)
print(f"   已加载并校正 {len(cad_list)} 个车位点。")

print("3. 读取 3D 场景并提取车辆...")
with open(INPUT_JSON, 'r', encoding='utf-8') as f:
    scene_data = json.load(f)

nodes = scene_data.get('d', [])
car_nodes = [] 
car_coords_arr = []

for node in nodes:
    style = node.get('s', {})
    props = node.get('p', {})
    if 'Car0-62.json' in str(style.get('shape3d', '')):
        pos = props.get('position')
        if pos:
            car_nodes.append(node)
            car_coords_arr.append([pos['x'], pos['y']])

car_coords_arr = np.array(car_coords_arr)

# --- 核心算法：全局唯一最优匹配 ---
print("4. 开始全局唯一匹配 (解决错位/重复)...")

# 计算距离矩阵
diff = car_coords_arr[:, np.newaxis, :] - cad_coords_arr[np.newaxis, :, :]
dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))

matches = []
rows, cols = dist_matrix.shape
for r in range(rows):
    for c in range(cols):
        d = dist_matrix[r, c]
        if d < MATCH_THRESHOLD:
            matches.append((d, r, c))

print("   正在排序...")
matches.sort(key=lambda x: x[0])

used_cars = set()
used_spaces = set()
success_count = 0

print("   正在分配...")
for dist, car_idx, space_idx in matches:
    if car_idx in used_cars or space_idx in used_spaces:
        continue
    
    target_tag = cad_list[space_idx]['tag']
    car_node = car_nodes[car_idx]
    
    if 'p' not in car_node: car_node['p'] = {}
    car_node['p']['tag'] = target_tag
    
    used_cars.add(car_idx)
    used_spaces.add(space_idx)
    success_count += 1

print("-" * 30)
print(f"处理结果报告:")
print(f"成功绑定: {success_count} / {len(cad_list)}")

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(scene_data, f, ensure_ascii=False, indent=2)

print(f"新文件已生成: {OUTPUT_JSON}")

# ... (接在脚本最后) ...

# --- 导出未匹配名单 ---
if len(cad_list) - success_count > 0:
    print("\n正在生成未匹配清单...")
    unmatched_data = []
    
    # 遍历所有 CAD 数据，看谁的索引不在 used_spaces 集合里
    for i, item in enumerate(cad_list):
        if i not in used_spaces:
            unmatched_data.append({
                "车位号": item['original'],
                "原因": "未找到附近的3D模型",
                "理论3D坐标": f"{cad_coords_arr[i]}"
            })
            
    if unmatched_data:
        pd.DataFrame(unmatched_data).to_csv('missing_b3.csv', index=False, encoding='utf-8-sig')
        print(f"⚠️ 还有 {len(unmatched_data)} 个车位没匹配上，详情已保存到 'missing_b3.csv'，请核对。")