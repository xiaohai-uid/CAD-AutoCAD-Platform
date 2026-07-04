# 9 Engine Implementation Design

> Date: 2026-07-03
> Status: Draft
> Project: cad-direct-control-platform

## Architecture

Each microservice gets an `engine.py` with core business logic. Services remain independent FastAPI processes; their `main.py` routes call into `engine.py` functions. Gateway orchestrates the 11-step workflow via `httpx` calls to downstream services.

```
User Request
  │
  ▼
[Gateway] ─── httpx ───→ [Intake]     port 8001
  │                       [Vision]     port 8002  (if image/pdf)
  │                       [DWG Scan]   port 8007  (if dwg)
  │                       [CADPlan]    port 8003
  │                       [Validation] port 8004
  │                       [CAD COM]    port 8005
  │                       [Preview]    port 8006
  │
  └──────────────────────→ [Artifacts] port 8008
```

## 1. IntakeEngine — `services/intake/engine.py`

### Interface
```python
@dataclass
class ParsedContext:
    intent: str               # "create" | "edit" | "unknown"
    input_type: InputType
    dimensions: dict | None   # {width, height, diameter, radius, angle}
    unit: str                 # extracted or default "mm"
    description: str          # cleaned request text
    files_valid: bool
    needs_more_info: bool

def parse(raw_text: str, files: list[str], output_level: OutputLevel) -> ParsedContext
```

### Capabilities
- **Regex extraction**: `(\d+)\s*[xX×]\s*(\d+)` → width×height; `Φ(\d+)` → diameter; `R(\d+)` → radius; `(\d+)°` → angle
- **Intent classification**: keyword-based (draw/create/make/add → "create"; edit/modify/change → "edit")
- **File validation**: check file paths exist, type matches (image/pdf/dwg)
- **Unit detection**: "mm" / "cm" / "m" / "inch" in text, fallback to declared_unit

### Error handling
- Word count < 3 → `needs_more_info: True` with question list
- Invalid file path → `files_valid: False`
- No dimension match → `dimensions: None`

## 2. VisionEngine — `services/vision/engine.py`

### Interface
```python
@dataclass
class DetectedLine:
    x1, y1, x2, y2: float
    length: float
    angle: float
    confidence: float

@dataclass
class DetectedCircle:
    cx, cy, radius: float
    confidence: float

@dataclass
class DetectedRect:
    x, y, width, height: float
    confidence: float

@dataclass
class VisionResult:
    lines: list[DetectedLine]
    circles: list[DetectedCircle]
    rects: list[DetectedRect]
    image_width: int
    image_height: int
    success: bool
    error: str | None

def analyze(image_path: str) -> VisionResult
```

### Pipeline (OpenCV)
1. **Grayscale** → `cv2.cvtColor`
2. **GaussianBlur** → `cv2.GaussianBlur(kernel=5)`
3. **Canny** → `cv2.Canny(threshold1=50, threshold2=150)`
4. **HoughLinesP** → line detection (rho=1, theta=π/180, threshold=50)
5. **HoughCircles** → circle detection (dp=1.2, minDist=20)
6. **findContours + approxPolyDP** → rectangle/polygon detection

### Constraints
- All pixel sizes marked `confidence < 1.0` as `estimated: true`
- Confidence < 0.5 filtered out
- PDF support via `pdf2image` → PNG → analyze

### Error handling
- File not found → `success: False, error: "File not found"`
- No shapes detected → empty lists, `success: True`

## 3. CADPlanEngine — `services/cadplan/engine.py`

### Interface
```python
@dataclass
class PlanEntity:
    type: str            # "line" | "circle" | "arc" | "polyline" | "rectangle" | "text"
    params: dict         # type-specific geometry
    layer: str           # target layer name
    color: int | None    # AutoCAD color index

@dataclass
class PlanLayer:
    name: str
    color: int           # AutoCAD color index
    description: str

@dataclass
class PlanDimension:
    type: str            # "aligned" | "linear"
    start: tuple         # (x, y)
    end: tuple
    text_position: tuple | None

@dataclass
class Plan:
    layers: list[PlanLayer]
    entities: list[PlanEntity]
    dimensions: list[PlanDimension]
    texts: list[dict]
    assumptions: list[dict]   # uncertain values recorded here

def generate(user_request: str, vision_result: VisionResult | None,
             output_level: OutputLevel, unit: str) -> Plan
```

