"""Auth router: OAuth2 password login and a whoami endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from auth.dependencies import get_current_principal
from auth.security import Principal, create_access_token, verify_password
from db.database import session_scope
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    role: str


class WhoAmI(BaseModel):
    username: str
    tenant_id: str
    role: str


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """Exchange username/password for a signed JWT (OAuth2 password flow)."""
    with session_scope() as session:
        user = session.query(User).filter(User.username == form.username).first()
        if user is None or not verify_password(form.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal = Principal(
            user_id=user.id,
            username=user.username,
            tenant_id=user.tenant_id,
            role=user.role,
        )

    token = create_access_token(principal)
    return TokenResponse(
        access_token=token, tenant_id=principal.tenant_id, role=principal.role
    )


@router.get("/me", response_model=WhoAmI)
def whoami(principal: Principal = Depends(get_current_principal)) -> WhoAmI:
    """Return the identity encoded in the current bearer token."""
    return WhoAmI(
        username=principal.username,
        tenant_id=principal.tenant_id,
        role=principal.role,
    )
