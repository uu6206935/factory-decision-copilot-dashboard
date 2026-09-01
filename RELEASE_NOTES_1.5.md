# Release Notes — 1.5.0 DeepSeek V4 Flash RC1

## One LLM everywhere: DeepSeek V4 Flash

All semantic/text reasoning in this build is routed through exactly one model:

`deepseek-v4-flash`

No Pro routing is present. Retired `deepseek-chat` / `deepseek-reasoner` model ids are not used.

DeepSeek Flash is now used for:

1. low-confidence Excel/CSV column semantic inference;
2. cross-file JOIN semantic validation and suggestions;
3. manufacturing RAG query rewriting;
4. RAG-grounded answers;
5. root-cause hypothesis explanation;
6. next-check / improvement-action wording;
7. automatic analysis after data upload.

Specialized engines remain specialized: YOLOX/Anomalib for vision, Python/statistics/River/PyOD paths for numerical anomaly detection, and OR-Tools for optimization. The LLM orchestrates semantics and explanation rather than replacing deterministic analysis.

## Secret handling

The API key is never bundled into the ZIP or source. Run `CONFIGURE_DEEPSEEK_WINDOWS.bat` and paste the key once. It is stored only in `.env.local`, which is gitignored.

## Data policy

Metadata-only is the safe default. Sample values, retrieved document text and structured factory evidence are OFF for external transmission unless the operator explicitly selects FULL mode during local configuration.

FULL mode is only for dummy/public data or environments where external DeepSeek API use is explicitly approved.

## Verification

- All original Zero-Config/Adaptive/Vision/Enterprise tests retained.
- Added tests asserting every DeepSeek request uses `deepseek-v4-flash`.
- Added test asserting no Pro or retired DeepSeek model id exists in application source.
- Added test asserting `.env.example` contains no API key.
