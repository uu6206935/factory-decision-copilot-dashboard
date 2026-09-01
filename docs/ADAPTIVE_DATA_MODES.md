# Adaptive Data Modes

Version 1.3 removes the old assumption that quality + process data must exist before the product is useful.

The application scans the data directory, infers semantic roles, builds a capability registry and enables only the modules whose minimum inputs are present.

## Examples

| Available input | Automatically enabled |
|---|---|
| Quality only | Quality trend / NG composition analysis |
| Process only | Process variants, deviations, bottleneck analysis |
| Equipment logs only | Sensor anomaly health, drift, threshold forecast, maintenance-priority planning |
| Maintenance only | Recurrence / frequent issue analysis |
| Parts only | Product-to-lot traceability |
| Quality + parts | Lot-to-quality association even without process history |
| PDF / DOCX / TXT / Markdown only | Local RAG assistant |
| Camera configuration only | Vision inspection / tracking / OCR / rules |
| WAV baseline + comparison audio | Acoustic condition monitoring |
| Quality + process | Root-cause investigation and stop/continue decision support |
| Quality + process + sensor + maintenance + parts + docs + vision | Full multimodal evidence fusion |

## Design principle

Missing datasets are **not errors**. They are feature gates.

```text
scan files
  -> infer semantic roles
  -> build Capability Registry
  -> enable supported modules
  -> route user query to available analyzers
  -> show missing inputs only as optional upgrades
```

The registry is available at:

```text
GET /api/v1/capabilities
```

The UI uses the same registry for navigation, top-level module status and "data waiting" states.

## Minimum role shapes

- quality: `vehicle_id`, `result`
- process: `vehicle_id`, `equipment_id`
- equipment_logs: `equipment_id`, `timestamp`, plus one or more sensor columns when possible
- maintenance: `equipment_id`, `issue`
- parts: `vehicle_id`, `part_lot`

Column aliases in Japanese/English are normalized in `app/schema.py`.

## Important interpretation rule

When modules run independently, their scores are **prioritization signals**, not causal probabilities. For example, an equipment-log-only deployment can say "EQ-03 has the strongest anomaly signal" but cannot claim "EQ-03 caused this quality defect" until quality/process linkage exists.
