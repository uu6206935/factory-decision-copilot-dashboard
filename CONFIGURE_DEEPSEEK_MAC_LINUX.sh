#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
printf "DeepSeek V4 Flash API key (input hidden): "
IFS= read -r -s KEY
printf "\n"
if [ -z "$KEY" ]; then
  echo "No key entered. DeepSeek remains OFF; local analysis still works."
  exit 0
fi
echo "Metadata-only is the safe default."
echo "Type FULL only for dummy/public data or explicitly approved external DeepSeek API use."
printf "Mode [metadata-only]: "
IFS= read -r MODE
if [ "${MODE^^}" = "FULL" ]; then SAMPLE=true; DOCS=true; STRUCTURED=true; else SAMPLE=false; DOCS=false; STRUCTURED=false; fi
cat > .env.local <<EOF
# Local secret file. Never commit/share this file.
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=$KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_SEND_SAMPLE_VALUES=$SAMPLE
DEEPSEEK_SEND_DOCUMENT_TEXT=$DOCS
DEEPSEEK_SEND_STRUCTURED_EVIDENCE=$STRUCTURED
DEEPSEEK_QUERY_REWRITE=true
DEEPSEEK_JOIN_REASONING=true
DEEPSEEK_SCHEMA_REASONING=true
EOF
chmod 600 .env.local || true
echo "Configured model: deepseek-v4-flash"
