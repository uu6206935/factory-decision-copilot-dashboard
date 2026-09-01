# Validation report — DeepSeek V4 Flash FULL embedded build

Build: `1.5.2-deepseek-flash-full-embedded-tested-rc2`

Validated locally:

- `deepseek-v4-flash` is hard-locked as the only LLM model.
- DeepSeek base URL is `https://api.deepseek.com`.
- Embedded API key is present (value intentionally not printed in diagnostics).
- FULL flags are enabled: sample values, document text, structured evidence, schema reasoning, join reasoning, query rewrite.
- LLM redaction is disabled for this private FULL build.
- 35/35 regression tests passed with external calls disabled.
- FastAPI root and onboarding routes return HTTP 200.
- DeepSeek status API reports configured Flash + FULL.
- Mocked end-to-end analysis confirmed every LLM request uses Flash, the official chat-completions endpoint, Bearer auth, and FULL payload paths.

Live network test note:

The build environment used to package this ZIP blocks outbound DNS, so a real POST to `api.deepseek.com` could not be completed here. This is an environment network restriction, not an API-key validation result.

For a true live test on Windows, run:

`RUN_DEEPSEEK_FULL_DIAGNOSTICS_WINDOWS.bat`

It validates DNS, authenticated `/models`, non-thinking chat completion, JSON output mode, and thinking mode against the real DeepSeek API.
