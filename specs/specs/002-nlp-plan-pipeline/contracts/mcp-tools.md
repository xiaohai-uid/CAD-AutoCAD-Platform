
---

# Contract v2.1 增补（002-nlp-plan-pipeline，+7 工具）

### cad_parse_text
`{text}` → `{intent, entities[], unit, missing[], text}`（FR-8 正则库，确定性）
### cad_plan
`{text, origin?[x,y], scale?=1}` → `{plan}`（parse+布局假设生成完整 Plan；assumptions 必填至少一条或空数组说明无假设）
### cad_validate_plan
`{plan}` → `{issues:[{severity,category,code,message,location?}], pass:bool}`（四类校验）
### cad_execute_plan
`{plan}` → OperationResult（批量落图+真标注；assumptions/warnings 透传进 data；存在 error 级 issue 时拒绝执行并内联返回 validate 结果）
### cad_init_sheet
`{template?="gb-mech", size?="A4", title_block?=true, origin?=[10,10]}` → `{layers_created[], frame_handle?, tb_handles[]}` 幂等
### cad_import_image_geometry
`{path, scale?=1, origin?=[0,0], min_confidence?=0.5}` → `{items:[create_batch items], detections:{lines,circles,rects}}`；无 opencv → MISSING_DEP
### cad_scan_dwg
`{path, sample?=20}` → `{total, by_type:{}, layers[], sample[]}`；FILE_NOT_FOUND 错误码新增
