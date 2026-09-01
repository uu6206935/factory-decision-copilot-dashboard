# Factory Decision Copilot — Product One-Pager

## Problem
Quality investigations often require engineers to jump across QMS spreadsheets, process traceability, equipment logs, maintenance history and manuals. Valuable time is spent locating and joining evidence before engineering judgment can even begin.

## Product
Factory Decision Copilot automatically maps heterogeneous manufacturing data, traces affected products through equipment/process history, calculates quantitative associations and anomaly signals, retrieves relevant prior incidents/manuals, and creates an auditable ranked investigation case.

## Why it is not "just RAG"
- deterministic/statistical analysis before LLM explanation;
- product/equipment/lot traceability;
- evidence sources and file hashes;
- human-confirmed investigation workflow;
- optional on-prem operation with LLM completely disabled;
- REST integration instead of forcing engineers into a standalone chatbot.

## Initial buyer
Vehicle/manufacturing quality engineering, production engineering, maintenance engineering, plant digital transformation teams.

## Paid-pilot scope
One plant, one quality-loss family, 3-5 data sources, 1-3 months of history. Measure investigation lead time, repeat-defect recurrence and engineer search time before/after.

## Multimodal expansion in 1.2
The same investigation case can now consume visual inspection events (YOLOX / Anomalib sidecar), equipment telemetry, process-path deviations, machine sound, data drift and maintenance optimization. This is important commercially: the product is not sold as a chatbot or one AI model, but as the evidence-fusion workflow around manufacturing incidents.
