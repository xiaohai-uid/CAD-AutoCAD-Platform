# Design: 9 Microservices Implementation

## Overall Architecture

Each service is an independent FastAPI process with its own uvicorn instance. Gateway acts as the synchronous orchestrator.

### Service startup command pattern
```bash
cd D:/Projects/cad-direct-control-platform
.venv/Scripts/python.exe -m services.{name}.main
```

### File structure per service
```
services/{name}/
├── __init__.py
├── main.py          # FastAPI app, routes, uvicorn entry
└── engine.py        # Core business logic (new for real impl)
```

## Engine Modules (new files)

### 1. Gateway engine — `services/gateway/engine.py`

#### OrchestratorEngine
- `create_job_workflow(req: CreateJobRequest) -> JobResponse`
  Synchronous orchestration:
  1. Call Intake → parse result
  2. If has files → call Vision (image) or DWG Scan (dwg)
  3. Call CADPlan → get plan
  4. Call Validation → get validation result
  5. If blocking_questions → return await_confirmation
  6. Else → call CAD COM execute → save → Preview → Artifacts
- Uses `httpx.AsyncClient`, timeout 60s
- All errors captured as ErrorResponse

#### JobStore (in-memory dict)

### 2. Intake engine — `services/intake/engine.py`

#### IntakeEngine
- `parse(raw_text, files, output_level)` → structured context
- Regex extraction: dimensions (WxH), diameter (Φ), radius (R), angle, unit
- Keyword intent classification (draw/create/edit/open)
- File type and existence validation

### 3. Vision engine — `services/vision/engine.py`

#### VisionEngine
- OpenCV pipeline:
  1. Grayscale → GaussianBlur → Canny
  2. HoughLinesP line detection
  3. HoughCircles circle detection
  4. findContours + approxPolyDP rectangle/polygon
- All pixel sizes marked `estimated: true`
- Confidence < 0.5 filtered out
- PDF support: pdf2image → PNG then analyze

### 4. CADPlan engine — `services/cadplan/engine.py`

#### PlanGenerator
- `generate(user_request, vision_analysis, output_level, unit)` → Plan JSON
- Rule layer:
  - Rectangle: 4-point closed polyline from WxH
  - Circle: center + radius
  - Line: start + end point
  - Layer assignment: 轮廓线(7 white), 中心线(1 red), 标注(3 green), 填充(8 gray)
- Inherit geometry from vision results
- Uncertain values → assumptions
- Output: layers[], entities[], dimensions[], texts[]

### 5. Validation engine — `services/validation/engine.py`

#### ValidationEngine
- 4 check categories:
  - Completeness: entity count, layer count, required fields
  - Consistency: unit consistency, dimension non-contradiction
  - Executability: coordinate range, radius>0, width>0
  - professional_dwg: full dimensions, title, scale info
- Returns blocking_questions + non_blocking_warnings

### 6. CAD COM engine — `services/cad_com/engine.py`

#### CadComEngine (wraps cad_controller.py logic)
- `connect()` → GetActiveObject("AutoCAD.Application")
- `new_drawing()` → Documents.Add()
- `open_drawing(path)` → Documents.Open(path)
- `execute_plan(plan)` → iterate entities, call COM methods
- `save(path)` → SaveAs(path)
- `ensure_layer(name, color, lineweight)` → Layers.Add()
- `disconnect()` → cleanup

Entity-by-entity execution, failures logged and continued.

### 7. Preview engine — `services/preview/engine.py`

#### PreviewEngine
- `screenshot(job_id, width, height, format)`:
  1. COM: ZoomExtents()
  2. COM: ActiveDocument.Export(path, format)
  3. Fallback: Windows PrintWindow API
- `export_pdf(job_id)`:
  1. COM Plot.PlotToFile(path) or SendCommand "-PLOT"

### 8. DWG Scan engine — `services/dwg_scan/engine.py`

#### DwgScanEngine
- `scan(path)`: iterate ModelSpace entities via COM
- `find(path, query)`: filter by layer/type/property
- `edit(path, operations)`: limited modification

### 9. Artifacts engine — `services/artifacts/engine.py`

#### ArtifactManager
- SQLite database: `output/artifacts.db`
- `store(job_id, files)`: copy files + write metadata
- `get(job_id)`: query 4-piece artifact set
- File streaming: FastAPI FileResponse
