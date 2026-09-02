from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    """Load a small local env file without adding another dependency.

    Existing process environment variables always win. Quotes around values are
    stripped. The file is intentionally local-only and is gitignored.
    """
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # A malformed local file must never prevent the offline application from starting.
        pass


# Secrets belong here (or in the process environment), never in source control.
_load_env_file(ROOT / ".env.local")

DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "sample_data"))).resolve()
RUNTIME_DIR = Path(os.getenv("RUNTIME_DIR", str(ROOT / "runtime"))).resolve()
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = os.getenv("APP_NAME", "Factory Decision Copilot Enterprise")
APP_VERSION = "1.7.4-japanese-markdown-rc1"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(RUNTIME_DIR / 'factory_copilot.db').as_posix()}")

# DeepSeek V4 Flash is the single LLM used everywhere text reasoning is useful.
# The model id is deliberately fixed in code so this build cannot silently route
# a task to Pro or to an unrelated external model.
DEEPSEEK_ENABLED = os.getenv("DEEPSEEK_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("LLM_API_KEY", ""))
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_TIMEOUT_SECONDS = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
DEEPSEEK_SEND_SAMPLE_VALUES = os.getenv("DEEPSEEK_SEND_SAMPLE_VALUES", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_SEND_DOCUMENT_TEXT = os.getenv("DEEPSEEK_SEND_DOCUMENT_TEXT", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_SEND_STRUCTURED_EVIDENCE = os.getenv("DEEPSEEK_SEND_STRUCTURED_EVIDENCE", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_QUERY_REWRITE = os.getenv("DEEPSEEK_QUERY_REWRITE", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_JOIN_REASONING = os.getenv("DEEPSEEK_JOIN_REASONING", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_SCHEMA_REASONING = os.getenv("DEEPSEEK_SCHEMA_REASONING", "true").lower() in {"1", "true", "yes", "on"}

# Compatibility aliases for existing modules/UI.
LLM_MODE = "deepseek_v4_flash" if DEEPSEEK_ENABLED else "off"
LLM_BASE_URL = DEEPSEEK_BASE_URL
LLM_API_KEY = DEEPSEEK_API_KEY
LLM_MODEL = DEEPSEEK_MODEL
SCHEMA_LLM_ENABLED = DEEPSEEK_SCHEMA_REASONING
SCHEMA_LLM_SAMPLE_VALUES = DEEPSEEK_SEND_SAMPLE_VALUES

# Link-only access gate for the public demo deployment. When set, every page
# and API call requires ?k=<key> once (which then sticks as a cookie); anything
# else gets a 404 so the site looks like it isn't there. Empty locally, so
# local runs are never gated.
ACCESS_KEY = os.getenv("ACCESS_KEY", "").strip()

AUTH_MODE = os.getenv("AUTH_MODE", "off").strip().lower()
API_KEYS_JSON = os.getenv("API_KEYS_JSON", '{"demo-admin-key":"admin","demo-engineer-key":"engineer","demo-viewer-key":"viewer"}')
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "").rstrip("/")
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", f"{OIDC_ISSUER}/protocol/openid-connect/certs" if OIDC_ISSUER else "")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "factory-copilot")

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "local").strip().lower()
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "factory_docs")

FILE_ALLOWLIST = {x.strip().lower() for x in os.getenv("FILE_ALLOWLIST", ".csv,.xlsx,.xlsm,.xls,.json,.pdf,.docx,.txt,.md,.wav,.png,.jpg,.jpeg,.bmp,.webp").split(',') if x.strip()}
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "200"))
REDACT_BEFORE_LLM = os.getenv("REDACT_BEFORE_LLM", "false").lower() in {"1","true","yes","on"}


def api_keys() -> dict[str, str]:
    try:
        obj = json.loads(API_KEYS_JSON)
        return {str(k): str(v) for k, v in obj.items()}
    except Exception:
        return {}

VISION_CONFIG = Path(os.getenv("VISION_CONFIG", str(ROOT / "config" / "cameras.json"))).resolve()
