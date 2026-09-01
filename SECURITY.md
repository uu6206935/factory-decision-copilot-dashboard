# Security / data handling

This proof of concept defaults to `LLM_MODE=off` and can run without sending data to any external model.

Before using company information:

1. Use only data and environments explicitly approved by the company.
2. Prefer synthetic data with the same schema first.
3. Keep confidential files inside the approved device/network.
4. Do not point `LLM_BASE_URL` at a personal/public AI service unless company policy explicitly permits it.
5. Source folders should be mounted read-only where possible.
6. Keep raw company files unchanged; adapt column names in `app/schema.py`.
7. The audit log under `runtime/audit.jsonl` records questions and selected source names. Treat it according to company policy too.
8. Root-cause scores are investigation priorities, not proof or probability.

The included `sample_data/` is entirely synthetic and contains no Nissan/Toyota/other company data.
