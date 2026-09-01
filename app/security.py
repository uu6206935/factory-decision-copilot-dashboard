from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient

from .config import AUTH_MODE, OIDC_AUDIENCE, OIDC_ISSUER, OIDC_JWKS_URL, api_keys

ROLE_LEVEL = {"viewer": 10, "engineer": 20, "admin": 30}

@dataclass
class UserContext:
    subject: str
    role: str
    claims: dict

def _from_api_key(x_api_key: str | None) -> UserContext:
    keys = api_keys()
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")
    role = keys[x_api_key]
    return UserContext(subject=f"apikey:{x_api_key[:6]}", role=role, claims={})

def _from_oidc(auth: str | None) -> UserContext:
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if not OIDC_JWKS_URL:
        raise HTTPException(status_code=500, detail="OIDC_JWKS_URL not configured")
    try:
        signing_key = PyJWKClient(OIDC_JWKS_URL).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, signing_key.key, algorithms=["RS256","ES256"], audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER or None)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"token validation failed: {exc}")
    realm_roles = ((claims.get("realm_access") or {}).get("roles") or [])
    client_roles = (((claims.get("resource_access") or {}).get(OIDC_AUDIENCE) or {}).get("roles") or [])
    roles = set(map(str, realm_roles + client_roles))
    role = "admin" if "admin" in roles else ("engineer" if "engineer" in roles else "viewer")
    return UserContext(subject=str(claims.get("preferred_username") or claims.get("sub") or "oidc-user"), role=role, claims=claims)

def current_user(x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> UserContext:
    if AUTH_MODE == "off":
        return UserContext(subject="local-demo", role="admin", claims={})
    if AUTH_MODE == "api_key":
        return _from_api_key(x_api_key)
    if AUTH_MODE == "oidc":
        return _from_oidc(authorization)
    raise HTTPException(status_code=500, detail="unsupported AUTH_MODE")

def require_role(min_role: str):
    def dep(user: UserContext = Depends(current_user)) -> UserContext:
        if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL.get(min_role, 999):
            raise HTTPException(status_code=403, detail="insufficient role")
        return user
    return dep
