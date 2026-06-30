"""FastAPI dependencies for authentication and authorisation.

``get_current_principal`` is attached to every protected endpoint. It extracts
the bearer token, verifies it, and returns a :class:`Principal`. Because the
token already carries ``tenant`` and ``role``, no DB round-trip is required on
the hot path -- the tenant scoping is derived straight from the verified claims.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.security import Principal, decode_token

# tokenUrl is where Swagger's "Authorize" button posts credentials.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_principal(token: str = Depends(oauth2_scheme)) -> Principal:
    """Resolve and validate the caller from the ``Authorization: Bearer`` header."""
    principal = decode_token(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_reviewer(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Allow only reviewers/admins -- guards the human review endpoints."""
    if principal.role not in ("reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer or admin role required.",
        )
    return principal
