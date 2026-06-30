"""Authentication and multi-tenancy package (JWT-based).

Exposes the FastAPI auth router, request dependencies that resolve the current
principal + tenant, and a seeder that creates the default tenants/users on first
startup.
"""

from auth.security import (  # noqa: F401
    Principal,
    configure_auth,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
