# Intake Parser Spec

## 职责
解析用户自然语言输入，检测意图、输入类型、提取关键参数

## API 接口

### POST /intake/parse
- 输入: IntakeRequest (user_request, files[], output_level)
- 输出: {context_id, detected_intent, input_type, parameters{unit, scale, dimensions[]}, missing_critical_info[], assumptions[]}

## 解析逻辑

### 意图检测
- 关键词匹配: draw/create/make/add → "create"
- edit/modify/change/update → "edit"
- open/load/read → "open"
- 默认 "unknown"

### 参数提取 (正则)
- 尺寸: (\d+)\s*x\s*(\d+) → width x height
- 直径: [Φφ](\d+) → diameter
- 半径: [Rr](\d+) → radius
- 角度: (\d+)° 或 (\d+)\s*度 → angle
- 单位: \d+\s*(mm|cm|m|inch|ft) → unit

### 文件检测
- 检查 files[] 中每个路径是否存在
- 按扩展名分类: .png/.jpg/.jpeg/.bmp → image; .pdf → pdf; .dwg → dwg
- 检测混合输入类型

## 输出
返回结构化上下文，包含提取的参数列表和缺失的关键信息提示
