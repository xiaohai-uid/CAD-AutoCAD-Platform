# CAD COM Executor Spec

## 职责
通过 Windows COM 接口连接 AutoCAD 2026，执行绘图计划、管理文档、保存输出

## API 接口

### POST /cad/connect
- 行为: 连接正在运行的 AutoCAD (win32com.client.GetActiveObject)
- 输出: {connected: bool, version: string, document_count: int}

### POST /cad/new-drawing
- 行为: 创建新图纸
- 输出: {drawing_name: string, drawing_path: string}

### POST /cad/open
- 输入: {path: string}
- 行为: 打开已有 DWG
- 输出: {drawing_name: string}

### GET /cad/status
- 输出: 当前 AutoCAD 状态（已连接、当前文档、修改状态）

### POST /cad/execute-plan
- 输入: {plan: PlanJSON, job_id: string}
- 行为: 依次执行 plan 中的每个 entity，创建图层、绘制实体、添加标注
- 输出: {executed: int, failed: int, log: string[]}

### POST /cad/save
- 输入: {path: string}
- 行为: 保存 DWG 到指定路径
- 输出: {path: string, size_bytes: int}

### POST /cad/layer/ensure
- 输入: {name, color, lineweight}
- 行为: 创建或确保图层存在

### POST /cad/disconnect
- 断开 COM 连接（清理资源）

## COM 操作映射

| Plan Entity | COM 方法 |
|-------------|----------|
| line | ModelSpace.AddLine(start, end) |
| circle | ModelSpace.AddCircle(center, radius) |
| arc | ModelSpace.AddArc(center, radius, startAngle, endAngle) |
| rectangle | ModelSpace.AddPolyline(4 points, closed) |
| polyline | ModelSpace.AddPolyline(points) |
| text | ModelSpace.AddText(text, insertion, height) |
| dimension | ModelSpace.AddDimAligned/AddDimRotated |
| layer | Layers.Add(name), .color, .lineweight |

## 错误处理
- AutoCAD 未运行: HTTP 503
- COM 超时: HTTP 504
- 绘图命令失败: 记录到 log 继续执行下一条
