# Threat Model (starter)

Assets: customer production data, quality history, process know-how, maintenance manuals, identities, audit records.

Key threats:
- data exfiltration through external LLM/API
- overly broad local file access
- prompt injection embedded in documents
- tampered input files
- stolen API keys/tokens
- cross-tenant data exposure if multi-tenancy is later added
- unsafe operational recommendation interpreted as autonomous control

Controls already in prototype:
- external LLM disabled by default
- file extension/size allowlist
- SHA-256 provenance catalog
- OIDC/API-key hooks and roles
- audit events and saved cases
- quantitative analysis separated from LLM explanation
- prompt explicitly disallows unsupported conclusions

Required before production:
- sandbox document parsing
- malware scanning
- immutable/WORM audit target or SIEM export
- secret manager
- full OIDC browser login/reverse proxy integration
- prompt-injection filters and retrieval policy
- network egress control
- penetration testing
