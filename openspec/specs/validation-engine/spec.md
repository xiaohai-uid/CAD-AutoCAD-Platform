# Validation Engine Spec

## 职责
校验 CAD 计划的完整性、一致性、可执行性，生成 blocking/non-blocking 问题列表

## API 接口

### POST /validation/plan
- 输入: {plan_id, output_level, unit}
- 输出: {valid: bool, blocking_questions[], non_blocking_warnings[], suggestions[], assumptions[]}

## 校验规则

### 1. 完整性检查
- 是否有至少 1 个 entity？
- 每个 entity 是否指定了 layer？
- 每个 layer 是否指定了 color？
- 每个 dimension 是否关联了 entity？

### 2. 一致性检查
- 单位是否一致？（不允许 mm 和 inch 混用）
- 尺寸是否相互矛盾？（如长边 < 短边）
- 标注值是否匹配实际几何尺寸？

### 3. 可执行性检查
- entity 坐标是否在合理范围内？
- 圆半径 > 0？
- 矩形宽高 > 0？

### 4. professional_dwg 级别额外检查
- 是否有完整的标注？
- 是否有标题/图号？
- 是否有图层命名规范？
- 是否有比例信息？

## Blocking vs Non-blocking

| 类型 | 处理方式 |
|------|----------|
| blocking | 必须用户确认后才能继续 |
| non-blocking | 记录到假设清单，不阻塞流程 |

## 输出
blocking_questions 格式: {id, category, question, options[], default_value}