### Layer Rules
| Layer | Color | Purpose |
|-------|-------|---------|
| 轮廓线 | 7 (white) | Main outlines |
| 中心线 | 1 (red) | Center lines |
| 标注 | 3 (green) | Dimensions |
| 填充 | 8 (gray) | Hatch/fill |
| 文字 | 2 (yellow) | Text annotations |

### Entity Generation Rules
- **Rectangle**: from `width × height` → 4-point closed polyline
- **Circle**: from radius → center + radius
- **Line**: from start/end points
- Inherit geometry from vision results when available
- Uncertain values → record in assumptions list

### Output level
- `sketch`: minimal layers, no dimensions
- `professional_dwg`: all 5 layers, dimensions, scale info

## 4. ValidationEngine — `services/validation/engine.py`

### Interface
```python
@dataclass
class ValidationIssue:
    category: str        # "completeness" | "consistency" | "executability" | "professional"
    severity: str        # "blocking" | "warning"
    message: str
    field: str | None

@dataclass
class ValidationResult:
    valid: bool
    blocking_questions: list[str]
    non_blocking_warnings: list[str]
    issues: list[ValidationIssue]

def validate(plan: Plan, output_level: OutputLevel, unit: str) -> ValidationResult
```

### 4 Check Categories
1. **Completeness**: entity count > 0? layer count sufficient? all required fields present?
2. **Consistency**: unit consistent across entities? dimensions non-contradictory?
3. **Executability**: coordinates within range? radius > 0? width > 0? height > 0?
4. **Professional** (professional_dwg only): full dimensions present? title block? scale info?

### Error handling
- Empty plan → blocking "No entities to draw"
- Invalid geometry → blocking "Radius must be > 0"

## 5. CadComEngine — `services/cad_com/engine.py`

### Interface
```python
@dataclass
class ExecutionResult:
    success: bool
    entity_count: int
    failed_entities: int
    errors: list[str]
    drawing_path: str | None

def connect() -> bool
def new_drawing() -> bool
def open_drawing(path: str) -> bool
def execute_plan(plan: Plan) -> ExecutionResult
def save(path: str) -> bool
def zoom_extents() -> bool
def disconnect()
```

