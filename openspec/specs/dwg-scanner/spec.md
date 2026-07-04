# DWG Scanner Spec

## 职责
通过 COM 接口读取现有的 DWG 图纸信息，提取图层、实体、尺寸、块等元素

## API 接口

### POST /dwg/scan
- 输入: {path: string}
- 输出: {scan_id, summary{layer_count, entity_count, dim_count, block_count}, layers[], entities[], dimensions[], blocks[]}

### POST /dwg/edit
- 输入: {path: string, operations: [{type, params}]}
- 行为: 在现有 DWG 上执行修改操作
- 输出: {modified_entities, log}

### POST /dwg/find
- 输入: {path, query: {layer?, entity_type?, property?}}
- 行为: 查找符合条件的实体
- 输出: {matches[]}

## 扫描能力

### 图层信息
- 名称、颜色、线型、线宽、开/关状态、冻结/解冻

### 实体信息
- 类型、坐标、长度/面积、图层、句柄

### 尺寸标注
- 类型（对齐/线性/直径/半径/角度）、测量值、标注文字

### 块定义
- 块名称、插入点、属性

## 约束
- 只读操作不修改原图
- 大文件 (>10MB) 限制图层/实体返回数
- 通过 COM 遍历 ModelSpace / PaperSpace
