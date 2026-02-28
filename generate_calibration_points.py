import pandas as pd
import re
import math

# ================= 配置区域 =================
CAD_FILE = 'cad_b2.xlsx'           # CAD 坐标表 (B2层)
HT_3D_FILE = 'b2f-3d_benchmarks.xlsx'  # 3D 坐标表 (刚才提取的已绑定点)
OUTPUT_FILE = 'b2_benchmarks.txt' # 结果输出到这个文本文件

# 你希望生成多少个基准点？
# 如果想用全部 152 个点，就把这里改成 9999
NUM_POINTS_TO_GENERATE = 30  
# ===========================================

print("1. 正在读取数据...")
df_cad = pd.read_excel(CAD_FILE)
df_3d = pd.read_excel(HT_3D_FILE)

# 构建 3D 查找字典
map_3d = {}
for idx, row in df_3d.iterrows():
    raw_tag = str(row.get('Tag (3D标签)', '')).strip()
    if not raw_tag: continue
    
    # 清洗逻辑：car-B2-0090 -> B2-0090
    clean_tag = raw_tag.replace('car-', '') 
    map_3d[clean_tag] = [row['3D_X'], row['3D_Y']]
    
    # 兼容逻辑：处理前导0 (比如 CAD是 B2-90，3D是 B2-0090)
    # 尝试去掉数字前的0
    parts = clean_tag.split('-')
    if len(parts) >= 2:
        try:
            area = parts[0]
            num = int(re.search(r'\d+', parts[-1]).group())
            no_zero_tag = f"{area}-{num}" # B2-90
            map_3d[no_zero_tag] = [row['3D_X'], row['3D_Y']]
        except:
            pass

print(f"   3D 数据索引构建完成，有效数据: {len(map_3d)} 条")

# 遍历 CAD 寻找匹配
matched_pairs = []
for idx, row in df_cad.iterrows():
    cad_code = str(row['车位号']).strip()
    # 尝试匹配
    if cad_code in map_3d:
        p3d = map_3d[cad_code]
        matched_pairs.append([row['X'], row['Y'], p3d[0], p3d[1], cad_code])

total_matches = len(matched_pairs)
print(f"2. 共成功匹配到 {total_matches} 对坐标。")

if total_matches < 4:
    print("❌ 匹配数量过少，无法生成有效基准点。请检查表格中的车位号格式是否一致。")
    exit()

# 智能筛选逻辑
points_selected = []

if NUM_POINTS_TO_GENERATE >= total_matches:
    print("   已选择所有匹配点作为基准点。")
    points_selected = matched_pairs
else:
    print(f"   正在从 {total_matches} 个点中筛选分布最均匀的 {NUM_POINTS_TO_GENERATE} 个点...")
    # 1. 先把最边缘的4个点（上下左右）拿出来，保证地图边界不塌陷
    # 按X排序取头尾
    matched_pairs.sort(key=lambda x: x[0]) 
    points_selected.append(matched_pairs[0])
    points_selected.append(matched_pairs[-1])
    
    # 按Y排序取头尾
    matched_pairs.sort(key=lambda x: x[1])
    points_selected.append(matched_pairs[0])
    points_selected.append(matched_pairs[-1])
    
    # 去重
    points_unique = []
    seen = set()
    for p in points_selected:
        if p[4] not in seen:
            points_unique.append(p)
            seen.add(p[4])
    points_selected = points_unique

    # 2. 从剩下的点里，等间距抽取
    remaining = [p for p in matched_pairs if p[4] not in seen]
    
    # 为了保证空间分布均匀，我们可以简单地按列表索引等距抽取
    # (因为刚才按Y排序过，所以等距抽取大约等于在Y轴上均匀分布)
    needed = NUM_POINTS_TO_GENERATE - len(points_selected)
    if needed > 0 and len(remaining) > 0:
        step = max(1, len(remaining) // needed)
        for i in range(0, len(remaining), step):
            if len(points_selected) < NUM_POINTS_TO_GENERATE:
                points_selected.append(remaining[i])

# 生成文本内容
print("3. 正在生成代码文件...")
output_content = []
output_content.append(f"# 🔴 B2层 自动生成的基准点列表 (共 {len(points_selected)} 个)")
output_content.append("# 直接复制下面的内容替换 auto_bind 脚本里的 calibration_points")
output_content.append("calibration_points = [")

for p in points_selected:
    # 格式对齐，方便阅读
    line = f"    [{p[0]:.3f}, {p[1]:.3f},  {p[2]:.5f}, {p[3]:.5f}], # {p[4]}"
    output_content.append(line)

output_content.append("]")

# 写入文件
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_content))

print(f"✅ 成功！请打开文件: 【 {OUTPUT_FILE} 】 复制里面的代码。")