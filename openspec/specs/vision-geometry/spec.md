# Vision Geometry Spec

## 职责
对图片/PDF 进行几何要素检测，识别基本图形元素并估算尺寸

## API 接口

### POST /vision/analyze/image
- 输入: {path: string}
- 输出: {analysis_id, detected_geometry[], image_dimensions{width, height, unit}, processing_time_ms}

### POST /vision/analyze/pdf
- 输入: {path: string, page?: number}
- 输出: 同上 + pages[]

### GET /vision/analysis/{id}
- 返回已存储的分析结果

## 检测能力 (OpenCV)

### 直线检测
- Canny 边缘检测 + HoughLinesP
- 输出: {type: "line", confidence, geometry: {start_point, end_point}, estimated_length, estimated_unit: "pixel"}

### 圆检测
- HoughCircles
- 输出: {type: "circle", confidence, geometry: {center, radius}, estimated_diameter}

### 矩形检测
- findContours + approxPolyDP (4 顶点)
- 输出: {type: "rectangle", confidence, geometry: {corner1, corner2, width, height}}

### 弧检测
- 轮廓拟合
- 输出: {type: "arc", confidence, geometry: {center, radius, start_angle, end_angle}}

## 约束
- 所有尺寸标记 `estimated: true`
- 置信度 < 0.5 的结果不返回
- 像素尺寸不可作为最终制造尺寸
