# CADPlan Generator Spec

## 职责

接收用户请求 + 视觉分析结果 + DWG 扫描结果，生成结构化的 CAD 执行计划

## API 接口

### POST /cadplan/draft
- 输入: PlanRequest (user_request, vision_analysis_id?, dwg_scan_id?, output_level, unit)
- 输出: {plan_id, layers[], entities[], dimensions[], texts[], assumptions[], warnings[]}

### POST /cadplan/finalize
- 输入: {plan_id, confirmations: {}}
- 输出: 最终的 Plan JSON（已解决所有假设）

## Plan JSON 结构

### layers
```json
{"name": "轮廓线", "color": "7", "lineweight": 0.5, "description": "main outline"}
```

### entities
```json
{
  "type": "line|circle|arc|rectangle|polyline",
  "params": {"start_point": [0,0,0], "end_point": [100,0,0]},
  "layer": "轮廓线",
  "depends_on": []
}
```

### dimensions
```json
{"type": "aligned|linear|diameter|radius", "point1": [0,0], "point2": [100,0], "text": "100"}
```

## 生成策略

### 规则层 (Rule-based)
- 从 user_request 中提取的尺寸参数直接映射到实体
- 常见形状模板识别: 矩形、圆孔、阵列
- 图层自动分配: 轮廓线、中心线、标注、填充

### LLM 辅助点
- 复杂几何布局、标注策略、图层配色方案作为 "assumptions" 标记
- Validation 会针对 assumptions 提问

## 输出约束
- 所有尺寸带 unit 标注
- 每个 entity 必须指定 layer
- 坐标系: AutoCAD WCS (World Coordinate System)