### Wraps `cad_mcp_bridge/cad_controller.py`
- `connect()` → `CADController()` → `start_cad()`
- `execute_plan(plan)` → iterate entities → call `draw_line`/`draw_circle`/etc.
- Entity-by-entity execution: failures logged and continued (don't abort on single entity error)
- `save(path)` → `save_drawing(file_path)`

### Error handling
- COM not available → `success: False` with error message
- Entity drawing fails → log, increment `failed_entities`, continue

## 6. PreviewEngine — `services/preview/engine.py`

### Interface
```python
@dataclass
class PreviewResult:
    success: bool
    file_path: str | None
    format: str
    error: str | None

def screenshot(job_id: str, width: int = 1920, height: int = 1080,
               format: str = "png") -> PreviewResult
def export_pdf(job_id: str) -> PreviewResult
```

### Methods
1. **screenshot**: ZoomExtents → Export PNG → return file path
   - Fallback: Windows PrintWindow API if COM Export fails
2. **export_pdf**: COM Plot.PlotToFile or SendCommand "-PLOT"

### Error handling
- No active document → `success: False, error: "No active drawing"`
- Export fails → fallback to PrintWindow

## 7. DwgScanEngine — `services/dwg_scan/engine.py`

### Interface
```python
@dataclass
class DwgEntity:
    type: str
    properties: dict
    layer: str

@dataclass
class DwgContent:
    entities: list[DwgEntity]
    layers: list[str]
    entity_count: int

def scan(path: str) -> DwgContent
def find(path: str, query: dict) -> list[DwgEntity]
def edit(path: str, operations: list[dict]) -> bool
```

### Capabilities
- `scan()`: iterate ModelSpace via COM, extract entity type/properties/layer
- `find()`: filter by layer/type/property key-value
- `edit()`: limited modification (simple operations)

### Error handling
- File not found → raise FileNotFoundError
- COM error → return partial results with error log

## 8. ArtifactManager — `services/artifacts/engine.py`

### Interface
```python
@dataclass
class ArtifactRecord:
    job_id: str
    files: dict[str, str]    # {kind: file_path}
    created_at: str
    metadata: dict

def store(job_id: str, files: dict[str, str], metadata: dict | None = None) -> ArtifactRecord
def get(job_id: str) -> ArtifactRecord | None
def get_all() -> list[ArtifactRecord]
def delete(job_id: str) -> bool
```

### Database
- SQLite at `output/artifacts.db`
- Table `artifacts`: job_id TEXT PK, files_json TEXT, created_at TEXT, metadata_json TEXT
- File storage: `output/{job_id}/{kind}.{ext}`

### File kinds
- `dwg`: AutoCAD drawing
- `preview`: screenshot/export image
- `pdf`: PDF export
- `log`: execution log

## 9. GatewayEngine — `services/gateway/engine.py`

### Interface
```python
@dataclass
class JobStore:
    jobs: dict[str, JobResponse]

class OrchestratorEngine:
    def __init__(self)
    def create_job_workflow(req: CreateJobRequest) -> JobResponse
    def get_job(job_id: str) -> JobResponse | None
    def confirm_job(job_id: str, confirmations: dict) -> JobResponse
```

### Workflow (11 Steps)
```
1. create job     →  job_id, status=created
2. intake.parse   →  parse text, validate files
3. if image/pdf   →  vision.analyze
4. if dwg         →  dwg_scan.analyze
5. cadplan.generate →  build plan from parsed context + vision
6. validation.check  →  4 checks
7. if blocking?   →  return needs_confirmation, wait for user
8. cad_com.execute  →  draw in AutoCAD
9. save drawing     →  SaveAs
10. preview.generate → screenshot
11. artifacts.store  →  collect DWG + preview + log
```

### Error handling
- Any downstream failure → capture as ErrorResponse with detail
- httpx timeout 60s per call
- Workflow state persisted in `JobStore`

## Testing Strategy

### Unit tests (per engine)
```python
# Example: test_intake_engine.py
def test_parse_rectangle_dimensions():
    engine = IntakeEngine()
    ctx = engine.parse("draw a 200x100 rectangle", [], OutputLevel.sketch)
    assert ctx.dimensions["width"] == 200
    assert ctx.dimensions["height"] == 100
    assert ctx.intent == "create"
```

### Integration tests
- Test Gateway → downstream calls (mock httpx)
- Test CAD COM engine with simulated COM responses

## File Change Summary

| File | Action |
|------|--------|
| `services/intake/engine.py` | CREATE |
| `services/intake/__init__.py` | CREATE |
| `services/vision/engine.py` | CREATE |
| `services/vision/__init__.py` | CREATE |
| `services/cadplan/engine.py` | CREATE |
| `services/cadplan/__init__.py` | CREATE |
| `services/validation/engine.py` | CREATE |
| `services/validation/__init__.py` | CREATE |
| `services/cad_com/engine.py` | CREATE |
| `services/cad_com/__init__.py` | CREATE |
| `services/preview/engine.py` | CREATE |
| `services/preview/__init__.py` | CREATE |
| `services/dwg_scan/engine.py` | CREATE |
| `services/dwg_scan/__init__.py` | CREATE |
| `services/artifacts/engine.py` | CREATE |
| `services/artifacts/__init__.py` | CREATE |
| `services/gateway/engine.py` | CREATE |
| `services/gateway/__init__.py` | CREATE |
| `tests/test_intake_engine.py` | CREATE |
| `tests/test_vision_engine.py` | CREATE |
| `tests/test_cadplan_engine.py` | CREATE |
| `tests/test_validation_engine.py` | CREATE |
| `tests/test_gateway_engine.py` | CREATE |