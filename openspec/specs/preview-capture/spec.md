# Preview Capture Spec

## 职责
通过 COM + OS 工具捕获 AutoCAD 视口截图，支持 PNG/PDF 导出

## API 接口

### POST /preview/screenshot
- 输入: {job_id, width: 1920, height: 1080, format: "png"|"jpg"}
- 行为: 通过 COM 控制 AutoCAD 缩放至全图 → 截图保存
- 输出: {preview_id, path, width, height, size_bytes}

### POST /preview/pdf
- 输入: {job_id, pages: "all"}
- 行为: 通过 COM Export 或 AutoCAD Plot 命令导出 PDF
- 输出: {path, size_bytes}

### GET /preview/{id}
- 返回预览文件路径

## 截图策略

### 首选方案: AutoCAD COM Export
- acad.ActiveDocument.GetInterfaceObject("IMAGING") 或
- acad.ZoomExtents() → acad.ActiveDocument.Export(path, "PNG", width, height)
- 要求: AutoCAD 支持 Export 命令

### 兜底方案: Windows 截图
- 通过 Windows API 定位 AutoCAD 窗口句柄
- SetWindowPos 设置视口大小
- PrintWindow / BitBlt 截图

## 输出约束
- 截图保存到 output/{job_id}/preview.{format}
- PDF 保存到 output/{job_id}/preview.pdf
- 文件路径返回给调用方
