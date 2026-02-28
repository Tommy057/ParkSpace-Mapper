# Digital Twin Coordinate Mapper (数字孪生坐标映射工具)

## 📖 Introduction (简介)
A high-precision automated solution for mapping 2D CAD coordinates to 3D WebGL scenes (e.g., Hightopo). It solves the problem of **non-linear distortion** between architectural drawings and 3D models using the **Rubber Sheeting (IDW)** algorithm.

一套用于将 2D CAD 图纸坐标高精度映射到 3D WebGL 场景（如 HT for Web）的自动化解决方案。通过引入**橡皮膜算法 (IDW插值)**，完美解决了 CAD 图纸与 3D 模型之间因非线性形变导致的点位错位问题。

## 🚀 Key Features (核心特性)

*   **AutoLISP Extraction**: Batch extract text coordinates from AutoCAD efficiently.
    *   支持 AutoCAD 批量提取车位/设备坐标。
*   **Rubber Sheeting Algorithm**: Uses IDW (Inverse Distance Weighting) to correct local non-linear distortions.
    *   **橡皮膜算法纠偏**：通过局部加权插值，自动修复模型局部拉伸、位移导致的错位。
*   **Global Unique Matching**: Solves duplicate binding and adjacent displacement using distance sorting.
    *   **全局唯一匹配**：防止多车抢一位，自动纠正相邻车位错位。
*   **Self-Calibration**: Generates high-quality calibration points from existing manual bindings.
    *   **自适应校准**：利用少量已绑定数据反向生成全局基准点，实现“越用越准”。

## 🛠️ Prerequisites (环境要求)

*   Python 3.10+
*   AutoCAD (for LISP execution)
*   Libraries: `pandas`, `numpy`, `scipy`, `openpyxl`

```bash
pip install -r requirements.txt
