# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-03

### Added
- 9 microservices architecture with FastAPI
  - Gateway (port 8000) - 11-step workflow orchestrator
  - Intake (port 8001) - NLP parsing engine
  - Vision (port 8002) - OpenCV image recognition
  - CADPlan (port 8003) - CAD execution plan generator
  - Validation (port 8004) - 4-type validation engine
  - CAD COM (port 8005) - COM execution bridge
  - Preview (port 8006) - Screenshot/PDF export
  - DWG Scan (port 8007) - DWG file scanner
  - Artifacts (port 8008) - SQLite artifact persistence
- Natural language input support (Chinese/English)
- Image/PDF geometry recognition
- Intelligent CAD planning with 5-layer assignment
- 4-type validation (completeness/consistency/executability/professional)
- 38 unit tests covering all engines
- OpenSpec specifications for all services
- Reasonix Subagent Skill integration

### Security
- Parameterized SQL queries (SQLite)
- yaml.safe_load for secure YAML parsing
- No hardcoded secrets or credentials

### Documentation
- Comprehensive README with architecture diagram
- CONTRIBUTING.md guidelines
- CODE_OF_CONDUCT.md
- OpenSpec design documents
- API endpoint examples

[0.1.0]: https://github.com/daobataotie/cad-direct-control-platform/releases/tag/v0.1.0
