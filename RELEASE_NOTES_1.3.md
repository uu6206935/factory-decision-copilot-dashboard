# Release notes — 1.3.0-adaptive-data-rc1

## Main change

The application no longer requires a fixed "quality + process" bundle. It discovers available inputs and enables only the modules that can run with those inputs.

## New

- Capability Registry (`app/capabilities.py`)
- `GET /api/v1/capabilities`
- automatic UI ON / DATA WAIT states
- adaptive query routing
- quality-only analysis
- equipment-log-only anomaly, drift and threshold-watch mode
- process-only variant / deviation / bottleneck mode
- maintenance-only recurrence analysis
- parts-only traceability
- quality + parts lot correlation without process history
- documents-only RAG mode
- audio-only acoustic capability detection
- empty-data safe startup
- adaptive data-quality semantics: missing optional roles are `skip`, not errors
- dynamic default prompt based on available modules
- documentation and validation script for partial datasets

## Compatibility

The full synthetic demo still performs the original root-cause workflow and keeps the existing APIs/routes. Vision, acoustic, sensor, process, RAG and root-cause modules remain integrated.

## Validation

- 27 automated tests
- default UI/API HTTP smoke test
- equipment-log-only real Uvicorn smoke test
- documents-only real Uvicorn smoke test
