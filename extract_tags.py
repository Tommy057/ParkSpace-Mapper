import json
import pandas as pd

# ================= 配置区域 =================
# 这里填入你那个包含手动绑定信息的 JSON 文件名
INPUT_JSON = 'B1F-3dinfo.json'  
# 输出结果文件名
OUTPUT_EXCEL = 'b1f-3d_benchmarks.xlsx' 
# ===========================================

print(f"正在读取文件: {INPUT_JSON} ...")

try:
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        scene_data = json.load(f)
except FileNotFoundError:
    print(f"❌ 错误: 找不到文件 {INPUT_JSON}，请确认文件名是否正确。")
    exit()

nodes = scene_data.get('d', [])
extracted_data = []

print("正在扫描带有 tag 的节点...")

for node in nodes:
    # 获取属性
    props = node.get('p', {})
    
    # 检查是否有 'tag' 属性
    # 注意：有时候 tag 是空的字符串，我们要排除掉
    tag = props.get('tag')
    
    if tag and str(tag).strip() != "":
        # 获取坐标
        pos = props.get('position', {})
        x = pos.get('x', 0)
        y = pos.get('y', 0)
        
        # 提取原始车位号 (去掉 car- 前缀，方便去 CAD 表里对账)
        # 假设格式是 "car-B3-0156"，我们尝试提取 "B3-156" 或原始编号
        # 这里不做强行处理，保留原 tag 方便你自己看
        
        extracted_data.append({
            'Tag (3D标签)': tag,
            '3D_X': x,
            '3D_Y': y,
            'Node_ID': node.get('i') # 节点的内部ID，备用
        })

if extracted_data:
    # 转为 DataFrame 并保存
    df = pd.DataFrame(extracted_data)
    
    # 按 Tag 排序，方便查看
    df.sort_values(by='Tag (3D标签)', inplace=True)
    
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"✅ 提取成功！")
    print(f"共提取到 {len(extracted_data)} 个基准点。")
    print(f"结果已保存为: {OUTPUT_EXCEL}")
    print("-" * 30)
    print("【接下来的操作建议】")
    print("1. 打开这个 Excel 表格。")
    print("2. 打开你之前的 CAD 坐标 Excel 表格。")
    print("3. 挑选 6-8 个分布在地图不同角落（左上、右下、中间、边缘）的点。")
    print("4. 将它们的 CAD坐标 和这里提取的 3D坐标 组合，填入 auto_bind 脚本的 calibration_points 列表里。")
else:
    print("⚠️ 警告: 在文件中没有找到任何带有 'tag' 属性的节点。")