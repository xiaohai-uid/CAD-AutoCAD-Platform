# Artifact Manager Spec

## 职责
管理 CAD 任务产出的四件套文件（DWG、预览、日志、假设清单）的存储、查询和归档

## API 接口

### GET /artifacts/{job_id}
- 返回: {job_id, status, created_at, completed_at, artifacts: {dwg, preview, log, assumptions}}

### GET /artifacts/{job_id}/dwg
- 返回 DWG 文件（流式下载）

### GET /artifacts/{job_id}/preview
- 返回预览图片（流式下载）

### GET /artifacts/{job_id}/log
- 返回 JSONL 格式的执行日志

### GET /artifacts/{job_id}/assumptions
- 返回假设清单 JSON

### POST /artifacts/store
- 输入: {job_id, files: {dwg_path?, preview_path?, log_content?, assumptions}}
- 行为: 将文件复制到归档目录，记录元数据到 SQLite
- 输出: ArtifactList

## 存储结构

```
output/
└── {job_id}/
    ├── drawing.dwg
    ├── preview.png
    ├── plan.json
    ├── log.jsonl
    └── assumptions.json
```

## 元数据 SQLite

### artifacts 表
- job_id (TEXT PRIMARY KEY)
- status (TEXT)
- created_at (TEXT)
- completed_at (TEXT)
- dwg_path (TEXT)
- dwg_size (INTEGER)
- preview_path (TEXT)
- preview_size (INTEGER)
- log_path (TEXT)
- assumptions (TEXT JSON)

## 约束
- 文件操作通过 shutil.copy2 保持元数据
- SQLite 自动创建
- 设置 .gitkeep 保持目录结构
