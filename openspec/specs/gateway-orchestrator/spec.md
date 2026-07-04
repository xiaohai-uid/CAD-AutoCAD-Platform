# Gateway Orchestrator Spec

## 职责
Job CRUD + 11 步工作流同步编排 + 下游服务级联调用 + 假设/确认管理

## API 接口

### POST /job/create
- 输入: CreateJobRequest (intent, input_type, user_request, files, output_level, declared_unit)
- 输出: JobResponse (job_id, status=created, next_action, assumptions[], questions[])
- 行为: 创建 Job → 调用 Intake → 如有文件调用 Vision → 调用 CADPlan → 调用 Validation

### GET /job/{job_id}
- 返回当前 Job 状态

### POST /job/{job_id}/confirm
- 输入: ConfirmRequest (confirmations dict)
- 行为: 记录确认 → 更新 plan → 调用 Validation 重新校验 → 如 ready 则进入执行

### POST /job/{job_id}/execute
- 行为: 调用 CAD COM (连接 → 新建图纸 → 执行计划 → 保存) → 调用 Preview → 调用 Artifacts

### GET /job/{job_id}/artifacts
- 返回四件套: DWG, 预览, 日志, 假设清单

### GET /health
- 健康检查

### GET /routes
- 返回所有路由和下游服务地址

## 工作流状态机

```
created → intake_pending → [vision_pending] → plan_pending → validation_pending
→ [awaiting_confirmation → validation_pending] → executing → saving
→ preview_pending → archiving → completed
```

## 错误处理
- 任何下游服务失败: 返回 ErrorResponse，Job 状态置为 error
- 下游服务不可达 (ConnectionError): HTTP 503
- Job 不存在: HTTP 404
