# DeepSeek V4 Flash Integration — FULL Embedded Private Build

This edition routes every LLM-capable semantic task through `deepseek-v4-flash`.

## FULL mode defaults

- Schema reasoning: ON
- JOIN reasoning: ON
- Retrieval query rewrite: ON
- Sample values sent to DeepSeek: ON
- Retrieved document text sent to DeepSeek: ON
- Structured analysis evidence sent to DeepSeek: ON
- Pre-LLM redaction: OFF

The API key is embedded in `.env.local` for this private build.

Specialist numerical and perception engines remain specialist engines: Python statistics, YOLOX, Anomalib, acoustic DSP and OR-Tools are not replaced by the LLM. DeepSeek is used for semantic interpretation, synthesis and explanation.

## Status endpoint

`GET /api/v1/deepseek/status`

should report `deepseek-v4-flash` and all three external-send flags as enabled.
