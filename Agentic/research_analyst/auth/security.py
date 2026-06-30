"""Password hashing and JWT token primitives.

Why python-jose + passlib (vs rolling our own / vs OAuth provider):
    * passlib[bcrypt] is the de-facto standard for salted password hashing --
      never store or compare plaintext.
    * python-jose gives signed, expiring, stateless JWTs. Stateless means a
      Celery worker or a second API replica can verify a token with only the
      shared secret -- no session store round-trip. That is exactly the
      horizontally-scalable posture a bank expects.
    * A full OAuth2/OIDC provider (Keycloak/Auth0) is the real-world answer, but
      it is overkill to *run on a laptop*. The token shape here is OIDC-like
      (``sub``, ``tenant``, ``role``, ``exp``) so swapping the issuer later is
      cosmetic.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class _AuthSettings:
    secret_key: str
    algorithm: str
    expire_minutes: int


@dataclass
class Principal:
    """The authenticated caller resolved from a bearer token."""

    user_id: int
    username: str
    tenant_id: str
    role: str


_settings: Optional[_AuthSettings] = None


def configure_auth(config: dict) -> None:
    """Initialise auth settings from config, honouring the secret env var.

    Args:
        config: Full pipeline config; the ``auth`` sub-dict is read here.
    """
    global _settings
    auth_cfg = config.get("auth", {})
    secret_env = auth_cfg.get("secret_env_var", "JWT_SECRET_KEY")
    secret = os.environ.get(secret_env) or auth_cfg.get(
        "default_secret", "dev-only-insecure-change-me"
    )
    _settings = _AuthSettings(
        secret_key=secret,
        algorithm=auth_cfg.get("algorithm", "HS256"),
        expire_minutes=int(auth_cfg.get("access_token_expire_minutes", 480)),
    )


def _require_settings() -> _AuthSettings:
    if _settings is None:
        raise RuntimeError("Auth not configured. Call configure_auth(config) first.")
    return _settings


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of ``plain``."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time check of ``plain`` against a stored bcrypt ``hashed``."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(principal: Principal) -> str:
    """Mint a signed JWT carrying the principal's identity, tenant, and role."""
    settings = _require_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": principal.username,
        "uid": principal.user_id,
        "tenant": principal.tenant_id,
        "role": principal.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[Principal]:
    """Verify a JWT and return the Principal, or ``None`` if invalid/expired."""
    settings = _require_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

    username = payload.get("sub")
    tenant_id = payload.get("tenant")
    if not username or not tenant_id:
        return None

    return Principal(
        user_id=int(payload.get("uid", 0)),
        username=username,
        tenant_id=tenant_id,
        role=payload.get("role", "analyst"),
    )
